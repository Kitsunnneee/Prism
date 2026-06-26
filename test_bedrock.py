"""
Quick test to verify AWS Bedrock integration works.
"""

import os
from dotenv import load_dotenv
from prism.utils.llm import get_llm_client

load_dotenv()

def test_bedrock():
    print("Testing AWS Bedrock connection...")

    llm = get_llm_client()
    if not llm:
        print("ERROR: Could not create LLM client")
        return

    print(f"Using model: {llm.model_id}")
    print(f"Region: {llm.region}")

    # Simple test prompt
    response = llm.generate_insight(
        prompt="Say 'Hello from AWS Bedrock!' and nothing else.",
        max_tokens=50
    )

    if response:
        print(f"\nSuccess! Response:\n{response}")
    else:
        print("\nERROR: No response from Bedrock")

if __name__ == "__main__":
    test_bedrock()
