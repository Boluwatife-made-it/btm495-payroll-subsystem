"""
Compensation Service (Use Case 3: Manage Compensation & Earnings)
Handles hourly wage modifications and maintains the SOX-compliant audit log.
Coordinates with CompensationRepository for Data Access Management (Chapter 7 C.5).
"""

from models.job_information import JobInformation
from models.pay_change_history import PayChangeHistory
from models.employee import Employee
from repositories.compensation_repository import CompensationRepository

class CompensationService:
    @staticmethod
    def update_employee_wage(employee_id: int, new_rate: float, reason: str, authorized_by: str):
        """Updates employee wage and records an unalterable audit log entry."""
        job_row = CompensationRepository.get_job_info_by_employee(employee_id)
        if not job_row:
            raise ValueError(f"Job information for employee #{employee_id} not found.")

        job = JobInformation.from_row(job_row)

        # Domain model updates rate and produces audit entry
        audit_entry = job.update_hourly_rate(new_rate=new_rate, reason=reason, authorized_by=authorized_by)

        # 1. Update database job_information via repository
        CompensationRepository.update_job_rate(employee_id, job.hourly_rate, job.base_salary)

        # 2. Insert into pay_change_history via repository
        history_id = CompensationRepository.save_audit_entry(audit_entry)

        return {
            "history_id": history_id,
            "employee_id": employee_id,
            "previous_rate": audit_entry.previous_rate,
            "new_rate": audit_entry.new_rate,
            "audit_summary": audit_entry.get_audit_summary()
        }

    @staticmethod
    def get_audit_trail(employee_id: int = None, client_id: int = None):
        """Fetches audit trail records, optionally filtered by employee or client."""
        rows = CompensationRepository.get_audit_trail(employee_id, client_id)
        results = []
        for r in rows:
            entry = PayChangeHistory.from_row(r)
            d = entry.to_dict()
            d["employee_name"] = Employee.format_full_name(r["first_name"], r["last_name"])
            results.append(d)
        return results
