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

    @staticmethod
    def update_employee(employee_id: int, first_name: str = None, last_name: str = None,
                        email: str = None, phone: str = None, status: str = None,
                        institution_number: str = None, transit_number: str = None,
                        account_number: str = None, account_type: str = None,
                        job_title: str = None, department: str = None,
                        employment_type: str = None):
        """
        Updates an existing employee record, bank coordinates, and job placement.
        Directly implements Use Case 1 SubFlow 3S.2 (Edit Employee Record).
        """
        emp = db.query_one("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
        if not emp:
            raise ValueError(f"Employee #{employee_id} not found.")

        # 1. Update personal details
        fn = first_name if first_name is not None else emp["first_name"]
        ln = last_name if last_name is not None else emp["last_name"]
        em = email if email is not None else emp["email"]
        ph = phone if phone is not None else emp["phone"]
        st = status if status is not None else emp["status"]

        db.execute(
            """UPDATE employees
               SET first_name = ?, last_name = ?, email = ?, phone = ?, status = ?
               WHERE employee_id = ?""",
            (fn, ln, em, ph, st, employee_id)
        )

        # 2. Update banking details if provided
        if any(v is not None for v in (institution_number, transit_number, account_number, account_type)):
            bank = db.query_one("SELECT * FROM bank_accounts WHERE employee_id = ?", (employee_id,))
            if bank:
                inst = institution_number if institution_number is not None else bank["institution_number"]
                trn = transit_number if transit_number is not None else bank["transit_number"]
                acc = account_number if account_number is not None else bank["account_number"]
                at = account_type if account_type is not None else bank["account_type"]
                db.execute(
                    """UPDATE bank_accounts
                       SET institution_number = ?, transit_number = ?, account_number = ?, account_type = ?
                       WHERE employee_id = ?""",
                    (inst, trn, acc, at, employee_id)
                )

        # 3. Update job details if provided
        if any(v is not None for v in (job_title, department, employment_type)):
            job = db.query_one("SELECT * FROM job_information WHERE employee_id = ?", (employee_id,))
            if job:
                jt = job_title if job_title is not None else job["job_title"]
                dep = department if department is not None else job["department"]
                et = employment_type if employment_type is not None else job["employment_type"]
                db.execute(
                    """UPDATE job_information
                       SET job_title = ?, department = ?, employment_type = ?
                       WHERE employee_id = ?""",
                    (jt, dep, et, employee_id)
                )

        return {
            "employee_id": employee_id,
            "full_name": f"{fn} {ln}",
            "status": st,
            "message": f"Employee #{employee_id} ({fn} {ln}) successfully updated."
        }
