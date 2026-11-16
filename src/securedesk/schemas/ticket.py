from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10_000)
    
class TicketRead(BaseModel):
    model_config = ConfigDict(from_attribute=True)
    
    id: int
    title: str
    description: str
    tenant_id: int
    created_by_id: int
    created_at: datetime