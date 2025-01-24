from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime

class EpicInfo(BaseModel):
    key: str
    summary: str

class AnalysisInfo(BaseModel):
    main_objective: str
    technical_domains: List[str] = Field(default_factory=list)
    core_requirements: List[str] = Field(default_factory=list)
    stakeholders: List[str] = Field(default_factory=list)

class HighLevelTask(BaseModel):
    id: str
    type: str
    name: str
    complexity: str

class ExecutionPlanStats(BaseModel):
    user_stories: int
    technical_tasks: int
    total_subtasks: int

class ProposedTickets(BaseModel):
    file: str
    summary: Dict[str, Any]
    high_level_tasks: List[HighLevelTask]
    subtasks_by_parent: Dict[str, int]

class BreakdownInfo(BaseModel):
    execution_plan: ExecutionPlanStats
    proposed_tickets: ProposedTickets

class MetricsInfo(BaseModel):
    total_story_points: int
    estimated_days: float
    required_skills: List[str]

class EpicBreakdownResponse(BaseModel):
    status: str = "success"
    timestamp: datetime = Field(default_factory=datetime.now)
    epic: EpicInfo
    analysis: AnalysisInfo
    breakdown: BreakdownInfo
    metrics: MetricsInfo 