"""
turso_db.py
===========
Provides two utilities for Turso (libSQL cloud) integration:

1.  get_turso_engine(url, token)
    Returns a SQLAlchemy engine that routes all SQL to Turso via the
    libsql_client HTTP client — no Rust / compiled extensions required.
    Works on Windows (local dev) AND Linux (Render).

2.  sync_local_db_to_turso(local_db_path)
    One-shot migration: reads local SQLite and pushes all schema + rows
    to Turso via the HTTP API (for initial data seeding).
"""

import os
import sqlite3
import json
import requests


# ──────────────────────────────────────────────────────────────────────────────
#  PURE HTTP CLIENT (Replaces libsql_client to avoid asyncio/thread deadlocks)
# ──────────────────────────────────────────────────────────────────────────────

class TursoHttpClient:
    """A synchronous, pure-Python HTTP client for Turso (libsql-experimental)."""

    def __init__(self, url, token):
        self.url = url.replace("libsql://", "https://")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()

    def execute(self, sql, params=None):
        payload = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": sql,
                        "args": list(params) if params else []
                    }
                },
                {"type": "close"}
            ]
        }

        try:
            resp = self.session.post(
                f"{self.url}/v2/pipeline",
                json=payload,
                headers=self.headers,
                timeout=30
            )

            if resp.status_code == 401:
                raise Exception("Turso: Unauthorized — check TURSO_AUTH_TOKEN")
            if resp.status_code not in (200, 201):
                raise Exception(f"Turso HTTP {resp.status_code}: {resp.text[:500]}")

            data = resp.json()

            # top-level error (e.g. bad request format)
            if "error" in data and "results" not in data:
                raise Exception(f"Turso top-level error: {data['error']}")

            results = data.get("results", [])
            if not results:
                return {}  # DDL with no result set

            result_obj = results[0]

            # Pipeline-level error ─ type = "error"
            if result_obj.get("type") == "error":
                err = result_obj.get("error", {})
                raise Exception(
                    f"Turso SQL error [{err.get('code', '?')}]: {err.get('message', str(err))}"
                    f"\n  SQL: {sql[:300]}"
                )

            response = result_obj.get("response", {})
            if "result" in response:
                return response["result"]

            # close/non-execute response — DDL succeeded with no rows
            return {}

        except requests.exceptions.RequestException as e:
            raise Exception(f"Turso network error: {e}")


    def close(self):
        self.session.close()

# ──────────────────────────────────────────────────────────────────────────────
#  DBAPI-COMPATIBLE CURSOR  (wraps TursoHttpClient for SQLAlchemy)
# ──────────────────────────────────────────────────────────────────────────────

class TursoCursor:
    """A minimal PEP-249-compatible cursor that talks to Turso via HTTP."""

    def __init__(self, client):
        self._client   = client
        self.rowcount  = -1
        self.lastrowid = None
        self._rows     = []
        self._pos      = 0
        self.description = None

    def _convert_value(self, libsql_val):
        """Convert libsql typed value back to Python value."""
        if not isinstance(libsql_val, dict):
            return libsql_val
            
        v_type = libsql_val.get("type", "null")
        val = libsql_val.get("value")
        
        if v_type == "null":
            return None
        elif v_type == "integer":
            return int(val)
        elif v_type == "float":
            return float(val)
        elif v_type == "text":
            return str(val)
        elif v_type == "blob":
            import base64
            return base64.b64decode(val)
        return val

    def _run(self, sql, params=None):
        sql = sql.strip()
        if not sql:
            return

        # SQLAlchemy's pysqlite dialect auto-sends SQLite PRAGMAs (e.g.
        # PRAGMA read_uncommitted, PRAGMA journal_mode=WAL) on every connection.
        # Turso's HTTP API rejects these with 404. Silently skip all PRAGMAs.
        if sql.upper().startswith("PRAGMA"):
            self.description = None
            self._rows = []
            self.rowcount = -1
            return

        # Replace standard ? placeholders with indexed/libsql ones or send directly
        # Format params for libsql API:
        # libsql expects args as [{"type": "text", "value": "foo"}, ...]
        
        formatted_args = []
        if params:
            for p in params:
                # bool MUST come before int — bool is a subclass of int in Python
                if isinstance(p, bool):
                    formatted_args.append({"type": "integer", "value": "1" if p else "0"})
                elif p is None:
                    formatted_args.append({"type": "null"})
                elif isinstance(p, int):
                    formatted_args.append({"type": "integer", "value": str(p)})
                elif isinstance(p, float):
                    formatted_args.append({"type": "float", "value": p})
                elif isinstance(p, str):
                    formatted_args.append({"type": "text", "value": p})
                elif isinstance(p, bytes):
                    import base64
                    formatted_args.append({"type": "blob", "value": base64.b64encode(p).decode("ascii")})
                else:
                    formatted_args.append({"type": "text", "value": str(p)})


        try:
            rs = self._client.execute(sql, formatted_args)
            
            # rs has "cols": [{"name": "id", ...}] and "rows": [[{"type": "integer", "value": "1"}]]
            cols = rs.get("cols", [])
            raw_rows = rs.get("rows", [])
            
            if cols:
                self.description = [(col.get("name"), None, None, None, None, None, None)
                                    for col in cols]
                self._rows = [
                    tuple(self._convert_value(cell) for cell in row)
                    for row in raw_rows
                ]
            else:
                self.description = None
                self._rows = []

            self._pos      = 0
            self.rowcount  = rs.get("affected_row_count", len(self._rows) if self._rows else -1)
            self.lastrowid = rs.get("last_insert_rowid", None)
            
        except Exception as e:
            raise Exception(f"[TursoCursor] SQL error: {e}\nSQL: {sql}\nParams: {params}")

    def execute(self, sql, params=None):
        self._run(sql, params)

    def executemany(self, sql, seq_of_params):
        for params in seq_of_params:
            self._run(sql, params)

    def fetchone(self):
        if self._pos < len(self._rows):
            row = self._rows[self._pos]
            self._pos += 1
            return row
        return None

    def fetchall(self):
        rows = self._rows[self._pos:]
        self._pos = len(self._rows)
        return rows

    def fetchmany(self, size=1):
        rows = self._rows[self._pos:self._pos + size]
        self._pos += len(rows)
        return rows

    def close(self):
        pass

    def __iter__(self):
        return iter(self._rows[self._pos:])

    def setinputsizes(self, *args):
        pass

    def setoutputsize(self, *args):
        pass

