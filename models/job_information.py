"""
JobInformation Domain Model (Use Case 1: Employment Profiles & Pay Rates)
Maintains departmental placement, employment type, and wage rates.
"""

from .pay_change_history import PayChangeHistory

class JobInformation:
    VALID_TYPES = {"Full-Time", "Part-Time", "Contract"}

    def __init__(self, job_id: int, employee_id: int, job_title: str,
                 department: str, employment_type: str, base_salary: float,
                 hourly_rate: float):
        self.job_id = int(job_id)
        self.employee_id = int(employee_id)
        self.job_title = str(job_title)
        self.department = str(department)

        if employment_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid employment type '{employment_type}'. Must be one of {self.VALID_TYPES}")
        self.employment_type = employment_type

        self.base_salary = float(base_salary)
        self.hourly_rate = float(hourly_rate)

    def get_effective_hourly_rate(self) -> float:
        """Returns hourly rate directly, or derives from standard 2,080 annual salary hours."""
        if self.hourly_rate > 0:
            return round(self.hourly_rate, 2)
        if self.base_salary > 0:
            return round(self.base_salary / 2080.0, 2)
        return 0.0

    def update_hourly_rate(self, new_rate: float, reason: str, authorized_by: str, 
                           history_id: int = None) -> PayChangeHistory:
        """Updates wage rate and produces an immutable audit record for SOX compliance."""
        previous = self.hourly_rate
        self.hourly_rate = round(float(new_rate), 2)
        
        # If salaried, update annualized base salary proportionally
        if self.base_salary > 0:
            self.base_salary = round(self.hourly_rate * 2080.0, 2)

        audit_entry = PayChangeHistory(
            history_id=history_id or 0,
            employee_id=self.employee_id,
            previous_rate=previous,
            new_rate=self.hourly_rate,
            change_reason=reason,
            authorized_by=authorized_by
        )
        return audit_entry

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "employee_id": self.employee_id,
            "job_title": self.job_title,
            "department": self.department,
            "employment_type": self.employment_type,
            "base_salary": self.base_salary,
            "hourly_rate": self.hourly_rate,
            "effective_hourly_rate": self.get_effective_hourly_rate()
        }

    def __repr__(self) -> str:
        return f"<JobInfo #{self.job_id} for Emp #{self.employee_id}: {self.job_title} ({self.hourly_rate} CAD/hr)>"
