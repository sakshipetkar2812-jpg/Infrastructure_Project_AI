"""
Project Risk Supervisor Agent.
Coordinates specialist agents, resolves inter-agent discrepancies, validates evidence chains,
and generates definitive forensic investigation reports and leadership briefings.
"""

from typing import Dict, Any, List, Optional
import pandas as pd

from src.agents.specialists import (
    ScheduleAgent,
    ProcurementAgent,
    CostAgent,
    ContractorAgent,
    ContractAgent
)
from src.analytics.investigation_engine import RootCauseInvestigationEngine
from src.analytics.risk_engine import RiskAndForecastingEngine
from src.analytics.recommendation_engine import RecommendationEngine


class ProjectRiskSupervisor:
    """
    Master supervisory coordinator for multi-agent infrastructure forensics.
    Synthesizes specialist findings without delegating deterministic calculations to LLMs.
    """

    def __init__(
        self,
        schedule_agent: ScheduleAgent,
        procurement_agent: ProcurementAgent,
        cost_agent: CostAgent,
        contractor_agent: ContractorAgent,
        contract_agent: ContractAgent,
        investigation_engine: RootCauseInvestigationEngine,
        risk_engine: RiskAndForecastingEngine
    ):
        self.schedule_agent = schedule_agent
        self.procurement_agent = procurement_agent
        self.cost_agent = cost_agent
        self.contractor_agent = contractor_agent
        self.contract_agent = contract_agent
        self.investigation_engine = investigation_engine
        self.risk_engine = risk_engine

    def conduct_full_investigation(self, activity_id: str, project_id: str) -> Dict[str, Any]:
        """
        Orchestrates an end-to-end multi-agent forensic investigation.
        """
        # 1. Invoke Specialist Agents
        sched_res = self.schedule_agent.investigate(activity_id, project_id)
        if sched_res.get("status") == "NOT_FOUND":
            return {"status": "ERROR", "message": f"Activity {activity_id} in {project_id} not found."}

        proc_res = self.procurement_agent.investigate(activity_id, project_id)
        delay_days = sched_res.get("delay_days", 0)
        cost_res = self.cost_agent.investigate(activity_id, project_id, delay_days=delay_days)
        cont_res = self.contractor_agent.investigate(activity_id, project_id)

        # 2. Forensic Root Cause Correlation
        forensic = self.investigation_engine.investigate_activity(activity_id, project_id)
        probable_cause = forensic.get("probable_root_cause", "Root cause not established")

        # 3. Legal Contract Citations via ContractAgent
        contract_query = f"delay liquidated damages obligations remedies {probable_cause}"
        contract_res = self.contract_agent.investigate(contract_query)

        # 4. Conflict Resolution & Consistency Check between Specialist Agents
        conflicts_identified = self._detect_agent_conflicts(sched_res, proc_res, cost_res, cont_res)

        # 5. Risk Scoring & Predictive Forecasting
        # Look up activity series
        act_df = self.schedule_agent.engine.processed_df
        act_row = act_df[(act_df["project_id"] == project_id) & (act_df["activity_id"] == activity_id)].iloc[0]

        risk_profile = self.risk_engine.calculate_activity_risk_score(
            act_row,
            procurement_status={"has_shortage": proc_res["has_stock_shortage"], "has_delivery_defect": proc_res["has_delivery_defect"]},
            contractor_status={"has_productivity_deficit": cont_res["has_productivity_deficit"], "has_contractor_risk": cont_res["has_contractor_risk"]}
        )

        forecast = self.risk_engine.forecast_completion_and_cost(act_row)

        # 6. Corrective Action Recommendations
        recommendations = RecommendationEngine.generate_recommendations(forensic)

        # 7. Identify Missing Telemetry / Information
        missing_info = self._identify_missing_information(sched_res, proc_res, cont_res, forensic)

        # 8. Executive Narrative Synthesis
        executive_summary = self._synthesize_executive_narrative(
            sched_res, proc_res, cost_res, cont_res, forensic, risk_profile, forecast
        )

        return {
            "activity_id": activity_id,
            "project_id": project_id,
            "activity_name": sched_res.get("activity_name", ""),
            "status": sched_res.get("status", ""),
            "risk_profile": risk_profile,
            "forecasting": forecast,
            "probable_root_cause": probable_cause,
            "confidence_level": forensic.get("confidence_level", "LOW"),
            "supporting_evidence": forensic.get("supporting_evidence", []),
            "conflicts_identified": conflicts_identified,
            "missing_information": missing_info,
            "recommendations": recommendations,
            "legal_citations": contract_res.get("citations", []),
            "executive_summary": executive_summary,
            "specialist_telemetry": {
                "schedule": sched_res,
                "procurement": proc_res,
                "cost": cost_res,
                "contractor": cont_res
            }
        }

    def _detect_agent_conflicts(
        self,
        sched: Dict[str, Any],
        proc: Dict[str, Any],
        cost: Dict[str, Any],
        cont: Dict[str, Any]
    ) -> List[str]:
        """Detects and reconciles inter-agent discrepancies."""
        conflicts = []

        # Check: Activity is on time, but CostAgent reports cost overrun
        if sched.get("delay_days", 0) <= 0 and cost.get("cost_variance", 0) > 0:
            conflicts.append(
                "Cost vs Schedule Discrepancy: Activity has zero recorded schedule delay, yet exhibits a cost overrun. "
                "Supervisor Conclusion: Cost increase is driven by unit rate inflation or equipment intensity, not schedule delay."
            )

        # Check: Material shortage reported, but activity is 100% completed
        if sched.get("status") == "COMPLETED" and proc.get("has_stock_shortage"):
            conflicts.append(
                "Procurement vs Status Discrepancy: Current warehouse stock is depleted, but activity is marked COMPLETED. "
                "Supervisor Conclusion: Material shortage affects downstream successor activities rather than this finished task."
            )

        # Check: Compound bottlenecks
        if proc.get("has_stock_shortage") and cont.get("has_productivity_deficit"):
            conflicts.append(
                "Compound Risk Detected: Both material shortages and contractor labor productivity deficits are active simultaneously. "
                "Supervisor Conclusion: Material stockout may be inducing labor idle time on site."
            )

        return conflicts

    def _identify_missing_information(
        self,
        sched: Dict[str, Any],
        proc: Dict[str, Any],
        cont: Dict[str, Any],
        forensic: Dict[str, Any]
    ) -> List[str]:
        """Lists critical data points missing from the telemetry needed to deepen investigation."""
        missing = []
        if not proc.get("has_material_requirement"):
            missing.append("Bill of Quantities (BOQ) mapping for this specific activity is not defined.")
        if not cont.get("has_labor_assignment"):
            missing.append("Dedicated contractor labor allocation records were not found for this activity.")
        missing.append("Daily site weather and precipitation telemetry logs.")
        missing.append("Approved change-order request timestamps and client approval signatures.")
        return missing

    def _synthesize_executive_narrative(
        self,
        sched: Dict[str, Any],
        proc: Dict[str, Any],
        cost: Dict[str, Any],
        cont: Dict[str, Any],
        forensic: Dict[str, Any],
        risk: Dict[str, Any],
        forecast: Dict[str, Any]
    ) -> str:
        """Generates an executive-level risk briefing for senior leadership."""
        act_name = sched.get("activity_name", "Activity")
        delay = sched.get("delay_days", 0)
        is_crit = sched.get("is_critical_path", False)
        root_cause = forensic.get("probable_root_cause", "Unspecified")
        variance = cost.get("cost_variance", 0.0)
        burn_rate = cost.get("daily_actual_burn_rate", 0.0)
        pred_cost = forecast.get("predicted_final_cost", 0.0)

        crit_str = "is on the CRITICAL PATH and directly impacts project delivery" if is_crit else "is a non-critical activity with available schedule float"

        narrative = (
            f"**Executive Briefing for {act_name} ({sched.get('activity_id')})**\n\n"
            f"- **Schedule Impact**: Activity is currently delayed by **{delay} calendar days** ({crit_str}).\n"
            f"- **Probable Root Cause**: {root_cause} (Confidence: {forensic.get('confidence_level')}).\n"
            f"- **Financial Exposure**: Recorded baseline variance of **INR {variance:,.2f}**. "
            f"Ongoing delay incurs an estimated daily burn rate of **INR {burn_rate:,.2f}/day**, "
            f"with final completion cost projected at **INR {pred_cost:,.2f}**.\n"
            f"- **Responsible Entities**: Contractor: *{cont.get('contractor_name', 'N/A')}* | "
            f"Materials Involved: *{', '.join(forensic.get('materials_involved', [])[:3]) or 'None'}*.\n"
            f"- **Recommended Priority**: **{risk.get('risk_level')}** (Risk Score: {risk.get('risk_score')}/100)."
        )
        return narrative
