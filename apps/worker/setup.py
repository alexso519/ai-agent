"""CrewAI Enterprise Control Center — Celery Worker

Governance: Section 5 — Celery Orchestration Model
"""

from setuptools import find_packages, setup

setup(
    name="crewai-worker",
    version="0.1.0",
    description="CrewAI Enterprise Control Center Celery Worker",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.12",
    install_requires=[
        "celery>=5.4.0",
        "redis>=5.0.0",
        "pydantic>=2.5.0",
        "crewai-shared-types>=0.1.0",
        "crewai-crew-runtime>=0.1.0",
        "httpx>=0.27.0",
        "python-dotenv>=1.0.0",
    ],
)