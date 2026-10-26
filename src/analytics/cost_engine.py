"""
Deterministic Cost & Financial Variance Engine.
Calculates budget vs actual spend, cost variance, cost by trade/type,
daily delay burn rates, and financial exposure calibration against historical ledger records.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from config.settings import COST_OVERRUN_ALERT_PCT


class CostEngine:
    """
    Deterministic cost analytics engine for infrastructure programs.
    Strictly differentiates between actual incurred costs, budget variance,
    calibrated forecast exposure, and contractual liquidated damages.
    """

    def __init__(
        self,
        activities_df: pd.DataFrame,
        cost_ledger_df: pd.DataFrame,
        reconciliation_df: Optional[pd.DataFrame] = None
    ):
        self.activities_df = activities_df.copy()
        self.cost_ledger_df = cost_ledger_df.copy()
        self.reconciliation_df = reconciliation_df.copy() if reconciliation_df is not None else pd.DataFrame()

    def get_portfolio_cost_kpis(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates portfolio or project-level budget and actual financial metrics."""
        act = self.activities_df
        led = self.cost_ledger_df
        if project_id:
            act = act[act["project_id"] == project_id] if not act.empty else act
            led = led[led["project_id"] == project_id] if not led.empty else led

        if act.empty:
            return {"status": "Insufficient data"}

        total_baseline = float(act["baseline_cost"].sum())
        total_actual = float(act["actual_cost"].sum())
        total_variance = total_actual - total_baseline
        variance_pct = round(total_variance / total_baseline * 100, 2) if total_baseline > 0 else 0.0

        overrun_acts = act[act["actual_cost"] > act["baseline_cost"]]
        overrun_count = len(overrun_acts)
        severe_overrun = act[(act["actual_cost"] - act["baseline_cost"]) / (act["baseline_cost"] + 1e-6) * 100 > COST_OVERRUN_ALERT_PCT]

        # Cost breakdown by ledger category
        ledger_breakdown = {}
        if not led.empty and "cost_type" in led.columns:
            by_type = led.groupby("cost_type")["amount"].sum().to_dict()
            ledger_breakdown = {k: round(float(v), 2) for k, v in by_type.items()}

        # Cost reconciliation accuracy if available
        recon_metrics = {}
        if not self.reconciliation_df.empty:
            rec = self.reconciliation_df
            if project_id:
                rec = rec[rec["project_id"] == project_id]
            if not rec.empty:
                mae = float(rec["absolute_error"].mean())
                mape = float(rec["error_percentage"].mean())
                recon_metrics = {
                    "historical_calibrations_count": len(rec),
                    "mean_absolute_error": round(mae, 2),
                    "mean_percentage_error": round(mape, 2)
                }

        return {
            "total_baseline_cost": round(total_baseline, 2),
            "total_actual_cost": round(total_actual, 2),
            "total_cost_variance": round(total_variance, 2),
            "cost_variance_percentage": variance_pct,
            "activities_over_budget": overrun_count,
            "activities_severe_overrun": len(severe_overrun),
            "ledger_by_category": ledger_breakdown,
            "calibration_metrics": recon_metrics
        }

    def get_activity_cost_detail(self, activity_id: str, project_id: str, delay_days: int = 0) -> Dict[str, Any]:
        """
        Calculates granular activity financial variance and transparent delay cost exposure.
        """
        match = self.activities_df[
            (self.activities_df["project_id"] == project_id) &
            (self.activities_df["activity_id"] == activity_id)
        ]

        if match.empty:
            return {"status": "Activity not found", "activity_id": activity_id}

        row = match.iloc[0]
        baseline = float(row.get("baseline_cost", 0))
        actual = float(row.get("actual_cost", 0))
        variance = actual - baseline
        variance_pct = round(variance / baseline * 100, 2) if baseline > 0 else 0.0

        # Ledger breakdown for this activity
        ledger_items = []
        ledger_total = 0.0
        cost_drivers = {}

        if not self.cost_ledger_df.empty and "project_id" in self.cost_ledger_df.columns and "activity_id" in self.cost_ledger_df.columns:
            led_match = self.cost_ledger_df[
                (self.cost_ledger_df["project_id"] == project_id) &
                (self.cost_ledger_df["activity_id"] == activity_id)
            ]
            if not led_match.empty:
                ledger_total = float(led_match["amount"].sum())
                by_type = led_match.groupby("cost_type")["amount"].sum().to_dict()
                cost_drivers = {k: round(float(v), 2) for k, v in by_type.items()}
                for _, lrow in led_match.head(10).iterrows():
                    ledger_items.append({
                        "cost_type": lrow.get("cost_type"),
                        "amount": float(lrow.get("amount", 0)),
                        "invoice_id": lrow.get("invoice_id"),
                        "description": lrow.get("description")
                    })

        # Calculate daily burn rate and estimated potential delay financial exposure
        # Daily burn rate = (Actual Cost / Planned Duration) if available
        planned_dur = max(1, float(row.get("planned_duration_days", 1) or 1))
        daily_baseline_rate = baseline / planned_dur
        daily_actual_rate = actual / max(1, float(row.get("actual_duration_days", planned_dur) or planned_dur))

        # Potential delay financial exposure:
        # Explicit formula: delay_days * daily_actual_rate for critical delayed activities
        delay_exposure = round(delay_days * daily_actual_rate, 2) if delay_days > 0 else 0.0

        return {
            "activity_id": activity_id,
            "project_id": project_id,
            "baseline_cost": baseline,
            "actual_cost": actual,
            "cost_variance": round(variance, 2),
            "cost_variance_pct": variance_pct,
            "ledger_recorded_total": round(ledger_total, 2),
            "cost_drivers": cost_drivers,
            "recent_ledger_entries": ledger_items,
            "daily_baseline_rate": round(daily_baseline_rate, 2),
            "daily_actual_burn_rate": round(daily_actual_rate, 2),
            "delay_days_evaluated": delay_days,
            "potential_delay_exposure": delay_exposure,
            "delay_exposure_formula": "delay_days * daily_actual_burn_rate (assuming ongoing site resource holding costs)"
        }
