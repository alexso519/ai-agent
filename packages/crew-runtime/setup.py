"""CrewAI Enterprise Control Center — Crew Runtime Package

This package provides the CrewRuntime abstraction layer that wraps CrewAI
execution for managed lifecycle, event capture, checkpointing, and memory operations.

Governance: Section 4 — CrewRuntime Abstraction Design
"""

from setuptools import find_packages, setup

setup(
    name="crewai-crew-runtime",
    version="0.1.0",
    description="CrewRuntime abstraction wrapping CrewAI execution",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.12",
    install_requires=[
        "crewai>=0.70.0",
        "crewai-shared-types>=0.1.0",
        "pydantic>=2.5.0",
        "redis>=5.0.0",
    ],
)