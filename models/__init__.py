"""
MNP Payroll Subsystem - Domain Models Package
Exports the 9 Core UML Classes matching Milestone 3 Class Diagram
and the 5 approved use cases.
"""

from .client import Client
from .employee import Employee
from .bank_account import BankAccount
from .job_information import JobInformation
from .timesheet import Timesheet
from .compensation_structure import CompensationStructure
from .pay_change_history import PayChangeHistory
from .statutory_remittance import StatutoryRemittance
from .payroll_run import PayrollRun, PayStub, TaxSlip

__all__ = [
    "Client",
    "Employee",
    "BankAccount",
    "JobInformation",
    "Timesheet",
    "CompensationStructure",
    "PayChangeHistory",
    "StatutoryRemittance",
    "PayrollRun",
    "PayStub",
    "TaxSlip"
]
