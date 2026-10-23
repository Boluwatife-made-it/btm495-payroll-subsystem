"""
Employee Domain Model (Use Case 1: Manage Employee Information)
Master record for individual client personnel.
"""

class Employee:
    VALID_STATUSES = {"Active", "On Leave", "Terminated"}

    def __init__(self, employee_id: int, client_id: int, first_name: str, 
                 last_name: str, email: str, phone: str, hire_date: str, 
                 status: str = "Active"):
        self.employee_id = int(employee_id)
        self.client_id = int(client_id)
        self.first_name = str(first_name)
        self.last_name = str(last_name)
        self.email = str(email)
        self.phone = str(phone)
        self.hire_date = str(hire_date)
        
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {self.VALID_STATUSES}")
        self.status = status

    def get_full_name(self) -> str:
        """Returns the formatted full name of the employee."""
        return f"{self.first_name} {self.last_name}"

    def update_status(self, new_status: str) -> bool:
        """Updates employment status with validation."""
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {self.VALID_STATUSES}")
        self.status = new_status
        return True

    def to_dict(self) -> dict:
        return {
            "employee_id": self.employee_id,
            "client_id": self.client_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.get_full_name(),
            "email": self.email,
            "phone": self.phone,
            "hire_date": self.hire_date,
            "status": self.status
        }

    def __repr__(self) -> str:
        return f"<Employee #{self.employee_id}: {self.get_full_name()} ({self.status})>"
