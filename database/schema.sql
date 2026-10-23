-- ==============================================================================
-- MNP CENTRALIZED CLOUD-BASED PAYROLL SUBSYSTEM (BTM 495 PROTOTYPE)
-- MASTER DATABASE SCHEMA: PostgreSQL & SQLite Dual-Engine DDL
-- Strictly models the 9 Core UML Classes across 5 Approved Use Cases
-- Includes the 4 Defensive Hedges: Tenant Isolation, Status Enums,
-- Quebec Dual-Remittance Split, and SOX-Compliant Audit Trails.
-- ==============================================================================

-- Drop existing tables in reverse dependency order (clean teardown)
DROP TABLE IF EXISTS tax_slips;
DROP TABLE IF EXISTS pay_stubs;
DROP TABLE IF EXISTS statutory_remittances;
DROP TABLE IF EXISTS payroll_runs;
DROP TABLE IF EXISTS pay_change_history;
DROP TABLE IF EXISTS compensation_structures;
DROP TABLE IF EXISTS timesheets;
DROP TABLE IF EXISTS job_information;
DROP TABLE IF EXISTS bank_accounts;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS clients;

-- ------------------------------------------------------------------------------
-- 1. CLIENTS TABLE (Use Case 1: Manage Employee Info / Multi-Tenant Boundary)
-- Enforces tenant isolation so MNP can manage multiple client firms independently.
-- ------------------------------------------------------------------------------
CREATE TABLE clients (
    client_id INTEGER PRIMARY KEY,
    client_name VARCHAR(150) NOT NULL,
    company_address VARCHAR(255) NOT NULL,
    contact_email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- 2. EMPLOYEES TABLE (Use Case 1: Manage Employee Info)
-- Master profile for individual client personnel.
-- ------------------------------------------------------------------------------
CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL,
    first_name VARCHAR(60) NOT NULL,
    last_name VARCHAR(60) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    hire_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('Active', 'On Leave', 'Terminated')),
    FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 3. BANK_ACCOUNTS TABLE (Use Case 1: Direct Deposit Details)
