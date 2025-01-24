from pydantic import BaseModel

class EpicInfo(BaseModel):
    key: str
    summary: str 