"""
Timesheet Service (Use Case 2: Track Time & Attendance)
Manages hours logging, submission, and post-approval lockout enforcement.
"""

from database.db import db
from models.timesheet import Timesheet

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
            ts = Timesheet(
                timesheet_id=r["timesheet_id"],
                employee_id=r["employee_id"],
                period_start=r["period_start"],
                period_end=r["period_end"],
                regular_hours=float(r["regular_hours"]),
                overtime_hours=float(r["overtime_hours"]),
                vacation_days=int(r["vacation_days"]),
                sick_days=int(r["sick_days"]),
                status=r["status"]
            )
            d = ts.to_dict()
            d["employee_name"] = f"{r['first_name']} {r['last_name']}"
            results.append(d)
        return results

    @staticmethod
    def submit_timesheet(timesheet_id: int):
        """Submits a draft timesheet for manager review."""
        row = db.query_one("SELECT * FROM timesheets WHERE timesheet_id = ?", (timesheet_id,))
        if not row:
            raise ValueError(f"Timesheet #{timesheet_id} not found.")

        ts = Timesheet(
            timesheet_id=row["timesheet_id"], employee_id=row["employee_id"],
            period_start=row["period_start"], period_end=row["period_end"],
            regular_hours=row["regular_hours"], overtime_hours=row["overtime_hours"],
            status=row["status"]
        )
        ts.submit()

        db.execute("UPDATE timesheets SET status = 'Submitted' WHERE timesheet_id = ?", (timesheet_id,))
        return {"timesheet_id": timesheet_id, "status": "Submitted", "message": "Timesheet submitted for approval."}

    @staticmethod
    def update_hours(timesheet_id: int, regular_hours: float, overtime_hours: float):
        """Updates work hours; strictly prevents modification if timesheet is locked."""
        row = db.query_one("SELECT * FROM timesheets WHERE timesheet_id = ?", (timesheet_id,))
        if not row:
            raise ValueError(f"Timesheet #{timesheet_id} not found.")

        ts = Timesheet(
            timesheet_id=row["timesheet_id"], employee_id=row["employee_id"],
            period_start=row["period_start"], period_end=row["period_end"],
            regular_hours=row["regular_hours"], overtime_hours=row["overtime_hours"],
            status=row["status"]
        )

        # Enforce domain model lockout check
        ts.update_hours(regular_hours, overtime_hours)

        db.execute(
            "UPDATE timesheets SET regular_hours = ?, overtime_hours = ? WHERE timesheet_id = ?",
            (ts.regular_hours, ts.overtime_hours, timesheet_id)
        )
        return {"timesheet_id": timesheet_id, "status": ts.status, "regular_hours": ts.regular_hours, "overtime_hours": ts.overtime_hours}
