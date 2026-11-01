"""
Automated Integration Verification Suite for MNP Payroll Subsystem (BTM 495)
Verifies all 5 Use Cases, 9 Domain Models, and the 4 Defensive Hedges.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.db import db
from models.timesheet import Timesheet
from models.payroll_run import PayrollRun
from services.employee_service import EmployeeService
from services.timesheet_service import TimesheetService
from services.compensation_service import CompensationService
from services.remittance_service import RemittanceService
from services.payroll_service import PayrollService

def run_tests():
    print("==================================================================")
    print(" STARTING MNP PAYROLL SUBSYSTEM INTEGRATION VERIFICATION")
    print("==================================================================")

    # Reset and seed database for a clean test run
    db.init_database(force_reset=True)

    # ------------------------------------------------------------------
    # TEST 1: Multi-Tenant Client & Employee Isolation (Use Case 1)
    # ------------------------------------------------------------------
    print("\n[TEST 1] Verifying UC1: Tenant Isolation & Employee Retrieval...")
    apex_employees = EmployeeService.get_employees_by_client(101)
    bakery_employees = EmployeeService.get_employees_by_client(102)

    assert len(apex_employees) == 3, f"Expected 3 employees for Apex Logistics, got {len(apex_employees)}"
    assert len(bakery_employees) == 1, f"Expected 1 employee for Boulangerie, got {len(bakery_employees)}"
    assert apex_employees[0]["bank"]["masked_account"] == "****4567"
    print("  --> PASS: Tenant isolation confirmed. Apex (3 employees), Bakery (1 employee).")
    print("  --> PASS: Bank account masking active (****4567).")

    # SubFlow 3S.2: Edit Existing Employee Record
    update_res = EmployeeService.update_employee(
        employee_id=1,
        phone="514-555-9999",
        job_title="Lead Logistics Coordinator"
    )
    assert update_res["employee_id"] == 1
    updated_emp = EmployeeService.get_employees_by_client(101)[0]
    assert updated_emp["phone"] == "514-555-9999"
    assert updated_emp["job"]["job_title"] == "Lead Logistics Coordinator"
    print("  --> PASS: UC1 SubFlow 3S.2 confirmed: Employee record updated (514-555-9999, Lead Logistics Coordinator).")

    # ------------------------------------------------------------------
    # TEST 2: Timesheet Submission & Post-Approval Lockout (Use Case 2)
    # ------------------------------------------------------------------
    print("\n[TEST 2] Verifying UC2: Timesheet Submission & Post-Approval Lockout...")
    timesheets = TimesheetService.get_timesheets_for_client(101)
    assert len(timesheets) == 3, f"Expected 3 timesheets, got {len(timesheets)}"

    # Timesheet #1 is already Locked from seed run #1
    try:
        TimesheetService.update_hours(timesheet_id=1, regular_hours=95.0, overtime_hours=10.0)
        assert False, "Security failure: Tampering was allowed on a locked timesheet!"
    except PermissionError as e:
        assert "Tampering prevented" in str(e)
        print(f"  --> PASS: Post-approval tampering blocked: '{e}'")

    # Timesheet #3 is Submitted
    ts3 = [t for t in timesheets if t["timesheet_id"] == 3][0]
    assert ts3["status"] == "Submitted"
    print(f"  --> PASS: Timesheet #{ts3['timesheet_id']} active with status '{ts3['status']}'.")

    # ------------------------------------------------------------------
    # TEST 3: Compensation Modification & SOX Audit Trail (Use Case 3)
    # ------------------------------------------------------------------
    print("\n[TEST 3] Verifying UC3: Wage Modification & SOX Audit Logging...")
    # Update Jean Beliveau (employee #3) rate from 24.00 to 28.00 CAD
    audit_res = CompensationService.update_employee_wage(
        employee_id=3,
        new_rate=28.00,
        reason="Completed Heavy Equipment Operating Certification",
        authorized_by="Bolu Olayinka - Senior Accounting Technician"
    )
    assert audit_res["previous_rate"] == 24.00
    assert audit_res["new_rate"] == 28.00

    # Verify audit trail database row exists
    audit_rows = CompensationService.get_audit_trail(employee_id=3)
    assert len(audit_rows) >= 1
    assert "Heavy Equipment" in audit_rows[0]["change_reason"]
    print(f"  --> PASS: Hourly rate updated: 24.00 -> 28.00 CAD.")
    print(f"  --> PASS: SOX Audit badge verified: '{audit_rows[0]['audit_summary']}'")

    # ------------------------------------------------------------------
    # TEST 4: Quebec Dual Statutory Remittance & CRA/RQ Tokens (Use Case 4)
    # ------------------------------------------------------------------
    print("\n[TEST 4] Verifying UC4: Quebec Dual Remittance & Gateway Tokens...")
    # Transmit remittance for Run #1
    remit_res = RemittanceService.transmit_remittance(remittance_id=1, simulate_timeout=False)
    assert remit_res["success"] is True
    assert remit_res["status"] == "Acknowledged"
    assert "CRA-CONF-2026" in remit_res["cra_confirmation"]
    assert "RQ-BATCH-2026-QC" in remit_res["rq_confirmation"]
    print(f"  --> PASS: CRA Federal Confirmation: {remit_res['cra_confirmation']}")
    print(f"  --> PASS: Revenu Quebec Confirmation: {remit_res['rq_confirmation']}")

    # Test Alternative Flow 7a: Gateway Timeout
    remit_timeout = RemittanceService.transmit_remittance(remittance_id=1, simulate_timeout=True)
    assert remit_timeout["success"] is False
    assert remit_timeout["status"] == "Failed_Timeout"
    assert "Alt Flow 7a" in remit_timeout["alert"]
    print(f"  --> PASS: UC4 Alternate Flow 7a Handled: '{remit_timeout['alert']}'")

    # ------------------------------------------------------------------
    # TEST 5: Payroll Approval Workflow & Rejection Alert Banner (Use Case 5)
    # ------------------------------------------------------------------
    print("\n[TEST 5] Verifying UC5: Approval Workflow & UC5 Rejection Feedback Loop...")
    # Test Manager Rejection (UC5 Alternative Flow 3a - Feedback Loop)
    reject_res = PayrollService.process_approval(
        run_id=1,
        approve=False,
        reason="Discrepancy: Jean Beliveau unpaid leave counted as regular hours.",
        rejected_by="Sarah Jenkins (Client Manager)"
    )
    assert reject_res["status"] == "Rejected"
    alert = reject_res["alert"]
    assert "Alt Flow 3a" in alert["banner_text"]
    assert "Sarah Jenkins" in alert["banner_text"]
    print(f"  --> PASS: UC5 Alternate Flow 3a Alert Banner generated for Technician:")
    print(f"            '{alert['banner_text']}'")

    # Transition Guard Check: Cannot directly approve an already Rejected run without resubmission (Chapter 6: Behavioral Modeling)
    try:
        PayrollService.process_approval(run_id=1, approve=True)
        assert False, "State machine violation: Direct approval allowed from Rejected state without resubmission!"
    except ValueError as e:
        assert "Cannot approve" in str(e)
        print(f"  --> PASS: Chapter 6 Transition Guard blocked direct approval from 'Rejected': '{e}'")

    # Technician addresses discrepancy and resubmits (Rejected -> Pending_Approval)
    resubmit_res = PayrollService.resubmit_for_approval(run_id=1)
    assert resubmit_res["status"] == "Pending_Approval"
    print("  --> PASS: Payroll Run #1 resubmitted: status transitioned to 'Pending_Approval'.")

    # Test Manager Approval (Pending_Approval -> Approved)
    approve_res = PayrollService.process_approval(run_id=1, approve=True)
    assert approve_res["status"] == "Approved"
    print(f"  --> PASS: Payroll Run #1 Approved at {approve_res['approved_at']}.")

    # Verify Timesheet domain operations were invoked (Chapter 7: Transitions Tie to Class Operations)
    # Timesheet 3 was 'Submitted' prior to approval, now locked via Timesheet.lock()
    ts_list = TimesheetService.get_timesheets_for_client(101)
    ts3 = [t for t in ts_list if t["timesheet_id"] == 3][0]
    assert ts3["status"] == "Locked"
    print("  --> PASS: Timesheet #3 locked via domain operation Timesheet.lock() during run approval.")

    # Transition Guard Check: Terminal state prevents duplicate approval (Chapter 6: Only Drawn Transitions)
    try:
        PayrollService.process_approval(run_id=1, approve=True)
        assert False, "State machine violation: Allowed approving an already Approved run!"
    except ValueError as e:
        assert "Cannot approve" in str(e)
        print(f"  --> PASS: Chapter 6 Transition Guard blocked duplicate approval on 'Approved' run: '{e}'")

    # Verify Pay Stubs
    stubs = PayrollService.get_stubs_by_run(run_id=1)
    assert len(stubs) == 2
    assert stubs[0]["earnings"]["gross"] > 0
    assert stubs[0]["net_pay"] > 0
    print(f"  --> PASS: Itemized Pay Stubs generated for {stubs[0]['employee_name']} (Net: {stubs[0]['net_pay']} CAD).")

    # ------------------------------------------------------------------
    # TEST 5b: UC5 Year-End Tax Slip Generation (T4 & Releve 1)
    # ------------------------------------------------------------------
    print("\n[TEST 5b] Verifying UC5: Annual T4 & Releve 1 Tax Slip Generation...")
    # Generate 2026 tax slips for Client 101 (Apex Logistics)
    tax_res = PayrollService.generate_tax_slips(client_id=101, tax_year=2026)
    assert tax_res["success"] is True
    assert tax_res["count"] == 4, f"Expected 4 slips (2 employees x 2 slip types), got {tax_res['count']}"

    # Query generated tax slips
    slips = PayrollService.get_tax_slips(client_id=101, tax_year=2026)
    assert len(slips) == 4

    t4_slips = [s for s in slips if s["slip_type"] == "T4"]
    rl1_slips = [s for s in slips if s["slip_type"] == "Releve_1"]
    assert len(t4_slips) == 2
    assert len(rl1_slips) == 2

    # Verify YTD numbers match pay stubs
    marc_t4 = [s for s in t4_slips if s["employee_id"] == 1][0]
    assert marc_t4["box_employment_income"] == 3675.00
    assert marc_t4["box_income_tax_deducted"] == 551.25
    assert marc_t4["box_ei_premiums"] == 61.01
    assert marc_t4["box_cpp_qpp_contributions"] == 200.29

    marc_rl1 = [s for s in rl1_slips if s["employee_id"] == 1][0]
    assert marc_rl1["box_employment_income"] == 3675.00
    assert marc_rl1["box_income_tax_deducted"] == 551.25
    assert marc_rl1["box_qpip_premiums"] == 18.01

    print(f"  --> PASS: T4 Slip verified for {marc_t4['employee_name']} (Employment Income: {marc_t4['box_employment_income']} CAD).")
    print(f"  --> PASS: Releve 1 Slip verified for {marc_rl1['employee_name']} (QPIP: {marc_rl1['box_qpip_premiums']} CAD).")

    # Verify Defensive Rule: Unapproved run prevents tax slip generation
    db.execute(
        """INSERT INTO payroll_runs (run_id, client_id, period_start, period_end, total_gross,
                                    total_deductions, total_net, approval_status)
           VALUES (999, 101, '2026-11-01', '2026-11-15', 5000.0, 1500.0, 3500.0, 'Pending_Approval')"""
    )
    try:
        PayrollService.generate_tax_slips(client_id=101, tax_year=2026)
        assert False, "Defensive check failed: Tax slips generated while a pay run was unapproved!"
    except ValueError as e:
        assert "must be Approved" in str(e)
        print(f"  --> PASS: UC5 Defensive Rule confirmed: Unapproved run blocked tax slip generation: '{e}'")

    # ------------------------------------------------------------------
    # TEST 6: Domain Integrity - Draft Timesheet Exclusion (Chapter 6) & Salaried Staff Pay (Chapter 7)
    # ------------------------------------------------------------------
    print("\n[TEST 6] Verifying Domain Integrity: Draft Timesheet Exclusion & Salaried Pay Calculation...")
    # 1. Draft Timesheet Exclusion (Chapter 6: Guard Conditions)
    # Timesheet #4 for Client 102 (Boulangerie) is currently in 'Draft'
    try:
        PayrollService.calculate_new_run(client_id=102, period_start="2026-10-01", period_end="2026-10-15")
        assert False, "Accounting integrity failure: Draft timesheet was processed and paid!"
    except ValueError as e:
        assert "No submitted timesheets found" in str(e)
        print(f"  --> PASS: Chapter 6 Guard Verified: Draft timesheets excluded from pay run: '{e}'")

    # Submit Timesheet #4 so it becomes payable
    TimesheetService.submit_timesheet(timesheet_id=4)
    run_bakery = PayrollService.calculate_new_run(client_id=102, period_start="2026-10-01", period_end="2026-10-15")
    assert run_bakery["run_id"] is not None
    print(f"  --> PASS: Timesheet #4 submitted and processed in Pay Run #{run_bakery['run_id']}.")

    # 2. Salaried Staff Pay Calculation (Chapter 7: Attribute Traceability)
    # Add a purely salaried employee (hourly_rate = 0.00, base_salary = 78000.00)
    new_sal_emp = EmployeeService.create_employee(
        client_id=102,
        first_name="Henri",
        last_name="Richard",
        email="h.richard@boulangeriesl.ca",
        phone="514-555-8888",
        hire_date="2026-01-15",
        institution_number="001",
        transit_number="12345",
        account_number="9876543",
        account_type="Checking",
        job_title="Executive Pastry Chef",
        department="Kitchen",
        employment_type="Full-Time",
        hourly_rate=0.00,
        base_salary=78000.00,
        pay_frequency="Bi-Weekly"
    )
    sal_emp_id = new_sal_emp["employee_id"]

    # Seed a submitted timesheet for Henri for the next pay period
    db.execute(
        """INSERT INTO timesheets (employee_id, period_start, period_end, regular_hours, overtime_hours, status)
           VALUES (?, '2026-10-16', '2026-10-31', 80.00, 0.00, 'Submitted')""",
        (sal_emp_id,)
    )

    sal_run = PayrollService.calculate_new_run(client_id=102, period_start="2026-10-16", period_end="2026-10-31")
    sal_stubs = PayrollService.get_stubs_by_run(sal_run["run_id"])
    henri_stub = [s for s in sal_stubs if s["employee_id"] == sal_emp_id][0]

    # Expected bi-weekly regular earnings: 78000 / 26 = 3000.00 CAD
    expected_sal_reg = round(78000.00 / 26.0, 2)
    assert henri_stub["earnings"]["regular"] == expected_sal_reg
    assert henri_stub["earnings"]["gross"] == expected_sal_reg
    print(f"  --> PASS: Chapter 7 Traceability Verified: Salaried employee {henri_stub['employee_name']} earned {henri_stub['earnings']['gross']} CAD (78000/26), not 0 CAD.")

    # ------------------------------------------------------------------
    # TEST 7: Domain State Machine Transition Guards (Chapter 6: Behavioral Modeling)
    # ------------------------------------------------------------------
    print("\n[TEST 7] Verifying Explicit Transition Guards on Timesheet & PayrollRun...")
    
    # Timesheet Transition Guards:
    ts_test = Timesheet(timesheet_id=999, employee_id=1, period_start="2026-11-01", period_end="2026-11-15", status="Draft")
    
    # Guard: Cannot lock from Draft
    try:
        ts_test.lock()
        assert False, "State violation: Timesheet.lock() succeeded from Draft!"
    except ValueError as e:
        assert "Cannot lock timesheet" in str(e)
        print(f"  --> PASS: Timesheet transition guard blocked lock() from 'Draft': '{e}'")

    # Guard: Cannot approve from Draft
    try:
        ts_test.approve()
        assert False, "State violation: Timesheet.approve() succeeded from Draft!"
    except ValueError as e:
        assert "Cannot approve timesheet" in str(e)
        print(f"  --> PASS: Timesheet transition guard blocked approve() from 'Draft': '{e}'")

    # Transition Draft -> Submitted
    ts_test.submit()
    assert ts_test.status == "Submitted"

    # Guard: Cannot submit from Submitted
    try:
        ts_test.submit()
        assert False, "State violation: Timesheet.submit() succeeded from Submitted!"
    except ValueError as e:
        assert "Cannot submit timesheet" in str(e)
        print(f"  --> PASS: Timesheet transition guard blocked submit() from 'Submitted': '{e}'")

    # PayrollRun Transition Guards:
    pr_test = PayrollRun(run_id=888, client_id=101, period_start="2026-11-01", period_end="2026-11-15", approval_status="Draft")
    
    # Guard: Cannot approve from Draft
    try:
        pr_test.approve()
        assert False, "State violation: PayrollRun.approve() succeeded from Draft!"
    except ValueError as e:
        assert "Cannot approve payroll run" in str(e)
        print(f"  --> PASS: PayrollRun transition guard blocked approve() from 'Draft': '{e}'")

    # Guard: Cannot reject from Draft
    try:
        pr_test.reject("Draft rejection")
        assert False, "State violation: PayrollRun.reject() succeeded from Draft!"
    except ValueError as e:
        assert "Cannot reject payroll run" in str(e)
        print(f"  --> PASS: PayrollRun transition guard blocked reject() from 'Draft': '{e}'")

    print("\n==================================================================")
    print(" ALL INTEGRATION TESTS PASSED: 100% SUCCESS")
    print(" ALL 5 USE CASES, DOMAIN REFACTORS & GUARDS VERIFIED")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()
