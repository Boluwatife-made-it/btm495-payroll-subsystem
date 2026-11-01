"""
Payroll Repository (Data Access Management / DAM Layer)
Encapsulates SQL queries and persistence for Payroll Runs, Pay Stubs, and Tax Slips (Chapter 7 C.5).
"""

from database.db import db
from models.payroll_run import PayrollRun, PayStub, TaxSlip

class PayrollRepository:
    @staticmethod
    def get_runs_by_client(client_id: int):
        """Fetches all payroll runs for a client."""
        sql = "SELECT * FROM payroll_runs WHERE client_id = ? ORDER BY run_id DESC"
        return db.query_all(sql, (client_id,))

    @staticmethod
    def get_run_by_id(run_id: int):
        """Fetches a single payroll run by primary key."""
        sql = "SELECT * FROM payroll_runs WHERE run_id = ?"
        return db.query_one(sql, (run_id,))

    @staticmethod
    def create_run(run: PayrollRun) -> int:
        """Inserts a new payroll run record and returns its generated run_id."""
        return db.execute(
            """INSERT INTO payroll_runs (client_id, period_start, period_end, total_gross,
                                        total_deductions, total_net, approval_status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (run.client_id, run.period_start, run.period_end, run.total_gross,
             run.total_deductions, run.total_net, run.approval_status)
        )

    @staticmethod
    def update_approval_status(run_id: int, status: str, approved_at: str = None, rejection_reason: str = None):
        """Updates payroll run approval status, timestamp, and optional rejection reason."""
        db.execute(
            "UPDATE payroll_runs SET approval_status = ?, approved_at = ?, rejection_reason = ? WHERE run_id = ?",
            (status, approved_at, rejection_reason, run_id)
        )

    @staticmethod
    def save_pay_stubs(stubs: list):
        """Inserts itemized pay stub records into the pay_stubs table."""
        for s in stubs:
            db.execute(
                """INSERT INTO pay_stubs (run_id, employee_id, pay_period_start, pay_period_end,
                                         regular_earnings, overtime_earnings, gross_pay,
                                         fed_tax_deduction, ei_deduction, qc_tax_deduction,
                                         qpp_deduction, qpip_deduction, total_deductions, net_pay)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (s.run_id, s.employee_id, s.pay_period_start, s.pay_period_end, s.regular_earnings,
                 s.overtime_earnings, s.gross_pay, s.fed_tax_deduction, s.ei_deduction,
                 s.qc_tax_deduction, s.qpp_deduction, s.qpip_deduction, s.total_deductions, s.net_pay)
            )

    @staticmethod
    def get_stubs_by_run(run_id: int):
        """Fetches itemized pay stubs with joined employee names for a run."""
        sql = """
            SELECT p.*, e.first_name, e.last_name
            FROM pay_stubs p
            JOIN employees e ON p.employee_id = e.employee_id
            WHERE p.run_id = ?
        """
        return db.query_all(sql, (run_id,))

    @staticmethod
    def get_runs_for_tax_year(client_id: int, tax_year: int):
        """Fetches all payroll runs for a client within a calendar tax year."""
        year_prefix = f"{tax_year}%"
        sql = """
            SELECT run_id, period_start, period_end, approval_status
            FROM payroll_runs
            WHERE client_id = ? AND (period_start LIKE ? OR period_end LIKE ?)
        """
        return db.query_all(sql, (client_id, year_prefix, year_prefix))

    @staticmethod
    def get_ytd_stub_totals_for_year(client_id: int, tax_year: int):
        """Aggregates YTD gross earnings and statutory deductions per employee across approved runs."""
        year_prefix = f"{tax_year}%"
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
        return db.query_all(sql, (client_id, year_prefix, year_prefix))

    @staticmethod
    def delete_tax_slips_for_employee_year(employee_id: int, tax_year: int):
        """Ensures idempotency by removing existing slips before re-generating."""
        db.execute("DELETE FROM tax_slips WHERE employee_id = ? AND tax_year = ?", (employee_id, tax_year))

    @staticmethod
    def save_tax_slip(slip: TaxSlip) -> int:
        """Inserts an official tax slip record (T4 or Releve 1)."""
        return db.execute(
            """INSERT INTO tax_slips (employee_id, tax_year, slip_type,
                                      box_employment_income, box_income_tax_deducted,
                                      box_cpp_qpp_contributions, box_ei_premiums,
                                      box_qpip_premiums)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (slip.employee_id, slip.tax_year, slip.slip_type, slip.box_employment_income,
             slip.box_income_tax_deducted, slip.box_cpp_qpp_contributions,
             slip.box_ei_premiums, slip.box_qpip_premiums)
        )

    @staticmethod
    def get_tax_slips(client_id: int = None, employee_id: int = None, tax_year: int = None):
        """Fetches tax slips with optional filters on client, employee, and tax year."""
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
        return db.query_all(sql, tuple(params))
