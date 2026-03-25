from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "UP"

def test_create_and_get_item():
    payload = {"id": 1, "name": "Book", "price": 100}
    r1 = client.post("/items", json=payload)
    assert r1.status_code == 200
    assert r1.json()["price_with_tax"] == 118.0

    r2 = client.get("/items/1")
    assert r2.status_code == 200
    assert r2.json()["name"] == "Book"
