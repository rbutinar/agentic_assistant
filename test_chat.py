from fastapi.testclient import TestClient
from main import app

def test_start_session_and_chat():
    client = TestClient(app)
    # Start a new session
    resp = client.post("/session")
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    assert session_id
    # Send a chat message
    chat_payload = {"session_id": session_id, "message": "Hello, agent!"}
    resp = client.post("/chat", json=chat_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Hello, agent!"
    assert data["messages"][1]["role"] == "assistant"
    assert "Simulated response" in data["messages"][1]["content"]
