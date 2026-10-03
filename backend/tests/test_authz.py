from app.models import UserRole
from tests.conftest import add_user, auth_header, future_deadline, login


def test_unauthenticated_is_rejected(client):
    response = client.get("/requests")
    assert response.status_code == 401


def test_client_cannot_list_other_requests(client, db):
    add_user(db, "a@example.com", "secret1", UserRole.client, "A")
    add_user(db, "b@example.com", "secret1", UserRole.client, "B")
    token_a = login(client, "a@example.com", "secret1")
    token_b = login(client, "b@example.com", "secret1")
    created = client.post(
        "/requests",
        json={"task_name": "pick cup", "episodes_requested": 1, "deadline": future_deadline()},
        headers=auth_header(token_a),
    )
    assert created.status_code == 201
    request_id = created.json()["id"]
    listed = client.get("/requests", headers=auth_header(token_b))
    assert listed.status_code == 200
    assert listed.json() == []
    hidden = client.get(f"/requests/{request_id}", headers=auth_header(token_b))
    assert hidden.status_code == 404


def test_client_cannot_assign_or_import(client, db):
    add_user(db, "c@example.com", "secret1", UserRole.client, "C")
    token = login(client, "c@example.com", "secret1")
    created = client.post(
        "/requests",
        json={"task_name": "pick cup", "episodes_requested": 1, "deadline": future_deadline()},
        headers=auth_header(token),
    )
    request_id = created.json()["id"]
    assign = client.post(
        f"/requests/{request_id}/assignments",
        json={"episode_ids": ["EP-00001"]},
        headers=auth_header(token),
    )
    assert assign.status_code == 403
    imported = client.post("/episodes/import", files={"file": ("x.csv", b"episode_id\n", "text/csv")}, headers=auth_header(token))
    assert imported.status_code == 403


def test_operator_cannot_admin_users(client, db):
    add_user(db, "ops@example.com", "secret1", UserRole.operator, "Ops")
    token = login(client, "ops@example.com", "secret1")
    response = client.get("/users", headers=auth_header(token))
    assert response.status_code == 403


def test_admin_created_user_must_change_temporary_password(client, db):
    add_user(db, "admin@example.com", "secret1", UserRole.admin, "Admin")
    admin_token = login(client, "admin@example.com", "secret1")
    created = client.post(
        "/users",
        json={
            "email": "new.client@example.com",
            "password": "temporary123",
            "name": "New Client",
            "role": "client",
            "organisation": "Example Robotics",
        },
        headers=auth_header(admin_token),
    )
    assert created.status_code == 201
    assert created.json()["must_change_password"] is True

    temporary_token = login(client, "new.client@example.com", "temporary123")
    blocked = client.get("/requests", headers=auth_header(temporary_token))
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Password change required"

    changed = client.post(
        "/auth/change-password",
        json={"current_password": "temporary123", "new_password": "permanent123"},
        headers=auth_header(temporary_token),
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False
    assert client.get("/requests", headers=auth_header(temporary_token)).status_code == 200
