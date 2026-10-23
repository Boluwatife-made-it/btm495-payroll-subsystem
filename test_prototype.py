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

    print("\n==================================================================")
    print(" ALL INTEGRATION TESTS PASSED: 100% SUCCESS")
    print(" ALL 5 USE CASES AND BUSINESS RULES VERIFIED")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()
