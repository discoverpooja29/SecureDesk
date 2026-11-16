from sqlalchemy import select

from securedesk.core.security import verify_password
from securedesk.models import Role, User, Tenant

def test_tenant_registration_creates_first_admin(client, db_session):
    db_session.add(Role(name="admin"))
    db_session.commit()
    
    response = client.post("/auth/register/tenant",
                           json={
                               "email": "owner@example.com",
                               "password": "LearningSecureDesk123!",
                               "tenant_name": "North Star",
                               "tenant_slug": "north-star"
                           })
    
    assert response.status_code == 201
    
    user = db_session.get(User, response.json()["id"])
    
    assert user is not None
    assert user.email =="owner@example.com"
    assert user.tenant is not None
    assert user.tenant.slug == "north-star"
    assert {role.name for role in user.roles} == {"admin"}
    assert verify_password("LearningSecureDesk123!", user.hashed_password)
    
    
def test_registration_rejects_existing_tenant_slug(
    client,
    db_session,
):
    existing_tenant = Tenant(
        name="Existing Acme",
        slug="acme",
    )

    db_session.add_all([
        Role(name="admin"),
        existing_tenant,
    ])
    db_session.commit()

    original_tenant_id = existing_tenant.id

    response = client.post(
        "/auth/register/tenant",
        json={
            "email": "outsider@example.com",
            "password": "LearningSecureDesk123!",
            "tenant_name": "Attempted Organization",
            "tenant_slug": "acme",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Email or organization slug already registered",
    }

    new_user = db_session.scalar(
        select(User).where(
            User.email == "outsider@example.com"
        )
    )
    assert new_user is None

    tenant = db_session.get(Tenant, original_tenant_id)
    assert tenant is not None
    assert tenant.name == "Existing Acme"
    