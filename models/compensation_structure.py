"""
CompensationStructure Domain Model (Use Case 3: Manage Compensation & Earnings)
Defines pay frequency rules and overtime compensation formulas.
"""

class CompensationStructure:
    VALID_FREQUENCIES = {"Weekly", "Bi-Weekly", "Semi-Monthly", "Monthly"}

    def __init__(self, structure_id: int, employee_id: int, pay_frequency: str = "Bi-Weekly",
                 overtime_multiplier: float = 1.50, bonus_rate: float = 0.0,
                 commission_rate: float = 0.0):
        self.structure_id = int(structure_id)
        self.employee_id = int(employee_id)

        if pay_frequency not in self.VALID_FREQUENCIES:
            raise ValueError(f"Invalid pay frequency '{pay_frequency}'. Must be one of {self.VALID_FREQUENCIES}")
        self.pay_frequency = pay_frequency

        self.overtime_multiplier = float(overtime_multiplier)
        self.bonus_rate = float(bonus_rate)
        self.commission_rate = float(commission_rate)

    def calculate_gross(self, regular_hours: float, overtime_hours: float, hourly_rate: float) -> dict:
        """Calculates itemized regular earnings, overtime premium, and total gross pay."""
        reg_earnings = round(float(regular_hours) * float(hourly_rate), 2)
        ot_rate = round(float(hourly_rate) * self.overtime_multiplier, 2)
        ot_earnings = round(float(overtime_hours) * ot_rate, 2)
        total_gross = round(reg_earnings + ot_earnings + self.bonus_rate + self.commission_rate, 2)

        return {
            "regular_earnings": reg_earnings,
            "overtime_rate": ot_rate,
            "overtime_earnings": ot_earnings,
            "bonus_amount": self.bonus_rate,
            "commission_amount": self.commission_rate,
            "total_gross": total_gross
        }

    def to_dict(self) -> dict:
        return {
            "structure_id": self.structure_id,
            "employee_id": self.employee_id,
            "pay_frequency": self.pay_frequency,
            "overtime_multiplier": self.overtime_multiplier,
            "bonus_rate": self.bonus_rate,
            "commission_rate": self.commission_rate
        }

    def __repr__(self) -> str:
        return f"<CompStructure #{self.structure_id} for Emp #{self.employee_id}: {self.pay_frequency} (OT: {self.overtime_multiplier}x)>"
