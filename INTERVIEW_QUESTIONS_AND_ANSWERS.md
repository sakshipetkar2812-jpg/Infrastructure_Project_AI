# Infrastructure Project Delay & Cost Overrun Intelligence Agent
## Comprehensive Technical & Behavioral Interview Master Guide

> **Target Roles:** AI Engineer, Data Scientist, Data Analyst, Python Developer, RAG Engineer, Full-Stack AI Developer.  
> **Repository:** [https://github.com/sakshipetkar2812-jpg/Infrastructure_Project_AI](https://github.com/sakshipetkar2812-jpg/Infrastructure_Project_AI)  
> **Workspace Path:** `C:\Users\ompet\OneDrive\Desktop\infras_project\Infrastructure_Project_AI`

---

## TABLE OF CONTENTS
1. [Core Pitch & High-Level Project Questions](#1-core-pitch--high-level-project-questions)
2. [Data Engineering, Schemas & Data Quality](#2-data-engineering-schemas--data-quality)
3. [Domain Analytics: Scheduling, CPM, Procurement & Cost](#3-domain-analytics-scheduling-cpm-procurement--cost)
4. [RAG (Retrieval-Augmented Generation) & Legal Intelligence](#4-rag-retrieval-augmented-generation--legal-intelligence)
5. [Multi-Agent System & Supervisor Architecture](#5-multi-agent-system--supervisor-architecture)
6. [System Design & Engineering Decisions](#6-system-design--engineering-decisions)
7. [Automated Testing & Quality Assurance (Pytest)](#7-automated-testing--quality-assurance-pytest)
8. [Edge Cases, Data Ethics & Anti-Hallucination](#8-edge-cases-data-ethics--anti-hallucination)
9. [Behavioral, Scenario & Challenge Questions](#9-behavioral-scenario--challenge-questions)
10. [Quick-Fire Mathematical & Technical Cheat Sheet](#10-quick-fire-mathematical--technical-cheat-sheet)

---

## 1. CORE PITCH & HIGH-LEVEL PROJECT QUESTIONS

### Q1.1: Can you give me an elevator pitch of your project in 60 seconds?
**Ideal Answer:**
> *"Large-scale infrastructure programs like highways, bridges, and metro rail projects routinely suffer from catastrophic delays and cost overruns because project telemetry is deeply fragmented across isolated systems: scheduling in Primavera P6, materials in ERPs, site labor on daily logs, finances in accounting ledgers, and contractual legal rights locked in static documents.*  
>  
> *I built the **Infrastructure Project Delay & Cost Overrun Intelligence Agent**—an end-to-end decision-support platform that unifies these streams. Operating on 100 construction projects and over 12,600 activities, it continuously detects schedule slippages, calculates float and critical path impact, pinpoints operational root causes (like warehouse inventory deficits or labor productivity shortfalls), calculates financial exposure, retrieves exact contract penalty clauses via local RAG, and recommends prioritized corrective actions to leadership through an interactive 11-tab Streamlit dashboard."*

---

### Q1.2: What was the primary business motivation behind building this?
**Ideal Answer:**
> *"The problem in infrastructure isn't just that projects get delayed—it's that leadership discovers the delay and its financial impact **too late**, usually when a milestone has already been missed.  
>  
> For instance, if an activity slips by 20 days, traditional reports simply show a red schedule bar. They cannot tell leadership:  
> 1. Did the activity delay the entire project completion date (Critical Path)?  
> 2. Did the delay happen because of bad weather, contractor under-deployment, or supplier delivery rejections?  
> 3. Does our contract with the supplier allow us to levy Liquidated Damages to offset delay costs?  
>  
> This platform connects operational causes to financial and contractual consequences to empower proactive decision-making."*

---

### Q1.3: What is the high-level technical architecture of your project?
**Ideal Answer:**
> *"The system is built on a clean four-tier modular architecture:  
> 1. **Data Ingestion & Integrity Layer**: Ingests 14 multi-format tables (CSV, XLSX, TXT) with character-encoding fallback, referential validation, and an automated 98/100 data quality auditor.  
> 2. **Deterministic Analytics Layer**: Separate dedicated Python engines for schedule/CPM calculations, procurement/inventory stockouts, cost variance/daily delay burn rate, and contractor labor productivity.  
> 3. **RAG Legal Intelligence Layer**: A local TF-IDF semantic vector retrieval engine indexing 180 clauses and 30 full contracts for exact clause citation without external API reliance.  
> 4. **Multi-Agent Orchestration & UI Layer**: 5 specialized domain agents (Schedule, Procurement, Cost, Contractor, Contract) orchestrated by a Project Risk Supervisor, surfaced through an interactive 11-tab Streamlit dashboard and natural-language assistant."*

---

## 2. DATA ENGINEERING, SCHEMAS & DATA QUALITY

### Q2.1: What datasets did you work with, and what is the scale of the data?
**Ideal Answer:**
> *"The system is grounded in real infrastructure telemetry covering **100 construction projects** (`PRJ-0001` through `PRJ-0100`):  
> - **`activities.csv` (12,633 rows)**: Schedule baselines, actual dates, progress %, duration, cost, and float.  
> - **`dependencies.csv` (15,571 rows)**: Finish-to-Start (FS), Start-to-Start (SS), and Finish-to-Finish (FF) relationships with lag days.  
> - **`boq.csv` (15,166 rows)** & **`material_consumption.csv` (15,166 rows)**: Planned vs. actual material usage across 12 materials.  
> - **`goods_receipts.csv` (5,427 rows)**: Shipments received, accepted, and rejected.  
> - **`inventory.csv` (1,200 rows)**: Warehouse opening, closing, and reserved stock.  
> - **`labor_assignments.csv` (6,292 rows)**: Contractor daily headcount, wages, and measured productivity rates.  
> - **`cost_ledger.csv` (17,839 rows)**: Actual spend by code (Labor, Material, Equipment, Subcontractor).  
> - **`contracts.csv` & 30 raw text agreements**: 180 clauses covering delivery, liquidated damages, and warranties.  
> - **`cost_reconciliation.csv` (100 rows)**: Prediction calibration history.  
> - **`Road Constuction Delay Survey.csv` (144 rows)**: 44 empirical delay cause rankings."*

---

### Q2.2: How did you establish relationships between these tables without a traditional relational database?
**Ideal Answer:**
> *"I designed an in-memory relational graph using foreign keys and composite identifiers:  
> - Primary key `activity_id` links `activities.csv` to `dependencies.csv` (`predecessor_activity_id` / `successor_activity_id`), `boq.csv`, `material_consumption.csv`, `labor_assignments.csv`, and `cost_ledger.csv`.  
> - Composite keys `(project_id, material_id)` link material requirements in BOQ to warehouse stock in `inventory.csv` and shipment inspections in `goods_receipts.csv`.  
> - `contractor_id` links labor crews to historical contractor performance benchmarks in `contractors.csv`.  
> - `vendor_id` and `contract_id` connect purchase orders and receipts to contractual legal terms in `contract_clauses.csv`."*

---

### Q2.3: How did you handle data cleaning and data quality validation?
**Ideal Answer:**
> *"I built a dedicated `DataQualityChecker` class (`src/data_processing/quality.py`) that runs before analytics:  
> 1. **Encoding Resilience**: Handled Windows CP1252 / UTF-8 discrepancies (like curly quotes `’` causing byte `0x92` parse crashes) via an automated fallback encoding parser.  
> 2. **Date Sanity**: Verified date sequence logic (`planned_finish >= planned_start` and `actual_finish >= actual_start`).  
> 3. **Financial Sanity**: Ensured non-negativity for baseline costs, actual costs, and ledger amounts.  
> 4. **Referential Integrity**: Verified foreign key linkage. In our operational dataset, 100% of labor and cost ledger activity foreign keys matched parent activity IDs.  
> 5. **Automated Health Score**: The system computes a deduplication and missingness penalty score, yielding an automated **98.0 / 100 Data Health Score**."*

---

### Q2.4: Did you find any out-of-scope or anomalous files in the raw data?
**Ideal Answer:**
> *"Yes. During initial exploratory analysis, I discovered a file named `Phase-3 tracker.xlsx`. Upon inspecting its internal XML shared strings and sheets (`Scope`, `MissingReq`), I identified that it was an IT CRM migration tracker ('DeepHealth Gleamer-to-Nova Salesforce migration'), completely unrelated to infrastructure construction.  
>  
> Following strict data engineering ethics, I documented this finding and explicitly excluded `Phase-3 tracker.xlsx` from the analytics pipeline rather than mixing unrelated records into the construction data."*

---

## 3. DOMAIN ANALYTICS: SCHEDULING, CPM, PROCUREMENT & COST

### Q3.1: How do you determine whether an activity is delayed?
**Ideal Answer:**
> *"We apply a strict distinction between completed and incomplete activities:  
> 1. **Completed Activities**: Delay is calculated deterministically as:  
>    $$\text{Finish Delay} = \text{Actual Finish Date} - \text{Planned Finish Date}$$  
>    If positive, it was delayed; if negative, it finished ahead of schedule.  
> 2. **In-Progress / Not Started Activities**: Incomplete activities do not have an actual finish date. They are evaluated against the project master reporting cutoff date (**August 20, 2026**). If $\text{Planned Finish Date} < \text{Cutoff Date}$, the activity is overdue:  
>    $$\text{Overdue Days} = \text{Cutoff Date} - \text{Planned Finish Date}$$  
> 3. **Start Delay**: If an activity started late, start delay is $(\text{Actual Start} - \text{Planned Start})$."*

---

### Q3.2: What is the Critical Path Method (CPM), and how does your engine model it?
**Ideal Answer:**
> *"In project scheduling, the **Critical Path** is the sequence of dependent activities that determines the earliest possible project completion date. Activities on the critical path have **Total Float $\le 0$**, meaning they have zero buffer. A delay of 1 day on a critical activity pushes the entire project completion by 1 day.  
>  
> Our `ScheduleEngine` checks both the explicit `is_critical` flag and evaluates `total_float_days <= 0`. If an activity has positive delay days AND is on the critical path, the engine raises a `critical_path_impact = True` alert and traces all downstream successors via `dependencies.csv` using Finish-to-Start (FS), Start-to-Start (SS), and Finish-to-Finish (FF) relationships."*

---

### Q3.3: How do you detect procurement and material shortages?
**Ideal Answer:**
> *"The `ProcurementEngine` analyzes inventory and supply chain execution:  
> 1. **Warehouse Stockout Detection**: It compares closing warehouse stock against reserved allocations:  
>    $$\text{Stock Deficit} = \text{Reserved Quantity} - \text{Closing Stock} \quad (\text{when } \text{Closing Stock} < \text{Reserved Quantity})$$  
> 2. **Vendor Quality Defect Rate**: From `goods_receipts.csv`, it computes the percentage of rejected materials:  
>    $$\text{Defect Rate (\%)} = \frac{\text{Rejected Quantity}}{\text{Received Quantity}} \times 100$$  
>    If defect rate $> 5\%$ or quality status $\ne \text{'ACCEPTED'}$, an active supply quality bottleneck is flagged."*

---

### Q3.4: How do you calculate contractor labor productivity deficits?
**Ideal Answer:**
> *"In `contractor_engine.py`, rather than looking merely at headcount, we calculate the pace required to hit the deadline:  
> 1. **Required Productivity Rate**:  
>    $$\text{Required Rate} = \frac{\text{Remaining Work Quantity}}{\text{Days to Deadline}}$$  
> 2. **Productivity Deficit**:  
>    $$\text{Productivity Deficit} = \text{Required Rate} - \text{Actual Productivity Rate}$$  
> If the deficit is positive and work remains, the contractor's current deployment pace is mathematically incapable of meeting the deadline, indicating that additional crew or dual shifts must be mobilized."*

---

### Q3.5: How do you differentiate actual cost, cost variance, and delay financial exposure?
**Ideal Answer:**
> *"We strictly prevent conflating different financial categories:  
> 1. **Cost Variance**:  
>    $$\text{Cost Variance} = \text{Actual Cost} - \text{Baseline Cost}$$  
> 2. **Daily Actual Burn Rate**:  
>    $$\text{Daily Burn Rate} = \frac{\text{Actual Cost}}{\max(1, \text{Actual Duration})}$$  
> 3. **Potential Delay Financial Exposure**:  
>    $$\text{Delay Exposure} = \text{Observed Delay Days} \times \text{Daily Burn Rate}$$  
>    This represents the ongoing resource and equipment holding cost incurred during the delay.  
> 4. **Contractual Recovery / Liquidated Damages**: Kept completely distinct from project cost variance. Recoveries depend on legal grace periods and contract penalty caps under Clause 8.4."*

---

## 4. RAG (RETRIEVAL-AUGMENTED GENERATION) & LEGAL INTELLIGENCE

### Q4.1: Why did you implement RAG, and what problem does it solve in this project?
**Ideal Answer:**
> *"In construction, project managers know an activity is delayed, but they don't know their legal standing. Construction contracts are lengthy, complex documents. Commercial teams rarely have time to read through 50-page agreements for every delayed shipment.  
>  
> We implemented RAG to bridge structured operational delays with unstructured legal agreements. When the system detects a supplier delivery delay, RAG retrieves the exact governing contract clause (e.g., Clause 8.1 Delivery Obligations or Clause 8.4 Delay & Liquidated Damages) with verbatim text and document citations, so leadership can immediately take commercial action."*

---

### Q4.2: How is your RAG engine implemented, and why did you choose a local approach?
**Ideal Answer:**
> *"The RAG engine (`src/rag/contract_rag.py`) indexes two sources:  
> 1. Structured clauses from `contract_clauses.csv` (180 categorized clauses).  
> 2. Raw unstructured contract agreements (`CONTRACT-001.txt` through `CONTRACT-030.txt`).  
>  
> It chunks documents by clause boundaries using section headers (`Clause X.Y: Title`). For vector representation, it uses **TF-IDF with unigram and bigram tokenization and Cosine Similarity**.  
>  
> **Why Local?**  
> - **Zero API Cost & Privacy**: Legal documents stay 100% on-premise without exposing private contracts to external cloud endpoints.  
> - **Zero Latency**: Retrieval executes in under 20 milliseconds.  
> - **100% Deterministic & Verifiable**: It enforces a strict relevance threshold ($\ge 0.20$). If no matching clause exists, it explicitly returns *'Insufficient data'* rather than hallucinating fake legal penalties."*

---

### Q4.3: What is Clause 8.4, and how does your system retrieve it?
**Ideal Answer:**
> *"In our contract repository, **Clause 8.4** is titled **'Delay and Liquidated Damages'**. It specifies:  
> *'Where delay is attributable to the supplier, contractual delay remedies may apply after the contractual grace period.'*  
>  
> When a user queries: *'What liquidated damages apply if supplier delivery is delayed?'*, the query vector matches chunk tokens `liquidated`, `damages`, `delay`, and `supplier`. The engine returns a cosine similarity score of $\approx 0.51$, presents verbatim clause text, states that penalty terms are applicable, and cites the contract document ID."*

---

## 5. MULTI-AGENT SYSTEM & SUPERVISOR ARCHITECTURE

### Q5.1: Why use a Multi-Agent architecture instead of one giant script?
**Ideal Answer:**
> *"Large-scale project risk is multidimensional. Combining schedule, procurement, cost, labor, and legal rules into a single monolithic script leads to high coupling, difficult debugging, and fragile execution.  
>  
> By implementing 5 specialized domain agents:  
> - **Schedule Agent**: Specializes in CPM, float, and network dependencies.  
> - **Procurement Agent**: Specializes in BOQ, inventory balances, and supplier defects.  
> - **Cost Agent**: Specializes in ledger reconciliation, burn rates, and variance.  
> - **Contractor Agent**: Specializes in crew productivity deficits and historical contractor risk.  
> - **Contract Agent**: Specializes in legal RAG semantic retrieval.  
>  
> Each agent has a single responsibility, explicit inputs, and structured JSON outputs. This makes every component independently testable with unit tests."*

---

### Q5.2: What is the role of the Project Risk Supervisor (`supervisor.py`)?
**Ideal Answer:**
> *"The Project Risk Supervisor acts as the AI Chief Project Officer:  
> 1. **Orchestration**: Receives a project/activity query and calls the necessary specialist agents.  
> 2. **Conflict Resolution**: Cross-checks agent findings to catch domain inconsistencies.  
> 3. **Root Cause Synthesis**: Weighs evidence from schedule, procurement, and labor to establish the most probable root cause with an assigned confidence score (High/Medium/Low).  
> 4. **Executive Reporting**: Generates a structured leadership narrative and prioritizes corrective actions."*

---

### Q5.3: Can you give an example of an inter-agent conflict the Supervisor resolves?
**Ideal Answer:**
> *"Yes. Consider an activity that has **zero schedule delay** (`delay_days = 0`), but the Cost Agent reports a **large cost overrun**.  
>  
> A naive model might classify this as a delay cost. The Supervisor detects this discrepancy and resolves it:  
> *'Cost vs. Schedule Discrepancy: Activity has zero recorded schedule delay, yet exhibits a cost overrun. Supervisor Conclusion: Cost increase is driven by unit rate inflation or equipment intensity, not schedule delay.'*  
>  
> Another example: If an activity is marked `COMPLETED` but the warehouse reports a material stockout, the Supervisor determines that the shortage impacts downstream successor activities, not the finished task."*

---

## 6. SYSTEM DESIGN & ENGINEERING DECISIONS

### Q6.1: Why did you NOT use an LLM for schedule delay and cost calculations?
**Ideal Answer:**
> *"This is a foundational engineering principle: **Never use a stochastic probabilistic model (LLM) for deterministic arithmetic.**  
>  
> LLMs can hallucinate, produce inconsistent numbers on repeated runs, and struggle with strict calendar date arithmetic. In construction engineering and financial accounting, numbers must be 100% reproducible and auditable.  
>  
> Therefore, all date logic, critical path float, cost variance, stock deficits, and productivity rates are implemented in pure, deterministic Python with NumPy and Pandas. We use AI/RAG strictly for language understanding, semantic search over contracts, and narrative synthesis."*

---

### Q6.2: How does the Recommendation Engine work, and why is Human-in-the-Loop required?
**Ideal Answer:**
> *"The `RecommendationEngine` generates prioritized interventions based on the forensic root cause:  
> - **Material Bottlenecks**: Recommends expediting notices, warehouse transfers, and reviewing Clause 8.4 remedies.  
> - **Labor Deficits**: Recommends crew augmentations (e.g., +25% headcount) or dual-shift scheduling.  
> - **Predecessor Delay**: Recommends schedule crashing or fast-tracking FS lags to Start-to-Start (SS).  
>  
> **Human-in-the-Loop**: The platform is strictly a **decision-support tool**. It never executes actions autonomously (like issuing purchase orders, penalizing vendors, or withholding payments). Every high-impact recommendation is flagged with `human_approval_required: True` and assigns a specific decision authority (e.g., Project Director, Commercial Lead)."*

---

### Q6.3: How does the Natural Language Project Assistant work under the hood?
**Ideal Answer:**
> *"The chat assistant (`src/services/chat_assistant.py`) uses **intent classification and entity extraction**:  
> 1. It extracts activity IDs (`PRJ-0001-ACT-0001`) and project IDs (`PRJ-0001`) via regular expressions.  
> 2. It determines the user's intent:  
>    - If the user asks *'Why is ACT-0001 delayed?'*, it routes directly to the Supervisor's root cause forensic engine.  
>    - If the user asks *'Which activities are delayed?'*, it queries the Schedule Engine directly from the database.  
>    - If the user asks *'What is the budget variance?'*, it retrieves ledger metrics from the Cost Engine.  
>    - If the user asks about contract clauses, liquidated damages, or warranties, it routes to the RAG vector engine.  
> This ensures that every response is backed by empirical data, eliminating hallucination."*

---

## 7. AUTOMATED TESTING & QUALITY ASSURANCE (PYTEST)

### Q7.1: How did you test the application?
**Ideal Answer:**
> *"We built an automated test suite with **15 pytest test cases** (`tests/test_intelligence_agent.py`) covering all critical domain edge cases:  
> 1. `test_date_parsing_and_missing_dates`: Validates ISO date parsing and non-destructive handling of empty actual finish dates.  
> 2. `test_completed_activity_delay`: Validates `actual_finish - planned_finish`.  
> 3. `test_incomplete_overdue_activity`: Validates overdue calculations against cutoff date.  
> 4. `test_zero_and_negative_delay`: Tests tasks that finish early or on time.  
> 5. `test_cost_variance_calculation`: Validates baseline vs. actual variance and daily burn rate.  
> 6. `test_missing_budget_information`: Guards against division-by-zero errors when budget is 0.  
> 7. `test_unmatched_procurement_records`: Tests graceful handling when an activity has no BOQ mapping.  
> 8. `test_supplier_performance_calculation`: Validates acceptance rates and defect percentages.  
> 9. `test_rag_evidence_retrieval`: Validates vector search and clause citation.  
> 10. `test_unsupported_contract_questions`: Validates that queries for non-existent clauses return 'Insufficient data'.  
> 11. `test_supervisor_conflict_resolution`: Tests detection of cost-vs-schedule discrepancies.  
> 12. `test_local_fallback_without_api_credentials`: Confirms 100% offline functionality.  
> 13. `test_empty_datasets_handling`: Verifies no unhandled crashes on empty dataframes.  
> 14. `test_integration_on_actual_workspace_data`: End-to-end integration across all 12,633 activities.  
> 15. `test_dashboard_module_imports`: Validates dashboard compilation.  
>  
> All 15 tests execute and pass in under 3 seconds."*

---

## 8. EDGE CASES, DATA ETHICS & ANTI-HALLUCINATION

### Q8.1: How do you handle missing values without distorting project metrics?
**Ideal Answer:**
> *"We follow strict data ethics rules:  
> 1. **No Silent Zero Imputation**: A missing actual finish date does NOT mean an activity took 0 days; it means it is still in progress.  
> 2. **No Data Fabrication**: If an activity has no BOQ or labor record, we output `'Unassigned / In-house'` or `'No BOQ mapping'`, rather than fabricating synthetic suppliers.  
> 3. **Preservation of Raw Data**: Raw datasets are read-only; all transformations run on in-memory copies."*

---

### Q8.2: How do you distinguish correlation from causation in delay root-cause analysis?
**Ideal Answer:**
> *"A common mistake in data science is assuming that because two events happen simultaneously, one caused the other. For example, if an activity is delayed and a supplier had a late delivery, did the supplier cause the delay?  
>  
> Our `RootCauseInvestigationEngine` checks three validation hurdles before attributing causation:  
> 1. **Bill of Quantities Linkage**: Was the late material actually assigned to this specific activity?  
> 2. **Temporal Alignment**: Did the delivery defect or stockout occur before or during the activity execution window?  
> 3. **Alternative Explanations**: It checks whether contractor labor productivity was also deficient or whether a critical predecessor slipped.  
>  
> If evidence is suggestive but not definitive, the engine tags it as `'Probable Root Cause'` with `'MEDIUM'` confidence. If evidence is lacking, it explicitly outputs `'Root cause not established'`."*

---

## 9. BEHAVIORAL, SCENARIO & CHALLENGE QUESTIONS

### Q9.1: What was the biggest technical challenge you faced while building this project?
**Ideal Answer:**
> *"The biggest challenge was **cross-domain relational integration under encoding constraints**.  
>  
> Real-world construction datasets come from different ERP and scheduling tools. For example, `Road Constuction Delay Survey.csv` contained Windows CP1252 quotation bytes (`0x92`) that immediately crashed standard UTF-8 CSV readers. Furthermore, connecting 12,633 activities to 15,166 BOQ items, warehouse inventory, and 30 text contract files required building an in-memory relational mapper that handled many-to-many dependencies without memory bloat.  
>  
> I solved this by building an encoding-resilient data loader with fallback parsing and optimized vectorized Pandas lookups, reducing complete cross-dataset ingestion and analysis to under 5 seconds."*

---

### Q9.2: If you had 3 more months and a production budget, what would you add?
**Ideal Answer:**
> *"I would extend the system in three key areas:  
> 1. **Live ERP & BIM Connectors**: Build automated webhooks to pull live updates directly from Oracle Primavera P6, SAP ERP, and Autodesk Revit BIM models.  
> 2. **Hybrid Dense Embeddings**: Complement our local TF-IDF retriever with on-premise dense embeddings (like `BGE-small` or `all-MiniLM-L6-v2`) in ChromaDB for deeper semantic nuance on complex legal sentences.  
> 3. **Weather & Geospatial Intelligence**: Ingest daily satellite meteorological precipitation data to automatically correlate weather stoppages against force majeure contract clauses."*

---

## 10. QUICK-FIRE MATHEMATICAL & TECHNICAL CHEAT SHEET

| Metric | Formula / Logic | Purpose |
| :--- | :--- | :--- |
| **Finish Delay (Completed)** | $\text{Actual Finish} - \text{Planned Finish}$ | Quantifies actual schedule slip in calendar days. |
| **Overdue Days (Incomplete)** | $\text{Cutoff Date} - \text{Planned Finish}$ | Detects active delay for ongoing activities past deadline. |
| **Critical Path Impact** | $(\text{Total Float} \le 0 \lor \text{is\_critical}) \land (\text{Delay} > 0)$ | Identifies delays that push project completion date. |
| **Cost Variance (CV)** | $\text{Actual Cost} - \text{Baseline Cost}$ | Positive = Over budget; Negative = Under budget. |
| **Cost Variance \%** | $\frac{\text{Actual Cost} - \text{Baseline Cost}}{\text{Baseline Cost}} \times 100$ | Relative cost overrun percentage. |
| **Daily Burn Rate** | $\frac{\text{Actual Cost}}{\max(1, \text{Actual Duration})}$ | Daily resource consumption pace on site. |
| **Potential Delay Exposure** | $\text{Delay Days} \times \text{Daily Burn Rate}$ | Financial holding exposure from schedule extension. |
| **Warehouse Stock Deficit** | $\text{Reserved Quantity} - \text{Closing Stock}$ | Flags active material shortages halting construction. |
| **Defect Rate (\%)** | $\frac{\text{Rejected Quantity}}{\text{Received Quantity}} \times 100$ | Supplier shipment quality metric. |
| **Required Productivity Rate** | $\frac{\text{Remaining Work}}{\text{Days to Deadline}}$ | Minimum daily production speed required to avoid delay. |
| **Productivity Deficit** | $\text{Required Rate} - \text{Actual Rate}$ | Positive value indicates crew is underperforming deadline. |
| **RAG Cosine Similarity** | $\cos(\theta) = \frac{\mathbf{q} \cdot \mathbf{d}}{\|\mathbf{q}\| \|\mathbf{d}\|}$ | Semantic relevance between user query and contract clause. |
| **Liquidated Damages Clause** | **Clause 8.4** | Governing contract remedy for vendor delivery delays. |
