"""
Employee Service (Use Case 1: Manage Employee Information)
Handles client employee onboarding, profile retrieval, and tenant-scoped lookups.
Coordinates with EmployeeRepository for Data Access Management (Chapter 7 C.5).
"""

from models.employee import Employee
from models.bank_account import BankAccount
from models.job_information import JobInformation
from models.compensation_structure import CompensationStructure
from repositories.employee_repository import EmployeeRepository

class EmployeeService:
    @staticmethod
    def get_employees_by_client(client_id: int):
        """Fetches all employees for a client, enforcing tenant isolation."""
        rows = EmployeeRepository.get_employees_by_client(client_id)
        results = []
        for r in rows:
            bank = BankAccount.from_row(r)
            job = JobInformation.from_row(r)
            item = {
                "employee_id": r["employee_id"],
                "client_id": r["client_id"],
                "full_name": Employee.format_full_name(r["first_name"], r["last_name"]),
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
    def create_employee(employee: Employee = None, bank_account: BankAccount = None,
                        job_information: JobInformation = None,
                        compensation: CompensationStructure = None, **kwargs):
        """
        Creates an employee along with their bank details, job profile, and compensation structure.
        Implements Chapter 7 E.1: 'Pass the object, not its attributes'.
        Maintains business defaults in the domain layer and accepts kwargs for flexible onboarding.
        """
        # 1. Hydrate Employee domain object
        if employee is None:
            client_id = int(kwargs.get("client_id", 101))
            first_name = kwargs.get("first_name", "")
            last_name = kwargs.get("last_name", "")
            email = kwargs.get("email", "")
            phone = kwargs.get("phone", "514-555-0100")
            hire_date = kwargs.get("hire_date", "2026-10-01")
            status = kwargs.get("status", "Active")
            employee = Employee(
                employee_id=0, client_id=client_id, first_name=first_name,
                last_name=last_name, email=email, phone=phone, hire_date=hire_date, status=status
            )

        # 2. Hydrate BankAccount domain object with domain defaults
        if bank_account is None:
            bank_account = BankAccount(
                account_id=0, employee_id=employee.employee_id,
                institution_number=kwargs.get("institution_number", "001"),
                transit_number=kwargs.get("transit_number", "10234"),
                account_number=kwargs.get("account_number", "1234567"),
                account_type=kwargs.get("account_type", "Checking")
            )

        # 3. Hydrate JobInformation domain object with domain defaults
        if job_information is None:
            job_information = JobInformation(
                job_id=0, employee_id=employee.employee_id,
                job_title=kwargs.get("job_title", "Staff Associate"),
                department=kwargs.get("department", "Operations"),
                employment_type=kwargs.get("employment_type", "Full-Time"),
                hourly_rate=float(kwargs.get("hourly_rate", 25.0)),
                base_salary=float(kwargs.get("base_salary", 0.0))
            )

        # 4. Hydrate CompensationStructure domain object with domain defaults
        if compensation is None:
            compensation = CompensationStructure(
                structure_id=0, employee_id=employee.employee_id,
                pay_frequency=kwargs.get("pay_frequency", "Bi-Weekly"),
                overtime_multiplier=float(kwargs.get("overtime_multiplier", 1.50)),
                bonus_rate=float(kwargs.get("bonus_rate", 0.0)),
                commission_rate=float(kwargs.get("commission_rate", 0.0))
            )

        # Persist through Data Access Management (DAM) Layer
        emp_id = EmployeeRepository.save_employee_bundle(employee, bank_account, job_information, compensation)
        full_name = Employee.format_full_name(employee.first_name, employee.last_name)
        return {"employee_id": emp_id, "message": f"Employee {full_name} successfully created."}

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
        emp = EmployeeRepository.get_by_id(employee_id)
        if not emp:
            raise ValueError(f"Employee #{employee_id} not found.")

        fn = first_name if first_name is not None else emp["first_name"]
        ln = last_name if last_name is not None else emp["last_name"]
        em = email if email is not None else emp["email"]
        ph = phone if phone is not None else emp["phone"]
        st = status if status is not None else emp["status"]

        EmployeeRepository.update_employee_profile(
            employee_id=employee_id, first_name=fn, last_name=ln, email=em, phone=ph, status=st,
            institution_number=institution_number, transit_number=transit_number,
            account_number=account_number, account_type=account_type,
            job_title=job_title, department=department, employment_type=employment_type
        )

        full_name = Employee.format_full_name(fn, ln)
        return {
            "employee_id": employee_id,
            "full_name": full_name,
            "status": st,
            "message": f"Employee #{employee_id} ({full_name}) successfully updated."
        }