# ──────────────────────────────────────────────────────────────────────────────
#  DBAPI-COMPATIBLE CONNECTION  (wraps TursoHttpClient for SQLAlchemy)
# ──────────────────────────────────────────────────────────────────────────────

class TursoConnection:
    """A minimal PEP-249-compatible connection backed by TursoHttpClient."""

    def __init__(self, client):
        self._client = client

    def cursor(self):
        return TursoCursor(self._client)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass

    # ── SQLite3 compatibility shims ──────────────────────────────────────────

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql, seq):
        cur = self.cursor()
        cur.executemany(sql, seq)
        return cur

    def create_function(self, *args, **kwargs):
        pass

    def create_aggregate(self, *args, **kwargs):
        pass

    def set_authorizer(self, *args, **kwargs):
        pass

    def set_progress_handler(self, *args, **kwargs):
        pass

    def set_trace_callback(self, *args, **kwargs):
        pass

    def enable_load_extension(self, *args, **kwargs):
        pass

    def load_extension(self, *args, **kwargs):
        pass

    @property
    def in_transaction(self):
        return False

    @property
    def isolation_level(self):
        return None

    @isolation_level.setter
    def isolation_level(self, value):
        pass

    @property
    def row_factory(self):
        return None

    @row_factory.setter
    def row_factory(self, value):
        pass

    @property
    def text_factory(self):
        return str

    @text_factory.setter
    def text_factory(self, value):
        pass

    @property
    def total_changes(self):
        return 0

# ──────────────────────────────────────────────────────────────────────────────
#  PUBLIC: Build a SQLAlchemy connection backed by Turso
# ──────────────────────────────────────────────────────────────────────────────

def make_turso_connection(db_url: str, auth_token: str):
    """
    Creates and returns a raw TursoConnection object backed by pure HTTP.
    Used by SQLAlchemy's `creator` hook in app.py.
    """
    client = TursoHttpClient(db_url, auth_token)
    return TursoConnection(client)




# ──────────────────────────────────────────────────────────────────────────────
#  ONE-SHOT DATA MIGRATION: local SQLite → Turso
# ──────────────────────────────────────────────────────────────────────────────

class _TursoHTTP:
    """Thin helper: POST raw SQL batches to Turso's /v2/pipeline HTTP endpoint."""

    def __init__(self, db_url, auth_token):
        self.url     = db_url.replace("libsql://", "https://")
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type":  "application/json",
        }

    def execute_batch(self, queries):
        payload = {
            "requests": [
                {"type": "execute", "stmt": {"sql": q}}
                for q in queries if q.strip()
            ]
        }
        try:
            resp = requests.post(
                f"{self.url}/v2/pipeline",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            if resp.status_code != 200:
                print(f"[TURSO HTTP ERROR] {resp.status_code}: {resp.text}")
            return resp.json()
        except Exception as e:
            print(f"[TURSO HTTP ERROR] {e}")


def sync_local_db_to_turso(local_db_path="instance/cricshot.db"):
    """
    Reads the entire local SQLite database and pushes its schema and
    rows to Turso via the HTTP API. Use this for initial data seeding.
    """
    url   = os.getenv("TURSO_DATABASE_URL")
    token = os.getenv("TURSO_AUTH_TOKEN")

    if not url or not token:
        print("[TURSO] Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN in .env.")
        return False

    if not os.path.exists(local_db_path):
        print(f"[TURSO] Local DB '{local_db_path}' not found.")
        return False

    print(f"[TURSO] Syncing {local_db_path} → Turso …")
    http = _TursoHTTP(url, token)
    con  = sqlite3.connect(local_db_path)
    cur  = con.cursor()

    # 1. Push schema (CREATE TABLE IF NOT EXISTS …)
    cur.execute(
        "SELECT sql FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    schemas = [row[0].replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
               for row in cur.fetchall() if row[0]]
    print(f"[TURSO] Creating {len(schemas)} tables …")
    http.execute_batch(schemas)

    # 2. Push rows
    cur.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row[0] for row in cur.fetchall()]

    total = 0
    for table in tables:
        cur.execute(f"SELECT * FROM {table}")
        rows = cur.fetchall()
        if not rows:
            continue

        cur.execute(f"PRAGMA table_info({table})")
        cols = [c[1] for c in cur.fetchall()]

        queries = []
        for row in rows:
            vals = []
            for val in row:
                if val is None:
                    vals.append("NULL")
                elif isinstance(val, (int, float)):
                    vals.append(str(val))
                else:
                    safe = str(val).replace("'", "''")
                    vals.append(f"'{safe}'")
            queries.append(
                f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) "
                f"VALUES ({','.join(vals)});"
            )

        print(f"[TURSO] Pushing {len(queries)} rows → {table} …")
        # Send in batches of 100 to avoid payload limits
        for i in range(0, len(queries), 100):
            http.execute_batch(queries[i:i+100])
        total += len(queries)

    con.close()
    print(f"[TURSO] Done — {total} rows across {len(tables)} tables pushed.")
    return True


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    sync_local_db_to_turso()
