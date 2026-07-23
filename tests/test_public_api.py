from fastapi.testclient import TestClient

from app.public_app import create_public_app


def test_health(database_path):
    client = TestClient(create_public_app(database_path))
    assert client.get("/health").json() == {"status": "ok", "database": "ok"}


def test_unanswered_ranks_are_hidden(database_path):
    client = TestClient(create_public_app(database_path))
    payload = client.get("/api/state").json()
    menus = payload["categories"][0]["menus"]
    assert all("rank" not in menu for menu in menus)


def test_guess_reveals_rank_and_updates_summary(database_path):
    client = TestClient(create_public_app(database_path))
    response = client.post("/api/guesses", json={"menu_ids": ["menu-b", "menu-c"]})
    assert response.status_code == 200
    body = response.json()
    assert [result["rank"] for result in body["results"]] == [7, 19]
    assert body["summary"]["hitRanks"] == [7]
    state = client.get("/api/state").json()
    answered = {menu["id"]: menu for menu in state["categories"][0]["menus"]}
    assert answered["menu-b"]["rank"] == 7
    assert answered["menu-c"]["rank"] == 19
    assert "rank" not in answered["menu-a"]


def test_guess_is_idempotent(database_path):
    client = TestClient(create_public_app(database_path))
    first = client.post("/api/guesses", json={"menu_ids": ["menu-b"]}).json()
    second = client.post("/api/guesses", json={"menu_ids": ["menu-b"]}).json()
    assert first["results"][0]["newlyAnswered"] is True
    assert second["results"][0]["newlyAnswered"] is False
    assert second["summary"]["answeredCount"] == 1


def test_invalid_batch_does_not_partially_write(database_path):
    client = TestClient(create_public_app(database_path))
    response = client.post("/api/guesses", json={"menu_ids": ["menu-b", "missing"]})
    assert response.status_code == 404
    assert client.get("/api/state").json()["summary"]["answeredCount"] == 0
