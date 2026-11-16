import pytest 
from fastapi.testclient import TestClient

from securedesk.main import app

@pytest.mark.parametrize(
    "headers",
    [
        {},
        { "Authorization" : "Bearer invalid-token" }
    ],
    ids=["missing-token", "invalid-token"]
)
def test_read_ticket_rejects_unauthenticated_requests(headers, client):
    response = client.get("/tickets/1", headers=headers)
        
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing access token"
    }
    assert response.headers["www-authenticate"] == "Bearer"