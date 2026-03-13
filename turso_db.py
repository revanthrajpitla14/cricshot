import os
import sqlite3
import requests
import json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

class TursoEngine:
    """
    A lightweight wrapper that proxies standard SQLite execution 
    calls to Turso's hrana HTTP API when running on the cloud/Render.
    Leaves the local SQLite fully functional.
    """
    def __init__(self, db_url, auth_token):
        self.db_url = db_url.replace("libsql://", "https://")
        self.auth_token = auth_token
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }

    def execute_batch(self, queries):
        if not self.db_url or not self.auth_token:
            print("[TURSO] No DB URL or Auth Token provided.")
            return

        payload = {
            "requests": [
                {"type": "execute", "stmt": {"sql": q}} 
                for q in queries if q.strip()
            ]
        }
        
        try:
            resp = requests.post(f"{self.db_url}/v2/pipeline", json=payload, headers=self.headers)
            if resp.status_code != 200:
                print(f"[TURSO ERROR] {resp.text}")
            return resp.json()
        except Exception as e:
            print(f"[TURSO HTTP ERROR] {e}")


def sync_local_db_to_turso(local_db_path="instance/cricshot.db"):
    """
    Reads the entire local SQLite database and pushes its schema and rows to Turso.
    """
    url = os.getenv("TURSO_DATABASE_URL")
    token = os.getenv("TURSO_AUTH_TOKEN")
    
    if not url or not token:
        print("[TURSO] Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN in .env.")
        return False
        
    print(f"[TURSO] Syncing local {local_db_path} to Turso...")
    turso = TursoEngine(url, token)
    
    # Connect local SQLite
    if not os.path.exists(local_db_path):
        print(f"[TURSO] Local DB '{local_db_path}' not found.")
        return False
        
    con = sqlite3.connect(local_db_path)
    cur = con.cursor()
    
    # 1. Grab all schemas
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    schemas = [row[0] for row in cur.fetchall() if row[0]]
    
    print(f"[TURSO] Creating {len(schemas)} tables on remote...")
    turso.execute_batch(schemas)
    
    # 2. Grab all rows
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cur.fetchall()]
    
    total_inserts = 0
    for table in tables:
        cur.execute(f"SELECT * FROM {table}")
        rows = cur.fetchall()
        
        if not rows:
            continue
            
        cur.execute(f"PRAGMA table_info({table})")
        cols = [c[1] for c in cur.fetchall()]
        
        queries = []
        for row in rows:
            # Format row data safely for SQLite
            vals = []
            for val in row:
                if val is None:
                    vals.append("NULL")
                elif isinstance(val, (int, float)):
                    vals.append(str(val))
                else:
                    # Escape single quotes
                    safe_val = str(val).replace("'", "''")
                    vals.append(f"'{safe_val}'")
                    
            q = f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join(vals)});"
            queries.append(q)
            
        print(f"[TURSO] Pushing {len(queries)} rows to {table}...")
        turso.execute_batch(queries)
        total_inserts += len(queries)
        
    print(f"[TURSO] Successfully synced {total_inserts} rows across {len(tables)} tables to Turso.")
    return True

if __name__ == "__main__":
    # If run directly, read .env and push local sqlite up to Turso
    from dotenv import load_dotenv
    load_dotenv()
    sync_local_db_to_turso()
