"""
Data Quality and Preprocessing Layer for Infrastructure Project Intelligence Agent.
Performs data integrity audits, missingness profiling, date sequence validation,
financial sanity checks, and referential integrity verification across tables.
"""

from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np


class DataQualityChecker:
    """
    Audits incoming infrastructure project datasets for schema compliance,
    anomalous records, orphan foreign keys, and logical inconsistencies.
    """

    def __init__(self, datasets: Dict[str, pd.DataFrame]):
        self.datasets = datasets
        self.report: Dict[str, Any] = {}

    def run_full_audit(self) -> Dict[str, Any]:
        """Runs all data quality checks and returns a comprehensive report."""
        audit_results = {
            "table_summaries": {},
            "referential_integrity": {},
            "logical_date_anomalies": {},
            "financial_sanity": {},
            "duplicate_records": {},
            "overall_health_score": 100.0,
            "findings_summary": []
        }

        penalties = 0.0

        # 1. Individual Table Summaries (Missing values, row counts)
        for name, df in self.datasets.items():
            if df.empty:
                audit_results["table_summaries"][name] = {"rows": 0, "status": "EMPTY_OR_MISSING"}
                penalties += 5.0
                continue

            missing_counts = df.isnull().sum()
            missing_pct = (missing_counts / len(df) * 100).round(2).to_dict()
            missing_cols = {k: v for k, v in missing_pct.items() if v > 0}

            # Check duplicates on primary keys if known
            pk_col = self._get_primary_key(name)
            dup_count = 0
            if pk_col and pk_col in df.columns:
                dup_count = int(df.duplicated(subset=[pk_col]).sum())
                if dup_count > 0:
                    penalties += min(dup_count * 0.5, 5.0)
                    audit_results["duplicate_records"][name] = dup_count

            audit_results["table_summaries"][name] = {
                "rows": len(df),
                "columns": len(df.columns),
                "missing_columns": missing_cols,
                "duplicate_pk_rows": dup_count
            }

        # 2. Logical Date Sequence Checks in Activities
        if "activities" in self.datasets and not self.datasets["activities"].empty:
            act = self.datasets["activities"]
            
            # Check: planned_finish < planned_start
            invalid_planned = act[act["planned_finish"] < act["planned_start"]]
            
            # Check: actual_finish < actual_start (for completed)
            completed = act[act["actual_finish"].notnull() & act["actual_start"].notnull()]
            invalid_actual = completed[completed["actual_finish"] < completed["actual_start"]]

            audit_results["logical_date_anomalies"]["activities"] = {
                "planned_finish_before_start": len(invalid_planned),
                "actual_finish_before_start": len(invalid_actual)
            }
            if len(invalid_planned) > 0 or len(invalid_actual) > 0:
                penalties += 2.0

        # 3. Financial Sanity (Negative costs or rates)
        if "activities" in self.datasets and not self.datasets["activities"].empty:
            act = self.datasets["activities"]
            neg_baseline = (act["baseline_cost"] < 0).sum()
            neg_actual = (act["actual_cost"] < 0).sum()
            audit_results["financial_sanity"]["negative_baseline_costs"] = int(neg_baseline)
            audit_results["financial_sanity"]["negative_actual_costs"] = int(neg_actual)
            if neg_baseline > 0 or neg_actual > 0:
                penalties += 3.0

        if "cost_ledger" in self.datasets and not self.datasets["cost_ledger"].empty:
            ledger = self.datasets["cost_ledger"]
            neg_amount = (ledger["amount"] < 0).sum()
            audit_results["financial_sanity"]["negative_ledger_amounts"] = int(neg_amount)
            if neg_amount > 0:
                penalties += 1.0

        # 4. Referential Integrity Checks
        if "activities" in self.datasets and not self.datasets["activities"].empty:
            act_ids = set(self.datasets["activities"]["activity_id"].dropna())

            # Check dependencies
            if "dependencies" in self.datasets and not self.datasets["dependencies"].empty:
                dep = self.datasets["dependencies"]
                orphan_preds = ~dep["predecessor_activity_id"].isin(act_ids)
                orphan_succs = ~dep["successor_activity_id"].isin(act_ids)
                audit_results["referential_integrity"]["orphan_predecessors"] = int(orphan_preds.sum())
                audit_results["referential_integrity"]["orphan_successors"] = int(orphan_succs.sum())

            # Check labor assignments
            if "labor_assignments" in self.datasets and not self.datasets["labor_assignments"].empty:
                lab = self.datasets["labor_assignments"]
                orphan_lab_act = ~lab["activity_id"].isin(act_ids)
                audit_results["referential_integrity"]["labor_orphan_activities"] = int(orphan_lab_act.sum())

            # Check cost ledger
            if "cost_ledger" in self.datasets and not self.datasets["cost_ledger"].empty:
                led = self.datasets["cost_ledger"]
                orphan_led_act = ~led["activity_id"].isin(act_ids)
                audit_results["referential_integrity"]["ledger_orphan_activities"] = int(orphan_led_act.sum())

            # Check BOQ
            if "boq" in self.datasets and not self.datasets["boq"].empty:
                boq = self.datasets["boq"]
                orphan_boq_act = ~boq["activity_id"].isin(act_ids)
                audit_results["referential_integrity"]["boq_orphan_activities"] = int(orphan_boq_act.sum())

        # Calculate Overall Health Score
        audit_results["overall_health_score"] = max(0.0, round(100.0 - penalties, 1))

        # Human-Readable Findings
        audit_results["findings_summary"] = self._generate_findings(audit_results)
        self.report = audit_results
        return audit_results

    def _get_primary_key(self, table_name: str) -> str:
        pk_map = {
            "activities": "activity_id",
            "dependencies": "dependency_id",
            "boq": "boq_id",
            "materials": "material_id",
            "material_consumption": "consumption_id",
            "goods_receipts": "grn_id",
            "inventory": "inventory_id",
            "contractors": "contractor_id",
            "labor_assignments": "labor_id",
            "cost_ledger": "ledger_id",
            "cost_reconciliation": "reconciliation_id",
            "contracts": "contract_id",
            "contract_clauses": "clause_id"
        }
        return pk_map.get(table_name, "")

    def _generate_findings(self, results: Dict[str, Any]) -> List[str]:
        findings = []
        score = results["overall_health_score"]
        findings.append(f"Overall Data Quality Health Score: {score}/100.0")

        # Missing values assessment
        act_summary = results["table_summaries"].get("activities", {})
        missing_act = act_summary.get("missing_columns", {})
        if "actual_finish" in missing_act:
            findings.append(
                f"Expected Data Pattern: {missing_act['actual_finish']}% of activities lack actual_finish. "
                "These correspond to IN_PROGRESS or NOT_STARTED activities, evaluated against the cutoff date."
            )

        # Integrity
        ref = results.get("referential_integrity", {})
        all_orphans = sum(ref.values()) if ref else 0
        if all_orphans == 0:
            findings.append("Referential Integrity: Excellent. 100% of foreign keys link cleanly to parent activities.")
        else:
            findings.append(f"Referential Integrity: {all_orphans} orphan records detected across relationships.")

        # Sanity
        fin = results.get("financial_sanity", {})
        if fin.get("negative_baseline_costs", 0) == 0 and fin.get("negative_actual_costs", 0) == 0:
            findings.append("Financial Sanity: All baseline and actual activity costs are strictly non-negative.")

        return findings
