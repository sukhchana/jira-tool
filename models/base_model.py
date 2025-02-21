from pydantic import BaseModel as PydanticBaseModel
from datetime import datetime

class BaseModel(PydanticBaseModel):
    """Base model with common configuration for all models"""
    
    class Config:
        """Pydantic model configuration"""
        json_encoders = {
            # Convert datetime to ISO format string
            datetime: lambda dt: dt.isoformat()
        }
        # Add any other common configuration here
        arbitrary_types_allowed = True  # Allows for more flexible type validation
        populate_by_name = True  # Allows population by field name as well as alias 