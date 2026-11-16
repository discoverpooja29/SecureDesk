import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from securedesk.core.security import hash_refresh_token
from securedesk.models import AuthSession, RefreshToken


@pytest.fixture
def login_tokens(client, ticket_data):
    alice = ticket_data["users"]["alice"]

    response = client.post(
        "/auth/login",
        json={
            "email": alice.email,
            "password": "test-password-123",
        },
    )

    assert response.status_code == 200
    return response.json()

def test_refresh_rotates_token_in_same_session(
    client,
    db_session,
    login_tokens,
):
    old_raw_token = login_tokens["refresh_token"]

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": old_raw_token},
    )

    assert response.status_code == 200

    new_raw_token = response.json()["refresh_token"]
    assert new_raw_token != old_raw_token

    db_session.expire_all()

    old_record = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(old_raw_token)
        )
    )
    new_record = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(new_raw_token)
        )
    )

    assert old_record is not None
    assert new_record is not None
    assert old_record.used_at is not None
    assert new_record.used_at is None
    assert new_record.session_id == old_record.session_id
    assert new_record.expires_at == old_record.expires_at
    
def test_refresh_replay_revokes_session(
    client,
    db_session,
    login_tokens,
):
    old_raw_token = login_tokens["refresh_token"]

    rotated = client.post(
        "/auth/refresh",
        json={"refresh_token": old_raw_token},
    )
    assert rotated.status_code == 200

    new_raw_token = rotated.json()["refresh_token"]

    replay = client.post(
        "/auth/refresh",
        json={"refresh_token": old_raw_token},
    )
    assert replay.status_code == 401

    db_session.expire_all()

    old_record = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(old_raw_token)
        )
    )
    assert old_record is not None

    session = db_session.get(AuthSession, old_record.session_id)
    assert session is not None
    assert session.revoked_at is not None

    blocked = client.post(
        "/auth/refresh",
        json={"refresh_token": new_raw_token},
    )
    assert blocked.status_code == 401
    
def test_logout_revokes_only_target_session(
    client,
    db_session,
    login_tokens,
    ticket_data,
):
    first_token = login_tokens["refresh_token"]
    alice = ticket_data["users"]["alice"]

    second_login = client.post(
        "/auth/login",
        json={
            "email": alice.email,
            "password": "test-password-123",
        },
    )
    assert second_login.status_code == 200
    second_token = second_login.json()["refresh_token"]

    first_record = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(first_token)
        )
    )
    second_record = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(second_token)
        )
    )

    assert first_record is not None
    assert second_record is not None
    assert first_record.session_id != second_record.session_id

    logout = client.post(
        "/auth/logout",
        json={"refresh_token": first_token},
    )
    assert logout.status_code == 204
    assert logout.content == b""

    db_session.expire_all()

    first_session = db_session.get(AuthSession, first_record.session_id)
    second_session = db_session.get(AuthSession, second_record.session_id)

    assert first_session.revoked_at is not None
    assert second_session.revoked_at is None

    blocked = client.post(
        "/auth/refresh",
        json={"refresh_token": first_token},
    )
    assert blocked.status_code == 401

    allowed = client.post(
        "/auth/refresh",
        json={"refresh_token": second_token},
    )
    assert allowed.status_code == 200
    
def test_logout_is_repeatable(client, login_tokens):
    token = login_tokens["refresh_token"]

    for _ in range(2):
        response = client.post(
            "/auth/logout",
            json={"refresh_token": token},
        )

        assert response.status_code == 204
        assert response.content == b""
        
@pytest.mark.parametrize("expired_record", ["token", "session"])
def test_refresh_rejects_expired_credentials(
    client,
    db_session,
    login_tokens,
    expired_record,
):
    raw_token = login_tokens["refresh_token"]

    stored_token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(raw_token)
        )
    )
    assert stored_token is not None

    session = db_session.get(AuthSession, stored_token.session_id)
    assert session is not None

    past = datetime.now(timezone.utc) - timedelta(seconds=1)

    if expired_record == "token":
        stored_token.expires_at = past
    else:
        session.expires_at = past

    db_session.commit()

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": raw_token},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid refresh token"}

    db_session.refresh(stored_token)
    assert stored_token.used_at is None
    
def test_unknown_refresh_token_does_not_revoke_valid_session(
    client,
    login_tokens,
):
    rejected = client.post(
        "/auth/refresh",
        json={"refresh_token": "not-an-issued-token"},
    )

    assert rejected.status_code == 401
    assert rejected.json() == {"detail": "Invalid refresh token"}

    valid = client.post(
        "/auth/refresh",
        json={"refresh_token": login_tokens["refresh_token"]},
    )

    assert valid.status_code == 200