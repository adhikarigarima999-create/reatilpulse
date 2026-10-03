"""
01_load_kaggle_data.py
-----------------------
Loads the real Kaggle Olist Brazilian E-Commerce dataset directly into
SQLite (data/retailpulse_raw.db) matching the exact schema expected by the
staging, intermediate, and mart SQL layers.
"""
import sqlite3
from pathlib import Path
import pandas as pd
import kagglehub

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "retailpulse_raw.db"

def load_kaggle():
    print("Fetching Kaggle Olist Brazilian E-Commerce dataset via kagglehub...")
    dataset_dir = Path(kagglehub.dataset_download("olistbr/brazilian-ecommerce"))
    print(f"Loaded from cache/download: {dataset_dir}")

    # 1. Customers
    print("Processing customers...")
    df_cust = pd.read_csv(dataset_dir / "olist_customers_dataset.csv")
    # In Olist, customer_id is an order-level key, but customer_unique_id identifies the individual person.
    # We map customer_unique_id -> customer_id so that repeat orders correctly link to the same customer.
    cust_map = df_cust[['customer_id', 'customer_unique_id']].drop_duplicates()

    customers_table = (
        df_cust[['customer_unique_id', 'customer_city', 'customer_state']]
        .drop_duplicates(subset=['customer_unique_id'])
        .rename(columns={
            'customer_unique_id': 'customer_id',
            'customer_city': 'city',
            'customer_state': 'state'
        })
    )

    # 2. Orders
    print("Processing orders...")
    df_orders = pd.read_csv(dataset_dir / "olist_orders_dataset.csv")
    df_orders = df_orders.merge(cust_map, on='customer_id', how='inner')
    orders_table = pd.DataFrame({
        'order_id': df_orders['order_id'],
        'customer_id': df_orders['customer_unique_id'],
        'order_status': df_orders['order_status'],
        'purchase_ts': df_orders['order_purchase_timestamp'],
        'approved_ts': df_orders['order_approved_at'],
        'estimated_delivery_ts': df_orders['order_estimated_delivery_date'],
        'delivered_ts': df_orders['order_delivered_customer_date']
    })

    # 3. Order items + Products translation
    print("Processing order items & categories...")
    df_items = pd.read_csv(dataset_dir / "olist_order_items_dataset.csv")
    df_prod = pd.read_csv(dataset_dir / "olist_products_dataset.csv")
    df_trans = pd.read_csv(dataset_dir / "product_category_name_translation.csv")

    df_prod = df_prod.merge(df_trans, on='product_category_name', how='left')
    cat_series = df_prod['product_category_name_english'].fillna(df_prod['product_category_name']).fillna('other')
    prod_cat_map = dict(zip(df_prod['product_id'], cat_series))

    df_items['category'] = df_items['product_id'].map(prod_cat_map).fillna('other')
    order_items_table = pd.DataFrame({
        'order_id': df_items['order_id'],
        'item_no': df_items['order_item_id'],
        'product_id': df_items['product_id'],
        'seller_id': df_items['seller_id'],
        'category': df_items['category'],
        'price': df_items['price'],
        'freight_value': df_items['freight_value']
    })

    # 4. Payments
    print("Processing payments...")
    df_pay = pd.read_csv(dataset_dir / "olist_order_payments_dataset.csv")
    payments_table = pd.DataFrame({
        'order_id': df_pay['order_id'],
        'payment_type': df_pay['payment_type'],
        'installments': df_pay['payment_installments'],
        'payment_value': df_pay['payment_value']
    })

    # 5. Reviews
    print("Processing reviews...")
    df_rev = pd.read_csv(dataset_dir / "olist_order_reviews_dataset.csv")
    reviews_table = pd.DataFrame({
        'order_id': df_rev['order_id'],
        'review_score': df_rev['review_score']
    })

    # Connect to SQLite
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    print("Writing real Olist tables to SQLite...")
    customers_table.to_sql("customers", conn, if_exists="replace", index=False)
    orders_table.to_sql("orders", conn, if_exists="replace", index=False)
    order_items_table.to_sql("order_items", conn, if_exists="replace", index=False)
    payments_table.to_sql("payments", conn, if_exists="replace", index=False)
    reviews_table.to_sql("reviews", conn, if_exists="replace", index=False)

    print("Creating indexes on key columns for fast query execution...")
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_customers_id ON customers(customer_id);
        CREATE INDEX IF NOT EXISTS idx_orders_id ON orders(order_id);
        CREATE INDEX IF NOT EXISTS idx_orders_cust ON orders(customer_id);
        CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id);
        CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
        CREATE INDEX IF NOT EXISTS idx_reviews_order ON reviews(order_id);
    """)

    counts = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ["customers", "orders", "order_items", "payments", "reviews"]
    }
    conn.close()

    print(f"\nReal Kaggle Olist data successfully written to: {DB_PATH}")
    for t, c in counts.items():
        print(f"  {t:<15} {c:>8} rows")

if __name__ == "__main__":
    load_kaggle()
