from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Annotated
from datetime import datetime, timedelta, timezone

from ...core.security import hash_password, verify_password, create_access_token
from ...core.config import settings
from ...db.session import get_db
from ...models.tenant import Tenant
from ...models.user import User
from ...models.role import Role
from ...schemas.user import UserCreate, UserRead
from ...schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from ...services.tokens import (create_refresh_session, rotate_refresh_token, revoke_refresh_session)
from ..dependencies import get_current_user, require_permission, get_current_tenant


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/register/tenant", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    data: UserCreate,
    db: Annotated[Session, Depends(get_db)]
):
    email = str(data.email).lower()
    
    existing_user = db.scalar(select(User).where(User.email == email))
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
        
    admin_role = db.scalar(
        select(Role).where(Role.name == "admin")
    )
        
    if admin_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration is temporarily unavailable."
        )
        
    tenant = Tenant(
        name=data.tenant_name.strip(),
        slug=data.tenant_slug
    )
        
    user = User(
        email=email,
        hashed_password=hash_password(data.password),
        tenant=tenant
    )
    
    user.roles.append(admin_role)
    db.add(user)
    
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        
        if getattr(exc.orig, "sqlstate", None) != "23505":
            raise
        
        raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email or organization slug already registered"
                ) from exc
        
    db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    db: Annotated[Session, Depends(get_db)]
):
    email = str(data.email).lower()
    
    user = db.scalar(select(User).where(User.email == email))
    
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_session_days
    )
    
    try:
        raw_refresh_token = create_refresh_session(
            db=db,
            user_id=user.id,
            expires_at=expires_at
        )
        
        response = TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=raw_refresh_token
        )
        
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    return response
        
@router.post("/refresh", response_model=TokenResponse)
def refresh(
    data: RefreshRequest,
    db: Annotated[Session, Depends(get_db)]
):
    response = None

    try:
        result = rotate_refresh_token(
            db=db,
            raw_token=data.refresh_token
        )

        if result is not None:
            user_id, new_refresh_token = result

            response = TokenResponse(
                access_token=create_access_token(user_id),
                refresh_token=new_refresh_token
            )

        db.commit()
    except Exception:
        db.rollback()
        raise

    if response is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    return response

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def logout(
    data: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        revoke_refresh_session(
            db=db,
            raw_token=data.refresh_token,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/me", response_model=UserRead)
def get_my_profile(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user

@router.get("/assignment-check")
def check_assignment_access(current_user: Annotated[User, Depends(require_permission("tickets:assign"))]):
    return {
        "message": "You have permission to assign tickets",
        "user_id": current_user.id
    }
    
@router.get("/tenant-check")
def check_tenant(tenant: Annotated[Tenant,  Depends(get_current_tenant)]):
    return  {
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug
    }