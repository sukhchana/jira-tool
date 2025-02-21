from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ImplementationApproach(BaseModel):
    """Implementation approach details"""
    architecture: str = Field(..., description="System architecture components and data flow")
    apis: str = Field(..., description="Required APIs and services")
    database: str = Field(..., description="Database changes and schema updates")
    security: str = Field(..., description="Security considerations and requirements")

class TechnicalTask(BaseModel):
    """Complete technical task model"""
    id: Optional[str] = Field(None, description="The ID of the technical task")
    title: str = Field(..., description="The title of the technical task")
    type: str = Field("Technical Task", description="The type of the task")
    description: str = Field(..., description="Detailed technical description of what needs to be implemented")
    technical_domain: str = Field(..., description="The technical domain this task belongs to")
    complexity: str = Field("Medium", description="The complexity level (Low, Medium, High)")
    business_value: str = Field("Medium", description="The business value level (Low, Medium, High)")
    story_points: int = Field(3, description="Story points (1, 2, 3, 5, 8, 13)")
    required_skills: List[str] = Field(default_factory=list, description="List of required technical skills")
    suggested_assignee: str = Field("Unassigned", description="Role best suited for this task")
    dependencies: List[str] = Field(default_factory=list, description="List of dependent tasks")
    implementation_approach: ImplementationApproach = Field(..., description="Implementation approach details")
    acceptance_criteria: List[str] = Field(default_factory=list, description="List of acceptance criteria")
    performance_impact: str = Field(..., description="Performance impact analysis")
    scalability_considerations: str = Field(..., description="Scalability considerations")
    monitoring_needs: str = Field(..., description="Monitoring and observability needs")
    testing_requirements: str = Field(..., description="Testing requirements and approach")
    
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to ensure type field is always included"""
        data = super().model_dump(**kwargs)
        if "type" not in data:
            data["type"] = "Technical Task"
        return data 