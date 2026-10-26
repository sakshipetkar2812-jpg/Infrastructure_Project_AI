# Launch Script for Infrastructure Project Intelligence Agent
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Infrastructure Intelligence Agent Dashboard " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$env:PYTHONPATH = $PSScriptRoot
Write-Host "Set PYTHONPATH to $env:PYTHONPATH" -ForegroundColor Green

Write-Host "Launching Streamlit application at http://localhost:8501 ..." -ForegroundColor Yellow
python -m streamlit run "$PSScriptRoot\dashboard\app.py" --server.port 8501 --server.headless false
