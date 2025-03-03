from typing import List, Dict, Any, Union

from pydantic import BaseModel, Field


class HighLevelTask(BaseModel):
    """Model representing a high-level task/story"""
    title: str
    type: str = Field("High Level Task", description="The type of the task (User Story or Technical Task)")
    description: Union[str, Dict[str, Any]]  # Can be either a string (for technical tasks) or a dict (for user stories)
    technical_domain: str
    complexity: str
    dependencies: List[str]

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to ensure type field is always included"""
        data = super().model_dump(**kwargs)
        if "type" not in data:
            data["type"] = self.type
        return data
