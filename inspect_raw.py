"""
Inspect raw employee data structure.
"""

import os
import json
from dotenv import load_dotenv
from prism.api.client import CrustDataClient

load_dotenv()

def inspect():
    api_key = os.getenv("CRUSTDATA_API_KEY")
    client = CrustDataClient(api_key=api_key)

    company = client.identify_company("openai.com")
    employees = client.search_employees(company.name, limit=1)

    if employees:
        emp = employees[0]
        print(json.dumps(emp.raw_data, indent=2))

if __name__ == "__main__":
    inspect()
