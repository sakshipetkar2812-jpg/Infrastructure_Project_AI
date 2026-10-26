"""
Deterministic Contractor & Labor Performance Analytics Engine.
Evaluates contractor historical benchmarks, daily crew headcounts,
wage commitments, and required vs actual labor productivity against deadlines.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from config.settings import CONTRACTOR_HIGH_RISK_SCORE, CONTRACTOR_AVG_DELAY_WARNING_DAYS


class ContractorEngine:
    """
    Analyzes contractor performance and site labor productivity.
    Separates historical benchmark scores from observed on-site productivity deficits.
    """

    def __init__(self, contractors_df: pd.DataFrame, labor_df: pd.DataFrame):
        self.contractors_df = contractors_df.copy()
        self.labor_df = labor_df.copy()

    def get_portfolio_kpis(self) -> Dict[str, Any]:
        """Calculates portfolio-wide contractor performance metrics."""
        con = self.contractors_df
        if con.empty:
            return {"status": "Insufficient data"}

        total_con = len(con)
        avg_risk = float(con["historical_risk_score"].mean()) if "historical_risk_score" in con.columns else 0.0
        avg_hist_delay = float(con["average_delay_days"].mean()) if "average_delay_days" in con.columns else 0.0
        avg_cost_overrun = float(con["average_cost_overrun_pct"].mean()) if "average_cost_overrun_pct" in con.columns else 0.0

        high_risk_con = con[con["historical_risk_score"] >= CONTRACTOR_HIGH_RISK_SCORE]
        warning_delay_con = con[con["average_delay_days"] >= CONTRACTOR_AVG_DELAY_WARNING_DAYS]

        return {
            "total_contractors": total_con,
            "average_historical_risk_score": round(avg_risk, 2),
            "average_historical_delay_days": round(avg_hist_delay, 1),
            "average_cost_overrun_pct": round(avg_cost_overrun, 2),
            "high_risk_contractor_count": len(high_risk_con),
            "contractors_with_delay_history": len(warning_delay_con)
        }

    def get_activity_contractor_status(self, activity_id: str, project_id: str) -> Dict[str, Any]:
        """
        Analyzes labor assignment, crew sizing, productivity rate, and contractor risk
        associated with an infrastructure activity.
        """
        lab_match = self.labor_df[
            (self.labor_df["project_id"] == project_id) &
            (self.labor_df["activity_id"] == activity_id)
        ]

        if lab_match.empty:
            return {
                "has_labor_assignment": False,
                "contractor_id": None,
                "contractor_name": "Unassigned / In-house",
                "labor_records": [],
                "has_productivity_deficit": False,
                "has_labor_risk": False
            }

        labor_details = []
        has_deficit = False
        has_risk = False
        primary_con_id = lab_match.iloc[0]["contractor_id"]

        # Contractor master info
        con_info = {}
        if not self.contractors_df.empty:
            c_lookup = self.contractors_df[self.contractors_df["contractor_id"] == primary_con_id]
            if not c_lookup.empty:
                c = c_lookup.iloc[0]
                con_info = {
                    "name": c.get("contractor_name", primary_con_id),
                    "specialization": c.get("specialization", "GENERAL"),
                    "license_type": c.get("license_type", "N/A"),
                    "historical_risk_score": float(c.get("historical_risk_score", 0)),
                    "average_delay_days": float(c.get("average_delay_days", 0)),
                    "average_cost_overrun_pct": float(c.get("average_cost_overrun_pct", 0))
                }
                if con_info["historical_risk_score"] >= CONTRACTOR_HIGH_RISK_SCORE:
                    has_risk = True

        for _, lrow in lab_match.iterrows():
            headcount = int(lrow.get("deployed_headcount", 0))
            max_crew = int(lrow.get("max_crew_size", headcount))
            daily_wage = float(lrow.get("daily_wage", 0))
            prod_rate = float(lrow.get("productivity_rate", 0))
            remaining_work = float(lrow.get("remaining_work", 0))
            days_to_deadline = max(1, int(lrow.get("days_to_deadline", 1)))

            # Deterministic required productivity: remaining_work / days_to_deadline
            required_prod = round(remaining_work / days_to_deadline, 2)
            prod_deficit = round(required_prod - prod_rate, 2)

            is_deficit = prod_deficit > 0 and remaining_work > 0
            if is_deficit:
                has_deficit = True

            labor_details.append({
                "trade": lrow.get("trade", "GENERAL"),
                "deployed_headcount": headcount,
                "max_crew_size": max_crew,
                "crew_utilization_pct": round(headcount / max(1, max_crew) * 100, 1),
                "daily_crew_wage": round(headcount * daily_wage, 2),
                "actual_productivity_rate": prod_rate,
                "required_productivity_rate": required_prod,
                "productivity_deficit": prod_deficit,
                "is_productivity_deficit": is_deficit,
                "remaining_work": remaining_work,
                "days_to_deadline": days_to_deadline
            })

        return {
            "has_labor_assignment": True,
            "contractor_id": primary_con_id,
            "contractor_name": con_info.get("name", primary_con_id),
            "contractor_profile": con_info,
            "labor_allocations": labor_details,
            "has_productivity_deficit": has_deficit,
            "has_contractor_risk": has_risk
        }
