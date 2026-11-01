"""
Timesheet Service (Use Case 2: Track Time & Attendance)
Manages hours logging, submission, and post-approval lockout enforcement.
Coordinates with TimesheetRepository for Data Access Management (Chapter 7 C.5).
"""

from models.timesheet import Timesheet
from models.employee import Employee
from repositories.timesheet_repository import TimesheetRepository

class TimesheetService:
    @staticmethod
    def get_timesheets_for_client(client_id: int, period_start: str = None, period_end: str = None):
        """Fetches all timesheets for a client's employees for a pay period."""
        rows = TimesheetRepository.get_timesheets_for_client(client_id, period_start, period_end)
        results = []
        for r in rows:
            d = Timesheet.from_row(r).to_dict()
            d["employee_name"] = Employee.format_full_name(r["first_name"], r["last_name"])
            results.append(d)
        return results

    @staticmethod
    def submit_timesheet(timesheet_id: int):
        """Submits a draft timesheet for manager review."""
        row = TimesheetRepository.get_by_id(timesheet_id)
        if not row:
            raise ValueError(f"Timesheet #{timesheet_id} not found.")

        ts = Timesheet.from_row(row)
        ts.submit()

        TimesheetRepository.update_status(timesheet_id, "Submitted")
        return {"timesheet_id": timesheet_id, "status": "Submitted", "message": "Timesheet submitted for approval."}

    @staticmethod
    def update_hours(timesheet_id: int, regular_hours: float, overtime_hours: float):
        """Updates work hours; strictly prevents modification if timesheet is locked."""
        row = TimesheetRepository.get_by_id(timesheet_id)
        if not row:
            raise ValueError(f"Timesheet #{timesheet_id} not found.")

        ts = Timesheet.from_row(row)

        # Enforce domain model lockout check
        ts.update_hours(regular_hours, overtime_hours)

        TimesheetRepository.update_hours(timesheet_id, ts.regular_hours, ts.overtime_hours)
        return {
            "timesheet_id": timesheet_id,
            "status": ts.status,
            "regular_hours": ts.regular_hours,
            "overtime_hours": ts.overtime_hours
        }
