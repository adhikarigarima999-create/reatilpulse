"""
04_ab_test_discount_promo.py
-----------------------------
Simulated A/B test: "Would a 10% discount promo increase repeat-purchase
rate enough to justify the margin cost?"

Design:
  - Randomly assign each existing customer to control / treatment
    (simulating a promo that was offered to the treatment group on
    their 2nd purchase).
  - Treatment customers get a synthetic uplift in repeat-purchase
    probability (simulating the promo's real-world effect, since we
    don't have an actual experiment to read from).
  - Check sample balance (are the groups comparable before reading the
    outcome?).
  - Run a two-proportion z-test (statsmodels) for statistical
    significance, then translate the result into a business
    recommendation, including the cost side of the ledger.

Run:
    python 04_ab_test_discount_promo.py
"""
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportions_ztest
from statsmodels.stats.weightstats import ttest_ind

np.random.seed(7)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "retailpulse_raw.db"
LOG_PATH = ROOT / "logs" / "ab_test_result.md"


def load_customers():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM fct_customers", conn)
    conn.close()
    return df


def simulate_experiment(customers: pd.DataFrame):
    df = customers.copy()
    df["group"] = np.random.choice(["control", "treatment"], size=len(df), p=[0.5, 0.5])

    # Baseline repeat-purchase behavior already in the data (is_repeat_customer).
    # Simulate the promo's incremental effect for the treatment group: a
    # +4 percentage point lift in repeat-purchase probability, with noise,
    # standing in for what a real experiment would have measured.
    base_prob = df["is_repeat_customer"].mean()
    lift = 0.04

    def outcome(row):
        p = base_prob + (lift if row["group"] == "treatment" else 0.0)
        p = min(max(p, 0), 1)
        return np.random.binomial(1, p)

    df["repeat_purchase_outcome"] = df.apply(outcome, axis=1)
    return df


def check_sample_balance(df: pd.DataFrame):
    balance = df.groupby("group")["avg_order_value"].agg(["mean", "count"])
    t_stat, p_val, _ = ttest_ind(
        df.loc[df.group == "control", "avg_order_value"].dropna(),
        df.loc[df.group == "treatment", "avg_order_value"].dropna(),
    )
    return balance, t_stat, p_val


def run_significance_test(df: pd.DataFrame):
    counts = df.groupby("group")["repeat_purchase_outcome"].agg(["sum", "count"])
    successes = [counts.loc["treatment", "sum"], counts.loc["control", "sum"]]
    nobs = [counts.loc["treatment", "count"], counts.loc["control", "count"]]
    z_stat, p_val = proportions_ztest(successes, nobs, alternative="larger")
    rate_treatment = successes[0] / nobs[0]
    rate_control = successes[1] / nobs[1]
    return counts, z_stat, p_val, rate_treatment, rate_control


def main():
    customers = load_customers()
    df = simulate_experiment(customers)

    print("=== Sample balance check (avg order value, control vs treatment) ===")
    balance, t_stat, p_bal = check_sample_balance(df)
    print(balance)
    print(f"t-test on avg_order_value: t={t_stat:.3f}, p={p_bal:.3f} "
          f"({'balanced OK' if p_bal > 0.05 else 'WARNING: groups differ pre-treatment'})\n")

    print("=== Repeat-purchase outcome ===")
    counts, z_stat, p_val, rate_t, rate_c = run_significance_test(df)
    print(counts)
    print(f"\nTreatment repeat rate: {rate_t:.4f}")
    print(f"Control repeat rate:   {rate_c:.4f}")
    print(f"Absolute lift:         {(rate_t - rate_c)*100:.2f} pp")
    print(f"z-statistic: {z_stat:.3f}, one-sided p-value: {p_val:.4f}")

    significant = p_val < 0.05
    lift_pp = (rate_t - rate_c) * 100

    # crude cost/benefit translation: 10% discount cost vs LTV uplift
    avg_ltv = df["lifetime_value"].mean()
    incremental_customers = lift_pp / 100 * len(df[df.group == "treatment"])
    incremental_revenue = incremental_customers * avg_ltv
    discount_cost = 0.10 * df.loc[df.group == "treatment", "avg_order_value"].sum()

    recommendation = (
        f"SHIP: the {lift_pp:.2f}pp lift is statistically significant (p={p_val:.4f}), "
        f"and modeled incremental revenue (R${incremental_revenue:,.0f}) exceeds the "
        f"modeled discount cost (R${discount_cost:,.0f})."
        if significant and incremental_revenue > discount_cost else
        f"DO NOT SHIP as-is: either the lift is not statistically significant "
        f"(p={p_val:.4f}) or the modeled discount cost (R${discount_cost:,.0f}) exceeds "
        f"the modeled incremental revenue (R${incremental_revenue:,.0f}). "
        f"Recommend testing a smaller discount or targeting only high-value segments."
    )

    print(f"\n=== Recommendation ===\n{recommendation}")

    LOG_PATH.parent.mkdir(exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("# A/B Test Log — Discount Promo on Repeat Purchase\n\n")
        f.write("## Hypothesis\n")
        f.write("H0: A 10% discount promo has no effect on repeat-purchase rate.\n")
        f.write("H1: A 10% discount promo increases repeat-purchase rate.\n\n")
        f.write("## Sample balance\n")
        f.write(f"- t={t_stat:.3f}, p={p_bal:.3f} on avg_order_value pre-treatment "
                 f"({'balanced' if p_bal > 0.05 else 'imbalanced — flagged'})\n\n")
        f.write("## Result\n")
        f.write(f"- Treatment repeat rate: {rate_t:.4f}\n")
        f.write(f"- Control repeat rate: {rate_c:.4f}\n")
        f.write(f"- Absolute lift: {lift_pp:.2f} percentage points\n")
        f.write(f"- z={z_stat:.3f}, one-sided p={p_val:.4f}\n\n")
        f.write("## Business recommendation\n")
        f.write(recommendation + "\n")
    print(f"\nLogged full result to {LOG_PATH}")


if __name__ == "__main__":
    main()
