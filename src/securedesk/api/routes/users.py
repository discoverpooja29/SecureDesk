from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ...core.security import hash_password
from ...db.session import get_db
from ...models import Role, Tenant, User
from ...schemas.user import TenantUserCreate, UserRead
from ..dependencies import get_current_tenant, require_permission

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("users:manage"))]
)
def create_tenant_user(
    data: TenantUserCreate,
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    user_role = db.scalar(
        select(Role).where(Role.name == data.role)
    )

    if user_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User creation is temporarily unavailable"
        )
        
    user = User(
        email=str(data.email).lower(),
        hashed_password=hash_password(data.password),
        tenant=tenant,
        roles=[user_role]
    )
    
    db.add(user)
    
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        
        if getattr(exc.orig, "sqlstate", None) != "23505":
            raise

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc

    db.refresh(user)
    return user