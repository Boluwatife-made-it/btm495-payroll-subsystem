# MNP Centralized Cloud-Based Payroll Subsystem
### BTM 495 Working Prototype

**Course:** BTM 495 - Information Systems Design and Implementation  
**Academic Term:** Fall 2026  
**Institution:** John Molson School of Business, Concordia University  
**Professor:** Dr. Amin Ranj Bar  
**Project Team:**  
- Boluwatife Olayinka  
- Muhammed B Sillah  
- Yassine Chatta  
- Motaz Alarefi  
**Repository:** [https://github.com/Boluwatife-made-it/btm495-payroll-subsystem](https://github.com/Boluwatife-made-it/btm495-payroll-subsystem)  

---

## 1. Project Background & Problem Statement

MNP LLP is a national accounting, tax, and business consulting firm that manages external payroll operations for small and medium-sized enterprise (SME) clients across Canada. 

Prior to this system, MNP managed client payroll through standalone spreadsheets: client managers submitted weekly hours via email, accounting technicians manually entered figures into workbooks, and tax calculations were performed manually. This created three major operational bottlenecks:
1. **Spreadsheet Data Entry Errors:** Manual transcription frequently resulted in calculation discrepancies and incorrect direct deposit amounts.
2. **Statutory Penalty Exposure:** The Canada Revenue Agency (CRA) and Revenu Quebec (RQ) mandate monthly remittance filings by the 15th of the following month. Late or inaccurate remittances trigger automatic 10% statutory financial penalties.
3. **Disjointed Systems:** Personnel data, banking coordinates, and historical pay adjustments were stored in separate files with no central audit trail.

To solve this, our team developed a centralized, cloud-ready payroll subsystem that consolidates client records, automates Quebec and Canadian statutory tax calculations, enforces approval workflows, and provides an unalterable audit log.

---

## 2. System Architecture

We built the prototype using a layered architecture to keep presentation, business logic, domain models, and database operations decoupled:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   PRESENTATION & DASHBOARD LAYER                       │
│      Responsive Web Interface (Tailwind CSS / Client Workspace)       │
│   (Multi-Tenant Switcher, 5 Use Case Views, Technician Alert Banners)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON REST API (CORS Enabled)
┌───────────────────────────────────▼────────────────────────────────────┐
│                       APPLICATION SERVICE LAYER                        │
│   EmployeeService  ·  TimesheetService  ·  CompensationService        │
│          RemittanceService       ·       PayrollService                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Object-Oriented Operations
┌───────────────────────────────────▼────────────────────────────────────┐
│                      DOMAIN CLASS MODEL LAYER (9)                      │
│   Client  ·  Employee  ·  BankAccount  ·  JobInformation  ·  Timesheet │
│   CompensationStructure  ·  PayChangeHistory  ·  StatutoryRemittance  │
│                   PayrollRun (PayStub, TaxSlip)                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQL DDL / DML
┌───────────────────────────────────▼────────────────────────────────────┐
│                    DUAL-ENGINE PERSISTENCE LAYER                       │
│  Primary: Cloud Supabase PostgreSQL (Managed Cloud Database)           │
│  Fallback: Local SQLite Engine (payroll.db - Auto-initialized)         │
└────────────────────────────────────────────────────────────────────────┘
```

### Architecture Highlights
- **Domain Layer:** 9 object-oriented Python classes matching our structural models 1-to-1, with typed attributes and domain validation methods.
- **Dual Database Engine:** The system connects to our cloud Supabase PostgreSQL instance (`mokqkxhoxalupsqyhcek`), while also including an automatic local SQLite fallback (`payroll.db`) so the application can be evaluated locally without credential configuration.
- **REST Service Layer:** A built-in HTTP server exposing CORS-enabled JSON endpoints for all 5 use cases.

---

## 3. Use Case Traceability Matrix

This matrix demonstrates how our 5 approved use cases map directly to our 9 domain classes, database tables, and business rules:

| Use Case ID | Use Case Name | Primary Actor | Domain Classes | Database Tables | Implemented Business Rules |
|---|---|---|---|---|---|
| **UC1** | Manage Employee Information | Accounting Technician | `Client`, `Employee`, `BankAccount`, `JobInformation` | `clients`, `employees`, `bank_accounts`, `job_information` | Multi-tenant scoping by `client_id`; 3-digit institution and 5-digit transit validation; banking masking (`****5678`). |
| **UC2** | Track Time & Attendance | Client Manager | `Timesheet` | `timesheets` | Status lifecycle (`Draft` -> `Submitted` -> `Approved` -> `Locked`); timesheet modification is blocked once a pay run is approved. |
| **UC3** | Manage Compensation & Earnings | Accounting Technician | `CompensationStructure`, `PayChangeHistory` | `compensation_structures`, `pay_change_history` | 1.5x overtime multiplier; immutable audit trail logging rate changes, dates, reasons, and authorizer. |
| **UC4** | Submit Statutory Remittances | Accounting Technician | `StatutoryRemittance` | `statutory_remittances` | Quebec dual-remittance calculation (CRA vs. RQ); confirmation code tracking; handling for tax gateway timeouts (Alternative Flow 7a). |
| **UC5** | Generate Tax Slips & Approve Payroll | Client Manager & Accounting Technician | `PayrollRun`, `PayStub`, `TaxSlip` | `payroll_runs`, `pay_stubs`, `tax_slips` | Gross-to-net deductions; approval locks period timesheets; rejection captures mandatory reason and notifies technician (Alternative Flow 3a). |

---

## 4. Core Business Rules & System Controls

We implemented four key business rules to reflect the legal, financial, and operational requirements of an accounting firm:

### 1. Multi-Tenant Data Isolation
Because MNP manages payroll for multiple independent client companies, all data queries are strictly scoped by `client_id`. Client managers can only access employee records, timesheets, and pay runs for their own firm. Cross-tenant queries are prevented at the database and service layers.

### 2. Post-Approval Timesheet Lockout
To maintain payroll integrity, work hours cannot be edited after management approval. The moment a `PayrollRun` status is set to `Approved`, all associated `Timesheet` records for that period transition to `Locked`. Attempting to modify hours on a locked timesheet triggers a `PermissionError` preventing data tampering.

### 3. Quebec Dual-Remittance Processing
Quebec operates a separate tax system from the rest of Canada. Employers must remit taxes to two distinct government agencies:
- **Canada Revenue Agency (CRA):** Federal Income Tax and Employment Insurance (EI).
- **Revenu Quebec (RQ):** Quebec Provincial Tax, Quebec Pension Plan (QPP), and Quebec Parental Insurance Plan (QPIP).
Our system calculates both remittances separately and records distinct government transmission tokens (`CRA-CONF-2026-XXXXX` and `RQ-BATCH-2026-QC-XXXXX`). It also accounts for Alternative Flow 7a (tax authority timeout/rejection) by flagging the remittance as pending for technician review.

### 4. Real-Time Rejection Feedback Loop
In our Milestone 2 feedback, Professor Ranj Bar pointed out that payroll rejection should notify the Accounting Technician. We implemented Alternative Flow 3a: if a client manager rejects a pay run, they must enter a mandatory rejection reason. The system updates the status to `Rejected` and immediately generates an alert banner containing the manager name, timestamp, and specific reason so the technician can make the required adjustments.

---

## 5. How to Run the Prototype

Our prototype requires only Python 3 and runs out-of-the-box on Windows, macOS, or Linux with zero third-party package dependencies.

### Option A: 1-Click Launch (Windows)
1. Double-click `run_tests.bat` to run the automated integration tests.
2. Double-click `start.bat` to launch the API server and automatically open the MNP web dashboard in your default browser.

### Option B: Terminal Command Line (Windows, macOS, Linux)
1. **Clone & Navigate:**
```bash
git clone https://github.com/Boluwatife-made-it/btm495-payroll-subsystem.git
cd btm495-payroll-subsystem
```

2. **Run the Verification Tests:**
- On Windows: `python test_prototype.py` (or `py test_prototype.py`)
- On macOS/Linux: `python3 test_prototype.py`

*Expected output:*
```
==================================================================
 STARTING MNP PAYROLL SUBSYSTEM INTEGRATION VERIFICATION
==================================================================
[DB Info] Database successfully initialized and seeded at payroll.db

[TEST 1] Verifying UC1: Tenant Isolation & Employee Retrieval...
  --> PASS: Tenant isolation confirmed. Apex (3 employees), Bakery (1 employee).
  --> PASS: Bank account masking active (****4567).

[TEST 2] Verifying UC2: Timesheet Submission & Post-Approval Lockout...
  --> PASS: Post-approval tampering blocked: 'Tampering prevented: Cannot modify hours on a locked timesheet.'
  --> PASS: Timesheet #3 active with status 'Submitted'.

[TEST 3] Verifying UC3: Wage Modification & SOX Audit Logging...
  --> PASS: Hourly rate updated: 24.00 -> 28.00 CAD.
  --> PASS: SOX Audit badge verified: 'Rate updated from 24.00 CAD to 28.00 CAD on 2026-10-23 by Bolu Olayinka - Senior Accounting Technician: Completed Heavy Equipment Operating Certification'

[TEST 4] Verifying UC4: Quebec Dual Remittance & Gateway Tokens...
  --> PASS: CRA Federal Confirmation: CRA-CONF-2026-84612-OK
  --> PASS: Revenu Quebec Confirmation: RQ-BATCH-2026-QC-84612
  --> PASS: UC4 Alternate Flow 7a Handled: 'ALERT (UC4 Alt Flow 7a): Tax Authority Gateway timeout. Remittance flagged as Pending for Accounting Technician retry.'

[TEST 5] Verifying UC5: Approval Workflow & UC5 Rejection Feedback Loop...
  --> PASS: UC5 Alternate Flow 3a Alert Banner generated for Technician:
            'ALERT (UC5 Alt Flow 3a): Sarah Jenkins (Client Manager) rejected Pay Run #1 on 2026-10-23 18:42:03. Reason: 'Discrepancy: Jean Beliveau unpaid leave counted as regular hours.'. Please revise hours and resubmit.'
  --> PASS: Payroll Run #1 Approved at 2026-10-23 18:42:03.
  --> PASS: Itemized Pay Stubs generated for Marc Tremblay (Net: 2293.19 CAD).

==================================================================
 ALL INTEGRATION TESTS PASSED: 100% SUCCESS
 ALL 5 USE CASES AND BUSINESS RULES VERIFIED
==================================================================
```

### 3. Start the REST API & Web Dashboard
To start the backend API server and interactive UI dashboard:
```bash
python3 app.py
```

*Console output:*
```
============================================================
 MNP Payroll Subsystem Prototype REST API Server
 Web Dashboard: http://localhost:8000
 API Health:    http://localhost:8000/api/health
 Dual-mode: SQLite (payroll.db) + Supabase Cloud Engine
============================================================
```

Opening `http://localhost:8000` in any web browser loads the interactive MNP Cloud Payroll Subsystem dashboard. The dashboard can also be viewed offline by double-clicking `frontend/index.html`.

---

## 6. REST API Endpoints

The API provides JSON endpoints for frontend integration and external services:

| Method | Endpoint | Use Case | Purpose |
|---|---|---|---|
| `GET` | `/api/health` | System | Healthcheck confirmation |
| `GET` | `/api/clients` | System | Returns client list for the multi-tenant dropdown |
| `GET` | `/api/employees?client_id=101` | UC1 | Returns employees with masked banking details |
| `POST` | `/api/employees` | UC1 | Onboards a new employee, bank account, and job record (SubFlow 3S.1) |
| `POST` | `/api/employees/update` | UC1 | Updates existing employee, bank, and job placement (SubFlow 3S.2) |
| `GET` | `/api/timesheets?client_id=101` | UC2 | Returns period timesheets with status indicators |
| `POST` | `/api/timesheets/submit` | UC2 | Submits timesheet for review |
| `POST` | `/api/timesheets/update` | UC2 | Updates hours (enforces lockout rule) |
| `POST` | `/api/compensation/update` | UC3 | Updates wage rate and creates audit entry |
| `GET` | `/api/compensation/audit?client_id=101` | UC3 | Returns wage adjustment audit trail |
| `GET` | `/api/remittances?run_id=1` | UC4 | Returns Quebec dual remittance breakdown |
| `POST` | `/api/remittances/transmit` | UC4 | Dispatches remittance to CRA and RQ gateways |
| `GET` | `/api/payroll/runs?client_id=101` | UC5 | Returns payroll runs and current approval statuses |
| `POST` | `/api/payroll/calculate` | UC5 | Calculates gross-to-net pay run in `Pending_Approval` |
| `POST` | `/api/payroll/approve` | UC5 | Approves run and locks all associated timesheets |
| `POST` | `/api/payroll/reject` | UC5 | Rejects run and generates technician alert banner |
| `GET` | `/api/payroll/stubs?run_id=1` | UC5 | Returns itemized employee pay stubs |
| `GET` | `/api/payroll/tax-slips?client_id=101&tax_year=2026` | UC5 | Returns annual T4 and Releve 1 tax slips |
| `POST` | `/api/payroll/tax-slips/generate` | UC5 | Verifies finalized pay runs and generates T4 and Releve 1 slips |

---

## 7. Project File Structure

```
btm495-payroll-subsystem/
├── app.py                      ──▶ REST API Server (Python standard library HTTP server)
├── test_prototype.py           ──▶ Integration test suite verifying UC1 through UC5
├── README.md                   ──▶ System documentation & traceability matrix
├── .env.example                ──▶ Supabase cloud configuration template
├── database/
│   ├── db.py                   ──▶ Dual-engine database connection manager
│   ├── schema.sql              ──▶ DDL script for all 11 tables and constraints
│   ├── seed.sql                ──▶ Montreal and Quebec test scenarios
│   └── payroll.db              ──▶ Local SQLite database file (auto-generated)
├── models/
│   ├── __init__.py             ──▶ Exports all 9 core domain classes
│   ├── client.py               ──▶ UC1: Client domain class
│   ├── employee.py             ──▶ UC1: Employee domain class
│   ├── bank_account.py         ──▶ UC1: BankAccount domain class
│   ├── job_information.py      ──▶ UC1: JobInformation domain class
│   ├── timesheet.py            ──▶ UC2: Timesheet domain class
│   ├── compensation_structure.py ──▶ UC3: CompensationStructure domain class
│   ├── pay_change_history.py   ──▶ UC3: PayChangeHistory domain class
│   ├── statutory_remittance.py ──▶ UC4: StatutoryRemittance domain class
│   └── payroll_run.py          ──▶ UC5: PayrollRun, PayStub, and TaxSlip domain classes
└── services/
    ├── __init__.py             ──▶ Exports service orchestrators
    ├── employee_service.py     ──▶ UC1 Service
    ├── timesheet_service.py    ──▶ UC2 Service
    ├── compensation_service.py ──▶ UC3 Service
    ├── remittance_service.py   ──▶ UC4 Service
    └── payroll_service.py      ──▶ UC5 Service
```
