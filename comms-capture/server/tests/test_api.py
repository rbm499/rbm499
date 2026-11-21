import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from commscap import wire
from commscap.api import create_app

from conftest import STRANGER, TONY, mk


@pytest.fixture
def client(env):
    return TestClient(create_app(env.pipeline, env.settings, tick_seconds=None))


def signed(env, body: bytes = b"", ts=None, device="dev-1", secret="secret-1"):
    ts = int(env.clock.t) if ts is None else ts
    return {"X-Device-Id": device, "X-Timestamp": str(ts), "X-Signature": wire.sign(secret, ts, device, body)}


def post(client, env, path, obj, **kw):
    body = json.dumps(obj).encode()
    return client.post(path, content=body, headers=signed(env, body, **kw))


def test_signed_ingest_roundtrip(client, env):
    env.screener.when("hello", category="job_business", confidence=0.9)
    m = mk("dev-1", "in", TONY, env.clock.ms(), "hello there")
    r = post(client, env, "/v1/ingest", {"schema": 1, "device_id": "dev-1", "messages": [m]})
    assert r.status_code == 200 and r.json()["accepted"] == [m["uid"]]
    assert env.store.get_message(m["uid"])["state"] == "filed"


def test_authentication_failures_are_401_and_store_nothing(client, env):
    m = mk("dev-1", "in", TONY, env.clock.ms(), "hello")
    body = json.dumps({"messages": [m]}).encode()
    good = signed(env, body)
    assert client.post("/v1/ingest", content=body, headers={**good, "X-Signature": "0" * 64}).status_code == 401
    assert client.post("/v1/ingest", content=body + b" ", headers=good).status_code == 401  # body tampered
    assert client.post("/v1/ingest", content=body, headers=signed(env, body, device="dev-2")).status_code == 401  # unknown device
    assert client.post("/v1/ingest", content=body, headers=signed(env, body, secret="wrong")).status_code == 401
    assert client.post("/v1/ingest", content=body, headers=signed(env, body, ts=int(env.clock.t) - 301)).status_code == 401  # replay window
    assert client.post("/v1/ingest", content=body).status_code == 401
    assert env.store.q("SELECT COUNT(*) AS n FROM messages")[0]["n"] == 0


def test_heartbeat_delivers_nudge_once_after_ack(client, env):
    env.screener.when("can you", category="job_business", confidence=0.9, needs_reply=True, reply_urgency="normal", topics=["schedule"])
    post(client, env, "/v1/ingest", {"messages": [mk("dev-1", "in", TONY, env.clock.ms(), "can you come tuesday?")]})
    env.clock.advance(minutes=125)
    env.pipeline.tick()
    r = post(client, env, "/v1/heartbeat", {"ts_ms": env.clock.ms(), "permissions": {}, "queue_depth": 0}).json()
    assert len(r["nudges"]) == 1 and r["nudges"][0]["address"] == TONY
    nid = r["nudges"][0]["id"]
    r2 = post(client, env, "/v1/heartbeat", {"ts_ms": env.clock.ms(), "nudge_acks": [nid]}).json()
    assert r2["nudges"] == []
    assert env.store.q("SELECT acked_ms FROM nudges WHERE id=?", [nid])[0]["acked_ms"] is not None


def test_policy_reconcile_and_mark(client, env):
    pol = client.get("/v1/policy", headers=signed(env)).json()
    assert pol["numbers"][TONY] == "client" and "business_terms" in pol and pol["version"]
    r = post(client, env, "/v1/reconcile", {"expected_uids": ["e" * 64]}).json()
    assert r["missing"] == ["e" * 64]
    assert post(client, env, "/v1/mark", {"address": STRANGER, "verdict": "private"}).json() == {"ok": True}
    assert STRANGER in client.get("/v1/policy", headers=signed(env)).json()["exclude_numbers"]


def test_media_upload_hash_checked(client, env):
    env.screener.when("pic", category="job_business", confidence=0.9)
    data = b"jpegbytes"
    sha = hashlib.sha256(data).hexdigest()
    m = mk("dev-1", "in", TONY, env.clock.ms(), "pic of ceiling", media=[{"mime": "image/jpeg", "size": 9, "sha256": sha}])
    post(client, env, "/v1/ingest", {"messages": [m]})
    bad = client.put(f"/v1/media/{m['uid']}/{sha}", content=b"wrong", headers=signed(env, b"wrong"))
    assert bad.status_code == 409
    ok = client.put(f"/v1/media/{m['uid']}/{sha}", content=data, headers=signed(env, data))
    assert ok.status_code == 200
    assert client.put(f"/v1/media/{'f' * 64}/{sha}", content=data, headers=signed(env, data)).status_code == 404


def test_office_page_requires_token_and_works(client, env):
    env.screener.when("start", category="job_business", confidence=0.9, needs_reply=True, reply_urgency="normal", topics=["schedule"])
    from conftest import LUIS
    post(client, env, "/v1/ingest", {"messages": [mk("dev-1", "in", LUIS, env.clock.ms(), "can we move the start?")]})
    assert client.get("/ui").status_code == 200 and "text/html" in client.get("/ui").headers["content-type"]
    assert client.get("/ui/api/state").status_code == 401
    assert client.get("/ui/api/state", headers={"X-UI-Token": "nope"}).status_code == 401
    st = client.get("/ui/api/state", headers={"X-UI-Token": "ui-token"}).json()
    assert len(st["queue"]) == 1 and len(st["sla"]) == 1 and len(st["jobs"]) == 7
    r = client.post("/ui/api/assign", json={"address": LUIS, "job_no": "26-6527"}, headers={"X-UI-Token": "ui-token"})
    assert r.json() == {"ok": True, "filed": 1}
    assert client.get("/ui/api/state", headers={"X-UI-Token": "ui-token"}).json()["queue"] == []


def test_ui_disabled_without_token(env):
    env.settings.ui_token = None
    c = TestClient(create_app(env.pipeline, env.settings, tick_seconds=None))
    assert c.get("/ui/api/state").status_code == 403


def test_healthz_is_open_and_minimal(client):
    assert client.get("/healthz").json()["ok"] is True
