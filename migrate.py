import sqlite3
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import create_engine
import urllib.parse
from pathlib import Path

# URL encode the password for SQLAlchemy
password = urllib.parse.quote("Teekhi Mrichi")
pg_url = f"postgresql+psycopg2://postgres.bvblceezljunzicpkthd:{password}@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

print("Connecting to Postgres...")
pg_engine = create_engine(pg_url)

sqlite_path = Path("data") / "retailpulse_raw.db"
print(f"Connecting to SQLite: {sqlite_path}")
sqlite_conn = sqlite3.connect(sqlite_path)

# List tables in SQLite
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", sqlite_conn)

for table_name in tables['name']:
    print(f"Copying table {table_name}...")
    df = pd.read_sql(f"SELECT * FROM {table_name}", sqlite_conn)
    df.to_sql(table_name, pg_engine, if_exists='replace', index=False)
    print(f"Copied {len(df)} rows to {table_name}.")

print("Migration complete!")
