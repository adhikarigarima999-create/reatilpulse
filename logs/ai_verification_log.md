# AI-Assisted Development — Verification Log

This project was built with AI assistance (Claude) for scaffolding SQL,
Python, and the modeling code. Per the "AI-assisted analysis + verification"
skill item, every place the AI-generated output was wrong, imprecise, or
needed a manual correction is logged here rather than silently fixed. This
log is itself a portfolio artifact, not an afterthought.

## 1. Date-diff logic in `int_order_economics`
**AI first draft:** used `DATEDIFF(delivered_ts, estimated_delivery_ts)`
(SQL Server / Snowflake syntax).
**Problem:** this build runs on SQLite (standing in locally for
BigQuery), which has no `DATEDIFF` function.
**Fix:** rewrote using `julianday(delivered_ts) - julianday(estimated_delivery_ts)`,
cast to `INTEGER`. Verified against 10 hand-picked orders by computing the
day difference manually in Python and comparing to the SQL output — matched
in all 10 cases.
**Takeaway:** always confirm the target SQL dialect before accepting
AI-generated date arithmetic; it defaults to whichever dialect is most
common in training data, not necessarily the one in use.

## 2. Silent NULL handling in the payments staging model
**AI first draft:** the `stg_payments` view simply filtered out rows where
`payment_value IS NULL OR payment_value < 0`.
**Problem:** this silently drops bad data with no audit trail — if the
downstream mart's revenue numbers looked low, there would be no way to
tell how much was discarded or why.
**Fix:** changed to a `payment_quality_flag` column (`missing_value` /
`negative_value` / `ok`) so bad rows are visible and countable downstream
instead of vanishing. Confirmed the flag counts sum to the same total row
count as the raw `payments` table.

## 3. A/B test — comparing the wrong denominator
**AI first draft:** the significance test initially computed the repeat
rate as `treatment_repeat_count / total_customers` (using the full
dataset's row count as the denominator for both groups) instead of each
group's own count.
**Problem:** this understates both rates and, worse, can bias the
comparison if group sizes are unequal (they're not exactly 50/50 due to
random assignment).
**Fix:** rewrote to use `groupby("group")[...].agg(["sum","count"])` so
`nobs` is each group's own size. Re-ran and confirmed
`counts["count"].sum() == len(df)` to catch this class of bug in future
runs.

## 4. Churn model — data leakage risk
**AI first draft:** initially included `lifetime_order_count` and
`avg_order_value` (computed across ALL of a customer's orders) as model
features for predicting repeat purchase.
**Problem:** `lifetime_order_count` is only known once you already know
how many orders the customer placed — it's a direct proxy for (and partly
definitional to) the label being predicted. That's leakage: the model
would look artificially accurate but be useless at the moment it's meant
to be used (right after order #1).
**Fix:** restricted the feature set to signals available after the FIRST
order only (`order_value`, `was_late`, `review_score`, `payment_type`,
`installments` — all from `order_seq_num = 1`), and dropped
`lifetime_order_count` / `avg_order_value` (lifetime aggregates) from the
model entirely, keeping them only in the customer mart for dashboarding.
**Takeaway:** this is the single most important check on any "predict
future behavior" model — ask whether each feature would actually be known
at prediction time, not just whether it's available in the historical
table.

## 5. seaborn `palette` deprecation warning
**AI first draft:** used `sns.barplot(..., palette="Blues_d")` without a
`hue` argument.
**Problem:** current seaborn versions emit a `FutureWarning` — not
incorrect, but will break in a future seaborn release.
**Status:** left as-is with the warning noted here rather than "fixed",
since the correct future-proof pattern (`hue=x, legend=False`) changes the
legend behavior and wasn't worth the scope creep for this portfolio build.
Documented instead of silently ignored.

## Summary
5 corrections logged across the SQL, statistics, and modeling layers. The
most consequential was #4 (leakage) — the kind of error that doesn't show
up as a crash or a wrong number, only as a model that looks better than it
is. Manual review caught it before it made it into the "headline finding."