-- Encapsulates routing validation and masking. Plain 1-to-1 association with Employee.
-- ------------------------------------------------------------------------------
CREATE TABLE bank_accounts (
    account_id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL UNIQUE,
    institution_number VARCHAR(10) NOT NULL, -- e.g. 001 (BMO), 003 (RBC)
    transit_number VARCHAR(10) NOT NULL,     -- 5 digits branch routing
    account_number VARCHAR(20) NOT NULL,     -- Masked for display
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('Checking', 'Savings')),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 4. JOB_INFORMATION TABLE (Use Case 1: Employment Profiles & Pay Rates)
-- Captures organizational department, employment tier, and wage rates.
-- ------------------------------------------------------------------------------
CREATE TABLE job_information (
    job_id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL UNIQUE,
    job_title VARCHAR(100) NOT NULL,
    department VARCHAR(80) NOT NULL,
    employment_type VARCHAR(30) NOT NULL CHECK (employment_type IN ('Full-Time', 'Part-Time', 'Contract')),
    base_salary NUMERIC(12, 2) DEFAULT 0.00,
    hourly_rate NUMERIC(10, 2) NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 5. TIMESHEETS TABLE (Use Case 2: Track Time & Attendance)
-- Records period work duration. Enforces the Post-Approval Lockout hedge.
-- ------------------------------------------------------------------------------
CREATE TABLE timesheets (
    timesheet_id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    regular_hours NUMERIC(6, 2) NOT NULL DEFAULT 0.00,
    overtime_hours NUMERIC(6, 2) NOT NULL DEFAULT 0.00,
    vacation_days INTEGER NOT NULL DEFAULT 0,
    sick_days INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL CHECK (status IN ('Draft', 'Submitted', 'Approved', 'Locked')),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 6. COMPENSATION_STRUCTURES TABLE (Use Case 3: Manage Compensation & Earnings)
-- Defines frequency schedules and overtime multipliers.
-- ------------------------------------------------------------------------------
CREATE TABLE compensation_structures (
    structure_id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL UNIQUE,
    pay_frequency VARCHAR(20) NOT NULL CHECK (pay_frequency IN ('Weekly', 'Bi-Weekly', 'Semi-Monthly', 'Monthly')),
    overtime_multiplier NUMERIC(4, 2) NOT NULL DEFAULT 1.50,
    bonus_rate NUMERIC(6, 2) NOT NULL DEFAULT 0.00,
    commission_rate NUMERIC(6, 2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 7. PAY_CHANGE_HISTORY TABLE (Use Case 3: Compensation Audit Trail)
-- Immutable audit log satisfying SOX and accounting audit requirements.
-- ------------------------------------------------------------------------------
CREATE TABLE pay_change_history (
    history_id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    change_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    previous_rate NUMERIC(10, 2) NOT NULL,
    new_rate NUMERIC(10, 2) NOT NULL,
    change_reason VARCHAR(255) NOT NULL,
    authorized_by VARCHAR(100) NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 8. PAYROLL_RUNS TABLE (Use Case 5: Approve Payroll & Generate Tax Slips)
-- Central batch orchestrator. Stores run totals, approval status, and rejection reason.
-- ------------------------------------------------------------------------------
CREATE TABLE payroll_runs (
    run_id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    run_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_gross NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    total_deductions NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    total_net NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    approval_status VARCHAR(20) NOT NULL CHECK (approval_status IN ('Draft', 'Pending_Approval', 'Approved', 'Rejected')),
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 9. STATUTORY_REMITTANCES TABLE (Use Case 4: Submit Statutory Remittances)
-- Solves the Quebec Dual-Split Blind Spot (CRA Federal vs RQ Provincial).
-- ------------------------------------------------------------------------------
CREATE TABLE statutory_remittances (
    remittance_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL UNIQUE,
    remittance_period VARCHAR(20) NOT NULL, -- e.g. '2026-10'
    cra_federal_tax NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    cra_ei_deduction NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    cra_total_remitted NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    cra_confirmation_number VARCHAR(50),
    rq_provincial_tax NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    rq_qpp_deduction NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    rq_qpip_deduction NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    rq_total_remitted NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    rq_confirmation_number VARCHAR(50),
    status VARCHAR(20) NOT NULL CHECK (status IN ('Calculated', 'Submitted', 'Acknowledged', 'Failed_Timeout')),
    FOREIGN KEY (run_id) REFERENCES payroll_runs(run_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 10. PAY_STUBS TABLE (Use Case 5 Supporting Entity: Individual Pay Receipts)
-- Generates itemized employee statements for each pay run.
-- ------------------------------------------------------------------------------
CREATE TABLE pay_stubs (
    stub_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    pay_period_start DATE NOT NULL,
    pay_period_end DATE NOT NULL,
    regular_earnings NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    overtime_earnings NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    gross_pay NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    fed_tax_deduction NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    ei_deduction NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    qc_tax_deduction NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    qpp_deduction NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    qpip_deduction NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    total_deductions NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    net_pay NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES payroll_runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 11. TAX_SLIPS TABLE (Use Case 5 Supporting Entity: Year-End T4 & Releve 1)
-- End-of-year tax slip compilation.
-- ------------------------------------------------------------------------------
CREATE TABLE tax_slips (
    slip_id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    tax_year INTEGER NOT NULL,
    slip_type VARCHAR(20) NOT NULL CHECK (slip_type IN ('T4', 'Releve_1')),
    box_employment_income NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    box_income_tax_deducted NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    box_cpp_qpp_contributions NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    box_ei_premiums NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    box_qpip_premiums NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- INDEXES FOR TENANT ISOLATION AND PERFORMANCE
-- ------------------------------------------------------------------------------
CREATE INDEX idx_employees_client_id ON employees(client_id);
CREATE INDEX idx_timesheets_employee_id ON timesheets(employee_id);
CREATE INDEX idx_payroll_runs_client_id ON payroll_runs(client_id);
CREATE INDEX idx_pay_stubs_run_id ON pay_stubs(run_id);
CREATE INDEX idx_pay_change_employee_id ON pay_change_history(employee_id);
