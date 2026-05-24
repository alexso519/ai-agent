"""CrewAI Enterprise Control Center — Shared Types (Python)
Governance: Phase 0 — Monorepo Foundation
"""

from setuptools import find_packages, setup

setup(
    name="crewai-shared-types",
    version="0.1.0",
    description="Shared types, events, schemas, and constants for CrewAI Enterprise Control Center",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.12",
    install_requires=[
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
    ],
)