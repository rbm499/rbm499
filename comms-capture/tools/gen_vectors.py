#!/usr/bin/env python3
"""Generate the shared cross-language test vectors from the Python reference implementation.

    python tools/gen_vectors.py          # rewrites shared/vectors/*.json

The vectors are the specification the Android core must match. Review the diff of the generated
files whenever behaviour is changed on purpose. All numbers are fictional (206-555-01xx).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

from commscap import gate, phone, redact, wire  # noqa: E402

OUT = ROOT / "shared" / "vectors"
OUT.mkdir(parents=True, exist_ok=True)


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- phone
PHONE_INPUTS = [
    "+12065550101", "(206) 555-0101", "206.555.0101", "206-555-0101", "1 206 555 0101", "12065550101",
    "+1 (206) 555-0101", "+442071234567", "227898", "55555", "CHASE", "Chase-Alerts", "john@example.com",
    "", "   ", "abc123", "123456789012", "+123", "5551234",
]
dump("phone_vectors.json", {
    "classify": [{"input": i, "kind": phone.classify_address(i)[0], "e164": phone.classify_address(i)[1]}
                 for i in PHONE_INPUTS],
    "extract": [
        {"input": t, "numbers": phone.extract_phones(t)} for t in [
            "cell (206) 555-0101; office (206) 555-0102",
            "O (206) 555-0103, M (206) 555-0104",
            "Alex (206) 555-0105; main (206) 555-0106; Dan (206) 555-0107",
            "Sam (206) 555-0108; Manni: none on file",
            "(206) 555-0109 (L&I notice lists 206-555-0109)",
            "", "no numbers here 12345",
        ]
    ],
})

# --------------------------------------------------------------- redact
REDACT_INPUTS = [
    "my card is 4111 1111 1111 1111 exp 12/27",
    "card 4111-1111-1111-1112 typo",
    "ssn 123-45-6789 thanks",
    "password is hunter2 ok",
    "PIN: 4455",
    "pin the location on the map",
    "routing number 123456789 and account number 98765432",
    "acct # 12345678",
    "gate code is 4821",
    "call me at 206-555-0101",
    "invoice 26-4708 total $3,965.93",
    "nothing sensitive here",
    "",
]
OTP_INPUTS = [
    "Your verification code is 483920",
    "483920 is your verification code",
    "Your Acme login code is: 118822",
    "OTP 556677 do not share",
    "gate code is 4821",
    "the code is 4821",
    "verification of the site is 2026",
    "Your one-time passcode: 99887766",
    "Please confirm the 26-4708 start date",
    "",
]
dump("redact_vectors.json", {
    "redact": [{"input": i, "output": redact.redact(i)[0], "tags": redact.redact(i)[1]} for i in REDACT_INPUTS],
    "is_otp": [{"input": i, "otp": redact.is_otp(i)} for i in OTP_INPUTS],
})

# ----------------------------------------------------------------- gate
POLICY = gate.Policy(
    version="vector-policy-1",
    numbers={"+12065550101": "client", "+12065550102": "crew", "+12065550103": "vendor",
             "+12065550104": "agency"},
    exclude_numbers=["+12065550199"],
    provisional_business=["+12065550150"],
    client_labels=["AAAD Clients"],
)
C = lambda **k: k  # noqa: E731
GATE_CASES = [
    C(address="+12065550101", body="ok thanks"),
    C(address="(206) 555-0101", body="can you come tuesday"),
    C(address="206-555-0102", body="lol dinner after?"),
    C(address="+12065550103", body="results are in"),
    C(address="+12065550104", body="inspector will be on site"),
    C(address="+12065550199", body="I need a bid for 4708 8th Ave NE"),
    C(address="+12065550150", body="ok sounds good"),
    C(address="CHASE", body="Your invoice is ready"),
    C(address="227898", body="Your verification code is 483920"),
    C(address="john@example.com", body="photo attached", has_media=True),
    C(address="+12065550177", body="Your verification code is 483920"),
    C(address="+12065550177", body="Hi, I need a bid for asbestos testing at my house"),
    C(address="+12065550177", body="Can you give an estimate for 4708 8th Ave NE?"),
    C(address="+12065550177", body="happy birthday! love you"),
    C(address="+12065550177", body="ok"),
    C(address="+12065550177", body="", has_media=True),
    C(address="+12065550177", body="here you go", has_media=True),
    C(address="+12065550177", body="need a bid for 26-4708", contact_saved=True),
    C(address="+12065550177", body="need a bid for the house", contact_saved=True),
    C(address="+12065550177", body="dinner at 6?", contact_saved=True),
    C(address="+12065550177", body="hello", contact_labels=["AAAD Clients"]),
    C(address="+12065550177", body="gate code is 4821 for 26-4708"),
    C(address="+12065550177", body="the code is 4821"),
    C(address="+12065550177", body="I forbid it"),
    C(address="+12065550177", body="Quote: $4,500"),
    C(address="+12065550177", body="L&I inspector is here"),
    C(address="+12065550177", body="2026-11-21 dinner?"),
    C(address="+12065550177", body="call me at 206-555-0105"),
    C(address="+12065550177", body="we are at 6527 32nd Ave NW"),
    C(address="+12065550177", body="I owe you 200 bucks"),
    C(address="+442071234567", body="hello"),
    C(address="+12065550177", body=""),
    C(address="55555", body="bid on the job"),
    C(address="+12065550177", body="We need an asbestos survey"),
    C(address="+12065550177", body="mold on the bathroom ceiling"),
    C(address="+12065550177", body="moldy bread again"),
    C(address="+12065550177", body="BID"),
    C(address="+12065550101", body="", has_media=True),
    C(address="+12065550177", body="123 Main St is the place"),
    C(address="+12065550177", body="the 26-4708 job", contact_saved=True, contact_labels=["Family"]),
]
cases = []
for c in GATE_CASES:
    d = gate.decide(POLICY, c["address"], c.get("body", ""), c.get("has_media", False),
                    c.get("contact_saved", False), c.get("contact_labels", []))
    cases.append({
        "address": c["address"], "body": c.get("body", ""), "has_media": c.get("has_media", False),
        "contact_saved": c.get("contact_saved", False), "contact_labels": c.get("contact_labels", []),
        "decision": d.decision, "reason": d.reason, "kind": d.kind, "e164": d.e164,
    })
dump("gate_vectors.json", {"policy": POLICY.to_dict(), "cases": cases})

# ----------------------------------------------------------------- wire
SECRET = "test-secret-0001"
body = b'{"schema":1,"messages":[]}'
wire_v = {
    "secret": SECRET,
    "signatures": [
        {"ts": 1700000000, "device_id": "dev-1", "body": body.decode(),
         "body_sha256": wire.sha256_hex(body), "signature": wire.sign(SECRET, 1700000000, "dev-1", body)},
        {"ts": 1789999999, "device_id": "michael-phone-1", "body": "",
         "body_sha256": wire.sha256_hex(b""), "signature": wire.sign(SECRET, 1789999999, "michael-phone-1", b"")},
    ],
    "uids": [
        {"device_id": "dev-1", "direction": "in", "address": "(206) 555-0101", "ts_ms": 1789999999123,
         "body": "ok thanks", "media_count": 0,
         "uid": wire.msg_uid("dev-1", "in", "(206) 555-0101", 1789999999123, "ok thanks", 0)},
        {"device_id": "dev-1", "direction": "out", "address": "+12065550101", "ts_ms": 1789999999123,
         "body": "On my way — see you at 9", "media_count": 2,
         "uid": wire.msg_uid("dev-1", "out", "+12065550101", 1789999999123, "On my way — see you at 9", 2)},
        {"device_id": "dev-1", "direction": "in", "address": "CHASE", "ts_ms": 1, "body": "",
         "media_count": 0, "uid": wire.msg_uid("dev-1", "in", "CHASE", 1, "", 0)},
    ],
}
dump("wire_vectors.json", wire_v)
print("wrote vectors to", OUT)
for c in cases:
    print(f"{c['decision']:5} {c['reason']:30} {c['address']:16} {c['body'][:50]!r}")
