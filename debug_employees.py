"""
Debug script to see what employee data we're getting.
"""

import os
from dotenv import load_dotenv
from prism.api.client import CrustDataClient
import json

load_dotenv()

def debug():
    api_key = os.getenv("CRUSTDATA_API_KEY")
    client = CrustDataClient(api_key=api_key)

    company = client.identify_company("stripe.com")
    print(f"Company: {company.name}\n")

    employees = client.search_employees(company.name, limit=3)
    print(f"Found {len(employees)} employees\n")

    for i, emp in enumerate(employees):
        print(f"Employee {i+1}:")
        print(f"  Name: {emp.name}")
        print(f"  Title: {emp.current_title}")
        print(f"  Headline: {emp.headline}")
        print(f"  Skills: {emp.skills[:5] if emp.skills else 'None'}")
        print(f"  Experience ({len(emp.experience)} jobs):")
        for exp in emp.experience[:3]:
            print(f"    - {exp.title} @ {exp.company_name}")
        print()

if __name__ == "__main__":
    debug()
