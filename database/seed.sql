-- ==============================================================================
-- MNP CENTRALIZED CLOUD-BASED PAYROLL SUBSYSTEM (BTM 495 PROTOTYPE)
-- MASTER SEED DATA: Realistic Quebec & Canadian Payroll Scenarios
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. SEED CLIENTS (Multi-Tenant Test: 2 Separate Client Firms)
-- ------------------------------------------------------------------------------
INSERT INTO clients (client_id, client_name, company_address, contact_email) VALUES
(101, 'Apex Logistics Inc.', '1250 Rene-Levesque Blvd W, Montreal, QC H3B 4W8', 'payroll@apexlogistics.ca'),
(102, 'Boulangerie Saint-Laurent Inc.', '3922 Saint-Laurent Blvd, Montreal, QC H2W 1Y3', 'admin@boulangeriesl.ca');

-- ------------------------------------------------------------------------------
-- 2. SEED EMPLOYEES
-- Client 101: Apex Logistics (3 employees)
-- Client 102: Boulangerie Saint-Laurent (1 employee to verify tenant isolation)
-- ------------------------------------------------------------------------------
INSERT INTO employees (employee_id, client_id, first_name, last_name, email, phone, hire_date, status) VALUES
(1, 101, 'Marc', 'Tremblay', 'm.tremblay@apexlogistics.ca', '514-555-0143', '2022-03-15', 'Active'),
(2, 101, 'Sarah', 'Jenkins', 's.jenkins@apexlogistics.ca', '514-555-0188', '2023-06-01', 'Active'),
(3, 101, 'Jean', 'Beliveau', 'j.beliveau@apexlogistics.ca', '514-555-0199', '2024-01-10', 'Active'),
(4, 102, 'Amelie', 'Poulin', 'a.poulin@boulangeriesl.ca', '514-555-0211', '2023-11-20', 'Active');

-- ------------------------------------------------------------------------------
-- 3. SEED BANK ACCOUNTS (Direct Deposit Coordinates)
-- ------------------------------------------------------------------------------
INSERT INTO bank_accounts (account_id, employee_id, institution_number, transit_number, account_number, account_type) VALUES
(1, 1, '001', '10234', '1234567', 'Checking'), -- BMO
(2, 2, '003', '20456', '7654321', 'Checking'), -- RBC
(3, 3, '815', '30789', '9876543', 'Savings'),  -- Desjardins
(4, 4, '006', '40123', '3456789', 'Checking'); -- National Bank

-- ------------------------------------------------------------------------------
-- 4. SEED JOB INFORMATION (Titles, Departments, Wage Rates)
-- ------------------------------------------------------------------------------
INSERT INTO job_information (job_id, employee_id, job_title, department, employment_type, base_salary, hourly_rate) VALUES
(1, 1, 'Operations Manager', 'Operations', 'Full-Time', 87360.00, 42.00),
(2, 2, 'Logistics Coordinator', 'Dispatch', 'Full-Time', 67600.00, 32.50),
(3, 3, 'Warehouse Associate', 'Logistics', 'Part-Time', 0.00, 24.00),
(4, 4, 'Head Baker', 'Production', 'Full-Time', 45760.00, 22.00);

-- ------------------------------------------------------------------------------
-- 5. SEED COMPENSATION STRUCTURES (Bi-Weekly Frequency, 1.5x OT)
-- ------------------------------------------------------------------------------
INSERT INTO compensation_structures (structure_id, employee_id, pay_frequency, overtime_multiplier, bonus_rate, commission_rate) VALUES
(1, 1, 'Bi-Weekly', 1.50, 500.00, 0.00),
(2, 2, 'Bi-Weekly', 1.50, 0.00, 0.00),
(3, 3, 'Bi-Weekly', 1.50, 0.00, 0.00),
(4, 4, 'Bi-Weekly', 1.50, 0.00, 0.00);

-- ------------------------------------------------------------------------------
-- 6. SEED PAY CHANGE HISTORY (SOX-Compliant Audit Trail)
-- Proves Use Case 3 records an unalterable history log
-- ------------------------------------------------------------------------------
INSERT INTO pay_change_history (history_id, employee_id, change_date, previous_rate, new_rate, change_reason, authorized_by) VALUES
(1, 1, '2026-09-01 09:00:00', 38.00, 42.00, 'Annual Performance Review & Promotion to Lead', 'Bolu Olayinka - Senior Accounting Technician'),
(2, 2, '2026-08-15 11:30:00', 30.00, 32.50, 'Market Adjustment for Dispatch Certifications', 'Bolu Olayinka - Senior Accounting Technician');

