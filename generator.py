import json
import csv
import io
from faker import Faker
from employee import Employee
from company import CompanyProfile
import random
from datetime import date, timedelta

fake = Faker()

# Title prefixes applied per org level when building tier-appropriate titles.
# Level 1 = Executive, 2 = VP, 3 = Manager, 4 = Individual Contributor
LEVEL_PREFIXES = {
    1: ["Chief", "President,", "Head of", "Global"],
    2: ["Vice President of", "VP of", "Senior Director of", "Director of"],
    3: ["Manager,", "Senior Manager,", "Lead", "Team Lead,"],
    4: [],  # ICs use the raw LLM-generated titles as-is
}


def _make_title(level: int, base_titles: list[str]) -> str:
    """Return a job title appropriate for the given org level."""
    base = random.choice(base_titles)
    prefixes = LEVEL_PREFIXES.get(level, [])
    if prefixes:
        return f"{random.choice(prefixes)} {base}"
    return base


class EmployeeGenerator:
    def __init__(self, profile: CompanyProfile, num_employees: int):
        self.profile = profile
        self.num_employees = num_employees
        self.employees: list[Employee] = []

    def _generate_id(self, used_ids: set[str]) -> str:
        """Generate a unique employee ID not already in used_ids."""
        while True:
            emp_id = f"EMP{random.randint(10000, 99999)}"
            if emp_id not in used_ids:
                used_ids.add(emp_id)
                return emp_id

    def _generate_dates(self, count: int) -> list[date]:
        today = date.today()
        dates = []
        for _ in range(count):
            days_ago = random.randint(30, 365 * 10)
            dates.append(today - timedelta(days=days_ago))
        return sorted(dates)

    def _tier_counts(self) -> dict[int, int]:
        """
        Derive how many employees belong to each level based on total headcount.

        Level 1 (Executive): 1
        Level 2 (VP):        ~3-5% of total, min 2
        Level 3 (Manager):   ~10% of total, min 1
        Level 4 (IC):        remainder
        """
        n = self.num_employees
        n_exec = 1
        n_vp = max(2, int(n * 0.04))
        n_mgr = max(1, int(n * 0.10))
        # Ensure the leadership layers don't exceed total headcount
        n_vp = min(n_vp, max(1, n - n_exec - 1))
        n_mgr = min(n_mgr, max(1, n - n_exec - n_vp - 1))
        n_ic = max(0, n - n_exec - n_vp - n_mgr)
        return {1: n_exec, 2: n_vp, 3: n_mgr, 4: n_ic}

    def _make_employee(
        self,
        level: int,
        used_ids: set[str],
        start_date: date,
    ) -> Employee:
        first = fake.first_name()
        last = fake.last_name()
        location = random.choice(self.profile.office_locations)
        department = random.choice(self.profile.departments)
        is_manager = level < 4

        return Employee(
            employee_id=self._generate_id(used_ids),
            first_name=first,
            last_name=last,
            email=f"{first.lower()}.{last.lower()}@{location['domain']}",
            phone=fake.phone_number(),
            job_title=_make_title(level, self.profile.job_titles),
            department=department,
            office_location=f"{location['city']}, {location['country']}",
            manager_id=None,
            start_date=start_date,
            level=level,
            is_manager=is_manager,
            direct_reports=[],
        )

    def generate(self) -> list[Employee]:
        counts = self._tier_counts()
        total = sum(counts.values())
        dates = self._generate_dates(total)
        used_ids: set[str] = set()

        # Build each tier oldest-first (earlier start dates = more senior)
        tiers: dict[int, list[Employee]] = {}
        date_idx = 0
        for level in sorted(counts):
            tier = []
            for _ in range(counts[level]):
                emp = self._make_employee(level, used_ids, dates[date_idx])
                tier.append(emp)
                date_idx += 1
            tiers[level] = tier

        # Wire up the hierarchy: each employee in level N gets a manager from level N-1
        # Level 1 has no manager (top of the org)
        for level in range(2, 5):
            if level not in tiers or (level - 1) not in tiers:
                continue
            parents = tiers[level - 1]
            for emp in tiers[level]:
                manager = random.choice(parents)
                emp.manager_id = manager.employee_id
                manager.direct_reports.append(emp.employee_id)

        self.employees = [e for tier in tiers.values() for e in tier]
        return self.employees

    def to_json(self) -> str:
        return json.dumps([e.to_dict() for e in self.employees], indent=2)

    def to_csv(self) -> str:
        if not self.employees:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.employees[0].to_dict().keys())
        writer.writeheader()
        for emp in self.employees:
            writer.writerow(emp.to_dict())
        return output.getvalue()
