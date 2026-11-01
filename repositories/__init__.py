"""
Data Access Management (DAM) Layer
Exports repository classes encapsulating SQL persistence across all domain aggregates (Chapter 7 C.5).
"""

from .client_repository import ClientRepository
from .employee_repository import EmployeeRepository
from .timesheet_repository import TimesheetRepository
from .compensation_repository import CompensationRepository
from .remittance_repository import RemittanceRepository
from .payroll_repository import PayrollRepository

__all__ = [
    "ClientRepository",
    "EmployeeRepository",
    "TimesheetRepository",
    "CompensationRepository",
    "RemittanceRepository",
    "PayrollRepository"
]
