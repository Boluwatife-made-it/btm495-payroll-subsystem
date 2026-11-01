"""
Payroll Service (Use Case 5: Approve Payroll & Generate Tax Slips)
Executes gross-to-net pay calculation, manager approval/rejection lifecycle,
locks timesheets post-approval, and generates employee pay stubs.
Coordinates with PayrollRepository, TimesheetRepository, and RemittanceRepository
for Data Access Management (Chapter 7 C.5).
"""

from datetime import datetime
from models.payroll_run import PayrollRun, PayStub, TaxSlip
from models.timesheet import Timesheet
from models.employee import Employee
from models.statutory_remittance import StatutoryRemittance
from repositories.payroll_repository import PayrollRepository
from repositories.timesheet_repository import TimesheetRepository
from repositories.remittance_repository import RemittanceRepository

class PayrollService:
    @staticmethod
    def get_runs_by_client(client_id: int):
        """Fetches all payroll runs for a client (Chapter 7: Factoring)."""
        rows = PayrollRepository.get_runs_by_client(client_id)
        return [PayrollRun.from_row(r).to_dict() for r in rows]

    @staticmethod
    def calculate_new_run(client_id: int, period_start: str, period_end: str):
        """
        Gathers submitted timesheets for client personnel, calculates gross-to-net
        Quebec payroll, inserts payroll_run in 'Pending_Approval', and drafts pay stubs.
        """
        # 1. Fetch submitted timesheets via TimesheetRepository (DAM Layer)
        records = TimesheetRepository.get_submitted_for_payroll(client_id, period_start, period_end)
        if not records:
            raise ValueError(f"No submitted timesheets found for Client #{client_id} for period {period_start} to {period_end}.")

        # 2. Delegate earnings and statutory deductions calculation to domain models (Knowing & Doing Together)
        run = PayrollRun(
            run_id=0,
            client_id=client_id,
            period_start=period_start,
            period_end=period_end,
            approval_status="Pending_Approval"
        )
        stubs = []
        fed_tax_total = 0.0
        ei_total = 0.0
        qc_tax_total = 0.0
        qpp_total = 0.0
        qpip_total = 0.0

        for r in records:
            stub = PayStub.calculate(
                employee_id=r["employee_id"],
                regular_hours=r["regular_hours"],
                overtime_hours=r["overtime_hours"],
                hourly_rate=r["hourly_rate"],
                base_salary=r.get("base_salary") or 0.0,
                overtime_multiplier=r.get("overtime_multiplier") or 1.5,
                period_start=period_start,
                period_end=period_end
            )
            run.add_stub(stub)
            stubs.append(stub)

            fed_tax_total = round(fed_tax_total + stub.fed_tax_deduction, 2)
            ei_total = round(ei_total + stub.ei_deduction, 2)
            qc_tax_total = round(qc_tax_total + stub.qc_tax_deduction, 2)
            qpp_total = round(qpp_total + stub.qpp_deduction, 2)
            qpip_total = round(qpip_total + stub.qpip_deduction, 2)

        # 3. Insert Payroll Run via PayrollRepository (DAM Layer)
        run_id = PayrollRepository.create_run(run)
        run.run_id = run_id

        # 4. Insert Pay Stubs via PayrollRepository (DAM Layer)
        for s in stubs:
            s.run_id = run_id
        PayrollRepository.save_pay_stubs(stubs)

        # 5. Build and insert Statutory Remittance via Domain Factory and RemittanceRepository
        remittance = StatutoryRemittance.from_payroll_run(
            run_id=run_id,
            period_start=period_start,
            fed_tax=fed_tax_total,
            ei=ei_total,
            qc_tax=qc_tax_total,
            qpp=qpp_total,
            qpip=qpip_total
        )
        RemittanceRepository.save_initial(remittance)

        return {
            "run_id": run_id,
            "client_id": client_id,
            "period": f"{period_start} to {period_end}",
            "total_gross": run.total_gross,
            "total_deductions": run.total_deductions,
            "total_net": run.total_net,
            "approval_status": "Pending_Approval",
            "message": "Payroll run calculated and submitted for Client Manager approval."
        }

    @staticmethod
    def process_approval(run_id: int, approve: bool, reason: str = None, rejected_by: str = "Client Manager"):
        """
        Processes Client Manager approval or rejection.
        If approved: Locks timesheets and timestamps run.
        If rejected: Flags run as Rejected and triggers the UC5 Alt Flow 3a technician alert.
        """
        row = PayrollRepository.get_run_by_id(run_id)
        if not row:
            raise ValueError(f"Payroll Run #{run_id} not found.")

        run = PayrollRun.from_row(row)

        if approve:
            # Load associated timesheets as domain objects to tie transitions to operations
            ts_rows = TimesheetRepository.get_period_timesheets_for_approval(run.client_id, run.period_start, run.period_end)
            timesheet_objs = [Timesheet.from_row(ts) for ts in ts_rows]

            # 1. Approve domain model and lock associated timesheets via domain operations
            res = run.approve(associated_timesheets=timesheet_objs)

            # 2. Persist state machine transitions through repositories
            PayrollRepository.update_approval_status(run_id, "Approved", approved_at=run.approved_at)
            for ts in timesheet_objs:
                TimesheetRepository.update_status(ts.timesheet_id, ts.status)

            return {
                "success": True,
                "status": "Approved",
                "approved_at": run.approved_at,
                "timesheets_locked": res.get("timesheets_locked", len(timesheet_objs)),
                "message": "Payroll Run approved. All associated timesheets locked."
            }
        else:
            # Rejection flow (Alternative Flow 3a)
            alert = run.reject(reason=reason, rejected_by=rejected_by)
            PayrollRepository.update_approval_status(run_id, "Rejected", rejection_reason=run.rejection_reason)
            return {
                "success": False,
                "status": "Rejected",
                "rejection_reason": run.rejection_reason,
                "alert": alert
            }

    @staticmethod
    def resubmit_for_approval(run_id: int):
        """
        Resubmits a rejected pay run back to Pending_Approval after discrepancy resolution.
        Enforces the state machine transition Rejected -> Pending_Approval.
        """
        row = PayrollRepository.get_run_by_id(run_id)
        if not row:
            raise ValueError(f"Payroll Run #{run_id} not found.")

        run = PayrollRun.from_row(row)
        run.submit_for_approval()
        PayrollRepository.update_approval_status(run_id, "Pending_Approval")
        return {
            "success": True,
            "status": "Pending_Approval",
            "message": f"Payroll Run #{run_id} resubmitted for Client Manager approval."
        }

    @staticmethod
    def get_stubs_by_run(run_id: int):
        """Fetches itemized pay stubs for a run with employee names."""
        rows = PayrollRepository.get_stubs_by_run(run_id)
        results = []
        for r in rows:
            stub = PayStub.from_row(r)
            d = stub.to_dict()
            d["employee_name"] = Employee.format_full_name(r["first_name"], r["last_name"])
            results.append(d)
        return results

    @staticmethod
    def generate_tax_slips(client_id: int, tax_year: int):
        """
        Generates annual T4 (Federal) and Releve 1 (Quebec) tax slips for all employees
        of a client for a given tax year.
        Directly implements Use Case 5 Normal Flow:
        1. Verifies that all payroll runs for the tax year are finalized and Approved.
        2. Aggregates YTD gross earnings and statutory deductions across all approved pay stubs.
        3. Generates and stores official T4 and Releve 1 slips via PayrollRepository.
        """
        # 1. Fetch all payroll runs for client and tax year via repository
        runs = PayrollRepository.get_runs_for_tax_year(client_id, tax_year)
        if not runs:
            raise ValueError(f"No payroll runs found for Client #{client_id} in tax year {tax_year}.")

        # Verify all runs are Approved
        unapproved = [r for r in runs if r["approval_status"] != "Approved"]
        if unapproved:
            unappr_ids = ", ".join(f"#{r['run_id']} ({r['approval_status']})" for r in unapproved)
            raise ValueError(
                f"Cannot generate tax slips: Payroll runs {unappr_ids} are not finalized. "
                f"All pay runs for tax year {tax_year} must be Approved."
            )

        # 2. Aggregate YTD totals per employee across all approved runs in the tax year
        records = PayrollRepository.get_ytd_stub_totals_for_year(client_id, tax_year)
        if not records:
            raise ValueError(f"No pay stubs found for Client #{client_id} in tax year {tax_year}.")

        created_slips = []

        for r in records:
            emp_id = r["employee_id"]
            emp_name = Employee.format_full_name(r["first_name"], r["last_name"])
            gross = float(r["ytd_gross"])
            fed_tax = float(r["ytd_fed_tax"])
            ei = float(r["ytd_ei"])
            qc_tax = float(r["ytd_qc_tax"])
            qpp = float(r["ytd_qpp"])
            qpip = float(r["ytd_qpip"])

            # Remove prior slips for this year and employee to ensure idempotency
            PayrollRepository.delete_tax_slips_for_employee_year(emp_id, tax_year)

            # 2a. Federal T4 Tax Slip
            t4_slip = TaxSlip(
                slip_id=0, employee_id=emp_id, tax_year=tax_year,
                slip_type="T4", box_employment_income=gross,
                box_income_tax_deducted=fed_tax, box_cpp_qpp_contributions=qpp,
                box_ei_premiums=ei, box_qpip_premiums=qpip
            )
            t4_id = PayrollRepository.save_tax_slip(t4_slip)
            t4_slip.slip_id = t4_id
            t4_dict = t4_slip.to_dict()
            t4_dict["employee_name"] = emp_name
            created_slips.append(t4_dict)

            # 2b. Quebec Releve 1 (RL-1) Tax Slip
            rl1_slip = TaxSlip(
                slip_id=0, employee_id=emp_id, tax_year=tax_year,
                slip_type="Releve_1", box_employment_income=gross,
                box_income_tax_deducted=qc_tax, box_cpp_qpp_contributions=qpp,
                box_ei_premiums=ei, box_qpip_premiums=qpip
            )
            rl1_id = PayrollRepository.save_tax_slip(rl1_slip)
            rl1_slip.slip_id = rl1_id
            rl1_dict = rl1_slip.to_dict()
            rl1_dict["employee_name"] = emp_name
            created_slips.append(rl1_dict)

        return {
            "success": True,
            "client_id": client_id,
            "tax_year": tax_year,
            "count": len(created_slips),
            "tax_slips": created_slips,
            "message": f"Successfully generated {len(created_slips)} tax slips (T4 and Releve 1) for tax year {tax_year}."
        }

    @staticmethod
    def get_tax_slips(client_id: int = None, employee_id: int = None, tax_year: int = None):
        """Fetches tax slips filtered by client, employee, and/or tax year."""
        rows = PayrollRepository.get_tax_slips(client_id, employee_id, tax_year)
        results = []
        for r in rows:
            slip = TaxSlip.from_row(r)
            d = slip.to_dict()
            d["employee_name"] = Employee.format_full_name(r["first_name"], r["last_name"])
            d["client_id"] = r["client_id"]
            results.append(d)
        return results
