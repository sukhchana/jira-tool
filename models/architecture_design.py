from typing import List, Optional
from pydantic import BaseModel, Field

class ArchitectureDesignRequest(BaseModel):
    """Request model for generating architecture design based on JIRA epic"""
    epic_key: str = Field(..., description="JIRA epic key")
    cloud_provider: str = Field(..., description="Cloud provider (AWS or GCP)")
    additional_context: Optional[str] = Field(None, description="Additional context for the architecture design")
    
class DiagramInfo(BaseModel):
    """Information about a generated diagram"""
    title: str = Field(..., description="Title of the diagram")
    type: str = Field(..., description="Type of diagram (sequence, architecture, system design)")
    mermaid_code: str = Field(..., description="Mermaid markdown code for the diagram")
    description: Optional[str] = Field(None, description="Description of the diagram")

class ArchitectureDesignResponse(BaseModel):
    """Response model for architecture design generation"""
    execution_id: str = Field(..., description="Unique ID for this execution")
    epic_key: str = Field(..., description="JIRA epic key")
    cloud_provider: str = Field(..., description="Cloud provider used (AWS or GCP)")
    architecture_overview: str = Field(..., description="Overview of the proposed architecture")
    diagrams: List[DiagramInfo] = Field(..., description="List of mermaid diagrams")
    architecture_file_path: str = Field(..., description="Path to the generated architecture markdown file") 