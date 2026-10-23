"""
BankAccount Domain Model (Use Case 1: Direct Deposit Banking)
Encapsulates direct deposit routing validation and account number masking.
"""

class BankAccount:
    VALID_TYPES = {"Checking", "Savings"}

    def __init__(self, account_id: int, employee_id: int, institution_number: str,
                 transit_number: str, account_number: str, account_type: str = "Checking"):
        self.account_id = int(account_id)
        self.employee_id = int(employee_id)
        self.institution_number = str(institution_number).strip().zfill(3)
        self.transit_number = str(transit_number).strip().zfill(5)
        self.account_number = str(account_number).strip()

        if account_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid account type '{account_type}'. Must be one of {self.VALID_TYPES}")
        self.account_type = account_type

    def validate_routing(self) -> bool:
        """Verifies Canadian banking standard: 3 digits institution + 5 digits transit."""
        return (len(self.institution_number) == 3 and self.institution_number.isdigit() and
                len(self.transit_number) == 5 and self.transit_number.isdigit())

    def get_masked_account(self) -> str:
        """Returns masked account number (e.g., ****4567) to secure financial data."""
        if len(self.account_number) <= 4:
            return "****"
        return f"****{self.account_number[-4:]}"

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "employee_id": self.employee_id,
            "institution_number": self.institution_number,
            "transit_number": self.transit_number,
            "account_number": self.account_number,
            "masked_account": self.get_masked_account(),
            "account_type": self.account_type,
            "is_valid_routing": self.validate_routing()
        }

    def __repr__(self) -> str:
        return f"<BankAccount #{self.account_id} for Emp #{self.employee_id}: {self.get_masked_account()}>"
