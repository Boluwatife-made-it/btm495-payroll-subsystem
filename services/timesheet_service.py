"""
Timesheet Service (Use Case 2: Track Time & Attendance)
Manages hours logging, submission, and post-approval lockout enforcement.
"""

from database.db import db
from models.timesheet import Timesheet
from models.employee import Employee

class TimesheetService:
    @staticmethod
    def get_timesheets_for_client(client_id: int, period_start: str = None, period_end: str = None):
        """Fetches all timesheets for a client's employees for a pay period."""
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
        rows = db.query_all(sql, tuple(params))
        
        results = []
        for r in rows:
            d = Timesheet.from_row(r).to_dict()
            d["employee_name"] = Employee.format_full_name(r["first_name"], r["last_name"])
            results.append(d)
        return results

    @staticmethod
    def submit_timesheet(timesheet_id: int):
        """Submits a draft timesheet for manager review."""
        row = db.query_one("SELECT * FROM timesheets WHERE timesheet_id = ?", (timesheet_id,))
        if not row:
            raise ValueError(f"Timesheet #{timesheet_id} not found.")

        ts = Timesheet.from_row(row)
        ts.submit()

        db.execute("UPDATE timesheets SET status = 'Submitted' WHERE timesheet_id = ?", (timesheet_id,))
        return {"timesheet_id": timesheet_id, "status": "Submitted", "message": "Timesheet submitted for approval."}

    @staticmethod
    def update_hours(timesheet_id: int, regular_hours: float, overtime_hours: float):
        """Updates work hours; strictly prevents modification if timesheet is locked."""
        row = db.query_one("SELECT * FROM timesheets WHERE timesheet_id = ?", (timesheet_id,))
        if not row:
            raise ValueError(f"Timesheet #{timesheet_id} not found.")

        ts = Timesheet.from_row(row)

        # Enforce domain model lockout check
        ts.update_hours(regular_hours, overtime_hours)

        db.execute(
            "UPDATE timesheets SET regular_hours = ?, overtime_hours = ? WHERE timesheet_id = ?",
            (ts.regular_hours, ts.overtime_hours, timesheet_id)
        )
        return {"timesheet_id": timesheet_id, "status": ts.status, "regular_hours": ts.regular_hours, "overtime_hours": ts.overtime_hours}
