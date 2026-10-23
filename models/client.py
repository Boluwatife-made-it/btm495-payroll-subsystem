"""
Client Domain Model (Use Case 1: Manage Employee Info / Multi-Tenant Boundary)
Represents the employer firm contracting MNP for payroll management.
"""

from datetime import datetime

class Client:
    def __init__(self, client_id: int, client_name: str, company_address: str, 
                 contact_email: str, created_at: str = None):
        self.client_id = int(client_id)
        self.client_name = str(client_name)
        self.company_address = str(company_address)
        self.contact_email = str(contact_email)
        self.created_at = created_at or datetime.now().isoformat()

    def validate_contact(self) -> bool:
        """Validates company contact email format."""
        return "@" in self.contact_email and "." in self.contact_email

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "client_name": self.client_name,
            "company_address": self.company_address,
            "contact_email": self.contact_email,
            "created_at": self.created_at
        }

    def __repr__(self) -> str:
        return f"<Client #{self.client_id}: {self.client_name}>"
