"""
Remittance Repository (Data Access Management / DAM Layer)
Encapsulates SQL queries and persistence for Statutory Remittances (Chapter 7 C.5).
"""

from database.db import db
from models.statutory_remittance import StatutoryRemittance

class RemittanceRepository:
    @staticmethod
    def get_by_run_id(run_id: int):
        """Fetches remittance record for a specific payroll run."""
        sql = "SELECT * FROM statutory_remittances WHERE run_id = ?"
        return db.query_one(sql, (run_id,))

    @staticmethod
    def get_by_id(remittance_id: int):
        """Fetches remittance record by primary key."""
        sql = "SELECT * FROM statutory_remittances WHERE remittance_id = ?"
        return db.query_one(sql, (remittance_id,))

    @staticmethod
    def save_initial(remittance: StatutoryRemittance) -> int:
        """Inserts an initial calculated statutory remittance record."""
        return db.execute(
            """INSERT INTO statutory_remittances (run_id, remittance_period, cra_federal_tax,
                                                 cra_ei_deduction, cra_total_remitted,
                                                 rq_provincial_tax, rq_qpp_deduction,
                                                 rq_qpip_deduction, rq_total_remitted, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Calculated')""",
            (remittance.run_id, remittance.remittance_period, remittance.cra_federal_tax,
             remittance.cra_ei_deduction, remittance.cra_total_remitted,
             remittance.rq_provincial_tax, remittance.rq_qpp_deduction,
             remittance.rq_qpip_deduction, remittance.rq_total_remitted)
        )

    @staticmethod
    def update_transmission(remittance_id: int, status: str, cra_confirmation: str = None, rq_confirmation: str = None):
        """Updates transmission status and government gateway confirmation tokens."""
        db.execute(
            """UPDATE statutory_remittances
               SET status = ?, cra_confirmation_number = ?, rq_confirmation_number = ?
               WHERE remittance_id = ?""",
            (status, cra_confirmation, rq_confirmation, remittance_id)
        )
