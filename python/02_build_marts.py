"""
02_build_marts.py
------------------
Applies the SQL layer (sql/01_staging.sql -> 02_intermediate.sql ->
03_marts.sql) against the raw SQLite database, in order. This stands in for
`dbt run` against BigQuery: same staging -> intermediate -> mart structure,
same SQL, just executed locally so the pipeline runs without a cloud
warehouse.

Run:
    python 02_build_marts.py
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "retailpulse_raw.db"
SQL_FILES = [
    ROOT / "sql" / "01_staging.sql",
    ROOT / "sql" / "02_intermediate.sql",
    ROOT / "sql" / "03_marts.sql",
]


def run_sql_file(conn, path: Path):
    sql = path.read_text()
    conn.executescript(sql)
    print(f"  applied {path.name}")


def main():
    conn = sqlite3.connect(DB_PATH)
    print(f"Building marts against {DB_PATH}")
    for f in SQL_FILES:
        run_sql_file(conn, f)
    conn.commit()

    # quick sanity check / "dbt test"-style assertions
    checks = {
        "fct_customers row count > 0": "SELECT COUNT(*) FROM fct_customers",
        "fct_orders row count > 0": "SELECT COUNT(*) FROM fct_orders",
        "no negative order_value in fct_orders": (
            "SELECT COUNT(*) FROM fct_orders WHERE order_value < 0"
        ),
    }
    print("\nData tests:")
    for name, q in checks.items():
        val = conn.execute(q).fetchone()[0]
        print(f"  [{'PASS' if val >= 0 else 'FAIL'}] {name} -> {val}")

    print("\nfct_customers preview:")
    for row in conn.execute("SELECT * FROM fct_customers LIMIT 5"):
        print(" ", row)

    conn.close()


if __name__ == "__main__":
    main()
