from pydantic import BaseModel
from typing import List

class HighLevelTask(BaseModel):
    """Model representing a high-level task/story"""
    name: str
    description: str
    technical_domain: str
    complexity: str
    dependencies: List[str] 