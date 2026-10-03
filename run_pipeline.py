"""
RetailPulse — Cross-platform pipeline runner.
Runs:
  1. python/01_generate_raw_data.py
  2. python/02_build_marts.py
  3. python/03_eda.py
  4. python/04_ab_test_discount_promo.py
  5. python/05_repeat_purchase_model.py
"""
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON_DIR = ROOT / "python"

STEPS = [
    ("1/5 Generating raw data", "01_generate_raw_data.py"),
    ("2/5 Building staging -> intermediate -> mart SQL layer", "02_build_marts.py"),
    ("3/5 Running EDA", "03_eda.py"),
    ("4/5 Running A/B test", "04_ab_test_discount_promo.py"),
    ("5/5 Training repeat-purchase model", "05_repeat_purchase_model.py"),
]

def main():
    print("=" * 60)
    print("RetailPulse — Running Full Analytics & Modeling Pipeline")
    print("=" * 60)

    for desc, script_name in STEPS:
        script_path = PYTHON_DIR / script_name
        print(f"\n>> Step: {desc}")
        cmd = [sys.executable, str(script_path)]
        res = subprocess.run(cmd, cwd=str(PYTHON_DIR))
        if res.returncode != 0:
            print(f"\n[ERROR] Pipeline failed at {script_name} with exit code {res.returncode}")
            sys.exit(res.returncode)

    print("\n" + "=" * 60)
    print(" Pipeline completed successfully!")
    print(" - EDA Charts: charts/")
    print(" - A/B Test Report: logs/ab_test_result.md")
    print(" - Dashboard: index.html")
    print("=" * 60)

if __name__ == "__main__":
    main()
