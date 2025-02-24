from typing import List

from pydantic import BaseModel


class MetricsInfo(BaseModel):
    total_story_points: int
    estimated_days: float
    required_skills: List[str]
