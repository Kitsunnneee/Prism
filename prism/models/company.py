"""
Data models for company and employee information.
Uses Pydantic for validation and type safety.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CompanyBasicInfo(BaseModel):
    """
    Represents basic company information from CrustData API.
    Maps directly to the 'basic_info' field in API response.
    """
    name: str
    crustdata_company_id: int
    primary_domain: str
    all_domains: List[str] = Field(default_factory=list)
    website: Optional[str] = None
    description: Optional[str] = None
    year_founded: Optional[int] = None
    employee_count_range: Optional[str] = None
    industries: List[str] = Field(default_factory=list)


class Company(BaseModel):
    """
    Full company representation.
    Contains basic info and will hold employee data for analysis.
    """
    basic_info: CompanyBasicInfo
    # Will be populated by person search
    employees: List['Employee'] = Field(default_factory=list)

    @property
    def company_id(self) -> int:
        """Helper to get company ID quickly"""
        return self.basic_info.crustdata_company_id

    @property
    def name(self) -> str:
        """Helper to get company name quickly"""
        return self.basic_info.name


class EmployeeExperience(BaseModel):
    """
    Represents work experience from an employee's profile.
    Used to detect tech stack signals.
    """
    title: Optional[str] = None
    company_name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class EmployeeEducation(BaseModel):
    """
    Education background for clustering and quality signals.
    """
    school: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None


class Employee(BaseModel):
    """
    Simplified employee profile focused on tech stack inference.
    Only includes fields relevant for reverse engineering.
    """
    crustdata_person_id: int
    name: Optional[str] = None
    current_title: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None

    # These are the key fields for analysis
    experience: List[EmployeeExperience] = Field(default_factory=list)
    education: List[EmployeeEducation] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)

    # Raw data for debugging
    raw_data: Optional[Dict[str, Any]] = None


class TechSignal(BaseModel):
    """
    Represents a technology inferred from employee profiles.
    """
    technology: str
    confidence: float = Field(ge=0.0, le=1.0)  # Between 0 and 1
    evidence_count: int  # Number of profiles that mention this technology
    evidence: List[str] = Field(default_factory=list)
    category: str  # "language", "database", "framework", "infrastructure", etc

    def __lt__(self, other):
        """For sorting by confidence"""
        return self.confidence < other.confidence
