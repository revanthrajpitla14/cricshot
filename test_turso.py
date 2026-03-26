import os
from dotenv import load_dotenv
import libsql_client

load_dotenv()

url = os.getenv("TURSO_DATABASE_URL", "").replace("libsql://", "https://")
token = os.getenv("TURSO_AUTH_TOKEN")

print(f"Connecting to: {url}")

try:
    client = libsql_client.create_client_sync(url=url, auth_token=token)
    result = client.execute("SELECT 1")
    print("SUCCESS: Connection established!")
    print(result)
except Exception as e:
    print(f"FAILED: {e}")
