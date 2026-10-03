# RetailPulse — E-Commerce Customer Analytics & Experimentation

**Role:** Data Analyst | **Domain:** Retail / e-commerce
**Question:** Which customer segments and delivery conditions predict repeat
purchase, and would a proposed discount promotion actually move the needle?

This is one of the two projects from the portfolio plan, built out as a
runnable base: real multi-table structure, a staging → intermediate → mart
SQL layer, exploratory analysis, a hypothesis test, and a predictive model —
plus the documentation and AI-verification log a hiring manager would
actually want to see.

---

## 1. How it works (architecture)

```
┌─────────────────┐     ┌──────────────────────────────────────┐     ┌──────────────┐
│  01_generate_    │     │            SQL LAYER (sql/)           │     │   Python     │
│  raw_data.py     │────▶│  01_staging.sql                       │────▶│  analysis    │
│                  │     │    → 1:1 cleaned views                │     │  layer       │
│  writes raw      │     │  02_intermediate.sql                  │     │              │
│  SQLite tables:  │     │    → joins, window functions,         │     │ 03_eda.py    │
│  customers,      │     │      delivery-lateness logic          │     │ 04_ab_test.. │
│  orders,         │     │  03_marts.sql                         │     │ 05_model.py  │
│  order_items,    │     │    → fct_customers, fct_orders         │     │              │
│  payments,       │     │      (analysis-ready, one row per     │     │              │
│  reviews         │     │       customer / order)               │     │              │
└─────────────────┘     └──────────────────────────────────────┘     └──────────────┘
```

In the full production build (see the portfolio plan) this same SQL runs as
a **dbt project on BigQuery**, orchestrated by an **Airflow DAG**
(extract → load → `dbt run` → `dbt test`), with a **Tableau Public**
dashboard on top. Here, the identical staging/intermediate/mart SQL is
executed against a local **SQLite** database so the whole pipeline —
generation, transformation, analysis, testing, modeling — runs end-to-end
without needing cloud credentials. Swapping the SQLite connection for a
BigQuery client and adding a `dbt_project.yml` around the `sql/` files is
the only change needed to make this the real cloud build; the SQL itself
doesn't change.

### Why synthetic data instead of the real Olist dataset
The real build uses the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
(Kaggle). This base was generated in an environment without access to
Kaggle, so `01_generate_raw_data.py` produces a synthetic dataset with the
**same schema, the same kinds of messiness** (duplicate rows, missing
reviews, inconsistent state casing, bad payment values, late deliveries),
and the **same statistical relationships the case study is built around**
(late delivery → lower review score; some customers are repeat buyers,
most aren't). Dropping in the real Olist CSVs only requires rewriting
`01_generate_raw_data.py` as a CSV loader — every SQL and Python file
downstream is unchanged.

---

## 2. Repo layout

```
retailpulse/
├── README.md                       ← this file
├── requirements.txt
├── run_pipeline.sh                 ← runs everything in order
├── data/
│   └── retailpulse_raw.db          ← generated (gitignored in a real repo)
├── sql/
│   ├── 01_staging.sql              ← stg_* views
│   ├── 02_intermediate.sql         ← int_* views (joins + window fns)
│   └── 03_marts.sql                ← fct_customers, fct_orders
├── python/
│   ├── 01_generate_raw_data.py     ← synthetic raw data generator
│   ├── 02_build_marts.py           ← applies sql/ to the local warehouse + data tests
│   ├── 03_eda.py                   ← exploratory charts (seaborn/matplotlib)
│   ├── 04_ab_test_discount_promo.py← hypothesis test (statsmodels)
│   └── 05_repeat_purchase_model.py ← logistic regression (scikit-learn)
├── charts/                         ← PNGs written by 03_eda.py
└── logs/
    ├── ab_test_result.md           ← written by 04_ab_test_discount_promo.py
    └── ai_verification_log.md      ← documented AI-vs-manual QA corrections
```

## 3. How to run it

```bash
pip install -r requirements.txt
./run_pipeline.sh
```

This regenerates the raw data, rebuilds every SQL view, re-runs the EDA
(charts land in `charts/`), re-runs the A/B test (log lands in
`logs/ab_test_result.md`), and retrains the model — in that order, since
each stage depends on the one before it. Each script can also be run
individually from `python/` once the DB exists.

---

## 4. Method

1. **Staging** (`01_staging.sql`) — one view per raw table. Standardizes
   `state` casing, de-duplicates exact-duplicate order rows, casts types.
   No business logic.
2. **Intermediate** (`02_intermediate.sql`) — joins order items into
   per-order economics with a `SUM(...)` CTE, computes delivery lateness
   with a `julianday()` date-diff, and uses `ROW_NUMBER()` / `LAG()` /
   `COUNT() OVER (PARTITION BY customer_id ...)` window functions to
   sequence each customer's orders and flag repeats.
3. **Marts** (`03_marts.sql`) — `fct_customers` (customer grain: lifetime
   value, repeat flag, % orders late, avg review) and `fct_orders` (order
   grain, used by the A/B test and the model).
4. **EDA** (`03_eda.py`) — reads the marts with pandas, charts delivery
   lateness vs. review score, repeat-purchase rate by state, and order
   value distribution.
5. **A/B test** (`04_ab_test_discount_promo.py`) — simulates a 10%
   discount promo experiment: random assignment, a sample-balance check
   (t-test on pre-treatment order value) before trusting the outcome, then
   a two-proportion z-test (`statsmodels`) on repeat-purchase rate.
   Translates the result into a ship/no-ship call by comparing modeled
   incremental revenue against the modeled discount cost — not just
   "is p < 0.05."
6. **Model** (`05_repeat_purchase_model.py`) — logistic regression
   predicting repeat purchase using **only first-order signals**
   (order value, delivery lateness, review score, payment type,
   installments), reported as standardized coefficients and a
   business-cost framing of false positives vs. false negatives, not just
   an accuracy number.

## 5. Findings (from this synthetic run — see `logs/` for the live numbers)

- Orders delivered **late average a 3.75 review score vs. 4.20 for
  on-time deliveries** — delivery reliability is a visible lever on
  satisfaction, not just an operations metric.
- The simulated discount promo produced a **statistically significant
  ~4.3 percentage point lift** in repeat-purchase rate (p ≈ 0.007), and
  the modeled incremental revenue exceeded the modeled discount cost —
  recommendation: **ship**, but re-validate on a real experiment before
  committing, since the effect size here was injected for the simulation.
- The repeat-purchase model's strongest standardized driver was
  **first-order review score**; overall discriminative power was modest
  (ROC-AUC ≈ 0.54), which is an honest finding for synthetic data with
  only mild built-in signal — the real Olist dataset should show cleaner
  structure once behavioral and product-category features are added.

## 6. What I'd do with more time / on the real dataset

- Swap in the actual Olist CSVs and re-run unchanged.
- Add product-category and seller-level features to the model — category
  mix is a likely stronger churn driver than payment mechanics.
- Stand up the Airflow DAG and dbt project for real against BigQuery
  Sandbox, and publish the Tableau Public dashboard for a "VP of
  Retention" persona.
- Replace the simulated A/B outcome with a genuine holdout-based
  experiment once real promo data exists.
