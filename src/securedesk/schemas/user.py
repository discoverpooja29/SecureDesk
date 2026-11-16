from typing import Literal 
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    
    tenant_name: str = Field(min_length=1, max_length=150, pattern=r"\S")
    tenant_slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    
class TenantUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: Literal["customer", "agent"] = "customer"
    
class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str

class UserRead(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    roles: list[RoleRead]
    
    model_config = ConfigDict(from_attributes=True)