import pytest

from sqlalchemy.exc import IntegrityError
from securedesk.core.security import create_access_token


@pytest.mark.parametrize(
    "ticket_owner, expected_status",
    [
        ("alice", 200),
        ("bob", 404),
        ("carol", 404),
    ],
    ids=["own-ticket", "other-customer", "other-tenant"],
)
def test_customer_ticket_access(
    client,
    ticket_data,
    ticket_owner,
    expected_status,
):
    alice = ticket_data["users"]["alice"]
    ticket = ticket_data["tickets"][ticket_owner]
    token = create_access_token(alice.id)

    response = client.get(
        f"/tickets/{ticket.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == expected_status

    if expected_status == 200:
        assert response.json()["id"] == ticket.id
    else:
        assert response.json() == {"detail": "Ticket not found"}
        
@pytest.mark.parametrize(
    "ticket_owner, expected_status",
    [
        ("bob", 200),
        ("carol", 404),
    ],
    ids=["same-tenant", "other-tenant"],
)
def test_agent_ticket_access(
    client,
    ticket_data,
    ticket_owner,
    expected_status,
):
    agent = ticket_data["users"]["agent"]
    ticket = ticket_data["tickets"][ticket_owner]
    token = create_access_token(agent.id)

    response = client.get(
        f"/tickets/{ticket.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == expected_status

    if expected_status == 200:
        assert response.json()["id"] == ticket.id
    else:
        assert response.json() == {"detail": "Ticket not found"}
        
        
def test_user_without_read_permission_is_denied(
    client,
    db_session,
    ticket_data,
):
    alice = ticket_data["users"]["alice"]
    ticket = ticket_data["tickets"]["alice"]

    alice.roles.clear()
    db_session.flush()

    token = create_access_token(alice.id)
    response = client.get(
        f"/tickets/{ticket.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Insufficient permissions",
    }


def test_database_rejects_missing_tenant_membership(
    db_session,
    ticket_data,
):
    alice = ticket_data["users"]["alice"]

    with pytest.raises(IntegrityError) as error:
        with db_session.begin_nested():
            alice.tenant = None
            db_session.flush()

    assert error.value.orig.sqlstate == "23502"
    assert error.value.orig.diag.column_name == "tenant_id"
    
    
def test_create_ticket_uses_authenticated_user_and_tenant(
    client,
    ticket_data,
):
    alice = ticket_data["users"]["alice"]
    token = create_access_token(alice.id)

    response = client.post(
        "/tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Cannot log in",
            "description": "Please help restore my access.",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["created_by_id"] == alice.id
    assert data["tenant_id"] == alice.tenant_id
    assert data["title"] == "Cannot log in"
    
@pytest.mark.parametrize(
    "protected_field",
    ["tenant_id", "created_by_id"],
)
def test_create_ticket_rejects_protected_fields(
    client,
    ticket_data,
    protected_field,
):
    alice = ticket_data["users"]["alice"]
    carol = ticket_data["users"]["carol"]
    token = create_access_token(alice.id)

    protected_values = {
        "tenant_id": carol.tenant_id,
        "created_by_id": carol.id,
    }

    response = client.post(
        "/tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Cannot log in",
            "description": "Please help.",
            protected_field: protected_values[protected_field],
        },
    )

    assert response.status_code == 422
    assert any(
        error["type"] == "extra_forbidden"
        and error["loc"] == ["body", protected_field]
        for error in response.json()["detail"]
    )