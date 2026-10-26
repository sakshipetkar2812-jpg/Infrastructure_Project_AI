"""
Interactive Streamlit Dashboard for Infrastructure Project Delay & Cost Overrun Intelligence Agent.
Provides real-time schedule analysis, procurement monitoring, cost forensics,
RAG legal search, multi-agent root cause investigation, and AI conversational assistance.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Ensure project root is in Python sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing.loader import ProjectDataLoader
from src.data_processing.quality import DataQualityChecker
from src.analytics.schedule_engine import ScheduleEngine
from src.analytics.procurement_engine import ProcurementEngine
from src.analytics.cost_engine import CostEngine
from src.analytics.contractor_engine import ContractorEngine
from src.analytics.investigation_engine import RootCauseInvestigationEngine
from src.analytics.risk_engine import RiskAndForecastingEngine
from src.rag.contract_rag import ContractRAGEngine
from src.agents.specialists import (
    ScheduleAgent,
    ProcurementAgent,
    CostAgent,
    ContractorAgent,
    ContractAgent
)
from src.agents.supervisor import ProjectRiskSupervisor
from src.services.chat_assistant import ProjectAssistantService

# Streamlit Page Setup
st.set_page_config(
    page_title="Infrastructure Project Intelligence Agent",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-critical {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-high {
        background-color: #FFEDD5;
        color: #9A3412;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-success {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Initializing Infrastructure AI Intelligence Engine...")
def init_system():
    """Initializes and caches data loaders, analytical engines, and RAG pipelines."""
    loader = ProjectDataLoader()
    datasets = loader.load_all()

    quality_checker = DataQualityChecker(datasets)
    quality_report = quality_checker.run_full_audit()

    sched_engine = ScheduleEngine(datasets.get("activities", pd.DataFrame()), datasets.get("dependencies", pd.DataFrame()))
    analyzed_act = sched_engine.analyze()

    proc_engine = ProcurementEngine(
        datasets.get("boq", pd.DataFrame()),
        datasets.get("material_consumption", pd.DataFrame()),
        datasets.get("goods_receipts", pd.DataFrame()),
        datasets.get("inventory", pd.DataFrame()),
        datasets.get("materials", pd.DataFrame())
    )

    cost_engine = CostEngine(
        analyzed_act,
        datasets.get("cost_ledger", pd.DataFrame()),
        datasets.get("cost_reconciliation", pd.DataFrame())
    )

    contractor_engine = ContractorEngine(
        datasets.get("contractors", pd.DataFrame()),
        datasets.get("labor_assignments", pd.DataFrame())
    )

    rag_engine = ContractRAGEngine(datasets.get("contract_clauses", pd.DataFrame()))
    rag_engine.build_index()

    inv_engine = RootCauseInvestigationEngine(
        sched_engine, proc_engine, cost_engine, contractor_engine, rag_engine
    )

    risk_engine = RiskAndForecastingEngine(analyzed_act, datasets.get("contractors", pd.DataFrame()))

    # Agents
    s_agent = ScheduleAgent(sched_engine)
    p_agent = ProcurementAgent(proc_engine)
    c_agent = CostAgent(cost_engine)
    k_agent = ContractorAgent(contractor_engine)
    leg_agent = ContractAgent(rag_engine)

    supervisor = ProjectRiskSupervisor(
        s_agent, p_agent, c_agent, k_agent, leg_agent, inv_engine, risk_engine
    )

    assistant = ProjectAssistantService(
        supervisor, sched_engine, proc_engine, cost_engine, contractor_engine, rag_engine
    )

    return {
        "datasets": datasets,
        "quality_report": quality_report,
        "sched_engine": sched_engine,
        "proc_engine": proc_engine,
        "cost_engine": cost_engine,
        "contractor_engine": contractor_engine,
        "rag_engine": rag_engine,
        "inv_engine": inv_engine,
        "risk_engine": risk_engine,
        "supervisor": supervisor,
        "assistant": assistant
    }


sys_ctx = init_system()
datasets = sys_ctx["datasets"]
quality_report = sys_ctx["quality_report"]
sched_engine = sys_ctx["sched_engine"]
proc_engine = sys_ctx["proc_engine"]
cost_engine = sys_ctx["cost_engine"]
contractor_engine = sys_ctx["contractor_engine"]
rag_engine = sys_ctx["rag_engine"]
inv_engine = sys_ctx["inv_engine"]
risk_engine = sys_ctx["risk_engine"]
supervisor = sys_ctx["supervisor"]
assistant = sys_ctx["assistant"]

activities_df = sched_engine.processed_df

# Sidebar Controls
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=60)
    st.title("Project Controls")
    st.caption("AI Delay & Cost Overrun Agent")

    all_projects = sorted(activities_df["project_id"].unique()) if not activities_df.empty else ["PRJ-0001"]
    selected_project = st.selectbox("Select Active Project", all_projects, index=0)

    proj_acts = activities_df[activities_df["project_id"] == selected_project]
    act_options = sorted(proj_acts["activity_id"].unique()) if not proj_acts.empty else []
    selected_activity = st.selectbox("Focus Activity ID", act_options, index=0 if act_options else None)

    st.divider()
    st.markdown(f"**Data Cutoff Date:** `2026-08-20`")
    st.markdown(f"**Data Quality Score:** `{quality_report.get('overall_health_score', 98.0)}/100`")
    st.caption("All metrics strictly grounded in attached workspace data.")

# Main Header
st.markdown('<div class="main-header">Infrastructure Project Delay & Cost Overrun Intelligence</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">Program Monitoring, Cross-Domain Forensics, Legal Contract RAG & AI Decision Support | Viewing: <b>{selected_project}</b></div>', unsafe_allow_html=True)

# 11 Dashboard Navigation Tabs
tabs = st.tabs([
    "📊 Overview",
    "📅 Schedule",
    "⚠️ High-Risk",
    "📦 Procurement",
    "👷 Contractors",
    "💰 Cost Variance",
    "🔍 Root Cause",
    "📜 Contract RAG",
    "💬 AI Assistant",
    "🎯 Actions & Recs",
    "📋 Data Quality"
])

# ----------------- TAB 1: OVERVIEW -----------------
with tabs[0]:
    st.subheader(f"Portfolio & Project Scorecard: {selected_project}")
    p_kpi = sched_engine.get_kpis(selected_project)
    c_kpi = cost_engine.get_portfolio_cost_kpis(selected_project)
    pr_kpi = proc_engine.get_kpis(selected_project)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Activities", p_kpi.get("total_activities", 0), f"{p_kpi.get('completed_activities')} completed")
    col2.metric("Delayed Activities", p_kpi.get("delayed_activities", 0), f"{p_kpi.get('delayed_pct')}% of total", delta_color="inverse")
    col3.metric("Critical Path Delayed", p_kpi.get("critical_activities_delayed", 0), "High priority", delta_color="inverse")
    col4.metric("Cost Variance", f"₹{c_kpi.get('total_cost_variance', 0):,.0f}", f"{c_kpi.get('cost_variance_percentage')}%", delta_color="inverse")
    col5.metric("Material Shortages", pr_kpi.get("materials_with_shortage", 0), "Warehouse alerts", delta_color="inverse")

    st.divider()
    c_left, c_right = st.columns([3, 2])

    with c_left:
        st.markdown("#### Activity Execution Status & Delay Distribution")
        status_counts = proj_acts["status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig_status = px.pie(status_counts, names="Status", values="Count", hole=0.45,
                            color_discrete_sequence=["#3B82F6", "#10B981", "#F59E0B"])
        st.plotly_chart(fig_status, use_container_width=True)

    with c_right:
        st.markdown("#### Delay Severity Breakdown")
        delay_cats = proj_acts["delay_category"].value_counts().reset_index()
        delay_cats.columns = ["Severity", "Count"]
        fig_sev = px.bar(delay_cats, x="Severity", y="Count", color="Severity",
                         color_discrete_map={"ON_TIME": "#10B981", "LOW_DELAY": "#FBBF24", "MEDIUM_DELAY": "#F97316", "CRITICAL_DELAY": "#EF4444"})
        st.plotly_chart(fig_sev, use_container_width=True)

# ----------------- TAB 2: SCHEDULE ANALYSIS -----------------
with tabs[1]:
    st.subheader(f"Schedule Baseline vs Execution: {selected_project}")
    st.caption("Evaluated strictly against the verified program cutoff date (2026-08-20).")

    delayed_acts = proj_acts[proj_acts["delay_days"] > 0].sort_values(by="delay_days", ascending=False)

    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        fig_scatter = px.scatter(
            proj_acts,
            x="planned_duration_calc",
            y="delay_days",
            color="delay_category",
            size="baseline_cost",
            hover_name="activity_name",
            hover_data=["activity_id", "status", "is_critical_effective"],
            labels={"planned_duration_calc": "Planned Duration (Days)", "delay_days": "Observed Delay (Days)"},
            title="Activity Duration vs Delay Days (Size = Baseline Budget)"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_s2:
        st.markdown("#### Schedule Summary Metrics")
        st.write(f"- **Overdue Activities:** {p_kpi.get('overdue_activities')}")
        st.write(f"- **Delayed Milestones:** {p_kpi.get('milestones_delayed')}")
        st.write(f"- **Average Delay:** {p_kpi.get('average_delay_days')} days")
        st.write(f"- **Maximum Recorded Delay:** {p_kpi.get('maximum_delay_days')} days")
        st.info("Note: Activities without actual finish dates are in progress and evaluated against the project cutoff date.")

    st.markdown("#### Detailed Schedule Table")
    st.dataframe(
        proj_acts[[
            "activity_id", "activity_name", "status", "planned_start", "planned_finish",
            "actual_start", "actual_finish", "delay_days", "is_critical_effective", "is_overdue"
        ]],
        use_container_width=True,
        height=320
    )

# ----------------- TAB 3: HIGH RISK ACTIVITIES -----------------
with tabs[2]:
    st.subheader("Critical & High-Risk Activities Radar")
    st.caption("Identified using multi-factor deterministic risk scoring (Schedule + Float + Materials + Labor + Cost).")

    # Score activities in this project
    risk_list = []
    for _, r in proj_acts.iterrows():
        p_stat = proc_engine.get_activity_material_status(r["activity_id"], selected_project)
        c_stat = contractor_engine.get_activity_contractor_status(r["activity_id"], selected_project)
        r_profile = risk_engine.calculate_activity_risk_score(r, p_stat, c_stat)
        risk_list.append({
            "activity_id": r["activity_id"],
            "activity_name": r["activity_name"],
            "risk_score": r_profile["risk_score"],
            "risk_level": r_profile["risk_level"],
            "delay_days": r["delay_days"],
            "is_critical": r["is_critical_effective"],
            "cost_variance_pct": r_profile["cost_variance_pct"],
            "has_shortage": p_stat.get("has_shortage", False),
            "has_labor_deficit": c_stat.get("has_productivity_deficit", False)
        })

    risk_df = pd.DataFrame(risk_list).sort_values(by="risk_score", ascending=False)
    high_risk_df = risk_df[risk_df["risk_score"] >= 45.0]

    col_r1, col_r2 = st.columns([3, 1])
    with col_r1:
        fig_risk = px.histogram(risk_df, x="risk_score", color="risk_level",
                                color_discrete_map={"LOW": "#10B981", "MEDIUM": "#FBBF24", "HIGH": "#F97316", "CRITICAL": "#EF4444"},
                                nbins=20, title="Risk Score Distribution Across Activities")
        st.plotly_chart(fig_risk, use_container_width=True)

    with col_r2:
        st.metric("Critical Risk Activities", len(risk_df[risk_df["risk_level"] == "CRITICAL"]))
        st.metric("High Risk Activities", len(risk_df[risk_df["risk_level"] == "HIGH"]))
        st.metric("Medium Risk Activities", len(risk_df[risk_df["risk_level"] == "MEDIUM"]))

    st.markdown("#### High-Risk Priority Queue")
    st.dataframe(high_risk_df, use_container_width=True, height=280)

# ----------------- TAB 4: PROCUREMENT MONITORING -----------------
with tabs[3]:
    st.subheader(f"Procurement & Inventory Telemetry: {selected_project}")
    st.caption("Cross-referencing Bill of Quantities, Goods Receipts (GRN), and Warehouse Stock.")

    pr_detail = proc_engine.get_kpis(selected_project)
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("Receipts Monitored", pr_detail.get("total_goods_receipts", 0))
    col_p2.metric("Overall Acceptance Rate", f"{pr_detail.get('overall_acceptance_rate_pct', 100)}%")
    col_p3.metric("Deficit Material Items", pr_detail.get("materials_with_shortage", 0), delta_color="inverse")

    # Inventory Table for this project
    inv_df = datasets.get("inventory", pd.DataFrame())
    if not inv_df.empty and "project_id" in inv_df.columns:
        p_inv = inv_df[inv_df["project_id"] == selected_project].copy()
        if not p_inv.empty:
            mats_master = datasets.get("materials", pd.DataFrame())
            if not mats_master.empty:
                p_inv = p_inv.merge(mats_master[["material_id", "material_name", "category"]], on="material_id", how="left")
            p_inv["is_shortage"] = p_inv["closing_stock"] < p_inv["reserved_quantity"]
            p_inv["shortage_units"] = np.maximum(0, p_inv["reserved_quantity"] - p_inv["closing_stock"])

            st.markdown("#### Warehouse Inventory Stock Status")
            st.dataframe(
                p_inv[["material_id", "material_name", "category", "closing_stock", "reserved_quantity", "is_shortage", "shortage_units"]],
                use_container_width=True
            )

# ----------------- TAB 5: CONTRACTOR & LABOR PERFORMANCE -----------------
with tabs[4]:
    st.subheader("Contractor & Site Labor Performance Benchmarks")
    st.caption("Evaluates historical contractor risk profiles and site-level daily crew productivity.")

    con_df = datasets.get("contractors", pd.DataFrame())
    if not con_df.empty:
        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            fig_con = px.scatter(
                con_df,
                x="average_delay_days",
                y="average_cost_overrun_pct",
                size="historical_risk_score",
                color="historical_risk_score",
                hover_name="contractor_name",
                hover_data=["contractor_id", "license_type", "projects_completed"],
                labels={"average_delay_days": "Avg Delay Days (Past Projects)", "average_cost_overrun_pct": "Avg Cost Overrun %"},
                title="Contractor Historical Risk Matrix (Color & Size = Risk Score)"
            )
            st.plotly_chart(fig_con, use_container_width=True)

        with col_c2:
            st.markdown("#### Contractor Risk Thresholds")
            st.write("- **High Risk Score:** ≥ 75.0")
            st.write("- **Historical Delay Alert:** ≥ 5.0 days")
            st.write(f"- **Active Contractors:** {len(con_df)}")
            high_risk_cons = con_df[con_df["historical_risk_score"] >= 75.0]
            st.warning(f"⚠️ {len(high_risk_cons)} contractors flagged as High Risk based on past project records.")

        st.markdown("#### Master Contractor Registry")
        st.dataframe(con_df, use_container_width=True, height=250)

# ----------------- TAB 6: COST ANALYSIS -----------------
with tabs[5]:
    st.subheader(f"Financial Variance & Cost Ledger Breakdown: {selected_project}")
    st.caption("Transparent baseline vs actual spend with zero fabricated figures.")

    c_kpis = cost_engine.get_portfolio_cost_kpis(selected_project)
    col_cost1, col_cost2, col_cost3, col_cost4 = st.columns(4)
    col_cost1.metric("Baseline Budget", f"₹{c_kpis.get('total_baseline_cost', 0):,.2f}")
    col_cost2.metric("Actual Spend", f"₹{c_kpis.get('total_actual_cost', 0):,.2f}")
    col_cost3.metric("Net Cost Variance", f"₹{c_kpis.get('total_cost_variance', 0):,.2f}", f"{c_kpis.get('cost_variance_percentage')}%", delta_color="inverse")
    col_cost4.metric("Overrun Activities", c_kpis.get("activities_over_budget", 0))

    st.divider()
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.markdown("#### Expenditures by Ledger Category")
        cat_dict = c_kpis.get("ledger_by_category", {})
        if cat_dict:
            cat_df = pd.DataFrame(list(cat_dict.items()), columns=["Category", "Amount"])
            fig_cat = px.bar(cat_df, x="Category", y="Amount", color="Category", title="Incurred Spend by Cost Type (INR)")
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("No ledger category records available for this project.")

    with col_l2:
        st.markdown("#### Cost Calibration & Reconciliation")
        calib = c_kpis.get("calibration_metrics", {})
        if calib:
            st.write(f"- **Calibrated Historical Records:** {calib.get('historical_calibrations_count')}")
            st.write(f"- **Mean Absolute Error (MAE):** ₹{calib.get('mean_absolute_error'):,.2f}")
            st.write(f"- **Mean Percentage Error (MAPE):** {calib.get('mean_percentage_error')}%")
            st.success("Financial models are calibrated against ground-truth reconciliation records.")
        else:
            st.info("Reconciliation calibration data not loaded.")

# ----------------- TAB 7: ROOT CAUSE INVESTIGATION -----------------
with tabs[6]:
    st.subheader(f"Forensic Multi-Source Investigation: `{selected_activity}`")
    st.caption("Correlates schedule slippage, warehouse stockouts, labor deficits, and contract terms.")

    if selected_activity:
        forensic = supervisor.conduct_full_investigation(selected_activity, selected_project)

        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            st.markdown(f"### Activity: {forensic.get('activity_name')}")
            st.markdown(f"**Probable Root Cause:** `{forensic.get('probable_root_cause')}`")
            st.markdown(f"**Confidence Level:** `{forensic.get('confidence_level')}`")

            st.markdown("#### Supporting Empirical Evidence")
            for ev in forensic.get("supporting_evidence", []):
                st.markdown(f"- 🔎 {ev}")

            if forensic.get("conflicts_identified"):
                st.markdown("#### Inter-Agent Discrepancies & Resolution")
                for conf in forensic.get("conflicts_identified"):
                    st.warning(conf)

        with col_f2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown("#### Forensic Snapshot")
            st.write(f"**Status:** `{forensic.get('status')}`")
            st.write(f"**Delay:** **{forensic.get('specialist_telemetry', {}).get('schedule', {}).get('delay_days')} days**")
            st.write(f"**Critical Path:** {'YES ⚠️' if forensic.get('specialist_telemetry', {}).get('schedule', {}).get('is_critical_path') else 'NO'}")
            st.write(f"**Contractor:** {forensic.get('specialist_telemetry', {}).get('contractor', {}).get('contractor_name')}")
            st.write(f"**Cost Variance:** ₹{forensic.get('specialist_telemetry', {}).get('cost', {}).get('cost_variance', 0):,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.markdown("#### Executive Risk Narrative")
        st.markdown(forensic.get("executive_summary", ""))

# ----------------- TAB 8: CONTRACT RAG DOCUMENT SEARCH -----------------
with tabs[7]:
    st.subheader("Legal Contract RAG Document Intelligence")
    st.caption("Semantic retrieval grounded in 30 actual contract agreements and 180 structured clauses.")

    rag_query = st.text_input(
        "Enter legal, commercial, or contract query:",
        value="What liquidated damages or penalties apply if supplier delivery is delayed?",
        placeholder="e.g., change order approvals, quality rejection remedies, delay liquidated damages"
    )

    if st.button("Search Contract Repository", type="primary"):
        with st.spinner("Retrieving grounded clauses from vector index..."):
            rag_result = rag_engine.answer_contract_question(rag_query)

            st.markdown("### Answer Synthesis")
            st.markdown(rag_result["answer"])

            st.markdown("### Verbatim Source Citations")
            for cit in rag_result.get("citations", []):
                with st.expander(f"📄 {cit['contract_id']} - Clause {cit['clause_number']}: {cit['title']} (Page {cit['page']})"):
                    st.markdown(f"**Verbatim Contract Text:**\n> {cit['verbatim_text']}")
                    st.caption(f"Liquidated Damages / Penalty Applicable: {cit['penalty_applicable']}")

# ----------------- TAB 9: AI PROJECT ASSISTANT -----------------
with tabs[8]:
    st.subheader("Natural-Language Infrastructure Assistant")
    st.caption("Ask factual questions about schedules, bottlenecks, financial variance, or legal obligations.")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": f"Hello! I am your Project Intelligence Assistant for **{selected_project}**. Ask me any question regarding delayed activities, root causes, budget variance, or contract clauses."}
        ]

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Quick prompt buttons
    p1, p2, p3 = st.columns(3)
    if p1.button(f"Which activities are delayed in {selected_project}?"):
        user_prompt = f"Which activities are delayed in {selected_project}?"
    elif p2.button(f"Why is {selected_activity} delayed?"):
        user_prompt = f"Why is {selected_activity} delayed?"
    elif p3.button("What is the recorded budget variance?"):
        user_prompt = "What is the recorded budget variance?"
    else:
        user_prompt = st.chat_input("Ask a question about the project...")

    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Querying project telemetry and contract index..."):
                resp = assistant.answer_query(user_prompt, active_project_id=selected_project, active_activity_id=selected_activity)
                ans_text = resp["answer"]
                st.markdown(ans_text)
                st.session_state.chat_history.append({"role": "assistant", "content": ans_text})

# ----------------- TAB 10: EVIDENCE & RECOMMENDATIONS -----------------
with tabs[9]:
    st.subheader(f"Actionable Decision Support & Interventions: `{selected_activity}`")
    st.caption("Evidence-backed corrective strategies with human-in-the-loop escalation controls.")

    if selected_activity:
        forensic_rec = supervisor.conduct_full_investigation(selected_activity, selected_project)
        recs = forensic_rec.get("recommendations", [])

        for idx, r in enumerate(recs, 1):
            with st.container():
                st.markdown(f"#### {idx}. [{r.get('suggested_priority')}] {r.get('proposed_action')}")
                c_a, c_b = st.columns([3, 1])
                with c_a:
                    st.write(f"**Identified Problem:** {r.get('problem')}")
                    st.write(f"**Rationale:** {r.get('rationale')}")
                    st.write(f"**Expected Benefit:** {r.get('expected_benefit')}")
                    st.write(f"**Implementation Risks:** {r.get('risks_and_dependencies')}")
                with c_b:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.write(f"**Authority:** `{r.get('decision_authority')}`")
                    if r.get("human_approval_required"):
                        st.markdown('<span class="badge-critical">Human Approval Required</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge-success">Routine Execution</span>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                st.divider()

# ----------------- TAB 11: DATA QUALITY REPORT -----------------
with tabs[10]:
    st.subheader("Data Quality, Integrity & Schema Verification")
    st.caption("Transparent automated auditing across all 14 project tables.")

    score = quality_report.get("overall_health_score", 100.0)
    col_q1, col_q2 = st.columns([1, 3])
    with col_q1:
        st.metric("Overall Quality Score", f"{score}/100.0")
        if score >= 90:
            st.success("Data quality grade: EXCELLENT")
        elif score >= 75:
            st.warning("Data quality grade: ACCEPTABLE")
        else:
            st.error("Data quality grade: CRITICAL ATTENTION")

    with col_q2:
        st.markdown("#### Audit Findings & Observations")
        for finding in quality_report.get("findings_summary", []):
            st.markdown(f"- 🛡️ {finding}")

    st.markdown("#### Referential Integrity Across Operational Datasets")
    st.json(quality_report.get("referential_integrity", {}))

    st.markdown("#### Table Missingness & Duplicate Profiling")
    st.json(quality_report.get("table_summaries", {}))
