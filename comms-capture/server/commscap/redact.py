"""Deterministic redaction and automated-message detection.

Runs on the phone first and again on the server, before anything is stored or sent to an AI.
Mirrored in android/core Redact.kt; tested against shared/vectors/redact_vectors.json.

Site access codes ("gate code is 4821") are business information and are NOT redacted.
"""
from __future__ import annotations

import re
from typing import List, Tuple

_SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
_CARD_CANDIDATE = re.compile(r"(?<!\d)(?:\d[ \-]?){12,18}\d(?!\d)")
_SECRET = re.compile(r"(?i)\b(password|passcode|passwd|pin)\b(\s*(?:is|:|=)\s*)(\S+)")
_ROUTING = re.compile(r"(?i)\b(routing)\b([^\d]{0,15})(\d{9})(?!\d)")
_ACCOUNT = re.compile(r"(?i)\b(account|acct)\b([^\d]{0,15})(\d{6,17})(?!\d)")

# Automated one-time-code messages. Deliberately phrase-based: a bare "code" is not enough.
_OTP_KEY = (
    r"(?:(?:verification|security|confirmation|login|log-in|sign-in|authentication|one[- ]time)"
    r"\s+(?:code|passcode|pin)|otp|2fa)"
)
_OTP_A = re.compile(r"(?i)\b" + _OTP_KEY + r"\b[^\d]{0,30}(?<!\d)\d{4,8}(?!\d)")
_OTP_B = re.compile(r"(?i)\byour\s+(?:\w+\s+){0,2}code\s+(?:is|:)\s*\d{4,8}(?!\d)")
_OTP_C = re.compile(r"(?i)(?<!\d)\d{4,8}(?!\d)[^\d]{0,30}\b" + _OTP_KEY + r"\b")


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def is_otp(text: str) -> bool:
    t = text or ""
    return bool(_OTP_A.search(t) or _OTP_B.search(t) or _OTP_C.search(t))


def redact(text: str) -> Tuple[str, List[str]]:
    """Return (redacted_text, sorted unique tags that fired)."""
    tags: List[str] = []
    out = text or ""

    def sub_ssn(_m: "re.Match[str]") -> str:
        tags.append("ssn")
        return "[REDACTED:ssn]"

    out = _SSN.sub(sub_ssn, out)

    def sub_card(m: "re.Match[str]") -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            tags.append("card")
            return "[REDACTED:card]"
        return m.group(0)

    out = _CARD_CANDIDATE.sub(sub_card, out)

    def sub_routing(m: "re.Match[str]") -> str:
        tags.append("routing")
        return m.group(1) + m.group(2) + "[REDACTED:routing]"

    out = _ROUTING.sub(sub_routing, out)

    def sub_account(m: "re.Match[str]") -> str:
        tags.append("account")
        return m.group(1) + m.group(2) + "[REDACTED:account]"

    out = _ACCOUNT.sub(sub_account, out)

    def sub_secret(m: "re.Match[str]") -> str:
        tags.append("secret")
        return m.group(1) + m.group(2) + "[REDACTED:secret]"

    out = _SECRET.sub(sub_secret, out)
    return out, sorted(set(tags))
