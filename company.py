from dataclasses import dataclass


@dataclass
class CompanyProfile:
    name: str
    industry: str
    description: str
    job_titles: list[str]
    departments: list[str]
    office_locations: list[dict]
