"""
PayChangeHistory Domain Model (Use Case 3: Compensation Audit Trail)
Immutable audit record satisfying SOX and accounting compliance.
"""

from datetime import datetime

class PayChangeHistory:
    def __init__(self, history_id: int, employee_id: int, previous_rate: float,
                 new_rate: float, change_reason: str, authorized_by: str,
                 change_date: str = None):
        self.history_id = int(history_id)
        self.employee_id = int(employee_id)
        self.change_date = change_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.previous_rate = float(previous_rate)
        self.new_rate = float(new_rate)
        self.change_reason = str(change_reason)
        self.authorized_by = str(authorized_by)

    @classmethod
    def from_row(cls, row: dict) -> "PayChangeHistory":
        """Factory method to construct a PayChangeHistory domain object from a database row (Chapter 7: Factoring)."""
        return cls(
            history_id=int(row["history_id"]),
            employee_id=int(row["employee_id"]),
            previous_rate=float(row.get("previous_rate", 0.0) or 0.0),
            new_rate=float(row.get("new_rate", 0.0) or 0.0),
            change_reason=str(row.get("change_reason", "")),
            authorized_by=str(row.get("authorized_by", "")),
            change_date=row.get("change_date")
        )

    def get_audit_summary(self) -> str:
        """Formats audit string suitable for compliance badges."""
        return (f"Rate updated from {self.previous_rate:.2f} CAD to {self.new_rate:.2f} CAD "
                f"on {self.change_date} by {self.authorized_by}: '{self.change_reason}'")

    def to_dict(self) -> dict:
        return {
            "history_id": self.history_id,
            "employee_id": self.employee_id,
            "change_date": self.change_date,
            "previous_rate": self.previous_rate,
            "new_rate": self.new_rate,
            "rate_delta": round(self.new_rate - self.previous_rate, 2),
            "change_reason": self.change_reason,
            "authorized_by": self.authorized_by,
            "audit_summary": self.get_audit_summary()
        }

    def __repr__(self) -> str:
        return f"<PayChangeHistory #{self.history_id} for Emp #{self.employee_id}: {self.new_rate} CAD>"
