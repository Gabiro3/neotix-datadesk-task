from app.models import EpisodeQuality, UserRole
from tests.conftest import add_episode, add_user, auth_header, future_deadline, login


def test_cannot_assign_bad_or_taken_episode(client, db):
    add_user(db, "client@example.com", "secret1", UserRole.client, "Client")
    add_user(db, "ops@example.com", "secret1", UserRole.operator, "Ops")
    client_token = login(client, "client@example.com", "secret1")
    ops_token = login(client, "ops@example.com", "secret1")
    first = client.post(
        "/requests",
        json={"task_name": "pick cup", "episodes_requested": 2, "deadline": future_deadline()},
        headers=auth_header(client_token),
    ).json()["id"]
    second = client.post(
        "/requests",
        json={"task_name": "pick cup", "episodes_requested": 1, "deadline": future_deadline()},
        headers=auth_header(client_token),
    ).json()["id"]
    add_episode(db, "EP-GOOD", EpisodeQuality.good)
    add_episode(db, "EP-BAD", EpisodeQuality.bad)
    bad = client.post(
        f"/requests/{first}/assignments",
        json={"episode_ids": ["EP-BAD"]},
        headers=auth_header(ops_token),
    )
    assert bad.status_code == 409
    ok = client.post(
        f"/requests/{first}/assignments",
        json={"episode_ids": ["EP-GOOD"]},
        headers=auth_header(ops_token),
    )
    assert ok.status_code == 200
    taken = client.post(
        f"/requests/{second}/assignments",
        json={"episode_ids": ["EP-GOOD"]},
        headers=auth_header(ops_token),
    )
    assert taken.status_code == 409
    early = client.post(
        f"/requests/{first}/transition",
        json={"status": "in_progress"},
        headers=auth_header(ops_token),
    )
    assert early.status_code == 200
    blocked = client.post(
        f"/requests/{first}/transition",
        json={"status": "delivered"},
        headers=auth_header(ops_token),
    )
    assert blocked.status_code == 409
    assert "Need 2" in blocked.json()["detail"]
