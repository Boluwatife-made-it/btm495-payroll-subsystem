"""
Remittance Service (Use Case 4: Submit Statutory Remittances)
Manages Quebec Dual-Remittance calculations and Tax Authority Gateway transmissions.
Addresses Alternative Flow 7a (Government Rejection / Gateway Timeout).
"""

from database.db import db
from models.statutory_remittance import StatutoryRemittance

class RemittanceService:
    @staticmethod
    def get_remittance_by_run(run_id: int):
        """Fetches remittance details for a specific payroll run."""
        row = db.query_one("SELECT * FROM statutory_remittances WHERE run_id = ?", (run_id,))
        if not row:
            return None
        remittance = StatutoryRemittance(
            remittance_id=row["remittance_id"],
            run_id=row["run_id"],
            remittance_period=row["remittance_period"],
            cra_federal_tax=row["cra_federal_tax"],
            cra_ei_deduction=row["cra_ei_deduction"],
            cra_total_remitted=row["cra_total_remitted"],
            cra_confirmation_number=row["cra_confirmation_number"],
            rq_provincial_tax=row["rq_provincial_tax"],
            rq_qpp_deduction=row["rq_qpp_deduction"],
            rq_qpip_deduction=row["rq_qpip_deduction"],
            rq_total_remitted=row["rq_total_remitted"],
            rq_confirmation_number=row["rq_confirmation_number"],
            status=row["status"]
        )
        return remittance.to_dict()

    @staticmethod
    def transmit_remittance(remittance_id: int, simulate_timeout: bool = False):
        """Transmits dual remittance to CRA and RQ gateways with Alternate Flow 7a handling."""
        row = db.query_one("SELECT * FROM statutory_remittances WHERE remittance_id = ?", (remittance_id,))
        if not row:
            raise ValueError(f"Statutory Remittance #{remittance_id} not found.")

        remittance = StatutoryRemittance(
            remittance_id=row["remittance_id"],
            run_id=row["run_id"],
            remittance_period=row["remittance_period"],
            cra_federal_tax=row["cra_federal_tax"],
            cra_ei_deduction=row["cra_ei_deduction"],
            cra_total_remitted=row["cra_total_remitted"],
            cra_confirmation_number=row["cra_confirmation_number"],
            rq_provincial_tax=row["rq_provincial_tax"],
            rq_qpp_deduction=row["rq_qpp_deduction"],
            rq_qpip_deduction=row["rq_qpip_deduction"],
            rq_total_remitted=row["rq_total_remitted"],
            rq_confirmation_number=row["rq_confirmation_number"],
            status=row["status"]
        )

        result = remittance.transmit(simulate_timeout=simulate_timeout)

        # Update database with resulting status and confirmation tokens
        db.execute(
            """UPDATE statutory_remittances
               SET status = ?, cra_confirmation_number = ?, rq_confirmation_number = ?
               WHERE remittance_id = ?""",
            (remittance.status, remittance.cra_confirmation_number,
             remittance.rq_confirmation_number, remittance_id)
        )

        return result
