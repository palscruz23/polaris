from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chat_returns_response():
    response = client.post(
        "/chat",
        json={"message": "Identify repeat pump failures"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Identify repeat pump failures",
        "response": "The Reliability Team received your request.",
    }


def test_chat_rejects_missing_message():
    response = client.post("/chat", json={})

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "missing"


def test_chat_rejects_blank_message():
    response = client.post("/chat", json={"message": "   "})

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "string_too_short"


def test_chat_rejects_message_over_maximum_length():
    response = client.post("/chat", json={"message": "x" * 10_001})

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "string_too_long"
