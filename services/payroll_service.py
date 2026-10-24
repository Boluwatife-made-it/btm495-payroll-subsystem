"""
Payroll Service (Use Case 5: Approve Payroll & Generate Tax Slips)
Executes gross-to-net pay calculation, manager approval/rejection lifecycle,
locks timesheets post-approval, and generates employee pay stubs.
"""

from datetime import datetime
from database.db import db
from models.payroll_run import PayrollRun, PayStub, TaxSlip
from models.timesheet import Timesheet

class PayrollService:
    @staticmethod
    def get_runs_by_client(client_id: int):
        """Fetches all payroll runs for a client."""
        sql = "SELECT * FROM payroll_runs WHERE client_id = ? ORDER BY run_id DESC"
        rows = db.query_all(sql, (client_id,))
        results = []
        for r in rows:
            run = PayrollRun(
                run_id=r["run_id"],
                client_id=r["client_id"],
                period_start=r["period_start"],
                period_end=r["period_end"],
                run_date=r["run_date"],
                total_gross=float(r["total_gross"]),
                total_deductions=float(r["total_deductions"]),
                total_net=float(r["total_net"]),
                approval_status=r["approval_status"],
                approved_at=r["approved_at"],
                rejection_reason=r["rejection_reason"]
            )
            results.append(run.to_dict())
        return results

    @staticmethod
    def calculate_new_run(client_id: int, period_start: str, period_end: str):
        """
        Gathers submitted timesheets for client personnel, calculates gross-to-net
        Quebec payroll, inserts payroll_run in 'Pending_Approval', and drafts pay stubs.
        """
        # Fetch client employees and their job & timesheet records
        sql = """
            SELECT e.employee_id, e.first_name, e.last_name,
                   j.hourly_rate, j.base_salary,
                   c.overtime_multiplier,
                   t.timesheet_id, t.regular_hours, t.overtime_hours, t.status as timesheet_status
            FROM employees e
            JOIN job_information j ON e.employee_id = j.employee_id
            JOIN compensation_structures c ON e.employee_id = c.employee_id
            JOIN timesheets t ON e.employee_id = t.employee_id
            WHERE e.client_id = ? AND t.period_start = ? AND t.period_end = ?
        """
        records = db.query_all(sql, (client_id, period_start, period_end))
        if not records:
            raise ValueError(f"No submitted timesheets found for Client #{client_id} for period {period_start} to {period_end}.")

        run_gross = 0.0
        run_deductions = 0.0
        run_net = 0.0

        fed_tax_total = 0.0
        ei_total = 0.0
        qc_tax_total = 0.0
        qpp_total = 0.0
        qpip_total = 0.0

        stub_data = []

        for r in records:
            reg_hrs = float(r["regular_hours"])
            ot_hrs = float(r["overtime_hours"])
            rate = float(r["hourly_rate"])
            ot_mult = float(r["overtime_multiplier"])

            reg_earn = round(reg_hrs * rate, 2)
            ot_earn = round(ot_hrs * rate * ot_mult, 2)
            gross = round(reg_earn + ot_earn, 2)

            # Standard Canadian & Quebec Statutory Deductions formulas
            fed_tax = round(gross * 0.15, 2)       # 15% Federal Bracket
            ei = round(gross * 0.0166, 2)          # 1.66% EI Rate
            qc_tax = round(gross * 0.15, 2)        # 15% Quebec Provincial Bracket
            qpp = round(gross * 0.054, 2)          # 5.4% QPP Base Contribution
            qpip = round(gross * 0.00494, 2)       # 0.494% QPIP Employee Rate

            tot_ded = round(fed_tax + ei + qc_tax + qpp + qpip, 2)
            net = round(gross - tot_ded, 2)

            run_gross += gross
            run_deductions += tot_ded
            run_net += net

            fed_tax_total += fed_tax
            ei_total += ei
            qc_tax_total += qc_tax
            qpp_total += qpp
            qpip_total += qpip

            stub_data.append({
                "employee_id": r["employee_id"],
                "reg_earn": reg_earn,
                "ot_earn": ot_earn,
                "gross": gross,
                "fed_tax": fed_tax,
                "ei": ei,
                "qc_tax": qc_tax,
                "qpp": qpp,
                "qpip": qpip,
                "tot_ded": tot_ded,
                "net": net
            })

        # Insert Payroll Run (Initial status: Pending_Approval)
        run_id = db.execute(
            """INSERT INTO payroll_runs (client_id, period_start, period_end, total_gross,
                                        total_deductions, total_net, approval_status)
               VALUES (?, ?, ?, ?, ?, ?, 'Pending_Approval')""",
            (client_id, period_start, period_end, run_gross, run_deductions, run_net)
        )

        # Insert Pay Stubs
        for s in stub_data:
            db.execute(
                """INSERT INTO pay_stubs (run_id, employee_id, pay_period_start, pay_period_end,
                                         regular_earnings, overtime_earnings, gross_pay,
                                         fed_tax_deduction, ei_deduction, qc_tax_deduction,
                                         qpp_deduction, qpip_deduction, total_deductions, net_pay)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, s["employee_id"], period_start, period_end, s["reg_earn"], s["ot_earn"],
                 s["gross"], s["fed_tax"], s["ei"], s["qc_tax"], s["qpp"], s["qpip"], s["tot_ded"], s["net"])
            )

        # Insert Associated Statutory Remittance Draft
        period_label = period_start[:7] # e.g. '2026-10'
        cra_tot = round(fed_tax_total + ei_total, 2)
        rq_tot = round(qc_tax_total + qpp_total + qpip_total, 2)
        db.execute(
            """INSERT INTO statutory_remittances (run_id, remittance_period, cra_federal_tax,
                                                 cra_ei_deduction, cra_total_remitted,
                                                 rq_provincial_tax, rq_qpp_deduction,
                                                 rq_qpip_deduction, rq_total_remitted, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Calculated')""",
            (run_id, period_label, fed_tax_total, ei_total, cra_tot,
             qc_tax_total, qpp_total, qpip_total, rq_tot)
        )

        return {
            "run_id": run_id,
            "client_id": client_id,
            "period": f"{period_start} to {period_end}",
            "total_gross": run_gross,
            "total_deductions": run_deductions,
            "total_net": run_net,
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
        row = db.query_one("SELECT * FROM payroll_runs WHERE run_id = ?", (run_id,))
        if not row:
            raise ValueError(f"Payroll Run #{run_id} not found.")

        run = PayrollRun(
            run_id=row["run_id"],
            client_id=row["client_id"],
            period_start=row["period_start"],
            period_end=row["period_end"],
            run_date=row["run_date"],
            total_gross=row["total_gross"],
            total_deductions=row["total_deductions"],
            total_net=row["total_net"],
            approval_status=row["approval_status"]
        )

        if approve:
            # 1. Approve domain model
            res = run.approve()
            db.execute(
                "UPDATE payroll_runs SET approval_status = 'Approved', approved_at = ?, rejection_reason = NULL WHERE run_id = ?",
                (run.approved_at, run_id)
            )

            # 2. Lock all timesheets linked to this client and pay period (Post-Approval Hedge)
            db.execute(
                """UPDATE timesheets SET status = 'Locked'
                   WHERE period_start = ? AND period_end = ?
                   AND employee_id IN (SELECT employee_id FROM employees WHERE client_id = ?)""",
                (run.period_start, run.period_end, run.client_id)
            )
            return {
                "success": True,
                "status": "Approved",
                "approved_at": run.approved_at,
                "message": "Payroll Run approved. All associated timesheets locked."
            }
        else:
            # Rejection flow (Alternative Flow 3a)
            alert = run.reject(reason=reason, rejected_by=rejected_by)
            db.execute(
                "UPDATE payroll_runs SET approval_status = 'Rejected', rejection_reason = ? WHERE run_id = ?",
                (run.rejection_reason, run_id)
            )
            return {
                "success": False,
                "status": "Rejected",
                "rejection_reason": run.rejection_reason,
                "alert": alert
            }

    @staticmethod
    def get_stubs_by_run(run_id: int):
        """Fetches itemized pay stubs for a run with employee names."""
        sql = """
            SELECT p.*, e.first_name, e.last_name
            FROM pay_stubs p
            JOIN employees e ON p.employee_id = e.employee_id
            WHERE p.run_id = ?
        """
        rows = db.query_all(sql, (run_id,))
        results = []
        for r in rows:
            stub = PayStub(
                stub_id=r["stub_id"], run_id=r["run_id"], employee_id=r["employee_id"],
                pay_period_start=r["pay_period_start"], pay_period_end=r["pay_period_end"],
                regular_earnings=r["regular_earnings"], overtime_earnings=r["overtime_earnings"],
                gross_pay=r["gross_pay"], fed_tax_deduction=r["fed_tax_deduction"],
                ei_deduction=r["ei_deduction"], qc_tax_deduction=r["qc_tax_deduction"],
                qpp_deduction=r["qpp_deduction"], qpip_deduction=r["qpip_deduction"],
                total_deductions=r["total_deductions"], net_pay=r["net_pay"],
                generated_at=r["generated_at"]
            )
            d = stub.to_dict()
            d["employee_name"] = f"{r['first_name']} {r['last_name']}"
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
        3. Generates and stores official T4 and Releve 1 slips in the database.
        """
        year_prefix = f"{tax_year}%"

        # 1. Fetch all payroll runs for client and tax year
        runs = db.query_all(
            """SELECT run_id, period_start, period_end, approval_status
               FROM payroll_runs
               WHERE client_id = ? AND (period_start LIKE ? OR period_end LIKE ?)""",
            (client_id, year_prefix, year_prefix)
        )

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
        sql = """
            SELECT p.employee_id,
                   e.first_name, e.last_name,
                   ROUND(SUM(p.gross_pay), 2) as ytd_gross,
                   ROUND(SUM(p.fed_tax_deduction), 2) as ytd_fed_tax,
                   ROUND(SUM(p.ei_deduction), 2) as ytd_ei,
                   ROUND(SUM(p.qc_tax_deduction), 2) as ytd_qc_tax,
                   ROUND(SUM(p.qpp_deduction), 2) as ytd_qpp,
                   ROUND(SUM(p.qpip_deduction), 2) as ytd_qpip
            FROM pay_stubs p
            JOIN payroll_runs r ON p.run_id = r.run_id
            JOIN employees e ON p.employee_id = e.employee_id
            WHERE r.client_id = ? AND (r.period_start LIKE ? OR r.period_end LIKE ?)
            GROUP BY p.employee_id, e.first_name, e.last_name
        """
        records = db.query_all(sql, (client_id, year_prefix, year_prefix))
        if not records:
            raise ValueError(f"No pay stubs found for Client #{client_id} in tax year {tax_year}.")

        created_slips = []

        for r in records:
            emp_id = r["employee_id"]
            emp_name = f"{r['first_name']} {r['last_name']}"
            gross = float(r["ytd_gross"])
            fed_tax = float(r["ytd_fed_tax"])
            ei = float(r["ytd_ei"])
            qc_tax = float(r["ytd_qc_tax"])
            qpp = float(r["ytd_qpp"])
            qpip = float(r["ytd_qpip"])

            # Remove prior slips for this year and employee to ensure idempotency
            db.execute("DELETE FROM tax_slips WHERE employee_id = ? AND tax_year = ?", (emp_id, tax_year))

            # 2a. Federal T4 Tax Slip
            t4_id = db.execute(
                """INSERT INTO tax_slips (employee_id, tax_year, slip_type,
                                          box_employment_income, box_income_tax_deducted,
                                          box_cpp_qpp_contributions, box_ei_premiums,
                                          box_qpip_premiums)
                   VALUES (?, ?, 'T4', ?, ?, ?, ?, ?)""",
                (emp_id, tax_year, gross, fed_tax, qpp, ei, qpip)
            )
            t4_slip = TaxSlip(
                slip_id=t4_id, employee_id=emp_id, tax_year=tax_year,
                slip_type="T4", box_employment_income=gross,
                box_income_tax_deducted=fed_tax, box_cpp_qpp_contributions=qpp,
                box_ei_premiums=ei, box_qpip_premiums=qpip
            )
            t4_dict = t4_slip.to_dict()
            t4_dict["employee_name"] = emp_name
            created_slips.append(t4_dict)

            # 2b. Quebec Releve 1 (RL-1) Tax Slip
            rl1_id = db.execute(
                """INSERT INTO tax_slips (employee_id, tax_year, slip_type,
                                          box_employment_income, box_income_tax_deducted,
                                          box_cpp_qpp_contributions, box_ei_premiums,
                                          box_qpip_premiums)
                   VALUES (?, ?, 'Releve_1', ?, ?, ?, ?, ?)""",
                (emp_id, tax_year, gross, qc_tax, qpp, ei, qpip)
            )
            rl1_slip = TaxSlip(
                slip_id=rl1_id, employee_id=emp_id, tax_year=tax_year,
                slip_type="Releve_1", box_employment_income=gross,
                box_income_tax_deducted=qc_tax, box_cpp_qpp_contributions=qpp,
                box_ei_premiums=ei, box_qpip_premiums=qpip
            )
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
        conditions = []
        params = []
        if employee_id is not None:
            conditions.append("t.employee_id = ?")
            params.append(employee_id)
        if client_id is not None:
            conditions.append("e.client_id = ?")
            params.append(client_id)
        if tax_year is not None:
            conditions.append("t.tax_year = ?")
            params.append(tax_year)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"""
            SELECT t.*, e.first_name, e.last_name, e.client_id
            FROM tax_slips t
            JOIN employees e ON t.employee_id = e.employee_id
            {where_clause}
            ORDER BY t.tax_year DESC, e.last_name ASC, t.slip_type ASC
        """
        rows = db.query_all(sql, tuple(params))
        results = []
        for r in rows:
            slip = TaxSlip(
                slip_id=r["slip_id"], employee_id=r["employee_id"], tax_year=r["tax_year"],
                slip_type=r["slip_type"], box_employment_income=float(r["box_employment_income"]),
                box_income_tax_deducted=float(r["box_income_tax_deducted"]),
                box_cpp_qpp_contributions=float(r["box_cpp_qpp_contributions"]),
                box_ei_premiums=float(r["box_ei_premiums"]),
                box_qpip_premiums=float(r["box_qpip_premiums"]),
                generated_at=r["generated_at"]
            )
            d = slip.to_dict()
            d["employee_name"] = f"{r['first_name']} {r['last_name']}"
            d["client_id"] = r["client_id"]
            results.append(d)
        return results
