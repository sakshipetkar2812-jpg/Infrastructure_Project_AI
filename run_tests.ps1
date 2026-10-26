# Automated Test Execution Script
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Running Automated Pytest Validation Suite (15 Test Cases) " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$env:PYTHONPATH = $PSScriptRoot
python -m pytest "$PSScriptRoot\tests\test_intelligence_agent.py" -v
