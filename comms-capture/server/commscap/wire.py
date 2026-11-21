"""Wire-level helpers shared with the phone: request signing and stable message ids.

Signature = hex HMAC-SHA256(secret, f"{ts}.{device_id}.{sha256_hex(body_bytes)}")
Message uid = sha256_hex(f"{device_id}|{direction}|{address}|{ts_ms}|{sha256_hex(body_utf8)}|{media_count}")
where address is the E.164 number when the address is a phone number, else the trimmed raw address.
Both are tested against shared/vectors/wire_vectors.json (the phone must produce identical values).
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Optional

from .phone import classify_address

MAX_CLOCK_SKEW_SECONDS = 300


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sign(secret: str, ts: int, device_id: str, body: bytes) -> str:
    msg = f"{ts}.{device_id}.{sha256_hex(body)}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def verify(secret: str, ts: int, device_id: str, body: bytes, signature: str, now: int,
           skew: int = MAX_CLOCK_SKEW_SECONDS) -> bool:
    if abs(now - int(ts)) > skew:
        return False
    expected = sign(secret, ts, device_id, body)
    return hmac.compare_digest(expected, (signature or "").lower())


def canonical_address(raw: str) -> str:
    kind, e164 = classify_address(raw)
    return e164 if e164 else (raw or "").strip()


def msg_uid(device_id: str, direction: str, address_raw: str, ts_ms: int, body: str,
            media_count: int) -> str:
    addr = canonical_address(address_raw)
    body_hash = sha256_hex((body or "").encode("utf-8"))
    return sha256_hex(f"{device_id}|{direction}|{addr}|{ts_ms}|{body_hash}|{media_count}".encode("utf-8"))
