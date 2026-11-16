import pytest

from sqlalchemy import select

from securedesk.core.security import create_access_token
from securedesk.models import Permission, Role, User


@pytest.fixture
def admin_user(db_session, ticket_data):
    alice = ticket_data["users"]["alice"]

    admin_role = Role(
        name="admin",
        permissions=[Permission(name="users:manage")],
    )

    admin = User(
        email="admin@example.com",
        hashed_password=alice.hashed_password,
        tenant=alice.tenant,
        roles=[admin_role],
    )

    db_session.add(admin)
    db_session.commit()

    return admin

def test_admin_creates_agent_in_own_tenant(
    client,
    db_session,
    admin_user,
):
    token = create_access_token(admin_user.id)

    response = client.post(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "new-agent@example.com",
            "password": "AgentPassword123!",
            "role": "agent",
        },
    )

    assert response.status_code == 201

    created_user = db_session.get(User, response.json()["id"])

    assert created_user is not None
    assert created_user.tenant_id == admin_user.tenant_id
    assert {role.name for role in created_user.roles} == {"agent"}
    
@pytest.mark.parametrize("caller", ["alice", "agent"])
def test_user_without_manage_permission_cannot_create_users(
    client,
    db_session,
    ticket_data,
    caller,
):
    user = ticket_data["users"][caller]
    token = create_access_token(user.id)

    response = client.post(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "blocked-user@example.com",
            "password": "MemberPassword123!",
            "role": "customer",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Insufficient permissions",
    }

    created_user = db_session.scalar(
        select(User).where(User.email == "blocked-user@example.com")
    )
    assert created_user is None
    
@pytest.mark.parametrize(
    "field, expected_error",
    [
        ("role", "literal_error"),
        ("tenant_id", "extra_forbidden"),
    ],
    ids=["cannot-create-admin", "cannot-choose-tenant"],
)
def test_admin_cannot_bypass_user_creation_policy(
    client,
    db_session,
    admin_user,
    ticket_data,
    field,
    expected_error,
):
    token = create_access_token(admin_user.id)

    payload = {
        "email": "rejected-user@example.com",
        "password": "MemberPassword123!",
        "role": "customer",
    }

    if field == "role":
        payload["role"] = "admin"
    else:
        carol = ticket_data["users"]["carol"]
        payload["tenant_id"] = carol.tenant_id

    response = client.post(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 422
    assert any(
        error["loc"] == ["body", field]
        and error["type"] == expected_error
        for error in response.json()["detail"]
    )

    created_user = db_session.scalar(
        select(User).where(
            User.email == "rejected-user@example.com"
        )
    )
    assert created_user is None