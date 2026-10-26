"""
Natural-Language Infrastructure Project Assistant Service.
Processes user queries by routing to deterministic analytics engines, RAG contract retrieval,
or multi-agent supervisor forensics, ensuring answers are grounded strictly in factual data.
"""

from typing import Dict, Any, List, Optional
import re
import pandas as pd

from src.agents.supervisor import ProjectRiskSupervisor
from src.analytics.schedule_engine import ScheduleEngine
from src.analytics.procurement_engine import ProcurementEngine
from src.analytics.cost_engine import CostEngine
from src.analytics.contractor_engine import ContractorEngine
from src.rag.contract_rag import ContractRAGEngine


class ProjectAssistantService:
    """
    Intelligent conversational query engine for infrastructure project data.
    Routes queries to structured databases or RAG pipelines; never hallucinates figures.
    """

    def __init__(
        self,
        supervisor: ProjectRiskSupervisor,
        schedule_engine: ScheduleEngine,
        procurement_engine: ProcurementEngine,
        cost_engine: CostEngine,
        contractor_engine: ContractorEngine,
        rag_engine: ContractRAGEngine
    ):
        self.supervisor = supervisor
        self.schedule_engine = schedule_engine
        self.procurement_engine = procurement_engine
        self.cost_engine = cost_engine
        self.contractor_engine = contractor_engine
        self.rag_engine = rag_engine

    def answer_query(self, query: str, active_project_id: str = "PRJ-0001", active_activity_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes the intent of the query and returns a factual, data-backed answer.
        """
        q = query.lower().strip()

        # Extract explicit activity ID if mentioned in the query (e.g., ACT-0001 or PRJ-0001-ACT-0001)
        act_match = re.search(r"(PRJ-\d{4}-ACT-\d{4}|ACT-\d{4})", query, re.IGNORECASE)
        target_activity_id = active_activity_id
        if act_match:
            found = act_match.group(1).upper()
            if not found.startswith("PRJ-"):
                target_activity_id = f"{active_project_id}-{found}"
            else:
                target_activity_id = found

        # Extract explicit project ID if mentioned (e.g. PRJ-0005)
        prj_match = re.search(r"(PRJ-\d{4})", query, re.IGNORECASE)
        target_project_id = prj_match.group(1).upper() if prj_match else active_project_id

        # Intent 1: Why is an activity delayed? / Root cause investigation
        if "why" in q or "root cause" in q or "reason" in q or "investigate" in q:
            if target_activity_id:
                investigation = self.supervisor.conduct_full_investigation(target_activity_id, target_project_id)
                if investigation.get("status") == "ERROR":
                    return {
                        "query": query,
                        "answer": f"Investigation could not be completed: {investigation.get('message')}",
                        "source": "Supervisor Engine"
                    }

                answer = (
                    f"### Root Cause Investigation for `{target_activity_id}`\n\n"
                    f"- **Activity Name**: {investigation.get('activity_name')}\n"
                    f"- **Status**: `{investigation.get('status')}` | **Delay**: **{investigation.get('specialist_telemetry', {}).get('schedule', {}).get('delay_days')} days**\n"
                    f"- **Critical Path Impact**: {'YES (Direct Project Delay)' if investigation.get('specialist_telemetry', {}).get('schedule', {}).get('is_critical_path') else 'NO'}\n"
                    f"- **Probable Root Cause**: **{investigation.get('probable_root_cause')}** (Confidence: {investigation.get('confidence_level')})\n\n"
                    f"**Supporting Evidence:**\n" +
                    "\n".join([f"- {e}" for e in investigation.get("supporting_evidence", ["No direct anomalies recorded."])]) +
                    f"\n\n**Executive Briefing:**\n{investigation.get('executive_summary')}"
                )
                return {
                    "query": query,
                    "answer": answer,
                    "source": "Supervisor Forensic Engine",
                    "details": investigation
                }
            else:
                return {
                    "query": query,
                    "answer": "Please specify an Activity ID (e.g., `PRJ-0001-ACT-0001`) to run a root cause forensic investigation.",
                    "source": "Supervisor Engine"
                }

        # Intent 2: Which activities are delayed?
        if "which activities are delayed" in q or "delayed activities" in q or "delayed" in q and "which" in q:
            df = self.schedule_engine.processed_df
            if df.empty:
                df = self.schedule_engine.analyze()

            p_df = df[df["project_id"] == target_project_id]
            delayed = p_df[p_df["delay_days"] > 0].sort_values(by="delay_days", ascending=False)
            count = len(delayed)

            if count == 0:
                return {
                    "query": query,
                    "answer": f"All recorded activities in project **{target_project_id}** are currently progressing on or ahead of baseline schedule.",
                    "source": "Schedule Engine"
                }

            top_delayed = delayed.head(5)
            rows_str = []
            for _, r in top_delayed.iterrows():
                crit_flag = "⚠️ Critical Path" if r.get("is_critical_effective") else "Normal Float"
                rows_str.append(f"- **{r.activity_id}** ({r.activity_name}): **{r.delay_days} days delay** ({r.status}) - *{crit_flag}*")

            answer = (
                f"### Delayed Activities in Project `{target_project_id}`\n\n"
                f"A total of **{count} activities** have recorded delay or are overdue against the 2026-08-20 cutoff date.\n\n"
                f"**Top Most Delayed Activities:**\n" + "\n".join(rows_str) +
                f"\n\n*Use 'Why is PRJ-0001-ACT-0001 delayed?' to run a deep root-cause forensic investigation on any activity.*"
            )
            return {"query": query, "answer": answer, "source": "Schedule Engine"}

        # Intent 3: Critical path impact / project completion
        if "critical path" in q or "affect project completion" in q or "milestone" in q:
            df = self.schedule_engine.processed_df
            if df.empty:
                df = self.schedule_engine.analyze()

            p_df = df[df["project_id"] == target_project_id]
            crit_delayed = p_df[p_df["critical_path_impact"]].sort_values(by="delay_days", ascending=False)

            if crit_delayed.empty:
                return {
                    "query": query,
                    "answer": f"No critical path activities in **{target_project_id}** are currently delayed.",
                    "source": "Critical Path Engine"
                }

            rows_str = []
            for _, r in crit_delayed.head(5).iterrows():
                rows_str.append(f"- **{r.activity_id}** ({r.activity_name}): **{r.delay_days} days** ({r.status})")

            answer = (
                f"### Critical Path Activities Threatening Project Completion (`{target_project_id}`)\n\n"
                f"There are **{len(crit_delayed)} critical-path activities** currently experiencing delay, directly threatening the program completion date:\n\n" +
                "\n".join(rows_str)
            )
            return {"query": query, "answer": answer, "source": "Critical Path Engine"}

        # Intent 4: Budget / Cost Variance
        if "budget" in q or "cost variance" in q or "spend" in q or "overrun" in q:
            cost_kpi = self.cost_engine.get_portfolio_cost_kpis(target_project_id)
            if cost_kpi.get("status") == "Insufficient data":
                return {"query": query, "answer": "Insufficient cost data available for this project.", "source": "Cost Engine"}

            answer = (
                f"### Financial & Cost Variance Summary (`{target_project_id}`)\n\n"
                f"- **Baseline Budget**: INR {cost_kpi['total_baseline_cost']:,.2f}\n"
                f"- **Actual Incurred Spend**: INR {cost_kpi['total_actual_cost']:,.2f}\n"
                f"- **Total Cost Variance**: INR {cost_kpi['total_cost_variance']:,.2f} (**{cost_kpi['cost_variance_percentage']}%**)\n"
                f"- **Activities Over Budget**: {cost_kpi['activities_over_budget']} (Severe overruns >10%: {cost_kpi['activities_severe_overrun']})\n\n"
                f"**Expenditures by Category:**\n" +
                "\n".join([f"- **{k}**: INR {v:,.2f}" for k, v in cost_kpi.get("ledger_by_category", {}).items()])
            )
            return {"query": query, "answer": answer, "source": "Cost Engine"}

        # Intent 5: Supplier / Contractor performance
        if "supplier" in q or "contractor" in q or "vendor" in q:
            con_kpi = self.contractor_engine.get_portfolio_kpis()
            proc_kpi = self.procurement_engine.get_kpis(target_project_id)

            answer = (
                f"### Contractor & Supplier Performance Benchmarks\n\n"
                f"- **Total Contractors Monitored**: {con_kpi.get('total_contractors')}\n"
                f"- **High-Risk Contractors (Score >= 75)**: {con_kpi.get('high_risk_contractor_count')}\n"
                f"- **Average Historical Delay**: {con_kpi.get('average_historical_delay_days')} days\n"
                f"- **Procurement Acceptance Rate**: {proc_kpi.get('overall_acceptance_rate_pct')}% "
                f"({proc_kpi.get('rejected_shipment_count')} shipments flagged with defect rejections)\n"
                f"- **Materials with Active Warehouse Deficits**: {proc_kpi.get('materials_with_shortage')}"
            )
            return {"query": query, "answer": answer, "source": "Contractor & Procurement Engines"}

        # Intent 6: Contractual / Legal Clause inquiries (RAG)
        if "contract" in q or "clause" in q or "liquidated damages" in q or "penalty" in q or "warranty" in q or "change order" in q:
            rag_res = self.rag_engine.answer_contract_question(query)
            return {
                "query": query,
                "answer": rag_res["answer"],
                "source": "Contract RAG Intelligence Engine",
                "citations": rag_res.get("citations", [])
            }

        # Intent 7: Recommendations
        if "recommend" in q or "action" in q or "what should we do" in q:
            if target_activity_id:
                forensic = self.supervisor.investigation_engine.investigate_activity(target_activity_id, target_project_id)
                recs = self.supervisor.conduct_full_investigation(target_activity_id, target_project_id).get("recommendations", [])
                rec_strs = []
                for idx, r in enumerate(recs, 1):
                    rec_strs.append(
                        f"**{idx}. [{r.get('suggested_priority')}] {r.get('proposed_action')}**\n"
                        f"- *Rationale*: {r.get('rationale')}\n"
                        f"- *Expected Benefit*: {r.get('expected_benefit')}\n"
                        f"- *Approval Required*: {'YES (Authorized Leadership)' if r.get('human_approval_required') else 'NO'}"
                    )
                return {
                    "query": query,
                    "answer": f"### Corrective Recommendations for `{target_activity_id}`\n\n" + "\n\n".join(rec_strs),
                    "source": "Recommendation Engine"
                }

        # Fallback: RAG and Data Summary
        rag_attempt = self.rag_engine.answer_contract_question(query)
        if rag_attempt.get("evidence_retrieved"):
            return {
                "query": query,
                "answer": rag_attempt["answer"],
                "source": "Contract RAG Engine",
                "citations": rag_attempt.get("citations", [])
            }

        return {
            "query": query,
            "answer": (
                "I analyzed your inquiry against the project schedule, procurement, cost ledger, and contract repositories. "
                "To get precise details, you can ask:\n\n"
                "- *'Which activities are delayed in PRJ-0001?'*\n"
                "- *'Why is PRJ-0001-ACT-0001 delayed?'*\n"
                "- *'What is the recorded budget variance?'*\n"
                "- *'Which activities may affect project completion?'*\n"
                "- *'What liquidated damages apply for late material delivery under Clause 8.4?'*"
            ),
            "source": "Project Assistant Router"
        }
