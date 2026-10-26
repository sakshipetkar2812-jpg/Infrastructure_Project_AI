"""
Configuration and Settings for Infrastructure Project Delay & Cost Overrun Intelligence Agent.
Centralizes paths, analytical thresholds, and environment parameters.
"""

from pathlib import Path
from datetime import datetime, date
import os
from typing import Optional

# Base Project Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DOCUMENTS_DIR = PROJECT_ROOT / "documents"
CONTRACTS_RAW_DIR = DOCUMENTS_DIR / "contracts_raw"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Ensure runtime directories exist
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Project Analysis Cutoff / Snapshot Date (derived from inventory/labor/ledger records)
# In production, this represents the current project reporting cycle cutoff.
DEFAULT_CUTOFF_DATE_STR = os.getenv("DATA_CUTOFF_DATE", "2026-08-20")
DEFAULT_CUTOFF_DATE = datetime.strptime(DEFAULT_CUTOFF_DATE_STR, "%Y-%m-%d").date()

# Analytical Thresholds
# Schedule
CRITICAL_FLOAT_THRESHOLD_DAYS = int(os.getenv("CRITICAL_FLOAT_DAYS", "0"))
DELAY_LOW_THRESHOLD_DAYS = int(os.getenv("DELAY_THRESHOLD_LOW_DAYS", "5"))
DELAY_HIGH_THRESHOLD_DAYS = int(os.getenv("DELAY_THRESHOLD_HIGH_DAYS", "15"))

# Cost
COST_OVERRUN_ALERT_PCT = float(os.getenv("COST_OVERRUN_THRESHOLD_PCT", "10.0"))

# Contractor Risk
CONTRACTOR_HIGH_RISK_SCORE = 75.0
CONTRACTOR_AVG_DELAY_WARNING_DAYS = 5.0

# Procurement
MIN_ACCEPTANCE_RATE_PCT = 95.0

# Expected Raw Dataset Files
REQUIRED_DATASETS = {
    "activities": "activities.csv",
    "boq": "boq.csv",
    "contractors": "contractors.csv",
    "contracts": "contracts.csv",
    "contract_clauses": "contract_clauses.csv",
    "cost_ledger": "cost_ledger.csv",
    "cost_reconciliation": "cost_reconciliation.csv",
    "data_dictionary": "data_dictionary.csv",
    "dependencies": "dependencies.csv",
    "goods_receipts": "goods_receipts.csv",
    "inventory": "inventory.csv",
    "labor_assignments": "labor_assignments.csv",
    "materials": "materials.csv",
    "material_consumption": "material_consumption.csv",
    "survey_data": "Road Constuction Delay Survey.csv"
}

# LLM / AI Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")  # local, gemini, openai
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
