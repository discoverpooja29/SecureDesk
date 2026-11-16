from sqlalchemy import select

from securedesk.core.security import hash_refresh_token
from securedesk.models import AuthSession, RefreshToken


def test_login_creates_session_and_hashed_refresh_token(
    client,
    db_session,
    ticket_data,
):
    alice = ticket_data["users"]["alice"]

    response = client.post(
        "/auth/login",
        json={
            "email": alice.email,
            "password": "test-password-123",
        },
    )

    assert response.status_code == 200

    data = response.json()
    raw_token = data["refresh_token"]

    session = db_session.scalar(
        select(AuthSession).where(AuthSession.user_id == alice.id)
    )
    assert session is not None
    assert session.revoked_at is None

    stored_token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.session_id == session.id
        )
    )
    assert stored_token is not None
    assert stored_token.token_hash == hash_refresh_token(raw_token)
    assert stored_token.token_hash != raw_token
    assert stored_token.used_at is None
    assert stored_token.expires_at == session.expires_at

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["id"] == alice.id
    
def test_invalid_password_creates_no_session(
    client,
    db_session,
    ticket_data,
):
    alice = ticket_data["users"]["alice"]

    response = client.post(
        "/auth/login",
        json={
            "email": alice.email,
            "password": "incorrect-password",
        },
    )

    assert response.status_code == 401

    session = db_session.scalar(
        select(AuthSession).where(AuthSession.user_id == alice.id)
    )
    assert session is None