from typing import List

from pydantic import BaseModel, Field


class AnalysisInfo(BaseModel):
    main_objective: str
    technical_domains: List[str] = Field(default_factory=list)
    core_requirements: List[str] = Field(default_factory=list)
    stakeholders: List[str] = Field(default_factory=list)
