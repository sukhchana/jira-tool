from typing import List
from pydantic import BaseModel


class TestPlan(BaseModel):
    """Model for test plan structure"""
    unit_tests: List[str]
    integration_tests: List[str]
    edge_cases: List[str]
    performance_tests: List[str]
    test_data_requirements: List[str] 