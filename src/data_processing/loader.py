"""
Data Loading Layer for Infrastructure Project Delay & Cost Overrun Intelligence Agent.
Safely loads CSV, XLSX, and TXT contract files, validates required columns,
and performs robust type casting without silently mutating source data.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np

from config.settings import (
    RAW_DATA_DIR,
    CONTRACTS_RAW_DIR,
    REQUIRED_DATASETS,
    DEFAULT_CUTOFF_DATE_STR
)


class ProjectDataLoader:
    """
    Robust data ingestion engine for multi-table infrastructure datasets.
    Preserves original data fidelity and provides transparent schema validation.
    """

    def __init__(self, data_dir: Optional[Path] = None, contracts_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else RAW_DATA_DIR
        self.contracts_dir = Path(contracts_dir) if contracts_dir else CONTRACTS_RAW_DIR
        self._cached_data: Dict[str, pd.DataFrame] = {}
        self._load_errors: List[str] = []
        self._load_metadata: Dict[str, Dict[str, Any]] = {}

    def get_load_errors(self) -> List[str]:
        """Returns any non-fatal warnings or loading errors encountered."""
        return self._load_errors

    def get_load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Returns file inventory metadata including row counts, columns, and file sizes."""
        return self._load_metadata

    def load_all(self, force_reload: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Loads all required infrastructure project datasets into memory.
        """
        if self._cached_data and not force_reload:
            return self._cached_data

        self._load_errors.clear()
        self._load_metadata.clear()
        loaded: Dict[str, pd.DataFrame] = {}

        # 1. Activities
        loaded["activities"] = self._load_activities()

        # 2. Dependencies
        loaded["dependencies"] = self._load_csv(
            "dependencies",
            parse_dates=[],
            required_cols=["dependency_id", "project_id", "predecessor_activity_id", "successor_activity_id", "relationship_type"]
        )

        # 3. Bill of Quantities (BOQ)
        loaded["boq"] = self._load_csv(
            "boq",
            parse_dates=[],
            required_cols=["boq_id", "project_id", "activity_id", "material_id", "planned_quantity", "unit_rate", "planned_cost"]
        )

        # 4. Materials
        loaded["materials"] = self._load_csv(
            "materials",
            parse_dates=[],
            required_cols=["material_id", "material_name", "category", "standard_unit_cost", "criticality", "lead_time_days"]
        )

        # 5. Material Consumption
        loaded["material_consumption"] = self._load_csv(
            "material_consumption",
            parse_dates=["date"],
            required_cols=["consumption_id", "project_id", "activity_id", "material_id", "quantity_consumed", "remaining_quantity_required"]
        )

        # 6. Goods Receipts
        loaded["goods_receipts"] = self._load_csv(
            "goods_receipts",
            parse_dates=["received_date"],
            required_cols=["grn_id", "po_id", "project_id", "material_id", "vendor_id", "received_quantity", "accepted_quantity", "quality_status"]
        )

        # 7. Inventory
        loaded["inventory"] = self._load_csv(
            "inventory",
            parse_dates=["date"],
            required_cols=["inventory_id", "project_id", "material_id", "closing_stock", "reserved_quantity"]
        )

        # 8. Contractors
        loaded["contractors"] = self._load_csv(
            "contractors",
            parse_dates=[],
            required_cols=["contractor_id", "contractor_name", "specialization", "average_delay_days", "historical_risk_score"]
        )

        # 9. Labor Assignments
        loaded["labor_assignments"] = self._load_csv(
            "labor_assignments",
            parse_dates=["date"],
            required_cols=["labor_id", "project_id", "activity_id", "contractor_id", "deployed_headcount", "productivity_rate", "remaining_work"]
        )

        # 10. Cost Ledger
        loaded["cost_ledger"] = self._load_csv(
            "cost_ledger",
            parse_dates=["cost_date"],
            required_cols=["ledger_id", "project_id", "activity_id", "cost_type", "amount"]
        )

        # 11. Cost Reconciliation
        loaded["cost_reconciliation"] = self._load_csv(
            "cost_reconciliation",
            parse_dates=["reconciliation_date"],
            required_cols=["reconciliation_id", "project_id", "predicted_cost", "actual_cost", "error_percentage"]
        )

        # 12. Contracts
        loaded["contracts"] = self._load_csv(
            "contracts",
            parse_dates=["effective_date", "expiry_date"],
            required_cols=["contract_id", "vendor_id", "contract_name", "contract_type", "document_path"]
        )

        # 13. Contract Clauses
        loaded["contract_clauses"] = self._load_csv(
            "contract_clauses",
            parse_dates=[],
            required_cols=["clause_id", "contract_id", "vendor_id", "section", "clause_number", "title", "clause_text"]
        )

        # 14. Road Construction Delay Survey
        loaded["survey_data"] = self._load_survey()

        self._cached_data = loaded
        return self._cached_data

    def _read_csv_safe(self, fpath: Path, **kwargs) -> pd.DataFrame:
        """Reads CSV with encoding fallback for Windows-1252 / CP1252 symbols."""
        try:
            return pd.read_csv(fpath, encoding="utf-8", **kwargs)
        except UnicodeDecodeError:
            try:
                return pd.read_csv(fpath, encoding="cp1252", **kwargs)
            except Exception:
                return pd.read_csv(fpath, encoding="latin-1", **kwargs)

    def _load_activities(self) -> pd.DataFrame:
        """Specialized loader for activities dataset with date validation and status alignment."""
        fname = REQUIRED_DATASETS["activities"]
        fpath = self.data_dir / fname
        if not fpath.exists():
            err = f"CRITICAL: Required file {fname} not found in {self.data_dir}"
            self._load_errors.append(err)
            raise FileNotFoundError(err)

        df = self._read_csv_safe(fpath)
        self._record_metadata("activities", fname, df, fpath)

        # Parse date columns
        date_cols = ["planned_start", "planned_finish", "actual_start", "actual_finish"]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Numeric conversions without zero imputation
        num_cols = [
            "planned_duration_days", "actual_duration_days",
            "planned_progress_pct", "actual_progress_pct",
            "baseline_cost", "actual_cost", "total_float_days"
        ]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Boolean conversion
        for col in ["is_milestone", "is_critical"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.lower().isin(["true", "1", "t", "yes"])

        return df

    def _load_csv(self, key: str, parse_dates: List[str], required_cols: List[str]) -> pd.DataFrame:
        """Generic CSV loader with schema validation."""
        fname = REQUIRED_DATASETS.get(key, f"{key}.csv")
        fpath = self.data_dir / fname
        if not fpath.exists():
            warning = f"Warning: Dataset {fname} missing from {self.data_dir}"
            self._load_errors.append(warning)
            return pd.DataFrame()

        df = self._read_csv_safe(fpath)
        self._record_metadata(key, fname, df, fpath)

        # Validate required columns
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            self._load_errors.append(f"{fname} is missing required columns: {missing}")

        for col in parse_dates:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df

    def _load_survey(self) -> pd.DataFrame:
        """Loads delay survey data with clean column names."""
        fname = REQUIRED_DATASETS["survey_data"]
        fpath = self.data_dir / fname
        if not fpath.exists():
            return pd.DataFrame()

        df = self._read_csv_safe(fpath)
        self._record_metadata("survey_data", fname, df, fpath)
        return df

    def _record_metadata(self, key: str, fname: str, df: pd.DataFrame, fpath: Path):
        """Records file inventory metrics."""
        self._load_metadata[key] = {
            "file_name": fname,
            "path": str(fpath),
            "rows": len(df),
            "columns": list(df.columns),
            "size_kb": round(fpath.stat().st_size / 1024, 2)
        }

    def load_contract_texts(self) -> Dict[str, str]:
        """Loads all raw contract text documents into a mapping of contract_id -> text."""
        contracts_text: Dict[str, str] = {}
        if not self.contracts_dir.exists():
            return contracts_text

        for txt_file in self.contracts_dir.glob("*.txt"):
            contract_id = txt_file.stem  # e.g., 'CONTRACT-001'
            try:
                with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                    contracts_text[contract_id] = f.read()
            except Exception as e:
                self._load_errors.append(f"Failed to read contract file {txt_file.name}: {e}")

        return contracts_text
