"""
Employee Service (Use Case 1: Manage Employee Information)
Handles client employee onboarding, profile retrieval, and tenant-scoped lookups.
"""

from database.db import db
from models.employee import Employee
from models.bank_account import BankAccount
from models.job_information import JobInformation
from models.compensation_structure import CompensationStructure

class EmployeeService:
    @staticmethod
    def get_employees_by_client(client_id: int):
        """Fetches all employees for a client, enforcing tenant isolation."""
        sql = """
            SELECT e.*, b.institution_number, b.transit_number, b.account_number, b.account_type,
                   j.job_title, j.department, j.employment_type, j.hourly_rate, j.base_salary,
                   c.pay_frequency, c.overtime_multiplier
            FROM employees e
            LEFT JOIN bank_accounts b ON e.employee_id = b.employee_id
            LEFT JOIN job_information j ON e.employee_id = j.employee_id
            LEFT JOIN compensation_structures c ON e.employee_id = c.employee_id
            WHERE e.client_id = ?
            ORDER BY e.employee_id ASC
        """
        rows = db.query_all(sql, (client_id,))
        results = []
        for r in rows:
            bank = BankAccount(
                account_id=0, employee_id=r["employee_id"],
                institution_number=r["institution_number"] or "000",
                transit_number=r["transit_number"] or "00000",
                account_number=r["account_number"] or "0000",
                account_type=r["account_type"] or "Checking"
            )
            job = JobInformation(
                job_id=0, employee_id=r["employee_id"],
                job_title=r["job_title"] or "Staff",
                department=r["department"] or "General",
                employment_type=r["employment_type"] or "Full-Time",
                base_salary=float(r["base_salary"] or 0.0),
                hourly_rate=float(r["hourly_rate"] or 0.0)
            )
            item = {
                "employee_id": r["employee_id"],
                "client_id": r["client_id"],
                "full_name": f"{r['first_name']} {r['last_name']}",
                "email": r["email"],
                "phone": r["phone"],
                "hire_date": r["hire_date"],
                "status": r["status"],
                "job": job.to_dict(),
                "bank": bank.to_dict()
            }
            results.append(item)
        return results

    @staticmethod
    def create_employee(client_id: int, first_name: str, last_name: str, email: str,
                        phone: str, hire_date: str, institution_number: str,
                        transit_number: str, account_number: str, account_type: str,
                        job_title: str, department: str, employment_type: str,
                        hourly_rate: float, base_salary: float = 0.0,
                        pay_frequency: str = "Bi-Weekly"):
        """Creates an employee along with their bank details and job profile."""
        # 1. Insert employee
        emp_id = db.execute(
            """INSERT INTO employees (client_id, first_name, last_name, email, phone, hire_date, status)
               VALUES (?, ?, ?, ?, ?, ?, 'Active')""",
            (client_id, first_name, last_name, email, phone, hire_date)
        )

        # 2. Insert bank account
        db.execute(
            """INSERT INTO bank_accounts (employee_id, institution_number, transit_number, account_number, account_type)
               VALUES (?, ?, ?, ?, ?)""",
            (emp_id, institution_number, transit_number, account_number, account_type)
        )

        # 3. Insert job information
        db.execute(
            """INSERT INTO job_information (employee_id, job_title, department, employment_type, base_salary, hourly_rate)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (emp_id, job_title, department, employment_type, base_salary, hourly_rate)
        )

        # 4. Insert compensation structure
        db.execute(
            """INSERT INTO compensation_structures (employee_id, pay_frequency, overtime_multiplier, bonus_rate, commission_rate)
               VALUES (?, ?, 1.50, 0.00, 0.00)""",
            (emp_id, pay_frequency)
        )

        return {"employee_id": emp_id, "message": f"Employee {first_name} {last_name} successfully created."}
