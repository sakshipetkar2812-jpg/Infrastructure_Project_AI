"""
Specialized Domain Intelligence Agents for Infrastructure Projects.
Each specialist agent has a strict, testable responsibility, explicit input data,
deterministic analytical calculations, and structured JSON-serializable outputs.
"""

from typing import Dict, Any, List, Optional
import pandas as pd

from src.analytics.schedule_engine import ScheduleEngine
from src.analytics.procurement_engine import ProcurementEngine
from src.analytics.cost_engine import CostEngine
from src.analytics.contractor_engine import ContractorEngine
from src.rag.contract_rag import ContractRAGEngine


class ScheduleAgent:
    """Specialist Agent responsible for schedule variance, milestone tracking, and critical path analysis."""

    def __init__(self, engine: ScheduleEngine):
        self.engine = engine

    def investigate(self, activity_id: str, project_id: str) -> Dict[str, Any]:
        """Performs schedule forensic analysis for an activity."""
        df = self.engine.processed_df
        if df.empty:
            df = self.engine.analyze()

        match = df[(df["project_id"] == project_id) & (df["activity_id"] == activity_id)]
        if match.empty:
            return {"status": "NOT_FOUND", "agent": "ScheduleAgent", "error": f"Activity {activity_id} not found"}

        act = match.iloc[0]
        delay_days = int(act.get("delay_days", 0))
        is_crit = bool(act.get("is_critical_effective", False))
        is_overdue = bool(act.get("is_overdue", False))
        slippage = float(act.get("progress_slippage_pct", 0.0))

        # Downstream impacted successors
        successors = self.engine.get_successors(activity_id)

        return {
            "agent": "ScheduleAgent",
            "activity_id": activity_id,
            "project_id": project_id,
            "activity_name": act.get("activity_name", ""),
            "status": act.get("status", ""),
            "planned_start": str(act.get("planned_start")),
            "planned_finish": str(act.get("planned_finish")),
            "actual_start": str(act.get("actual_start")) if pd.notnull(act.get("actual_start")) else None,
            "actual_finish": str(act.get("actual_finish")) if pd.notnull(act.get("actual_finish")) else None,
            "delay_days": delay_days,
            "is_overdue": is_overdue,
            "is_critical_path": is_crit,
            "progress_slippage_pct": round(slippage, 1),
            "delay_category": act.get("delay_category", "ON_TIME"),
            "impacted_successors_count": len(successors),
            "impacted_successors": successors[:5]
        }


class ProcurementAgent:
    """Specialist Agent responsible for material supply, inventory shortages, and vendor receipt quality."""

    def __init__(self, engine: ProcurementEngine):
        self.engine = engine

    def investigate(self, activity_id: str, project_id: str) -> Dict[str, Any]:
        """Analyzes material demand, consumption, warehouse stocks, and vendor delivery defects."""
        status = self.engine.get_activity_material_status(activity_id, project_id)
        return {
            "agent": "ProcurementAgent",
            "activity_id": activity_id,
            "project_id": project_id,
            "has_material_requirement": status["has_material_requirement"],
            "has_stock_shortage": status["has_shortage"],
            "has_delivery_defect": status["has_delivery_defect"],
            "materials_count": len(status["materials"]),
            "materials_detail": status["materials"]
        }


class CostAgent:
    """Specialist Agent responsible for budget variance, financial ledger tracking, and delay cost exposure."""

    def __init__(self, engine: CostEngine):
        self.engine = engine

    def investigate(self, activity_id: str, project_id: str, delay_days: int = 0) -> Dict[str, Any]:
        """Calculates baseline vs actual costs, ledger breakdown, and calibrated delay financial exposure."""
        detail = self.engine.get_activity_cost_detail(activity_id, project_id, delay_days=delay_days)
        return {
            "agent": "CostAgent",
            "activity_id": activity_id,
            "project_id": project_id,
            "baseline_cost": detail.get("baseline_cost", 0.0),
            "actual_cost": detail.get("actual_cost", 0.0),
            "cost_variance": detail.get("cost_variance", 0.0),
            "cost_variance_pct": detail.get("cost_variance_pct", 0.0),
            "cost_drivers": detail.get("cost_drivers", {}),
            "daily_actual_burn_rate": detail.get("daily_actual_burn_rate", 0.0),
            "potential_delay_exposure": detail.get("potential_delay_exposure", 0.0),
            "delay_exposure_formula": detail.get("delay_exposure_formula", "")
        }


class ContractorAgent:
    """Specialist Agent responsible for labor allocations, crew productivity deficits, and contractor risk."""

    def __init__(self, engine: ContractorEngine):
        self.engine = engine

    def investigate(self, activity_id: str, project_id: str) -> Dict[str, Any]:
        """Evaluates contractor performance history, daily headcount, and measured productivity rates."""
        status = self.engine.get_activity_contractor_status(activity_id, project_id)
        return {
            "agent": "ContractorAgent",
            "activity_id": activity_id,
            "project_id": project_id,
            "has_labor_assignment": status["has_labor_assignment"],
            "contractor_id": status["contractor_id"],
            "contractor_name": status["contractor_name"],
            "contractor_profile": status.get("contractor_profile", {}),
            "has_productivity_deficit": status["has_productivity_deficit"],
            "has_contractor_risk": status.get("has_contractor_risk", False),
            "labor_allocations": status.get("labor_allocations", [])
        }


class ContractAgent:
    """Specialist Agent responsible for RAG retrieval over contracts, delivery terms, and liquidated damages."""

    def __init__(self, engine: ContractRAGEngine):
        self.engine = engine

    def investigate(self, query: str, contract_id: Optional[str] = None, vendor_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves verified contract clauses matching the specific dispute or risk context."""
        res = self.engine.answer_contract_question(query, contract_id=contract_id, vendor_id=vendor_id)
        return {
            "agent": "ContractAgent",
            "query": query,
            "answer": res["answer"],
            "evidence_retrieved": res["evidence_retrieved"],
            "citations": res["citations"]
        }
