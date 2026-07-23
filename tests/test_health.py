from fastapi.testclient import TestClient

from app.public_app import create_public_app
from app.settings import Settings


def test_health_reports_application_and_database(tmp_path):
    app = create_public_app(Settings(database_path=tmp_path / "health.sqlite3"))

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
