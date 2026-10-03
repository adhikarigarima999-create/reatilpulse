#!/usr/bin/env bash
# RetailPulse — full pipeline runner.
# Regenerates raw data, rebuilds the SQL marts, runs EDA, the A/B test,
# and the repeat-purchase model, in dependency order.
set -e
cd "$(dirname "$0")/python"

echo "== 1/5 Generating raw data =="
python3 01_generate_raw_data.py

echo -e "\n== 2/5 Building staging -> intermediate -> mart SQL layer =="
python3 02_build_marts.py

echo -e "\n== 3/5 Running EDA =="
python3 03_eda.py

echo -e "\n== 4/5 Running A/B test =="
python3 04_ab_test_discount_promo.py

echo -e "\n== 5/5 Training repeat-purchase model =="
python3 05_repeat_purchase_model.py

echo -e "\nDone. Charts in ../charts/, A/B log in ../logs/ab_test_result.md"
