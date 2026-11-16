from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pwdlib import PasswordHash

import jwt
import hashlib
import secrets

from ..core.config import settings

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str, hash_password: str) -> bool:
    return password_hash.verify(plain_password, hash_password)

def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    
    payload = {
        "sub": str(user_id),
        "iss": "securedesk",
        "aud": "securedesk-api",
        "iat": now,
        "exp": now + timedelta (
            minutes=settings.jwt_access_token_minutes
        ),
        "jti": str(uuid4()),
        "type": "access"
    }
    
    return jwt.encode(
        payload = payload,
        key = settings.jwt_secret_key,
        algorithm = settings.jwt_algorithm
    )
    
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)

def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()