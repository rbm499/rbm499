"""The capture gate: decides, per message and BEFORE any upload, what may leave the phone.

The same rules run on the phone (android/core Gate.kt) and again on the server (defence in
depth: the server never trusts the phone's gate). Both are tested against
shared/vectors/gate_vectors.json.

Decisions
  send   - upload now
  drop   - never leaves the phone (only a content-free counter is kept)
  defer  - keep on the phone up to policy.defer_hours; sent later if the same thread turns
           out to be business (so one keyword hit rescues the earlier "ok" / "yes" replies)
  hold   - media with no text from an unknown number; kept on the phone, not uploaded
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .phone import KIND_PHONE, classify_address
from .redact import is_otp

RULE_VERSION = "gate-1"

SEND, DROP, DEFER, HOLD = "send", "drop", "defer", "hold"

# Whole-word / phrase matches. Kept specific on purpose: every hit on an UNKNOWN number lets that
# message be read by the AI screen, so a vague word ("house", "schedule") would widen exposure.
DEFAULT_BUSINESS_TERMS: List[str] = [
    "bid", "estimate", "quote", "proposal", "invoice", "change order", "scope of work", "work order",
    "asbestos", "ahera", "abatement", "remediation", "mold", "lead paint", "vermiculite",
    "popcorn ceiling", "survey", "inspection", "clearance", "test results", "lab results",
    "pscaa", "l&i", "permit", "demolition", "contractor", "sq ft", "square feet",
]
JOB_NUMBER_PATTERN = r"(?<![\d-])\d{2}-\d{3,5}(?![\d-])"
ADDRESS_PATTERN = (
    r"(?i)\b\d{3,5}\s+(?:[NSEW]{1,2}\s+)?(?:\d{1,3}(?:st|nd|rd|th)|[A-Za-z]+)\s+"
    r"(?:ave|avenue|st|street|rd|road|blvd|way|ln|lane|dr|drive|ct|court|pl|place|pkwy|hwy)\b"
)

ROLE_CLIENT, ROLE_CREW, ROLE_VENDOR, ROLE_AGENCY = "client", "crew", "vendor", "agency"


@dataclass
class Policy:
    version: str = "default-0"
    numbers: Dict[str, str] = field(default_factory=dict)  # e164 -> role
    exclude_numbers: List[str] = field(default_factory=list)
    provisional_business: List[str] = field(default_factory=list)
    client_labels: List[str] = field(default_factory=list)
    drop_sender_kinds: List[str] = field(default_factory=lambda: ["alpha", "shortcode", "email"])
    business_terms: List[str] = field(default_factory=lambda: list(DEFAULT_BUSINESS_TERMS))
    job_number_pattern: str = JOB_NUMBER_PATTERN
    address_pattern: str = ADDRESS_PATTERN
    defer_hours: int = 24
    hold_media_days: int = 7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "numbers": dict(self.numbers),
            "exclude_numbers": list(self.exclude_numbers),
            "provisional_business": list(self.provisional_business),
            "client_labels": list(self.client_labels),
            "drop_sender_kinds": list(self.drop_sender_kinds),
            "business_terms": list(self.business_terms),
            "job_number_pattern": self.job_number_pattern,
            "address_pattern": self.address_pattern,
            "defer_hours": self.defer_hours,
            "hold_media_days": self.hold_media_days,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Policy":
        base = cls()
        for k, v in d.items():
            if hasattr(base, k):
                setattr(base, k, v)
        return base


@dataclass
class Decision:
    decision: str
    reason: str
    kind: str
    e164: Optional[str]


def _term_regex(terms: Sequence[str]) -> Optional["re.Pattern[str]"]:
    if not terms:
        return None
    parts = [re.escape(t.strip()).replace(r"\ ", r"\s+") for t in terms if t.strip()]
    return re.compile(r"(?i)(?<![A-Za-z0-9])(?:" + "|".join(parts) + r")(?![A-Za-z0-9])")


def business_signals(policy: Policy, body: str) -> List[str]:
    """Names of the signals present in the text: 'term', 'address', 'job_number'."""
    out: List[str] = []
    rx = _term_regex(policy.business_terms)
    if rx and rx.search(body):
        out.append("term")
    if policy.address_pattern and re.search(policy.address_pattern, body):
        out.append("address")
    if policy.job_number_pattern and re.search(policy.job_number_pattern, body):
        out.append("job_number")
    return out


def decide(
    policy: Policy,
    address_raw: str,
    body: str,
    has_media: bool = False,
    contact_saved: bool = False,
    contact_labels: Sequence[str] = (),
) -> Decision:
    kind, e164 = classify_address(address_raw)
    body = body or ""
    addr = e164 or ""

    if addr and addr in set(policy.exclude_numbers):
        return Decision(DROP, "explicit_exclude", kind, e164)
    if addr and addr in policy.numbers:
        return Decision(SEND, "allow_" + policy.numbers[addr], kind, e164)
    if addr and addr in set(policy.provisional_business):
        return Decision(SEND, "thread_business", kind, e164)
    if set(contact_labels) & set(policy.client_labels):
        return Decision(SEND, "label_client", kind, e164)
    if kind in policy.drop_sender_kinds:
        return Decision(DROP, "automated_sender", kind, e164)
    if is_otp(body):
        return Decision(DROP, "otp_code", kind, e164)

    signals = business_signals(policy, body)
    if contact_saved:
        if "job_number" in signals:
            return Decision(SEND, "saved_contact_job_number", kind, e164)
        return Decision(DROP, "saved_contact_not_allowlisted", kind, e164)

    # Unknown, unsaved number.
    if signals:
        return Decision(SEND, "unknown_business_signal", kind, e164)
    if not body.strip() and has_media:
        return Decision(HOLD, "media_only_unknown", kind, e164)
    return Decision(DEFER, "no_business_signal", kind, e164)
