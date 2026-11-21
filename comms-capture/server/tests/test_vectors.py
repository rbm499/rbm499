"""The shared vectors are the contract with the phone. The Python reference must pass them exactly
(and the Android core module passes the same files)."""
import json
from pathlib import Path

import pytest

from commscap import gate, phone, redact, wire

V = Path(__file__).resolve().parents[2] / "shared" / "vectors"


def load(name):
    return json.loads((V / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("c", load("phone_vectors.json")["classify"], ids=lambda c: repr(c["input"]))
def test_phone_classify(c):
    assert list(phone.classify_address(c["input"])) == [c["kind"], c["e164"]]


@pytest.mark.parametrize("c", load("phone_vectors.json")["extract"], ids=lambda c: repr(c["input"])[:30])
def test_phone_extract(c):
    assert phone.extract_phones(c["input"]) == c["numbers"]


@pytest.mark.parametrize("c", load("redact_vectors.json")["redact"], ids=lambda c: repr(c["input"])[:30])
def test_redact(c):
    out, tags = redact.redact(c["input"])
    assert (out, tags) == (c["output"], c["tags"])


@pytest.mark.parametrize("c", load("redact_vectors.json")["is_otp"], ids=lambda c: repr(c["input"])[:30])
def test_otp(c):
    assert redact.is_otp(c["input"]) is c["otp"]


GATE = load("gate_vectors.json")


@pytest.mark.parametrize("c", GATE["cases"], ids=lambda c: f"{c['address']}|{c['body'][:25]}")
def test_gate(c):
    pol = gate.Policy.from_dict(GATE["policy"])
    d = gate.decide(pol, c["address"], c["body"], c["has_media"], c["contact_saved"], c["contact_labels"])
    assert (d.decision, d.reason, d.kind, d.e164) == (c["decision"], c["reason"], c["kind"], c["e164"])


@pytest.mark.parametrize("c", GATE["cases_keyword"], ids=lambda c: f"kw|{c['address']}|{c['body'][:25]}")
def test_gate_keyword_mode(c):
    pol = gate.Policy.from_dict(GATE["policy_keyword"])
    d = gate.decide(pol, c["address"], c["body"], c["has_media"], c["contact_saved"], c["contact_labels"])
    assert (d.decision, d.reason, d.kind, d.e164) == (c["decision"], c["reason"], c["kind"], c["e164"])


W = load("wire_vectors.json")


@pytest.mark.parametrize("s", W["signatures"])
def test_signatures(s):
    body = s["body"].encode()
    assert wire.sha256_hex(body) == s["body_sha256"]
    assert wire.sign(W["secret"], s["ts"], s["device_id"], body) == s["signature"]
    assert wire.verify(W["secret"], s["ts"], s["device_id"], body, s["signature"], now=s["ts"] + 10)
    assert not wire.verify(W["secret"], s["ts"], s["device_id"], body, s["signature"], now=s["ts"] + 301)
    assert not wire.verify(W["secret"], s["ts"], s["device_id"], body + b" ", s["signature"], now=s["ts"])


@pytest.mark.parametrize("u", W["uids"])
def test_uids(u):
    assert wire.msg_uid(u["device_id"], u["direction"], u["address"], u["ts_ms"], u["body"], u["media_count"]) == u["uid"]
