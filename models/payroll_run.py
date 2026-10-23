"""
PayrollRun Domain Model (Use Case 5: Approve Payroll & Generate Tax Slips)
Includes PayStub and TaxSlip supporting artifact entities.
Implements Alternative Flow 3a (Client Manager Rejection & Technician Alert Banner).
"""

from datetime import datetime

class PayStub:
    """Itemized earnings and deductions slip for an individual employee."""
    def __init__(self, stub_id: int, run_id: int, employee_id: int,
                 pay_period_start: str, pay_period_end: str, regular_earnings: float,
                 overtime_earnings: float, gross_pay: float, fed_tax_deduction: float,
                 ei_deduction: float, qc_tax_deduction: float, qpp_deduction: float,
                 qpip_deduction: float, total_deductions: float, net_pay: float,
                 generated_at: str = None):
        self.stub_id = int(stub_id)
        self.run_id = int(run_id)
        self.employee_id = int(employee_id)
        self.pay_period_start = str(pay_period_start)
        self.pay_period_end = str(pay_period_end)
        self.regular_earnings = round(float(regular_earnings), 2)
        self.overtime_earnings = round(float(overtime_earnings), 2)
        self.gross_pay = round(float(gross_pay), 2)
        self.fed_tax_deduction = round(float(fed_tax_deduction), 2)
        self.ei_deduction = round(float(ei_deduction), 2)
        self.qc_tax_deduction = round(float(qc_tax_deduction), 2)
        self.qpp_deduction = round(float(qpp_deduction), 2)
        self.qpip_deduction = round(float(qpip_deduction), 2)
        self.total_deductions = round(float(total_deductions), 2)
        self.net_pay = round(float(net_pay), 2)
        self.generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return {
            "stub_id": self.stub_id,
            "run_id": self.run_id,
            "employee_id": self.employee_id,
            "pay_period": f"{self.pay_period_start} to {self.pay_period_end}",
            "earnings": {
                "regular": self.regular_earnings,
                "overtime": self.overtime_earnings,
                "gross": self.gross_pay
            },
            "deductions": {
                "federal_tax": self.fed_tax_deduction,
                "ei": self.ei_deduction,
                "quebec_tax": self.qc_tax_deduction,
                "qpp": self.qpp_deduction,
                "qpip": self.qpip_deduction,
                "total": self.total_deductions
            },
            "net_pay": self.net_pay,
            "generated_at": self.generated_at
        }


class TaxSlip:
    """Year-end tax slip compilation (T4 Federal / Releve 1 Quebec)."""
    VALID_SLIP_TYPES = {"T4", "Releve_1"}

    def __init__(self, slip_id: int, employee_id: int, tax_year: int,
                 slip_type: str, box_employment_income: float,
                 box_income_tax_deducted: float, box_cpp_qpp_contributions: float,
                 box_ei_premiums: float, box_qpip_premiums: float = 0.0,
                 generated_at: str = None):
        self.slip_id = int(slip_id)
        self.employee_id = int(employee_id)
        self.tax_year = int(tax_year)

        if slip_type not in self.VALID_SLIP_TYPES:
            raise ValueError(f"Invalid slip type '{slip_type}'. Must be one of {self.VALID_SLIP_TYPES}")
        self.slip_type = slip_type

        self.box_employment_income = round(float(box_employment_income), 2)
        self.box_income_tax_deducted = round(float(box_income_tax_deducted), 2)
        self.box_cpp_qpp_contributions = round(float(box_cpp_qpp_contributions), 2)
        self.box_ei_premiums = round(float(box_ei_premiums), 2)
        self.box_qpip_premiums = round(float(box_qpip_premiums), 2)
        self.generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return {
            "slip_id": self.slip_id,
            "employee_id": self.employee_id,
            "tax_year": self.tax_year,
            "slip_type": self.slip_type,
            "box_employment_income": self.box_employment_income,
            "box_income_tax_deducted": self.box_income_tax_deducted,
            "box_cpp_qpp_contributions": self.box_cpp_qpp_contributions,
            "box_ei_premiums": self.box_ei_premiums,
            "box_qpip_premiums": self.box_qpip_premiums,
            "generated_at": self.generated_at
        }


class PayrollRun:
    """Central orchestrator for gross-to-net calculation and approval workflow."""
    VALID_STATUSES = {"Draft", "Pending_Approval", "Approved", "Rejected"}

    def __init__(self, run_id: int, client_id: int, period_start: str,
                 period_end: str, run_date: str = None, total_gross: float = 0.0,
                 total_deductions: float = 0.0, total_net: float = 0.0,
                 approval_status: str = "Draft", approved_at: str = None,
                 rejection_reason: str = None):
        self.run_id = int(run_id)
        self.client_id = int(client_id)
        self.period_start = str(period_start)
        self.period_end = str(period_end)
        self.run_date = run_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.total_gross = round(float(total_gross), 2)
        self.total_deductions = round(float(total_deductions), 2)
        self.total_net = round(float(total_net), 2)

        if approval_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid approval status '{approval_status}'. Must be one of {self.VALID_STATUSES}")
        self.approval_status = approval_status
        self.approved_at = approved_at
        self.rejection_reason = rejection_reason

    def submit_for_approval(self) -> bool:
        """Transitions pay run to Pending_Approval for client manager review."""
        self.approval_status = "Pending_Approval"
        return True

    def approve(self, associated_timesheets: list = None) -> dict:
        """
        Approves pay run, locks all associated timesheets (post-approval hedge),
        and enables statutory remittance generation.
        """
        self.approval_status = "Approved"
        self.approved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.rejection_reason = None

        locked_count = 0
        if associated_timesheets:
            for ts in associated_timesheets:
                ts.lock()
                locked_count += 1

        return {
            "status": "Approved",
            "approved_at": self.approved_at,
            "timesheets_locked": locked_count
        }

    def reject(self, reason: str, rejected_by: str = "Client Manager") -> dict:
        """
        Implements UC5 Alternative Flow 3a:
        Records rejection reason and triggers real-time notification alert banner
        destined for the Accounting Technician's dashboard.
        """
        if not reason or not str(reason).strip():
            raise ValueError("A clear rejection reason must be entered by the Client Manager.")
        
        self.approval_status = "Rejected"
        self.rejection_reason = str(reason).strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        alert_payload = {
            "alert_type": "PAYROLL_REJECTION",
            "run_id": self.run_id,
            "client_id": self.client_id,
            "rejected_by": rejected_by,
            "timestamp": timestamp,
            "reason": self.rejection_reason,
            "banner_text": f"ALERT (UC5 Alt Flow 3a): {rejected_by} rejected Pay Run #{self.run_id} on {timestamp}. Reason: '{self.rejection_reason}'. Please revise hours and resubmit."
        }
        return alert_payload

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "client_id": self.client_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "run_date": self.run_date,
            "total_gross": self.total_gross,
            "total_deductions": self.total_deductions,
            "total_net": self.total_net,
            "approval_status": self.approval_status,
            "approved_at": self.approved_at,
            "rejection_reason": self.rejection_reason
        }

    def __repr__(self) -> str:
        return f"<PayrollRun #{self.run_id} for Client #{self.client_id}: Gross {self.total_gross} CAD | Net {self.total_net} CAD ({self.approval_status})>"
