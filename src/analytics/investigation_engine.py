"""
Evidence-Based Root Cause Investigation Engine.
Correlates findings across schedule, procurement, labor productivity,
contractor history, and contract clauses to determine probable root causes.
"""

from typing import Dict, Any, List, Optional
import pandas as pd

from src.analytics.schedule_engine import ScheduleEngine
from src.analytics.procurement_engine import ProcurementEngine
from src.analytics.cost_engine import CostEngine
from src.analytics.contractor_engine import ContractorEngine
from src.rag.contract_rag import ContractRAGEngine


class RootCauseInvestigationEngine:
    """
    Synthesizes multi-source telemetry to identify verified root causes of project delays.
    Maintains strict evidential standards: separates correlation from causation.
    """

    def __init__(
        self,
        schedule_engine: ScheduleEngine,
        procurement_engine: ProcurementEngine,
        cost_engine: CostEngine,
        contractor_engine: ContractorEngine,
        rag_engine: Optional[ContractRAGEngine] = None
    ):
        self.schedule_engine = schedule_engine
        self.procurement_engine = procurement_engine
        self.cost_engine = cost_engine
        self.contractor_engine = contractor_engine
        self.rag_engine = rag_engine

    def investigate_activity(self, activity_id: str, project_id: str) -> Dict[str, Any]:
        """
        Executes a rigorous cross-domain forensic investigation for a delayed or at-risk activity.
        """
        # 1. Schedule Evidence
        sched_df = self.schedule_engine.processed_df
        if sched_df.empty:
            sched_df = self.schedule_engine.analyze()

        act_match = sched_df[
            (sched_df["project_id"] == project_id) &
            (sched_df["activity_id"] == activity_id)
        ]

        if act_match.empty:
            return {
                "activity_id": activity_id,
                "project_id": project_id,
                "status": "Activity record not found in schedule dataset",
                "probable_root_cause": "Insufficient data"
            }

        act = act_match.iloc[0]
        delay_days = int(act.get("delay_days", 0))
        is_critical = bool(act.get("is_critical_effective", False))
        is_overdue = bool(act.get("is_overdue", False))
        slippage_pct = float(act.get("progress_slippage_pct", 0.0))
        activity_name = act.get("activity_name", activity_id)
        status = act.get("status", "UNKNOWN")

        # 2. Procurement Evidence
        proc_data = self.procurement_engine.get_activity_material_status(activity_id, project_id)
        has_shortage = proc_data.get("has_shortage", False)
        has_defect = proc_data.get("has_delivery_defect", False)
        materials_involved = proc_data.get("materials", [])

        # 3. Contractor & Labor Evidence
        cont_data = self.contractor_engine.get_activity_contractor_status(activity_id, project_id)
        has_productivity_deficit = cont_data.get("has_productivity_deficit", False)
        has_contractor_risk = cont_data.get("has_contractor_risk", False)
        contractor_name = cont_data.get("contractor_name", "Unassigned")
        labor_allocations = cont_data.get("labor_allocations", [])

        # 4. Cost Evidence
        cost_data = self.cost_engine.get_activity_cost_detail(activity_id, project_id, delay_days=delay_days)
        cost_variance = cost_data.get("cost_variance", 0.0)
        cost_variance_pct = cost_data.get("cost_variance_pct", 0.0)
        potential_exposure = cost_data.get("potential_delay_exposure", 0.0)

        # 5. Dependency / Predecessor Evidence
        dep_evidence = self._check_predecessor_slippage(activity_id, project_id)

        # 6. Synthesize Probable Root Cause & Confidence
        supporting_evidence = []
        alternative_causes = []
        probable_cause = "Root cause not established"
        confidence = "LOW"

        if delay_days <= 0 and not is_overdue:
            probable_cause = "No active delay observed (Activity executing on or ahead of baseline schedule)"
            confidence = "HIGH"
            supporting_evidence.append(f"Recorded progress is {act.get('actual_progress_pct')}% against planned {act.get('planned_progress_pct')}%.")

        elif has_shortage or has_defect:
            probable_cause = "Material Supply Shortage / Supplier Delivery Quality Bottleneck"
            confidence = "HIGH" if (has_shortage and has_defect) else "MEDIUM"
            if has_shortage:
                short_mats = [m["material_name"] for m in materials_involved if m.get("is_stock_shortage")]
                supporting_evidence.append(f"Warehouse stock shortage confirmed for materials: {', '.join(short_mats)}.")
            if has_defect:
                def_mats = [m["material_name"] for m in materials_involved if m.get("defect_pct", 0) > 5.0]
                supporting_evidence.append(f"Elevated supplier defect/rejection rates observed for: {', '.join(def_mats)}.")
            if has_productivity_deficit:
                alternative_causes.append("Co-occurring labor productivity deficit on site.")

        elif has_productivity_deficit:
            probable_cause = "Contractor Labor Under-Deployment / Site Productivity Deficit"
            confidence = "HIGH" if has_contractor_risk else "MEDIUM"
            supporting_evidence.append(
                f"Assigned contractor '{contractor_name}' deployed headcount with productivity rate below the pace required to meet deadline."
            )
            if has_contractor_risk:
                supporting_evidence.append(
                    f"Contractor has historical risk score of {cont_data.get('contractor_profile', {}).get('historical_risk_score', 'N/A')}."
                )
            alternative_causes.append("Unrecorded site access constraints or severe weather conditions.")

        elif dep_evidence["has_predecessor_delay"]:
            probable_cause = "Upstream Dependency Delay Propagation from Critical Predecessor"
            confidence = "MEDIUM"
            supporting_evidence.append(
                f"Critical predecessor activity '{dep_evidence['predecessor_name']}' experienced {dep_evidence['predecessor_delay']} days of delay."
            )
            alternative_causes.append("Simultaneous site mobilization delays.")

        else:
            probable_cause = "Design Revision, Scope Adjustment, or Site Approval Delay"
            confidence = "LOW"
            supporting_evidence.append(
                f"Schedule progress lagged by {slippage_pct:.1f}% without active material shortage or reported labor deficit."
            )
            alternative_causes.append("Permitting or client review bottleneck.")

        # 7. Relevant Contract Clause Retrieval via RAG
        contract_citations = []
        if self.rag_engine:
            query = f"delay damages material delivery failure liquidated damages contractor obligations {probable_cause}"
            citations = self.rag_engine.retrieve(query, top_k=2)
            contract_citations = citations

        return {
            "activity_id": activity_id,
            "project_id": project_id,
            "activity_name": activity_name,
            "status": status,
            "observed_delay_days": delay_days,
            "is_critical_path": is_critical,
            "is_overdue": is_overdue,
            "progress_slippage_pct": slippage_pct,
            "cost_variance": cost_variance,
            "cost_variance_pct": cost_variance_pct,
            "potential_delay_exposure": potential_exposure,
            "probable_root_cause": probable_cause,
            "confidence_level": confidence,
            "supporting_evidence": supporting_evidence,
            "alternative_causes": alternative_causes,
            "contractor_involved": contractor_name,
            "materials_involved": [m.get("material_name") for m in materials_involved],
            "predecessor_context": dep_evidence,
            "contract_citations": contract_citations
        }

    def _check_predecessor_slippage(self, activity_id: str, project_id: str) -> Dict[str, Any]:
        """Checks if predecessor activities in the network suffered schedule slippage."""
        dep_df = self.schedule_engine.dep_df
        sched_df = self.schedule_engine.processed_df

        if dep_df.empty or sched_df.empty or "predecessor_activity_id" not in dep_df.columns:
            return {"has_predecessor_delay": False}

        preds = dep_df[
            (dep_df["project_id"] == project_id) &
            (dep_df["successor_activity_id"] == activity_id)
        ]

        if preds.empty:
            return {"has_predecessor_delay": False}

        for _, prow in preds.iterrows():
            pred_id = prow["predecessor_activity_id"]
            pmatch = sched_df[sched_df["activity_id"] == pred_id]
            if not pmatch.empty:
                p_act = pmatch.iloc[0]
                p_delay = int(p_act.get("delay_days", 0))
                if p_delay > 5:
                    return {
                        "has_predecessor_delay": True,
                        "predecessor_id": pred_id,
                        "predecessor_name": p_act.get("activity_name", pred_id),
                        "predecessor_delay": p_delay
                    }

        return {"has_predecessor_delay": False}
