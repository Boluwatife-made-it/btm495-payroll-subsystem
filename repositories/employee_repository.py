"""
Employee Repository (Data Access Management / DAM Layer)
Encapsulates SQL queries and persistence for the Employee aggregate (Chapter 7 C.5).
"""

from database.db import db
from models.employee import Employee
from models.bank_account import BankAccount
from models.job_information import JobInformation
from models.compensation_structure import CompensationStructure

class EmployeeRepository:
    @staticmethod
    def get_employees_by_client(client_id: int):
        """Fetches raw employee profile records with joined bank, job, and comp details."""
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
        return db.query_all(sql, (client_id,))

    @staticmethod
    def get_by_id(employee_id: int):
        """Fetches an employee record by primary key."""
        sql = "SELECT * FROM employees WHERE employee_id = ?"
        return db.query_one(sql, (employee_id,))

    @staticmethod
    def save_employee_bundle(employee: Employee, bank: BankAccount, job: JobInformation, comp: CompensationStructure) -> int:
        """
        Persists a full employee onboarding aggregate across 4 related tables
        in the data management tier.
        """
        # 1. Insert Employee entity
        emp_id = db.execute(
            """INSERT INTO employees (client_id, first_name, last_name, email, phone, hire_date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (employee.client_id, employee.first_name, employee.last_name, employee.email,
             employee.phone, employee.hire_date, employee.status)
        )
        employee.employee_id = emp_id

        # 2. Insert BankAccount entity
        db.execute(
            """INSERT INTO bank_accounts (employee_id, institution_number, transit_number, account_number, account_type)
               VALUES (?, ?, ?, ?, ?)""",
            (emp_id, bank.institution_number, bank.transit_number, bank.account_number, bank.account_type)
        )

        # 3. Insert JobInformation entity
        db.execute(
            """INSERT INTO job_information (employee_id, job_title, department, employment_type, base_salary, hourly_rate)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (emp_id, job.job_title, job.department, job.employment_type, job.base_salary, job.hourly_rate)
        )

        # 4. Insert CompensationStructure entity
        db.execute(
            """INSERT INTO compensation_structures (employee_id, pay_frequency, overtime_multiplier, bonus_rate, commission_rate)
               VALUES (?, ?, ?, ?, ?)""",
            (emp_id, comp.pay_frequency, comp.overtime_multiplier, comp.bonus_rate, comp.commission_rate)
        )

        return emp_id

    @staticmethod
    def update_employee_profile(employee_id: int, first_name: str, last_name: str,
                                email: str, phone: str, status: str,
                                institution_number: str = None, transit_number: str = None,
                                account_number: str = None, account_type: str = None,
                                job_title: str = None, department: str = None,
                                employment_type: str = None):
        """Updates employee profile attributes, banking coordinates, and job placement."""
        db.execute(
            """UPDATE employees
               SET first_name = ?, last_name = ?, email = ?, phone = ?, status = ?
               WHERE employee_id = ?""",
            (first_name, last_name, email, phone, status, employee_id)
        )

        if any([institution_number, transit_number, account_number, account_type]):
            b = db.query_one("SELECT * FROM bank_accounts WHERE employee_id = ?", (employee_id,))
            if b:
                db.execute(
                    """UPDATE bank_accounts
                       SET institution_number = COALESCE(?, institution_number),
                           transit_number = COALESCE(?, transit_number),
                           account_number = COALESCE(?, account_number),
                           account_type = COALESCE(?, account_type)
                       WHERE employee_id = ?""",
                    (institution_number, transit_number, account_number, account_type, employee_id)
                )

        if any([job_title, department, employment_type]):
            j = db.query_one("SELECT * FROM job_information WHERE employee_id = ?", (employee_id,))
            if j:
                db.execute(
                    """UPDATE job_information
                       SET job_title = COALESCE(?, job_title),
                           department = COALESCE(?, department),
                           employment_type = COALESCE(?, employment_type)
                       WHERE employee_id = ?""",
                    (job_title, department, employment_type, employee_id)
                )
