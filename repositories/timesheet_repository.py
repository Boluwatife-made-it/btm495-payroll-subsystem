"""
Timesheet Repository (Data Access Management / DAM Layer)
Encapsulates SQL queries and persistence for the Timesheet aggregate (Chapter 7 C.5).
"""

from database.db import db
from models.timesheet import Timesheet

class TimesheetRepository:
    @staticmethod
    def get_timesheets_for_client(client_id: int, period_start: str = None, period_end: str = None):
        """Fetches joined timesheet records for a client's employees."""
        params = [client_id]
        sql = """
            SELECT t.*, e.first_name, e.last_name, e.client_id
            FROM timesheets t
            JOIN employees e ON t.employee_id = e.employee_id
            WHERE e.client_id = ?
        """
        if period_start and period_end:
            sql += " AND t.period_start = ? AND t.period_end = ?"
            params.extend([period_start, period_end])

        sql += " ORDER BY t.timesheet_id ASC"
        return db.query_all(sql, tuple(params))

    @staticmethod
    def get_by_id(timesheet_id: int):
        """Fetches a single timesheet by primary key."""
        sql = "SELECT * FROM timesheets WHERE timesheet_id = ?"
        return db.query_one(sql, (timesheet_id,))

    @staticmethod
    def update_status(timesheet_id: int, status: str):
        """Persists timesheet lifecycle state transition."""
        db.execute("UPDATE timesheets SET status = ? WHERE timesheet_id = ?", (status, timesheet_id))

    @staticmethod
    def update_hours(timesheet_id: int, regular_hours: float, overtime_hours: float):
        """Updates work duration hours."""
        db.execute(
            "UPDATE timesheets SET regular_hours = ?, overtime_hours = ? WHERE timesheet_id = ?",
            (regular_hours, overtime_hours, timesheet_id)
        )

    @staticmethod
    def get_submitted_for_payroll(client_id: int, period_start: str, period_end: str):
        """Fetches submitted timesheets joined with job info and compensation for payroll runs."""
        sql = """
            SELECT e.employee_id, e.first_name, e.last_name,
                   j.hourly_rate, j.base_salary,
                   c.overtime_multiplier,
                   t.timesheet_id, t.regular_hours, t.overtime_hours, t.status as timesheet_status
            FROM employees e
            JOIN job_information j ON e.employee_id = j.employee_id
            JOIN compensation_structures c ON e.employee_id = c.employee_id
            JOIN timesheets t ON e.employee_id = t.employee_id
            WHERE e.client_id = ? AND t.period_start = ? AND t.period_end = ? AND t.status = 'Submitted'
        """
        return db.query_all(sql, (client_id, period_start, period_end))

    @staticmethod
    def get_period_timesheets_for_approval(client_id: int, period_start: str, period_end: str):
        """Fetches timesheets associated with a pay period to perform domain lock during approval."""
        sql = """
            SELECT timesheet_id, employee_id, period_start, period_end,
                   regular_hours, overtime_hours, vacation_days, sick_days, status
            FROM timesheets
            WHERE period_start = ? AND period_end = ?
            AND employee_id IN (SELECT employee_id FROM employees WHERE client_id = ?)
        """
        return db.query_all(sql, (period_start, period_end, client_id))
