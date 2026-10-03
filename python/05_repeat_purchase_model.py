"""
05_repeat_purchase_model.py
-----------------------------
Logistic regression predicting whether a customer becomes a repeat
purchaser, using signals available after their FIRST order only (so the
model is usable at the moment that matters — right after order #1, not in
hindsight).

Reported in business terms rather than chasing accuracy: which factors
matter, and what a false positive/negative costs the business.

Run:
    python 05_repeat_purchase_model.py
"""
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix
)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "retailpulse_raw.db"


def load_first_order_features():
    conn = sqlite3.connect(DB_PATH)
    q = """
    SELECT
        fo.order_id,
        fo.customer_id,
        fo.order_value,
        fo.was_late,
        fo.review_score,
        fo.payment_type,
        fo.installments,
        fc.state,
        fc.is_repeat_customer
    FROM fct_orders fo
    JOIN fct_customers fc ON fc.customer_id = fo.customer_id
    WHERE fo.order_seq_num = 1
    """
    df = pd.read_sql(q, conn)
    conn.close()
    return df


def main():
    df = load_first_order_features()
    df["review_score"] = df["review_score"].fillna(df["review_score"].median())
    df["order_value"] = df["order_value"].fillna(df["order_value"].median())
    df["installments"] = df["installments"].fillna(1)
    df["was_late"] = df["was_late"].fillna(0)
    df["payment_type"] = df["payment_type"].fillna("unknown")
    df["is_repeat_customer"] = df["is_repeat_customer"].fillna(0)

    features_num = ["order_value", "was_late", "installments", "review_score"]
    features_cat = ["payment_type"]

    X = pd.get_dummies(df[features_num + features_cat], columns=features_cat, drop_first=True)
    y = df["is_repeat_customer"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_train_s, y_train)

    y_pred = model.predict(X_test_s)
    y_proba = model.predict_proba(X_test_s)[:, 1]

    print("=== Model performance ===")
    print(classification_report(y_test, y_pred, target_names=["not_repeat", "repeat"]))
    auc = roc_auc_score(y_test, y_proba)
    print(f"ROC-AUC: {auc:.3f}")

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    print(f"\nConfusion matrix:\n{cm}")
    print(f"  True negatives (correctly flagged as one-time):  {tn}")
    print(f"  False positives (predicted repeat, wasn't):      {fp}")
    print(f"  False negatives (missed a real repeat customer): {fn}")
    print(f"  True positives (correctly flagged as repeat):    {tp}")

    print("\n=== Business interpretation ===")
    coefs = pd.Series(model.coef_[0], index=X.columns).sort_values(key=abs, ascending=False)
    print("Standardized coefficients (larger |value| = stronger driver):")
    print(coefs.to_string())

    print(
        "\nCost framing:\n"
        "  - A false negative (missing a likely repeat customer) means we skip a\n"
        "    retention touch (email, loyalty nudge) on someone who would have come\n"
        "    back anyway — low cost, mostly a missed upsell opportunity.\n"
        "  - A false positive (flagging a one-time buyer as likely-repeat) means we\n"
        "    spend a retention-campaign dollar on someone who churns anyway — the\n"
        "    model is tuned with class_weight='balanced' to avoid under-predicting\n"
        "    the minority (repeat) class, accepting more false positives in exchange\n"
        "    for catching more true repeat customers, since a wasted email is far\n"
        "    cheaper than a missed retention opportunity."
    )

    top_driver = coefs.index[0]
    direction = "increases" if coefs.iloc[0] > 0 else "decreases"
    print(
        f"\nHeadline finding: '{top_driver}' is the strongest single driver and "
        f"{direction} the odds of becoming a repeat customer, holding other factors "
        f"constant."
    )


if __name__ == "__main__":
    main()
