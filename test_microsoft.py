"""
Test Microsoft employee fetch
"""

import os
from dotenv import load_dotenv
from prism.api.client import CrustDataClient

load_dotenv()

def test():
    api_key = os.getenv("CRUSTDATA_API_KEY")
    client = CrustDataClient(api_key=api_key)

    company = client.identify_company("microsoft.com")
    print(f"Company: {company.name}")

    # Clear cache for fresh data
    client.cache.clear()

    employees = client.search_employees(company.name, limit=70)
    print(f"Requested: 70 employees")
    print(f"Received: {len(employees)} employees")

    if len(employees) < 70:
        print(f"\nMissing {70 - len(employees)} employees!")
        print("This suggests parsing failures or API returned less data")

if __name__ == "__main__":
    test()
