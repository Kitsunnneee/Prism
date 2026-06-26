"""
CrustData API client with disk caching.
"""

import requests
from typing import List, Optional, Dict, Any
from diskcache import Cache
import hashlib
import json

from prism.models.company import Company, CompanyBasicInfo, Employee


class CrustDataClient:
    """
    Client for CrustData API.

    Features:
    - Automatic caching to disk
    - Small parsing layer from API payloads to app models
    """

    BASE_URL = "https://api.crustdata.com"
    API_VERSION = "2025-11-01"

    def __init__(self, api_key: str, cache_dir: str = ".cache"):
        """
        Initialize the client.

        Args:
            api_key: CrustData API key
            cache_dir: Where to store cached responses
        """
        self.api_key = api_key
        # diskcache creates a SQLite-backed cache on disk
        self.cache = Cache(cache_dir)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "x-api-version": self.API_VERSION
        })

    def _cache_key(self, endpoint: str, payload: Dict) -> str:
        """
        Generate a unique cache key for a request.
        """
        cache_str = f"{endpoint}:{json.dumps(payload, sort_keys=True)}"
        return hashlib.sha256(cache_str.encode()).hexdigest()

    def _make_request(
        self,
        endpoint: str,
        payload: Dict,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Make a POST request to CrustData API.

        Args:
            endpoint: API endpoint (e.g., "/company/identify")
            payload: Request body
            use_cache: Whether to use cached response if available

        Returns:
            API response as dict

        Raises:
            Exception if API returns error
        """
        # Check cache first
        if use_cache:
            cache_key = self._cache_key(endpoint, payload)
            cached = self.cache.get(cache_key)
            if cached is not None:
                print(f"[Cache Hit] {endpoint}")
                return cached

        # Make actual request
        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.post(url, json=payload)

        # Handle errors
        if response.status_code != 200:
            error_msg = response.text
            raise Exception(f"API Error {response.status_code}: {error_msg}")

        data = response.json()

        # Cache successful response
        if use_cache:
            # Cache for 24 hours (86400 seconds)
            self.cache.set(cache_key, data, expire=86400)

        return data

    def identify_company(self, domain: str) -> Optional[Company]:
        """
        Identify a company by domain.

        Args:
            domain: Company domain (e.g., "stripe.com")

        Returns:
            Company object or None if not found
        """
        payload = {"domains": [domain]}

        try:
            response = self._make_request("/company/identify", payload)

            # Response is a list with one element (our domain)
            if not response or len(response) == 0:
                return None

            matches = response[0].get("matches", [])
            if not matches:
                return None

            # Take the first match (highest confidence)
            company_data = matches[0]["company_data"]
            basic_info = CompanyBasicInfo(**company_data["basic_info"])

            return Company(basic_info=basic_info)

        except Exception as e:
            print(f"Error identifying company: {e}")
            return None

    def search_employees(
        self,
        company_name: str,
        limit: int = 10
    ) -> List[Employee]:
        """
        Search for employees at a company.

        Args:
            company_name: Name of the company
            limit: Max results (default 10)

        Returns:
            List of Employee objects
        """
        # Build filter for current employees at this company
        base_filter = {
            "field": "experience.employment_details.current.company_name",
            "type": "=",
            "value": company_name
        }

        payload = {
            "filters": base_filter,
            "limit": limit
        }

        try:
            response = self._make_request("/person/search", payload)

            profiles = response.get("profiles", [])
            employees = []

            for profile in profiles:
                # Extract relevant fields for our Employee model
                employee = self._parse_employee_profile(profile)
                if employee:
                    employees.append(employee)

            return employees

        except Exception as e:
            print(f"Error searching employees: {e}")
            return []

    def _parse_employee_profile(self, profile: Dict) -> Optional[Employee]:
        """
        Parse raw API profile into our Employee model.
        Extracts only what we need for tech stack analysis.
        """
        try:
            from prism.models.company import EmployeeExperience, EmployeeEducation

            basic = profile.get("basic_profile", {})
            exp_data = profile.get("experience", {}).get("employment_details", {})
            edu_data = profile.get("education", {}).get("schools", [])
            skills_data = profile.get("skills", {}).get("professional_network_skills", [])

            # Parse experience (current + past)
            experience_list = []

            # Add current jobs
            for job in exp_data.get("current", []):
                experience_list.append(EmployeeExperience(
                    title=job.get("title"),
                    company_name=job.get("name"),
                    description=job.get("description"),
                    start_date=job.get("start_date"),
                    end_date=job.get("end_date")
                ))

            # Add past jobs
            for job in exp_data.get("past", []):
                experience_list.append(EmployeeExperience(
                    title=job.get("title"),
                    company_name=job.get("name"),
                    description=job.get("description"),
                    start_date=job.get("start_date"),
                    end_date=job.get("end_date")
                ))

            # Parse education
            education_list = []
            for school in edu_data:
                education_list.append(EmployeeEducation(
                    school=school.get("school"),
                    degree=school.get("degree"),
                    field_of_study=school.get("field_of_study")
                ))

            # Build employee object
            employee = Employee(
                crustdata_person_id=profile.get("crustdata_person_id"),
                name=basic.get("name"),
                current_title=basic.get("current_title"),
                headline=basic.get("headline"),
                location=basic.get("location", {}).get("raw") if isinstance(basic.get("location"), dict) else None,
                skills=skills_data if isinstance(skills_data, list) else [],
                experience=experience_list,
                education=education_list,
                raw_data=profile  # Keep raw for debugging
            )

            return employee

        except Exception as e:
            print(f"Error parsing profile: {e}")
            return None
