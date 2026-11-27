"""Address classification and E.164 normalisation.

This module is mirrored on the phone (android/core PhoneNumber.kt). Both are tested
against shared/vectors/phone_vectors.json - change one, regenerate vectors, fix the other.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

_LETTER = re.compile(r"[A-Za-z]")
# North-American numbers inside free text (register phone fields hold several labelled numbers).
_PHONE_IN_TEXT = re.compile(
    r"(?<!\d)(?:\+?1[\s.\-]*)?\(?([2-9]\d{2})\)?[\s.\-]*([2-9]\d{2})[\s.\-]*(\d{4})(?!\d)"
)

KIND_PHONE = "phone"
KIND_SHORTCODE = "shortcode"
KIND_ALPHA = "alpha"
KIND_EMAIL = "email"
KIND_UNKNOWN = "unknown"


def classify_address(raw: Optional[str]) -> Tuple[str, Optional[str]]:
    """Return (kind, e164). e164 is only set when kind == 'phone'."""
    s = (raw or "").strip()
    if not s:
        return KIND_UNKNOWN, None
    if "@" in s:
        return KIND_EMAIL, None
    if _LETTER.search(s):
        return KIND_ALPHA, None
    digits = re.sub(r"\D", "", s)
    if not digits:
        return KIND_UNKNOWN, None
    if s.startswith("+"):
        if 8 <= len(digits) <= 15:
            return KIND_PHONE, "+" + digits
        return KIND_UNKNOWN, None
    if len(digits) == 10:
        return KIND_PHONE, "+1" + digits
    if len(digits) == 11 and digits[0] == "1":
        return KIND_PHONE, "+" + digits
    if 3 <= len(digits) <= 8:
        return KIND_SHORTCODE, None
    return KIND_UNKNOWN, None


def to_e164(raw: Optional[str]) -> Optional[str]:
    kind, e164 = classify_address(raw)
    return e164 if kind == KIND_PHONE else None


def extract_phones(text: Optional[str]) -> List[str]:
    """All North-American phone numbers found in free text, normalised, order kept, de-duplicated."""
    out: List[str] = []
    for m in _PHONE_IN_TEXT.finditer(text or ""):
        n = "+1" + m.group(1) + m.group(2) + m.group(3)
        if n not in out:
            out.append(n)
    return out


def mask(e164: Optional[str]) -> str:
    """Display form that is safe for alerts and digests: +1206•••0101."""
    if not e164:
        return "(unknown)"
    if len(e164) <= 6:
        return e164
    return e164[:5] + "•••" + e164[-4:]
