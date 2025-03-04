from typing import List, Union
from pydantic import BaseModel, field_validator


class ImplementationApproach(BaseModel):
    """Model for implementation approach structure"""
    architecture: Union[str, List[str]]
    apis: Union[str, List[str]]
    database: Union[str, List[str]]
    security: Union[str, List[str]]
    implementation_steps: List[str] = []
    potential_challenges: List[str] = []
    
    @field_validator('architecture', 'apis', 'database', 'security', mode='before')
    @classmethod
    def convert_list_to_string(cls, value):
        """Convert list to string if needed"""
        if isinstance(value, list):
            return "\n".join([f"- {item}" for item in value])
        return value 