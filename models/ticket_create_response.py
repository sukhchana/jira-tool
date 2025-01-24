from pydantic import BaseModel, HttpUrl

class TicketCreateResponse(BaseModel):
    """Response model for ticket creation"""
    status: str
    message: str
    ticket_key: str
    ticket_url: HttpUrl 