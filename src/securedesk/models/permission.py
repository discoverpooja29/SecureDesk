from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from ..db.base import Base
from .associations import role_permissions

if TYPE_CHECKING:
    from .role import Role

class Permission(Base):
    __tablename__="permissions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    roles: Mapped[list["Role"]] = relationship(secondary=role_permissions, back_populates="permissions")