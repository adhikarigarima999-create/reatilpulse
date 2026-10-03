"""
03_eda.py
---------
Exploratory data analysis on the fct_customers / fct_orders marts.
Produces the charts referenced in the case-study README.

Run:
    python 03_eda.py
Produces (in ../charts/):
    delivery_lateness_vs_review.png
    repeat_purchase_rate_by_state.png
    order_value_distribution.png
"""
import sqlite3
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "retailpulse_raw.db"
CHART_DIR = ROOT / "charts"
CHART_DIR.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid")


def load():
    conn = sqlite3.connect(DB_PATH)
    orders = pd.read_sql("SELECT * FROM fct_orders", conn)
    customers = pd.read_sql("SELECT * FROM fct_customers", conn)
    conn.close()
    return orders, customers


def chart_lateness_vs_review(orders: pd.DataFrame):
    df = orders.dropna(subset=["review_score"]).copy()
    df["delivery"] = df["was_late"].map({1: "Late", 0: "On time"})
    summary = df.groupby("delivery")["review_score"].mean().reset_index()

    plt.figure(figsize=(6, 4.5))
    ax = sns.barplot(data=summary, x="delivery", y="review_score", palette="Blues_d")
    ax.set_title("Average Review Score: Late vs. On-Time Delivery")
    ax.set_xlabel("")
    ax.set_ylabel("Average review score (1-5)")
    ax.set_ylim(0, 5)
    for p in ax.patches:
        ax.annotate(f"{p.get_height():.2f}", (p.get_x() + p.get_width() / 2, p.get_height()),
                    ha="center", va="bottom")
    plt.tight_layout()
    plt.savefig(CHART_DIR / "delivery_lateness_vs_review.png", dpi=130)
    plt.close()
    print("saved delivery_lateness_vs_review.png")
    print(summary.to_string(index=False))


def chart_repeat_rate_by_state(customers: pd.DataFrame):
    summary = (
        customers.groupby("state")["is_repeat_customer"]
        .mean()
        .mul(100)
        .sort_values(ascending=False)
        .reset_index()
    )
    plt.figure(figsize=(8, 5))
    ax = sns.barplot(data=summary, x="state", y="is_repeat_customer", palette="viridis")
    ax.set_title("Repeat-Customer Rate by State")
    ax.set_xlabel("State")
    ax.set_ylabel("Repeat-purchase rate (%)")
    plt.tight_layout()
    plt.savefig(CHART_DIR / "repeat_purchase_rate_by_state.png", dpi=130)
    plt.close()
    print("saved repeat_purchase_rate_by_state.png")


def chart_order_value_distribution(orders: pd.DataFrame):
    plt.figure(figsize=(7, 4.5))
    ax = sns.histplot(orders["order_value"], bins=40, kde=True, color="steelblue")
    ax.set_title("Order Value Distribution")
    ax.set_xlabel("Order value (R$)")
    plt.tight_layout()
    plt.savefig(CHART_DIR / "order_value_distribution.png", dpi=130)
    plt.close()
    print("saved order_value_distribution.png")


def main():
    orders, customers = load()
    print(f"Loaded {len(orders)} orders, {len(customers)} customers\n")
    chart_lateness_vs_review(orders)
    chart_repeat_rate_by_state(customers)
    chart_order_value_distribution(orders)


if __name__ == "__main__":
    main()
