from pydantic import BaseModel, Field


class ComplexityAnalysis(BaseModel):
    """Model for complexity analysis response"""
    analysis: str = Field(..., description="The structured analysis of complexity")
    raw_response: str = Field(..., description="The raw LLM response")
    story_points: int = Field(default=0, description="Estimated story points")
    complexity_level: str = Field(default="Medium", description="Assessed complexity level (Low/Medium/High)")
    effort_estimate: str = Field(default="", description="Estimated effort in human-readable format")
    technical_factors: list[str] = Field(default_factory=list, description="Technical factors affecting complexity")
    risk_factors: list[str] = Field(default_factory=list, description="Identified risk factors") 