-- ------------------------------------------------------------------------------
-- 7. SEED TIMESHEETS (Period: 2026-10-01 to 2026-10-15)
-- Employees 1 & 2 are Locked (already paid in Run #1)
-- Employee 3 is Submitted (ready for the next pay cycle)
-- ------------------------------------------------------------------------------
INSERT INTO timesheets (timesheet_id, employee_id, period_start, period_end, regular_hours, overtime_hours, vacation_days, sick_days, status) VALUES
(1, 1, '2026-10-01', '2026-10-15', 80.00, 5.00, 0, 0, 'Locked'),
(2, 2, '2026-10-01', '2026-10-15', 80.00, 0.00, 0, 0, 'Locked'),
(3, 3, '2026-10-01', '2026-10-15', 40.00, 2.00, 0, 1, 'Submitted'),
(4, 4, '2026-10-01', '2026-10-15', 75.00, 0.00, 0, 0, 'Draft');

-- ------------------------------------------------------------------------------
-- 8. SEED COMPLETED PAYROLL RUN #1 (Client 101, Approved & Paid)
-- ------------------------------------------------------------------------------
INSERT INTO payroll_runs (run_id, client_id, period_start, period_end, run_date, total_gross, total_deductions, total_net, approval_status, approved_at, rejection_reason) VALUES
(1, 101, '2026-10-01', '2026-10-15', '2026-10-16 10:00:00', 6275.00, 1819.75, 4455.25, 'Approved', '2026-10-16 14:30:00', NULL);

-- ------------------------------------------------------------------------------
-- 9. SEED STATUTORY REMITTANCES (Quebec Dual Split for Run #1)
-- Proves Use Case 4 Dual CRA and RQ Remittance with confirmation tokens
-- ------------------------------------------------------------------------------
INSERT INTO statutory_remittances (remittance_id, run_id, remittance_period, cra_federal_tax, cra_ei_deduction, cra_total_remitted, cra_confirmation_number, rq_provincial_tax, rq_qpp_deduction, rq_qpip_deduction, rq_total_remitted, rq_confirmation_number, status) VALUES
(1, 1, '2026-10', 941.25, 104.17, 1045.42, 'CRA-CONF-2026-98214-OK', 941.25, 341.99, 30.75, 1313.99, 'RQ-BATCH-2026-QC-44109', 'Acknowledged');

-- ------------------------------------------------------------------------------
-- 10. SEED PAY STUBS (Receipts for Employees 1 & 2 from Run #1)
-- ------------------------------------------------------------------------------
INSERT INTO pay_stubs (stub_id, run_id, employee_id, pay_period_start, pay_period_end, regular_earnings, overtime_earnings, gross_pay, fed_tax_deduction, ei_deduction, qc_tax_deduction, qpp_deduction, qpip_deduction, total_deductions, net_pay) VALUES
(1, 1, 1, '2026-10-01', '2026-10-15', 3360.00, 315.00, 3675.00, 551.25, 61.01, 551.25, 200.29, 18.01, 1381.81, 2293.19),
(2, 1, 2, '2026-10-01', '2026-10-15', 2600.00, 0.00, 2600.00, 390.00, 43.16, 390.00, 141.70, 12.74, 977.60, 1622.40);

-- ------------------------------------------------------------------------------
-- 11. SEED TAX SLIPS (Sample 2025 Prior Year T4 and Releve 1)
-- ------------------------------------------------------------------------------
INSERT INTO tax_slips (slip_id, employee_id, tax_year, slip_type, box_employment_income, box_income_tax_deducted, box_cpp_qpp_contributions, box_ei_premiums, box_qpip_premiums) VALUES
(1, 1, 2025, 'T4', 79040.00, 11856.00, 4038.40, 1049.12, 0.00),
(2, 1, 2025, 'Releve_1', 79040.00, 11856.00, 4038.40, 0.00, 387.30);
