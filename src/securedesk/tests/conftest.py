import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from securedesk.db.session import engine, get_db
from securedesk.main import app
from securedesk.core.security import hash_password
from securedesk.models import Permission, Role, Tenant, Ticket, User

@pytest.fixture
def db_session():
    if engine.url.database != "securedesk_test":
        raise RuntimeError(
            "Tests require the securedesk_test database. Run with --env-file .env.test"
        )
        
    with engine.connect() as connection:
        transaction = connection.begin()
        
        session = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            autoflush=False,
            expire_on_commit=False
        )
        
        try:
            yield session              # Give the session to the test
        finally:
            session.close()            # Close the session
            transaction.rollback()     # Undo the test's database changes

            
@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
        
    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        
'''      
Create db_session
      ↓
Replace get_db with the test-session provider
      ↓
Create TestClient → run the test
      ↓
Close TestClient
      ↓
Restore previous dependency overrides
      ↓
db_session fixture closes session and rolls back
'''

@pytest.fixture
def ticket_data(db_session):
    # Tenant creation
    acme = Tenant(name="Test Acme", slug="test-acme")
    globex = Tenant(name="Test Globex", slug="test-globex")

    # Customer Role Creation
    read_permission = Permission(name="tickets:read")
    create_permission = Permission(name="tickets:create")
    customer = Role(
        name="customer",
        permissions=[read_permission, create_permission],
    )
    
    # Agent Role creation
    tenant_read_permission = Permission(name="tickets:read:tenant")
    agent_role = Role(
        name="agent",
        permissions=[read_permission, tenant_read_permission],
    )

    password_hash = hash_password("test-password-123")

    users = {}
    for name, tenant in [
        ("alice", acme),
        ("bob", acme),
        ("carol", globex),
    ]:
        users[name] = User(
            email=f"{name}@example.com",
            hashed_password=password_hash,
            tenant=tenant,
            roles=[customer],
        )
        
    users["agent"] = User(
        email="agent@example.com",
        hashed_password=password_hash,
        tenant=acme,
        roles=[agent_role],
    )

    db_session.add_all(users.values())
    db_session.flush()

    tickets = {}
    for name, user in users.items():
        tickets[name] = Ticket(
            title=f"{name}'s ticket",
            description="Test ticket",
            tenant_id=user.tenant_id,
            created_by_id=user.id,
        )

    db_session.add_all(tickets.values())
    db_session.flush()

    return {"users": users, "tickets": tickets}