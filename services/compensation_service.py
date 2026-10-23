"""
Compensation Service (Use Case 3: Manage Compensation & Earnings)
Handles hourly wage modifications and maintains the SOX-compliant audit log.
"""

from database.db import db
from models.job_information import JobInformation
from models.pay_change_history import PayChangeHistory

class CompensationService:
    @staticmethod
    def update_employee_wage(employee_id: int, new_rate: float, reason: str, authorized_by: str):
        """Updates employee wage and records an unalterable audit log entry."""
        job_row = db.query_one("SELECT * FROM job_information WHERE employee_id = ?", (employee_id,))
        if not job_row:
            raise ValueError(f"Job information for employee #{employee_id} not found.")

        job = JobInformation(
            job_id=job_row["job_id"],
            employee_id=job_row["employee_id"],
            job_title=job_row["job_title"],
            department=job_row["department"],
            employment_type=job_row["employment_type"],
            base_salary=float(job_row["base_salary"]),
            hourly_rate=float(job_row["hourly_rate"])
        )

        # Domain model updates rate and produces audit entry
        audit_entry = job.update_hourly_rate(new_rate=new_rate, reason=reason, authorized_by=authorized_by)

        # 1. Update database job_information
        db.execute(
            "UPDATE job_information SET hourly_rate = ?, base_salary = ? WHERE employee_id = ?",
            (job.hourly_rate, job.base_salary, employee_id)
        )

        # 2. Insert into pay_change_history
        history_id = db.execute(
            """INSERT INTO pay_change_history (employee_id, previous_rate, new_rate, change_reason, authorized_by)
               VALUES (?, ?, ?, ?, ?)""",
            (employee_id, audit_entry.previous_rate, audit_entry.new_rate,
             audit_entry.change_reason, audit_entry.authorized_by)
        )

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
        params = []
        sql = """
            SELECT h.*, e.first_name, e.last_name, e.client_id
            FROM pay_change_history h
            JOIN employees e ON h.employee_id = e.employee_id
            WHERE 1=1
        """
        if employee_id:
            sql += " AND h.employee_id = ?"
            params.append(employee_id)
        if client_id:
            sql += " AND e.client_id = ?"
            params.append(client_id)

        sql += " ORDER BY h.change_date DESC"
        rows = db.query_all(sql, tuple(params))
        
        results = []
        for r in rows:
            entry = PayChangeHistory(
                history_id=r["history_id"],
                employee_id=r["employee_id"],
                previous_rate=float(r["previous_rate"]),
                new_rate=float(r["new_rate"]),
                change_reason=r["change_reason"],
                authorized_by=r["authorized_by"],
                change_date=r["change_date"]
            )
            d = entry.to_dict()
            d["employee_name"] = f"{r['first_name']} {r['last_name']}"
            results.append(d)
        return results
