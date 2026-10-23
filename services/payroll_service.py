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
