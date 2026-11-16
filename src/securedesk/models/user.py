from datetime import datetime
from sqlalchemy import DateTime, String, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from ..db.base import Base
from .associations import user_roles

if TYPE_CHECKING:
    from .role import Role
    from .tenant import Tenant

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", name="fk_users_tenant_id"), nullable=False, index=True)
    
    tenant: Mapped[Tenant] = relationship(back_populates="users")
    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users")