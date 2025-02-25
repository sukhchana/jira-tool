from pydantic import BaseModel, Field


class CodeBlock(BaseModel):
    """A code block with its language"""
    language: str = Field(..., description="The programming language of the code")
    description: str = Field(..., description="Description of what the code demonstrates")
    code: str = Field(..., description="The actual code") 