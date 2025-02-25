from typing import List
from pydantic import BaseModel, Field


class GherkinStep(BaseModel):
    """A single step in a Gherkin scenario"""
    keyword: str = Field(..., description="The step keyword (Given, When, Then, And)")
    text: str = Field(..., description="The step text")


class GherkinScenario(BaseModel):
    """A Gherkin scenario for a user story"""
    name: str = Field(..., description="The name of the scenario")
    steps: List[GherkinStep] = Field(default_factory=list, description="The steps in the scenario") 