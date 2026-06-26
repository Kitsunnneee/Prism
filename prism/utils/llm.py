"""
AWS Bedrock integration for LLM-powered insights.
Uses boto3 to call Claude via Bedrock.
"""

import json
import os
from typing import Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class BedrockLLM:
    """
    Client for AWS Bedrock Claude models.

    Handles:
    - Model invocation
    - Error handling
    - Response parsing
    """

    def __init__(
        self,
        region: str = "us-east-1",
        model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    ):
        """
        Initialize Bedrock client.

        Args:
            region: AWS region (default: us-east-1)
            model_id: Bedrock model ID for Claude
        """
        self.region = region
        self.model_id = model_id

        profile = os.getenv("AWS_PROFILE") or os.getenv("AWS_DEFAULT_PROFILE")
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()

        if not session.get_credentials():
            raise NoCredentialsError()

        # Initialize the bedrock-runtime client
        self.client = session.client(
            service_name='bedrock-runtime',
            region_name=region
        )

    def generate_insight(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 1.0
    ) -> Optional[str]:
        """
        Generate text using Claude via Bedrock.

        Args:
            prompt: Input prompt for Claude
            max_tokens: Maximum response length
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text or None on error
        """
        try:
            # Bedrock API format for Claude
            # Follows Anthropic Messages API format
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            # Invoke the model
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())

            # Extract text from response
            # Claude returns: {"content": [{"text": "..."}], ...}
            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text']

            return None

        except ClientError as e:
            # AWS-specific errors (permissions, throttling, etc)
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            print(f"[Bedrock Error] {error_code}: {error_msg}")
            return None

        except NoCredentialsError:
            print("[LLM Error] AWS credentials not found. Set AWS_PROFILE or AWS access keys in .env.")
            return None

        except Exception as e:
            print(f"[LLM Error] {str(e)}")
            return None

    def analyze_tech_stack(
        self,
        company_name: str,
        tech_signals: Dict[str, Any],
        employee_count: int
    ) -> Optional[str]:
        """
        Generate strategic insights about a company's tech stack.

        Args:
            company_name: Name of the company
            tech_signals: Detected technologies by category
            employee_count: Number of employees analyzed

        Returns:
            LLM-generated analysis or None on error
        """
        # Build structured prompt
        prompt = self._build_analysis_prompt(
            company_name,
            tech_signals,
            employee_count
        )

        return self.generate_insight(prompt, max_tokens=1500)

    def _build_analysis_prompt(
        self,
        company_name: str,
        tech_signals: Dict[str, Any],
        employee_count: int
    ) -> str:
        """
        Construct prompt for tech stack analysis.

        Template includes:
        - Company context
        - Detected technologies with confidence scores
        - Request for strategic insights
        """
        # Convert tech signals to readable format
        tech_summary = []

        for category, signals in tech_signals.items():
            tech_summary.append(f"\n{category.upper()}:")
            for signal in signals:
                tech_summary.append(
                    f"  - {signal['technology']}: "
                    f"{signal['confidence']:.0%} confidence "
                    f"({signal['evidence_count']} profiles)"
                )

        tech_text = "\n".join(tech_summary)

        # Craft prompt for strategic analysis
        prompt = f"""You are a tech industry analyst. Analyze this company's technology stack and provide strategic insights.

Company: {company_name}
Sample Size: {employee_count} employees

Detected Technologies:
{tech_text}

Provide a concise analysis covering:

1. ARCHITECTURE INFERENCE
What does this tech stack suggest about their product architecture and engineering approach?

2. STRATEGIC SIGNALS
What do the technology choices reveal about the company's priorities, maturity, or direction?

3. TEAM COMPOSITION
What does the stack suggest about team structure and specialization?

4. NOTABLE PATTERNS
Any interesting observations about technology adoption, missing pieces, or unusual combinations?

Keep the analysis focused, evidence-based, and insightful. Format with clear sections and bullet points.
Be specific about what the data reveals rather than generic tech commentary."""

        return prompt


def get_llm_client() -> Optional[BedrockLLM]:
    """
    Factory function to create LLM client from environment config.

    Returns:
        BedrockLLM instance or None if configuration missing
    """
    region = os.getenv("AWS_REGION", "us-east-1")
    model_id = os.getenv(
        "BEDROCK_MODEL_ID",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    )

    try:
        client = BedrockLLM(region=region, model_id=model_id)
        return client
    except NoCredentialsError:
        print("[Warning] AWS credentials not found. Set AWS_PROFILE=dev or provide AWS access keys.")
        return None

    except Exception as e:
        import traceback
        print(f"[Warning] Could not initialize LLM client: {e}")
        print(f"[Debug] Traceback: {traceback.format_exc()}")
        return None
