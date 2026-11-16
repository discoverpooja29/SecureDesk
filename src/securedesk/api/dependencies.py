import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from typing import Annotated

from ..core.config import settings
from ..db.session import get_db
from ..models.user import User
from ..models.tenant import Tenant

bearer_schema = HTTPBearer(auto_error=False)

def unauthorized() -> HTTPException:
    return HTTPException (
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing access token",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_schema)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    if credentials is None:
        raise unauthorized()
    
    try:
        payload = jwt.decode(
            jwt=credentials.credentials,
            key=settings.jwt_secret_key,
            algorithms=settings.jwt_algorithm,
            audience="securedesk-api",
            issuer="securedesk",
            options={
                "require": ["sub", "iss", "aud", "iat", "exp", "jti", "type"]
            }
        )
    
        if payload.get("type") != "access":
            raise unauthorized()
        
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized()
    
    user = db.get(User, user_id)
    
    if user is None:
        raise unauthorized()
    
    return user

def get_current_tenant(current_user: Annotated[User, Depends(get_current_user)]) -> Tenant:
    tenant = current_user.tenant
    
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant membership required"
        )
    
    return tenant

def require_permission(permission_name: str):
    def check_permission(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        has_permission = any(
            permission.name == permission_name
            for role in current_user.roles
            for permission in role.permissions
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
            
        return current_user

    return check_permission