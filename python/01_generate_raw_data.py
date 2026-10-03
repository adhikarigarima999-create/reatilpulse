"""
01_generate_raw_data.py
------------------------
RetailPulse — Raw data generator.

Simulates a messy, multi-table e-commerce order dataset shaped like the
public Olist Brazilian E-Commerce dataset (customers, orders, order_items,
payments, reviews, sellers). In the real build this step is replaced by
loading the actual Kaggle CSVs into BigQuery; here it produces an
equivalent local SQLite "raw" layer so the whole pipeline (SQL -> Python ->
stats -> model) is runnable end-to-end without external services.

Deliberately injects realistic messiness:
  - duplicate order rows
  - missing review scores
  - inconsistent state codes / casing
  - a handful of negative / null payment values
  - late deliveries vs. estimated delivery date

Run:
    python 01_generate_raw_data.py
Produces:
    data/retailpulse_raw.db   (SQLite database, "raw" schema tables)
"""
import sqlite3
import random
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)
np.random.seed(42)

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "retailpulse_raw.db"
N_CUSTOMERS = 4000
N_ORDERS = 9000

STATES = ["SP", "RJ", "MG", "RS", "PR", "BA", "SC", "GO", "PE", "CE"]
CATEGORIES = [
    "housewares", "electronics", "beauty", "sports_leisure", "furniture",
    "toys", "computers_accessories", "watches_gifts", "bed_bath_table",
    "auto",
]
PAYMENT_TYPES = ["credit_card", "boleto", "voucher", "debit_card"]


def rand_date(start, end):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def build_customers(conn):
    rows = []
    for i in range(1, N_CUSTOMERS + 1):
        state = random.choice(STATES)
        # inject inconsistent casing to simulate messy source data
        if random.random() < 0.05:
            state = state.lower()
        rows.append((f"CUST{i:05d}", f"city_{random.randint(1, 120)}", state))
    conn.executemany(
        "INSERT INTO customers (customer_id, city, state) VALUES (?,?,?)", rows
    )


def build_orders_and_children(conn):
    order_rows, item_rows, payment_rows, review_rows = [], [], [], []
    start = datetime(2024, 1, 1)
    end = datetime(2025, 12, 31)

    customer_ids = [f"CUST{i:05d}" for i in range(1, N_CUSTOMERS + 1)]
    # give ~28% of customers more than one order (repeat purchasers)
    repeat_customers = set(random.sample(customer_ids, int(N_CUSTOMERS * 0.28)))

    order_counter = 1
    assigned_orders = 0
    while assigned_orders < N_ORDERS:
        cust = random.choice(customer_ids)
        n_orders_for_cust = 1
        if cust in repeat_customers:
            n_orders_for_cust = np.random.poisson(2.2) + 1

        for _ in range(n_orders_for_cust):
            if assigned_orders >= N_ORDERS:
                break
            order_id = f"ORD{order_counter:06d}"
            order_counter += 1
            assigned_orders += 1

            purchase_ts = rand_date(start, end)
            approved_ts = purchase_ts + timedelta(hours=random.randint(1, 48))
            est_delivery = purchase_ts + timedelta(days=random.randint(7, 20))
            # 20% chance of a late delivery
            actual_delivery_days = random.randint(3, 18)
            if random.random() < 0.2:
                actual_delivery_days = random.randint(21, 35)
            delivered_ts = purchase_ts + timedelta(days=actual_delivery_days)

            status = "delivered" if random.random() > 0.03 else random.choice(
                ["canceled", "shipped", "processing"]
            )

            order_rows.append(
                (order_id, cust, status, purchase_ts.isoformat(),
                 approved_ts.isoformat(), est_delivery.isoformat(),
                 delivered_ts.isoformat() if status == "delivered" else None)
            )

            # inject ~1.5% duplicate order rows (messy source data)
            if random.random() < 0.015:
                order_rows.append(order_rows[-1])

            n_items = random.randint(1, 4)
            item_total = 0.0
            for item_no in range(1, n_items + 1):
                price = round(random.uniform(15, 800), 2)
                freight = round(price * random.uniform(0.03, 0.15), 2)
                item_total += price + freight
                item_rows.append(
                    (order_id, item_no, f"PROD{random.randint(1, 3000):05d}",
                     f"SELLER{random.randint(1, 300):04d}",
                     random.choice(CATEGORIES), price, freight)
                )

            pay_installments = random.choice([1, 1, 1, 2, 3, 6, 10])
            pay_value = round(item_total, 2)
            # inject a few bad values
            if random.random() < 0.01:
                pay_value = -abs(pay_value)  # bad negative payment
            if random.random() < 0.01:
                pay_value = None
            payment_rows.append(
                (order_id, random.choice(PAYMENT_TYPES), pay_installments, pay_value)
            )

            if status == "delivered" and random.random() < 0.92:
                # slightly worse review scores when delivery was late
                late = actual_delivery_days > (est_delivery - purchase_ts).days
                score = np.random.choice(
                    [1, 2, 3, 4, 5],
                    p=[0.10, 0.10, 0.15, 0.25, 0.40] if late else [0.03, 0.05, 0.12, 0.30, 0.50]
                )
                review_rows.append((order_id, int(score)))
            # ~8% of delivered orders have no review at all (missingness)

    conn.executemany(
        """INSERT INTO orders (order_id, customer_id, order_status, purchase_ts,
           approved_ts, estimated_delivery_ts, delivered_ts)
           VALUES (?,?,?,?,?,?,?)""",
        order_rows,
    )
    conn.executemany(
        """INSERT INTO order_items (order_id, item_no, product_id, seller_id,
           category, price, freight_value) VALUES (?,?,?,?,?,?,?)""",
        item_rows,
    )
    conn.executemany(
        """INSERT INTO payments (order_id, payment_type, installments, payment_value)
           VALUES (?,?,?,?)""",
        payment_rows,
    )
    conn.executemany(
        "INSERT INTO reviews (order_id, review_score) VALUES (?,?)", review_rows
    )


def main():
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE customers (
            customer_id TEXT, city TEXT, state TEXT
        );
        CREATE TABLE orders (
            order_id TEXT, customer_id TEXT, order_status TEXT,
            purchase_ts TEXT, approved_ts TEXT,
            estimated_delivery_ts TEXT, delivered_ts TEXT
        );
        CREATE TABLE order_items (
            order_id TEXT, item_no INTEGER, product_id TEXT, seller_id TEXT,
            category TEXT, price REAL, freight_value REAL
        );
        CREATE TABLE payments (
            order_id TEXT, payment_type TEXT, installments INTEGER, payment_value REAL
        );
        CREATE TABLE reviews (
            order_id TEXT, review_score INTEGER
        );
        """
    )
    build_customers(conn)
    build_orders_and_children(conn)
    conn.commit()

    counts = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ["customers", "orders", "order_items", "payments", "reviews"]
    }
    conn.close()
    print(f"Raw SQLite DB written to: {DB_PATH}")
    for t, c in counts.items():
        print(f"  {t:<15} {c:>7} rows")


if __name__ == "__main__":
    main()
