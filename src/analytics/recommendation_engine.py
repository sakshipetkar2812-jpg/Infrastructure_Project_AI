"""
Practical Corrective Recommendation Engine for Infrastructure Leadership.
Generates structured, evidence-backed corrective strategies with expected benefits,
implementation risks, priorities, and strict Human-in-the-Loop approval requirements.
"""

from typing import Dict, Any, List, Optional


class RecommendationEngine:
    """
    Synthesizes investigation outcomes into actionable, prioritized leadership interventions.
    Strictly functions as a decision-support system; never executes external actions autonomously.
    """

    @staticmethod
    def generate_recommendations(investigation_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Produces prioritized corrective actions grounded in the forensic investigation findings.
        """
        recommendations = []
        probable_cause = investigation_result.get("probable_root_cause", "")
        delay_days = investigation_result.get("observed_delay_days", 0)
        is_critical = investigation_result.get("is_critical_path", False)
        cost_variance = investigation_result.get("cost_variance", 0.0)
        activity_name = investigation_result.get("activity_name", "")
        contractor = investigation_result.get("contractor_involved", "Contractor")
        materials = investigation_result.get("materials_involved", [])

        # Priority calculation
        base_priority = "CRITICAL" if (is_critical and delay_days > 10) else ("HIGH" if is_critical or delay_days > 5 else "MEDIUM")

        # 1. Recommendations for Material / Supplier Bottlenecks
        if "Material" in probable_cause or "Supplier" in probable_cause:
            recommendations.append({
                "problem": f"Material delivery delay / inventory stockout affecting '{activity_name}'.",
                "proposed_action": f"Issue Formal Expediting Notice to supplier and evaluate inventory transfer for {', '.join(materials[:2])}.",
                "rationale": "Material shortages directly halt site progress and inflate daily overhead holding costs.",
                "supporting_evidence": investigation_result.get("supporting_evidence", ["Confirmed material stock deficit in project warehouse."]),
                "expected_benefit": "Restores material supply within standard lead times and prevents further critical path slip.",
                "risks_and_dependencies": "Potential premium freight or expedited transport surcharge.",
                "suggested_priority": base_priority,
                "human_approval_required": True,
                "decision_authority": "Procurement Lead / Project Director"
            })

            recommendations.append({
                "problem": "Supplier non-compliance with contractual delivery milestones.",
                "proposed_action": "Review contract terms and enforce Clause 8.4 (Delay & Liquidated Damages) after grace period.",
                "rationale": "Contractual notice protects the program's right to financial recovery and incentivizes supplier prioritization.",
                "supporting_evidence": [c.get("title", "Delay clause") for c in investigation_result.get("contract_citations", [])],
                "expected_benefit": "Financial offset against delay costs; enforces vendor contractual accountability.",
                "risks_and_dependencies": "Requires legal counsel review before formal liquidated damages claim submission.",
                "suggested_priority": "MEDIUM",
                "human_approval_required": True,
                "decision_authority": "Commercial & Contracts Director"
            })

        # 2. Recommendations for Contractor / Labor Productivity Deficit
        if "Labor" in probable_cause or "Contractor" in probable_cause:
            recommendations.append({
                "problem": f"Deployed labor productivity for {contractor} is below pace required to meet milestone.",
                "proposed_action": f"Direct {contractor} to augment crew headcount by 25% or implement dual-shift work schedule.",
                "rationale": "Empirical site records confirm remaining work cannot be finished before deadline at current productivity.",
                "supporting_evidence": investigation_result.get("supporting_evidence", ["Productivity deficit documented in labor allocations."]),
                "expected_benefit": "Recovers daily productivity rate to restore planned activity completion.",
                "risks_and_dependencies": "Increased congestion in working zone; contractor may submit claim for acceleration costs.",
                "suggested_priority": base_priority,
                "human_approval_required": True,
                "decision_authority": "Project Manager / Construction Lead"
            })

            recommendations.append({
                "problem": f"Repeated historical delay patterns by {contractor}.",
                "proposed_action": "Implement daily progress milestone monitoring and mandatory weekly productivity reviews.",
                "rationale": "Early detection of labor slippage prevents compounding critical-path slippage.",
                "supporting_evidence": ["Contractor historical risk score benchmark."],
                "expected_benefit": "Provides immediate visibility and rapid corrective escalation for site leadership.",
                "risks_and_dependencies": "Requires additional supervisory inspection hours.",
                "suggested_priority": "HIGH",
                "human_approval_required": False,
                "decision_authority": "Site Supervision Engineer"
            })

        # 3. Recommendations for Schedule Predecessor Slippage
        if "Predecessor" in probable_cause:
            recommendations.append({
                "problem": f"Activity start delayed due to unfinished predecessor work.",
                "proposed_action": "Perform schedule crashing / re-sequencing to decouple non-essential successor dependencies.",
                "rationale": "Finish-to-Start lags can often be converted to Start-to-Start (SS) with lead to allow early commencement.",
                "supporting_evidence": investigation_result.get("supporting_evidence", ["Predecessor delay documented in activity network."]),
                "expected_benefit": "Compresses downstream critical path duration by up to 5-10 calendar days.",
                "risks_and_dependencies": "Requires site safety and structural sequencing approval.",
                "suggested_priority": "HIGH",
                "human_approval_required": True,
                "decision_authority": "Lead Planning Engineer"
            })

        # 4. Recommendations for Financial Overrun
        if cost_variance > 0:
            recommendations.append({
                "problem": f"Cost overrun of INR {cost_variance:,.2f} recorded against baseline budget.",
                "proposed_action": "Audit ledger cost codes and review change order approvals under Clause 14.2.",
                "rationale": "Disproportionate equipment or subcontractor expenses must be verified against actual approved work orders.",
                "supporting_evidence": [f"Cost variance of {investigation_result.get('cost_variance_pct', 0)}% above baseline."],
                "expected_benefit": "Prevents unauthorized financial leakage and enforces invoice validation.",
                "risks_and_dependencies": "Invoice payments may be temporarily placed on hold during reconciliation.",
                "suggested_priority": "MEDIUM",
                "human_approval_required": True,
                "decision_authority": "Finance & Commercial Manager"
            })

        # Default recommendation if on time
        if not recommendations:
            recommendations.append({
                "problem": "Activity performing within normal schedule and cost tolerances.",
                "proposed_action": "Maintain routine baseline tracking and regular material inventory checks.",
                "rationale": "No critical anomalies or bottlenecks currently detected.",
                "supporting_evidence": ["Schedule variance within acceptable threshold."],
                "expected_benefit": "Ensures continued baseline execution.",
                "risks_and_dependencies": "None.",
                "suggested_priority": "LOW",
                "human_approval_required": False,
                "decision_authority": "Routine Project Controls"
            })

        return recommendations
