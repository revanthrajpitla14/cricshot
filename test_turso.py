from dotenv import load_dotenv
load_dotenv()
from turso_db import make_turso_connection
import os

conn = make_turso_connection(os.getenv('TURSO_DATABASE_URL'), os.getenv('TURSO_AUTH_TOKEN'))
cur = conn.cursor()
cur.execute('SELECT 1')
print('Basic connection:', cur.fetchone())

cur.execute("CREATE TABLE IF NOT EXISTS _healthcheck (id INTEGER PRIMARY KEY)")
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('Tables in DB:', tables)
conn.close()
print('SUCCESS - Turso DB is live and ready!')
