from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel, ConfigDict


class BaseModel(PydanticBaseModel):
    """Base model with common configuration for all models"""

    model_config = ConfigDict(
        # Add any other common configuration here
        arbitrary_types_allowed=True,  # Allows for more flexible type validation
        populate_by_name=True  # Allows population by field name as well as alias
    )
    
    # Define custom serializer for datetime objects
    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
        
    # Also override model_dump_json for direct JSON serialization
    def model_dump_json(self, **kwargs):
        return super().model_dump_json(**kwargs)
