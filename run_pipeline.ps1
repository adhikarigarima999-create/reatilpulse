# RetailPulse — Windows PowerShell Pipeline Runner
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$ScriptDir\python"

Write-Host "== 1/5 Generating raw data ==" -ForegroundColor Cyan
python 01_generate_raw_data.py

Write-Host "`n== 2/5 Building staging -> intermediate -> mart SQL layer ==" -ForegroundColor Cyan
python 02_build_marts.py

Write-Host "`n== 3/5 Running EDA ==" -ForegroundColor Cyan
python 03_eda.py

Write-Host "`n== 4/5 Running A/B test ==" -ForegroundColor Cyan
python 04_ab_test_discount_promo.py

Write-Host "`n== 5/5 Training repeat-purchase model ==" -ForegroundColor Cyan
python 05_repeat_purchase_model.py

Write-Host "`nDone! Charts saved in charts/, A/B log in logs/ab_test_result.md" -ForegroundColor Green
Set-Location $ScriptDir
