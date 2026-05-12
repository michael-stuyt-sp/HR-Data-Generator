from dataclasses import dataclass, field
from typing import Optional
from datetime import date


@dataclass
class Employee:
    employee_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    job_title: str
    department: str
    office_location: str
    manager_id: Optional[str]
    start_date: date
    level: int = 4          # 1=Executive, 2=VP, 3=Manager, 4=Individual Contributor
    is_manager: bool = False
    direct_reports: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "employee_id": self.employee_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "job_title": self.job_title,
            "department": self.department,
            "office_location": self.office_location,
            "manager_id": self.manager_id,
            "start_date": self.start_date.isoformat(),
            "level": self.level,
            "is_manager": self.is_manager,
            "direct_reports": self.direct_reports,
        }
