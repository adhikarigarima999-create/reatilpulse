"""Run the Postgres SQL transforms on Supabase to create views."""
from sqlalchemy import create_engine, text
import urllib.parse
from pathlib import Path

password = urllib.parse.quote("Teekhi Mrichi")
pg_url = f"postgresql+psycopg2://postgres.bvblceezljunzicpkthd:{password}@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

engine = create_engine(pg_url)

sql_dir = Path("sql")
sql_files = [
    sql_dir / "pg_01_staging.sql",
    sql_dir / "pg_02_intermediate.sql",
    sql_dir / "pg_03_marts.sql",
]

with engine.connect() as conn:
    for f in sql_files:
        print(f"Running {f.name}...")
        sql_text = f.read_text()
        # Split by semicolons and execute each statement
        for stmt in sql_text.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                conn.execute(text(stmt))
        conn.commit()
        print(f"  Done.")

# Quick test
import pandas as pd
with engine.connect() as conn:
    df = pd.read_sql("SELECT COUNT(*) as cnt FROM fct_orders", conn)
    print(f"\nfct_orders row count: {df['cnt'].iloc[0]}")
    df2 = pd.read_sql("SELECT COUNT(*) as cnt FROM fct_customers", conn)
    print(f"fct_customers row count: {df2['cnt'].iloc[0]}")

print("\nAll Postgres views created successfully!")
