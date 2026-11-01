"""
Compensation Repository (Data Access Management / DAM Layer)
Encapsulates SQL queries and persistence for Compensation and Pay Audit records (Chapter 7 C.5).
"""

from database.db import db
from models.pay_change_history import PayChangeHistory

class CompensationRepository:
    @staticmethod
    def get_job_info_by_employee(employee_id: int):
        """Fetches job information record for an employee."""
        sql = "SELECT * FROM job_information WHERE employee_id = ?"
        return db.query_one(sql, (employee_id,))

    @staticmethod
    def update_job_rate(employee_id: int, hourly_rate: float, base_salary: float):
        """Updates wage rate and base salary on job information."""
        db.execute(
            "UPDATE job_information SET hourly_rate = ?, base_salary = ? WHERE employee_id = ?",
            (hourly_rate, base_salary, employee_id)
        )

    @staticmethod
    def save_audit_entry(audit_entry: PayChangeHistory) -> int:
        """Persists an immutable SOX compliance pay change history record."""
        return db.execute(
            """INSERT INTO pay_change_history (employee_id, previous_rate, new_rate, change_reason, authorized_by)
               VALUES (?, ?, ?, ?, ?)""",
            (audit_entry.employee_id, audit_entry.previous_rate, audit_entry.new_rate,
             audit_entry.change_reason, audit_entry.authorized_by)
        )

    @staticmethod
    def get_audit_trail(employee_id: int = None, client_id: int = None):
        """Fetches audit history records joined with employee names."""
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
        return db.query_all(sql, tuple(params))
