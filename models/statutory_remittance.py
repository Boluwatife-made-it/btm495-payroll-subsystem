"""
StatutoryRemittance Domain Model (Use Case 4: Submit Statutory Remittances)
Solves the Quebec Dual-Remittance Split (CRA Federal vs. Revenu Quebec Provincial).
Implements Alternative Flow 7a (Government Gateway Rejection / Timeout).
"""

import random

class StatutoryRemittance:
    VALID_STATUSES = {"Calculated", "Submitted", "Acknowledged", "Failed_Timeout"}

    def __init__(self, remittance_id: int, run_id: int, remittance_period: str,
                 cra_federal_tax: float = 0.0, cra_ei_deduction: float = 0.0,
                 cra_total_remitted: float = 0.0, cra_confirmation_number: str = None,
                 rq_provincial_tax: float = 0.0, rq_qpp_deduction: float = 0.0,
                 rq_qpip_deduction: float = 0.0, rq_total_remitted: float = 0.0,
                 rq_confirmation_number: str = None, status: str = "Calculated"):
        self.remittance_id = int(remittance_id)
        self.run_id = int(run_id)
        self.remittance_period = str(remittance_period)
        self.cra_federal_tax = round(float(cra_federal_tax), 2)
        self.cra_ei_deduction = round(float(cra_ei_deduction), 2)
        self.cra_total_remitted = round(float(cra_total_remitted or (self.cra_federal_tax + self.cra_ei_deduction)), 2)
        self.cra_confirmation_number = cra_confirmation_number

        self.rq_provincial_tax = round(float(rq_provincial_tax), 2)
        self.rq_qpp_deduction = round(float(rq_qpp_deduction), 2)
        self.rq_qpip_deduction = round(float(rq_qpip_deduction), 2)
        self.rq_total_remitted = round(float(rq_total_remitted or (self.rq_provincial_tax + self.rq_qpp_deduction + self.rq_qpip_deduction)), 2)
        self.rq_confirmation_number = rq_confirmation_number

        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {self.VALID_STATUSES}")
        self.status = status

    @classmethod
    def from_payroll_run(cls, run_id: int, period_start: str,
                          fed_tax: float, ei: float, qc_tax: float,
                          qpp: float, qpip: float, remittance_id: int = 0) -> "StatutoryRemittance":
        """
        Factory method to construct a draft statutory remittance from a payroll run
        (Chapter 7: Method Cohesion & Knowing and Doing Together).
        """
        period_label = str(period_start)[:7]
        return cls(
            remittance_id=remittance_id,
            run_id=run_id,
            remittance_period=period_label,
            cra_federal_tax=fed_tax,
            cra_ei_deduction=ei,
            rq_provincial_tax=qc_tax,
            rq_qpp_deduction=qpp,
            rq_qpip_deduction=qpip,
            status="Calculated"
        )

    @classmethod
    def from_row(cls, row: dict) -> "StatutoryRemittance":
        """Factory method to construct a StatutoryRemittance domain object from a database row (Chapter 7: Factoring)."""
        return cls(
            remittance_id=row["remittance_id"],
            run_id=row["run_id"],
            remittance_period=row["remittance_period"],
            cra_federal_tax=float(row.get("cra_federal_tax", 0.0) or 0.0),
            cra_ei_deduction=float(row.get("cra_ei_deduction", 0.0) or 0.0),
            cra_total_remitted=float(row.get("cra_total_remitted", 0.0) or 0.0),
            cra_confirmation_number=row.get("cra_confirmation_number"),
            rq_provincial_tax=float(row.get("rq_provincial_tax", 0.0) or 0.0),
            rq_qpp_deduction=float(row.get("rq_qpp_deduction", 0.0) or 0.0),
            rq_qpip_deduction=float(row.get("rq_qpip_deduction", 0.0) or 0.0),
            rq_total_remitted=float(row.get("rq_total_remitted", 0.0) or 0.0),
            rq_confirmation_number=row.get("rq_confirmation_number"),
            status=row.get("status", "Calculated")
        )

    def transmit(self, simulate_timeout: bool = False) -> dict:
        """
        Transmits dual filing to CRA and Revenu Quebec gateways.
        If simulate_timeout is True (Alternative Flow 7a), flags as pending and alerts technician.
        """
        self.status = "Submitted"

        if simulate_timeout:
            self.status = "Failed_Timeout"
            return {
                "success": False,
                "status": self.status,
                "alert": "ALERT (UC4 Alt Flow 7a): Tax Authority Gateway timeout. Remittance flagged as Pending for Accounting Technician retry."
            }

        # Simulated successful tax authority transmission tokens
        random_suffix = random.randint(10000, 99999)
        self.cra_confirmation_number = f"CRA-CONF-2026-{random_suffix}-OK"
        self.rq_confirmation_number = f"RQ-BATCH-2026-QC-{random_suffix}"
        self.status = "Acknowledged"

        return {
            "success": True,
            "status": self.status,
            "cra_confirmation": self.cra_confirmation_number,
            "rq_confirmation": self.rq_confirmation_number,
            "total_remitted": round(self.cra_total_remitted + self.rq_total_remitted, 2)
        }

    def to_dict(self) -> dict:
        return {
            "remittance_id": self.remittance_id,
            "run_id": self.run_id,
            "remittance_period": self.remittance_period,
            "cra": {
                "federal_tax": self.cra_federal_tax,
                "ei_deduction": self.cra_ei_deduction,
                "total_remitted": self.cra_total_remitted,
                "confirmation_number": self.cra_confirmation_number
            },
            "revenu_quebec": {
                "provincial_tax": self.rq_provincial_tax,
                "qpp_deduction": self.rq_qpp_deduction,
                "qpip_deduction": self.rq_qpip_deduction,
                "total_remitted": self.rq_total_remitted,
                "confirmation_number": self.rq_confirmation_number
            },
            "combined_total": round(self.cra_total_remitted + self.rq_total_remitted, 2),
            "status": self.status
        }

    def __repr__(self) -> str:
        return f"<StatutoryRemittance #{self.remittance_id} for Run #{self.run_id}: CRA {self.cra_total_remitted} | RQ {self.rq_total_remitted} ({self.status})>"
