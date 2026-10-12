
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Library API is running"
    }

def test_book_not_found():
    response = client.get("/books/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Book not found"
    }