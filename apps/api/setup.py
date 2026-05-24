"""CrewAI Enterprise Control Center — API Server (FastAPI)

Governance: Section 1 — FastAPI Application Architecture
"""

from setuptools import find_packages, setup

setup(
    name="crewai-api",
    version="0.1.0",
    description="CrewAI Enterprise Control Center API Server",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.12",
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.29.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "crewai-shared-types>=0.1.0",
        "redis>=5.0.0",
        "httpx>=0.27.0",
        "python-dotenv>=1.0.0",
    ],
)