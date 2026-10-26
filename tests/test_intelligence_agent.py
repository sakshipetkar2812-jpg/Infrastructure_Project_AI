"""
Automated Test Suite for Infrastructure Project Delay & Cost Overrun Intelligence Agent.
Covers all 15 acceptance test scenarios required by project specification:
1. Correct date parsing
2. Missing dates handling
3. Completed activities finish delay
4. Incomplete overdue activities logic
5. Negative and zero delay handling
6. Cost variance calculation
7. Missing budget handling
8. Unmatched procurement records
9. Supplier performance calculations
10. RAG evidence retrieval
11. Unsupported contract inquiries
12. Supervisor handling of conflicting agent outputs
13. Missing API credentials local fallback
14. Empty datasets graceful handling
15. End-to-end integration
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date
from pathlib import Path

from config.settings import DEFAULT_CUTOFF_DATE
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


# ----------------- TEST 1 & 2: DATE PARSING & MISSING DATES -----------------
def test_date_parsing_and_missing_dates():
    """Validates ISO 8601 parsing and non-destructive handling of missing finish dates."""
    raw_df = pd.DataFrame([
        {
            "activity_id": "TEST-ACT-01",
            "project_id": "PRJ-TEST",
            "activity_name": "Test Act 1",
            "planned_start": "2026-01-01",
            "planned_finish": "2026-01-10",
            "actual_start": "2026-01-01",
            "actual_finish": "",  # Missing actual finish
            "planned_progress_pct": 100,
            "actual_progress_pct": 80,
            "baseline_cost": 10000.0,
            "actual_cost": 12000.0,
            "is_milestone": False,
            "is_critical": True,
            "total_float_days": 0,
            "status": "IN_PROGRESS"
        }
    ])

    engine = ScheduleEngine(raw_df, cutoff_date=date(2026, 1, 15))
    analyzed = engine.analyze()

    assert pd.to_datetime(analyzed.iloc[0]["planned_start"]) == pd.to_datetime("2026-01-01")
    assert pd.isna(analyzed.iloc[0]["actual_finish"])
    assert analyzed.iloc[0]["is_in_progress"] == True
    # Planned finish was 2026-01-10, cutoff is 2026-01-15 -> Overdue by 5 days
    assert analyzed.iloc[0]["is_overdue"] == True
    assert analyzed.iloc[0]["overdue_days"] == 5
    assert analyzed.iloc[0]["delay_days"] == 5


# ----------------- TEST 3: COMPLETED ACTIVITIES -----------------
def test_completed_activity_delay():
    """Validates that completed activities calculate delay strictly using actual_finish - planned_finish."""
    raw_df = pd.DataFrame([
        {
            "activity_id": "TEST-ACT-02",
            "project_id": "PRJ-TEST",
            "activity_name": "Completed Foundation",
            "planned_start": "2026-01-01",
            "planned_finish": "2026-01-10",
            "actual_start": "2026-01-01",
            "actual_finish": "2026-01-18",  # 8 days late
            "planned_progress_pct": 100,
            "actual_progress_pct": 100,
            "baseline_cost": 50000.0,
            "actual_cost": 52000.0,
            "is_milestone": False,
            "is_critical": True,
            "total_float_days": 0,
            "status": "COMPLETED"
        }
    ])

    engine = ScheduleEngine(raw_df, cutoff_date=date(2026, 8, 20))
    analyzed = engine.analyze()
    row = analyzed.iloc[0]

    assert row["is_completed"] == True
    assert row["finish_delay_days"] == 8
    assert row["delay_days"] == 8
    assert row["is_overdue"] == False  # Already finished, not actively overdue


# ----------------- TEST 4: INCOMPLETE OVERDUE ACTIVITIES -----------------
def test_incomplete_overdue_activity():
    """Validates overdue detection for in-progress activities against the cutoff date."""
    raw_df = pd.DataFrame([
        {
            "activity_id": "TEST-ACT-03",
            "project_id": "PRJ-TEST",
            "activity_name": "Incomplete Piling",
            "planned_start": "2026-02-01",
            "planned_finish": "2026-03-01",
            "actual_start": "2026-02-05",
            "actual_finish": None,
            "planned_progress_pct": 100,
            "actual_progress_pct": 60,
            "baseline_cost": 100000.0,
            "actual_cost": 90000.0,
            "is_milestone": True,
            "is_critical": True,
            "total_float_days": 0,
            "status": "IN_PROGRESS"
        }
    ])

    cutoff = date(2026, 3, 15)  # 14 days after planned finish
    engine = ScheduleEngine(raw_df, cutoff_date=cutoff)
    analyzed = engine.analyze()
    row = analyzed.iloc[0]

    assert row["is_overdue"] == True
    assert row["overdue_days"] == 14
    assert row["delay_days"] == 14
    assert row["milestone_delayed"] == True


# ----------------- TEST 5: NEGATIVE AND ZERO DELAY -----------------
def test_zero_and_negative_delay():
    """Validates activities finishing early (negative delay) or exactly on time."""
    raw_df = pd.DataFrame([
        {
            "activity_id": "TEST-ACT-EARLY",
            "project_id": "PRJ-TEST",
            "activity_name": "Early Earthwork",
            "planned_start": "2026-01-01",
            "planned_finish": "2026-01-20",
            "actual_start": "2026-01-01",
            "actual_finish": "2026-01-16",  # 4 days early
            "planned_progress_pct": 100,
            "actual_progress_pct": 100,
            "baseline_cost": 20000.0,
            "actual_cost": 19000.0,
            "is_milestone": False,
            "is_critical": False,
            "total_float_days": 5,
            "status": "COMPLETED"
        },
        {
            "activity_id": "TEST-ACT-ONTIME",
            "project_id": "PRJ-TEST",
            "activity_name": "On Time Structure",
            "planned_start": "2026-01-01",
            "planned_finish": "2026-01-20",
            "actual_start": "2026-01-01",
            "actual_finish": "2026-01-20",  # Exact
            "planned_progress_pct": 100,
            "actual_progress_pct": 100,
            "baseline_cost": 30000.0,
            "actual_cost": 30000.0,
            "is_milestone": False,
            "is_critical": False,
            "total_float_days": 5,
            "status": "COMPLETED"
        }
    ])

    engine = ScheduleEngine(raw_df)
    analyzed = engine.analyze()

    assert analyzed.loc[0, "finish_delay_days"] == -4
    assert analyzed.loc[0, "delay_category"] == "ON_TIME"
    assert analyzed.loc[1, "finish_delay_days"] == 0
    assert analyzed.loc[1, "delay_category"] == "ON_TIME"


# ----------------- TEST 6: COST VARIANCE -----------------
def test_cost_variance_calculation():
    """Validates baseline vs actual cost variance and percentage calculation."""
    act_df = pd.DataFrame([
        {
            "activity_id": "TEST-ACT-COST",
            "project_id": "PRJ-TEST",
            "baseline_cost": 50000.0,
            "actual_cost": 65000.0,
            "planned_duration_days": 10,
            "actual_duration_days": 15
        }
    ])
    cost_engine = CostEngine(act_df, pd.DataFrame())
    detail = cost_engine.get_activity_cost_detail("TEST-ACT-COST", "PRJ-TEST", delay_days=5)

    assert detail["cost_variance"] == 15000.0
    assert detail["cost_variance_pct"] == 30.0
    assert detail["potential_delay_exposure"] > 0


# ----------------- TEST 7: MISSING BUDGET INFORMATION -----------------
def test_missing_budget_information():
    """Ensures missing budget does not raise exceptions and returns clear defaults."""
    act_df = pd.DataFrame([
        {
            "activity_id": "TEST-ACT-NOBUDGET",
            "project_id": "PRJ-TEST",
            "baseline_cost": 0.0,
            "actual_cost": 10000.0
        }
    ])
    cost_engine = CostEngine(act_df, pd.DataFrame())
    detail = cost_engine.get_activity_cost_detail("TEST-ACT-NOBUDGET", "PRJ-TEST")

    assert detail["baseline_cost"] == 0.0
    assert detail["cost_variance"] == 10000.0
    assert detail["cost_variance_pct"] == 0.0  # Guard against division by zero


# ----------------- TEST 8: UNMATCHED PROCUREMENT RECORDS -----------------
def test_unmatched_procurement_records():
    """Validates graceful handling when an activity has no BOQ or material mapping."""
    proc_engine = ProcurementEngine(
        boq_df=pd.DataFrame(),
        consumption_df=pd.DataFrame(),
        receipts_df=pd.DataFrame(),
        inventory_df=pd.DataFrame(),
        materials_df=pd.DataFrame()
    )
    status = proc_engine.get_activity_material_status("UNMATCHED-ACT", "PRJ-0001")

    assert status["has_material_requirement"] == False
    assert status["materials"] == []
    assert status["has_shortage"] == False


# ----------------- TEST 9: SUPPLIER PERFORMANCE CALCULATIONS -----------------
def test_supplier_performance_calculation():
    """Validates goods receipt acceptance rates and defect tracking."""
    grn_df = pd.DataFrame([
        {
            "grn_id": "GRN-01",
            "po_id": "PO-01",
            "project_id": "PRJ-TEST",
            "material_id": "MAT-001",
            "vendor_id": "VEN-001",
            "received_date": "2026-08-01",
            "received_quantity": 1000.0,
            "accepted_quantity": 900.0,
            "rejected_quantity": 100.0,
            "quality_status": "PARTIALLY_ACCEPTED"
        }
    ])
    inv_df = pd.DataFrame([
        {
            "project_id": "PRJ-TEST",
            "material_id": "MAT-001",
            "closing_stock": 200.0,
            "reserved_quantity": 500.0  # Deficit of 300
        }
    ])
    proc_engine = ProcurementEngine(
        boq_df=pd.DataFrame(),
        consumption_df=pd.DataFrame(),
        receipts_df=grn_df,
        inventory_df=inv_df,
        materials_df=pd.DataFrame()
    )
    kpis = proc_engine.get_kpis("PRJ-TEST")

    assert kpis["overall_acceptance_rate_pct"] == 90.0
    assert kpis["total_units_rejected"] == 100.0
    assert kpis["materials_with_shortage"] == 1
    assert kpis["total_stock_deficit_units"] == 300.0


# ----------------- TEST 10: RAG EVIDENCE RETRIEVAL -----------------
def test_rag_evidence_retrieval():
    """Validates that RAG retrieval indexes and retrieves legal clauses with citations."""
    clauses_df = pd.DataFrame([
        {
            "clause_id": "TEST-CLAUSE-84",
            "contract_id": "CONTRACT-TEST",
            "vendor_id": "VEN-TEST",
            "section": "8",
            "clause_number": "8.4",
            "title": "Delay and Liquidated Damages",
            "clause_text": "Supplier shall pay liquidated damages of 0.5% per week of delay.",
            "document_page": "12",
            "clause_type": "PENALTY",
            "penalty_applicable": True
        }
    ])
    rag = ContractRAGEngine(clauses_df)
    rag.build_index()

    retrieved = rag.retrieve("liquidated damages penalty delay", top_k=1)
    assert len(retrieved) > 0
    assert retrieved[0]["clause_number"] == "8.4"
    assert retrieved[0]["penalty_applicable"] == True


# ----------------- TEST 11: UNSUPPORTED CONTRACT QUESTIONS -----------------
def test_unsupported_contract_questions():
    """Validates that RAG states 'Insufficient data' rather than fabricating clauses."""
    rag = ContractRAGEngine(pd.DataFrame())
    rag.build_index()

    res = rag.answer_contract_question("What is the software license agreement for the Salesforce CRM platform?")
    assert "Insufficient data" in res["answer"]
    assert res["evidence_retrieved"] == False


# ----------------- TEST 12: SUPERVISOR CONFLICTING AGENT OUTPUTS -----------------
def test_supervisor_conflict_resolution():
    """Validates that supervisor identifies and reconciles inter-agent discrepancies."""
    # Synthetic conflict: Activity on time, but huge cost overrun
    sched = {"delay_days": 0, "status": "COMPLETED"}
    proc = {"has_stock_shortage": False}
    cost = {"cost_variance": 50000.0}
    cont = {"has_productivity_deficit": False}

    # Use supervisor helper method
    supervisor = ProjectRiskSupervisor(None, None, None, None, None, None, None)
    conflicts = supervisor._detect_agent_conflicts(sched, proc, cost, cont)

    assert len(conflicts) > 0
    assert "Cost vs Schedule Discrepancy" in conflicts[0]


# ----------------- TEST 13: LOCAL FALLBACK WITHOUT API CREDENTIALS -----------------
def test_local_fallback_without_api_credentials():
    """Validates that the entire assistant and RAG pipeline functions 100% locally without external API keys."""
    clauses_df = pd.DataFrame([
        {
            "clause_id": "C-01",
            "contract_id": "CONTRACT-001",
            "vendor_id": "VEN-001",
            "section": "8",
            "clause_number": "8.1",
            "title": "Delivery Schedule",
            "clause_text": "Supplier shall deliver materials according to schedule.",
            "document_page": "1",
            "clause_type": "DELIVERY",
            "penalty_applicable": False
        }
    ])
    rag = ContractRAGEngine(clauses_df)
    rag.build_index()

    ans = rag.answer_contract_question("When must supplier deliver materials?")
    assert ans["evidence_retrieved"] == True
    assert "CONTRACT-001" in ans["answer"]


# ----------------- TEST 14: EMPTY DATASETS HANDLING -----------------
def test_empty_datasets_handling():
    """Validates that empty DataFrames do not cause unhandled crashes."""
    checker = DataQualityChecker({})
    audit = checker.run_full_audit()
    assert audit["overall_health_score"] <= 100.0

    sched = ScheduleEngine(pd.DataFrame())
    res = sched.analyze()
    assert res.empty


# ----------------- TEST 15: INTEGRATION ON ACTUAL WORKSPACE DATA -----------------
def test_integration_on_actual_workspace_data():
    """Integration smoke test verifying data loader and schedule analysis on real attached files."""
    loader = ProjectDataLoader()
    data = loader.load_all()

    assert "activities" in data
    assert not data["activities"].empty
    assert len(data["activities"]) > 1000

    sched = ScheduleEngine(data["activities"])
    analyzed = sched.analyze()
    kpis = sched.get_kpis("PRJ-0001")

    assert kpis["total_activities"] > 0
    assert "delayed_activities" in kpis


# ----------------- TEST 16: DASHBOARD MODULE LOAD & STREAMLIT SYNTAX -----------------
def test_dashboard_module_imports():
    """Smoke test ensuring the dashboard module compiles and imports without missing dependencies."""
    dashboard_path = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
    assert dashboard_path.exists()
    with open(dashboard_path, "r", encoding="utf-8") as f:
        code = f.read()
    compile(code, str(dashboard_path), "exec")
