from fastapi.testclient import TestClient

from app.admin_app import create_admin_app
from app.public_app import create_public_app


def test_rank_change_swaps_existing_menu(database_path):
    admin = TestClient(create_admin_app(database_path))
    response = admin.patch("/api/admin/menus/menu-c", json={"rank": 7})
    assert response.status_code == 200
    state = admin.get("/api/admin/state").json()
    ranks = {menu["id"]: menu["rank"] for menu in state["menus"]}
    assert ranks["menu-c"] == 7
    assert ranks["menu-b"] == 19


def test_answer_can_be_corrected(database_path):
    public = TestClient(create_public_app(database_path))
    admin = TestClient(create_admin_app(database_path))
    public.post("/api/guesses", json={"menu_ids": ["menu-b"]})
    assert admin.patch("/api/admin/menus/menu-b", json={"answered": False}).status_code == 200
    menu = public.get("/api/state").json()["categories"][0]["menus"][1]
    assert menu["answered"] is False
    assert "rank" not in menu


def test_admin_routes_do_not_exist_on_public_app(database_path):
    public = TestClient(create_public_app(database_path))
    assert public.get("/api/admin/state").status_code == 404
