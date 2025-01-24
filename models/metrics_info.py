from pydantic import BaseModel
from typing import List

class MetricsInfo(BaseModel):
    total_story_points: int
    estimated_days: float
    required_skills: List[str] 