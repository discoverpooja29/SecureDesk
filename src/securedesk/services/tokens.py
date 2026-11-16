from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import generate_refresh_token, hash_refresh_token
from ..models import AuthSession, RefreshToken


def create_refresh_session(
    db: Session,
    user_id: int,
    expires_at: datetime
) -> str:
    auth_session = AuthSession(
        user_id=user_id,
        expires_at=expires_at
    )

    db.add(auth_session)
    db.flush()

    raw_token = generate_refresh_token()

    refresh_token = RefreshToken(
        session_id=auth_session.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=expires_at
    )

    db.add(refresh_token)

    return raw_token

def rotate_refresh_token(
    db: Session,
    raw_token: str,
) -> tuple[int, str] | None:
    stored_token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(raw_token)
        )
    )

    if stored_token is None:
        return None

    auth_session = db.scalar(
        select(AuthSession)
        .where(AuthSession.id == stored_token.session_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if auth_session is None:
        return None

    db.refresh(stored_token)
    now = datetime.now(timezone.utc)

    if (
        auth_session.revoked_at is not None
        or auth_session.expires_at <= now
    ):
        return None

    if stored_token.used_at is not None:
        auth_session.revoked_at = now
        return None

    if stored_token.expires_at <= now:
        return None

    stored_token.used_at = now
    new_raw_token = generate_refresh_token()

    db.add(
        RefreshToken(
            session_id=auth_session.id,
            token_hash=hash_refresh_token(new_raw_token),
            expires_at=auth_session.expires_at,
        )
    )

    return auth_session.user_id, new_raw_token

def revoke_refresh_session(
    db: Session,
    raw_token: str,
) -> None:
    session_id = db.scalar(
        select(RefreshToken.session_id).where(
            RefreshToken.token_hash == hash_refresh_token(raw_token)
        )
    )

    if session_id is None:
        return

    auth_session = db.scalar(
        select(AuthSession)
        .where(AuthSession.id == session_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if auth_session is None or auth_session.revoked_at is not None:
        return

    auth_session.revoked_at = datetime.now(timezone.utc)