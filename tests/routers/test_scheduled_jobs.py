from collections.abc import Callable

from fastapi.testclient import TestClient

from app.container import container
from app.main import app

client = TestClient(app)


def test_trigger_job_requires_authentication():
    assert client.post("/api/scheduled-jobs/trigger?job_name=trade_execution").status_code == 401


def test_trigger_job_rejects_regular_user(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()

    response = client.post(
        "/api/scheduled-jobs/trigger?job_name=trade_execution",
        headers=auth_headers(user_id),
    )

    assert response.status_code == 403


def test_trigger_job_triggers_registered_job(service_auth_headers: dict[str, str]):
    response = client.post(
        "/api/scheduled-jobs/trigger?job_name=trade_execution",
        headers=service_auth_headers,
    )

    assert response.status_code == 204
    assert response.content == b""


def test_trigger_job_unknown_job_returns_404(service_auth_headers: dict[str, str]):
    response = client.post(
        "/api/scheduled-jobs/trigger?job_name=nonexistent",
        headers=service_auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Job with provided name not found"}


def test_trigger_job_without_job_name_returns_422(service_auth_headers: dict[str, str]):
    response = client.post("/api/scheduled-jobs/trigger", headers=service_auth_headers)

    assert response.status_code == 422
