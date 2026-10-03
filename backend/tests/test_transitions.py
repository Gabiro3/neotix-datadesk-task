from app.models import UserRole
from tests.conftest import add_episode, add_user, auth_header, future_deadline, login


def _setup(client, db):
    add_user(db, "client@example.com", "secret1", UserRole.client, "Client")
    add_user(db, "ops@example.com", "secret1", UserRole.operator, "Ops")
    client_token = login(client, "client@example.com", "secret1")
    ops_token = login(client, "ops@example.com", "secret1")
    created = client.post(
        "/requests",
        json={"task_name": "pick cup", "episodes_requested": 1, "deadline": future_deadline()},
        headers=auth_header(client_token),
    )
    return created.json()["id"], client_token, ops_token


def test_invalid_transition_rejected(client, db):
    request_id, _, ops_token = _setup(client, db)
    response = client.post(
        f"/requests/{request_id}/transition",
        json={"status": "delivered"},
        headers=auth_header(ops_token),
    )
    assert response.status_code == 409


def test_client_cannot_start_progress(client, db):
    request_id, client_token, _ = _setup(client, db)
    response = client.post(
        f"/requests/{request_id}/transition",
        json={"status": "in_progress"},
        headers=auth_header(client_token),
    )
    assert response.status_code == 409


def test_happy_path_and_rework(client, db):
    request_id, client_token, ops_token = _setup(client, db)
    add_episode(db, "EP-01000")
    started = client.post(
        f"/requests/{request_id}/transition",
        json={"status": "in_progress"},
        headers=auth_header(ops_token),
    )
    assert started.status_code == 200
    assigned = client.post(
        f"/requests/{request_id}/assignments",
        json={"episode_ids": ["EP-01000"]},
        headers=auth_header(ops_token),
    )
    assert assigned.status_code == 200
    delivered = client.post(
        f"/requests/{request_id}/transition",
        json={"status": "delivered"},
        headers=auth_header(ops_token),
    )
    assert delivered.status_code == 200
    ops_accept = client.post(
        f"/requests/{request_id}/transition",
        json={"status": "accepted"},
        headers=auth_header(ops_token),
    )
    assert ops_accept.status_code == 409
    rejected = client.post(
        f"/requests/{request_id}/transition",
        json={"status": "rejected"},
        headers=auth_header(client_token),
    )
    assert rejected.status_code == 200
    rework = client.post(
        f"/requests/{request_id}/transition",
        json={"status": "in_progress"},
        headers=auth_header(ops_token),
    )
    assert rework.status_code == 200
    events = client.get(f"/requests/{request_id}", headers=auth_header(ops_token)).json()["events"]
    assert [e["to_status"] for e in events] == [
        "submitted",
        "in_progress",
        "delivered",
        "rejected",
        "in_progress",
    ]
