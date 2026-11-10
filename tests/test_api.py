import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient

from devrescue import api, inference
from devrescue.db import make_session_factory


@pytest.fixture()
def client(monkeypatch):
    factory = make_session_factory("sqlite://")  # in-memory
    monkeypatch.setattr(api, "_factory", factory)
    monkeypatch.setattr(inference, "diagnose", lambda kind, text, **k: "ROOT CAUSE: x")
    return TestClient(api.app)


def test_flow(client):
    r = client.post("/diagnose", json={"kind": "log", "text": "boom"})
    assert r.status_code == 200
    iid = r.json()["incident_id"]
    assert client.post(f"/incidents/{iid}/resolve", json={"root_cause_correct": True, "fix_minutes": 24}).status_code == 200
    m = client.get("/metrics").json()
    assert m["resolved_incidents"] == 1 and m["root_cause_accuracy"] == 1.0


def test_pairs_from_feedback(client, tmp_path):
    from devrescue.data import export_from_db

    for resp, rating in [("good", 5), ("bad", 1)]:
        client.post("/feedback", json={"prompt": "p", "response": resp, "rating": rating})
    s = api._factory()
    assert export_from_db(s, str(tmp_path / "o.jsonl")) == 1
