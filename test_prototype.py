"""
Automated Integration Verification Suite for MNP Payroll Subsystem (BTM 495)
Verifies all 5 Use Cases, 9 Domain Models, and the 4 Defensive Hedges.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.db import db
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

    # Test Manager Approval
    approve_res = PayrollService.process_approval(run_id=1, approve=True)
    assert approve_res["status"] == "Approved"
    print(f"  --> PASS: Payroll Run #1 Approved at {approve_res['approved_at']}.")

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

    print("\n==================================================================")
    print(" ALL INTEGRATION TESTS PASSED: 100% SUCCESS")
    print(" ALL 5 USE CASES AND BUSINESS RULES VERIFIED")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()
