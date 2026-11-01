"""
Remittance Service (Use Case 4: Submit Statutory Remittances)
Manages Quebec Dual-Remittance calculations and Tax Authority Gateway transmissions.
Addresses Alternative Flow 7a (Government Rejection / Gateway Timeout).
Coordinates with RemittanceRepository for Data Access Management (Chapter 7 C.5).
"""

from models.statutory_remittance import StatutoryRemittance
from repositories.remittance_repository import RemittanceRepository

class RemittanceService:
    @staticmethod
    def get_remittance_by_run(run_id: int):
        """Fetches remittance details for a specific payroll run."""
        row = RemittanceRepository.get_by_run_id(run_id)
        if not row:
            return None
        remittance = StatutoryRemittance.from_row(row)
        return remittance.to_dict()

    @staticmethod
    def transmit_remittance(remittance_id: int, simulate_timeout: bool = False):
        """Transmits dual remittance to CRA and RQ gateways with Alternate Flow 7a handling."""
        row = RemittanceRepository.get_by_id(remittance_id)
        if not row:
            raise ValueError(f"Statutory Remittance #{remittance_id} not found.")

        remittance = StatutoryRemittance.from_row(row)
        result = remittance.transmit(simulate_timeout=simulate_timeout)

        # Update database with resulting status and confirmation tokens via repository
        RemittanceRepository.update_transmission(
            remittance_id=remittance_id,
            status=remittance.status,
            cra_confirmation=remittance.cra_confirmation_number,
            rq_confirmation=remittance.rq_confirmation_number
        )

        return result
