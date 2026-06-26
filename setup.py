"""
Setup configuration for Prism CLI tool.
Allows installation with: pip install -e .
"""

from setuptools import setup, find_packages

setup(
    name="prism-cli",
    version="0.1.0",
    description="Reverse engineer tech stacks from company hiring patterns",
    author="Rahul Maity",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "boto3>=1.35.0",
        "rich>=13.7.0",
        "typer>=0.12.3",
        "pydantic>=2.7.1",
        "python-dotenv>=1.0.0",
        "diskcache>=5.6.3",
    ],
    entry_points={
        "console_scripts": [
            "prism=prism.cli.app:main",
        ],
    },
    python_requires=">=3.8",
)
