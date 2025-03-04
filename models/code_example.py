from typing import List
from pydantic import BaseModel


class TestCase(BaseModel):
    """Model for test case structure"""
    description: str
    code: str


class CodeExample(BaseModel):
    """Model for code example structure"""
    language: str
    description: str
    code: str
    test_cases: List[TestCase] = [] 