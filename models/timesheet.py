"""
Timesheet Domain Model (Use Case 2: Track Time & Attendance)
Enforces work duration logging and post-approval timesheet lockout.
"""

class Timesheet:
    VALID_STATUSES = {"Draft", "Submitted", "Approved", "Locked"}

    def __init__(self, timesheet_id: int, employee_id: int, period_start: str,
                 period_end: str, regular_hours: float = 0.0, overtime_hours: float = 0.0,
                 vacation_days: int = 0, sick_days: int = 0, status: str = "Draft"):
        self.timesheet_id = int(timesheet_id)
        self.employee_id = int(employee_id)
        self.period_start = str(period_start)
        self.period_end = str(period_end)
        self.regular_hours = float(regular_hours)
        self.overtime_hours = float(overtime_hours)
        self.vacation_days = int(vacation_days)
        self.sick_days = int(sick_days)

        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {self.VALID_STATUSES}")
        self.status = status

    def calculate_total_hours(self) -> float:
        """Returns total hours logged."""
        return round(self.regular_hours + self.overtime_hours, 2)

    def submit(self) -> bool:
        """Transitions timesheet from Draft to Submitted."""
        if self.status == "Locked":
            raise PermissionError("Cannot modify or submit a locked timesheet.")
        self.status = "Submitted"
        return True

    def approve(self) -> bool:
        """Transitions timesheet to Approved."""
        if self.status == "Locked":
            raise PermissionError("Timesheet is already locked.")
        self.status = "Approved"
        return True

    def lock(self) -> bool:
        """Enforces the post-approval lockout hedge."""
        self.status = "Locked"
        return True

    def update_hours(self, regular_hours: float, overtime_hours: float) -> bool:
        """Updates work hours; strictly blocks tampering if timesheet is locked."""
        if self.status == "Locked":
            raise PermissionError("Tampering prevented: Cannot modify hours on a locked timesheet.")
        self.regular_hours = round(float(regular_hours), 2)
        self.overtime_hours = round(float(overtime_hours), 2)
        return True

    def to_dict(self) -> dict:
        return {
            "timesheet_id": self.timesheet_id,
            "employee_id": self.employee_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "regular_hours": self.regular_hours,
            "overtime_hours": self.overtime_hours,
            "total_hours": self.calculate_total_hours(),
            "vacation_days": self.vacation_days,
            "sick_days": self.sick_days,
            "status": self.status,
            "is_locked": self.status == "Locked"
        }

    def __repr__(self) -> str:
        return f"<Timesheet #{self.timesheet_id} for Emp #{self.employee_id}: {self.calculate_total_hours()}h ({self.status})>"
