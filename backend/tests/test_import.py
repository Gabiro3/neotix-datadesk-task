from io import StringIO

from app.models import Episode
from app.services.import_episodes import import_episodes

CSV = """episode_id,robot_id,task_name,recorded_at,duration_seconds,operator_name,quality
EP-00100,arm-01,pick cup,2026-08-01T10:00:00,30,Diane,good
EP-00100,arm-01,pick cup,2026-08-01T10:00:00,30,Diane,good
EP-00101,arm-99,pick cup,2026-08-01T10:00:00,30,Diane,good
,arm-01,pick cup,2026-08-01T10:00:00,30,Diane,good
EP-00102,arm-01,pick cup,not a date,30,Diane,good
EP-00103,arm-01,pick cup,2026-08-01T10:00:00,-5,Diane,good
EP-00104,arm-01,pick cup,2026-08-01T10:00:00,30,Diane,excellent
EP-00009,arm-01,stack blocks,2026-08-13T08:55:00,66,Jeanne,Good
 ep-00010, arm-02,  Pick Cup ,14/08/2026 09:15,45.5,Diane,USABLE
"""


def test_import_skips_bad_rows_and_is_idempotent(db):
    first = import_episodes(db, StringIO(CSV))
    assert first.imported == 3
    assert first.updated == 0
    reasons = {s.reason.split(" (")[0] for s in first.skips}
    assert "duplicate in file" in reasons
    assert "unknown or missing robot_id" in reasons
    assert "missing or invalid episode_id" in reasons
    assert "invalid recorded_at" in reasons
    assert "invalid duration_seconds" in reasons
    assert "invalid quality" in reasons

    second = import_episodes(db, StringIO(CSV))
    assert second.imported == 0
    assert second.updated == 0
    assert db.query(Episode).count() == 3
    ep = db.query(Episode).filter_by(episode_id="EP-00010").one()
    assert ep.task_name == "pick cup"
    assert ep.quality.value == "usable"
    assert ep.duration_seconds == 46
