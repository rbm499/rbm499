#!/usr/bin/env python3
"""Tests for Gate 1. Run: python3 test_doc_provenance.py

No pytest dependency — must run on the Windows box with nothing installed but Python.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from doc_provenance import (  # noqa: E402
    DEFAULT_CONFIG,
    NOT_IN_RECORD,
    ProvenanceError,
    boilerplate,
    load_patterns,
    prepare,
    render_audit,
    sourced,
    write_audit,
)

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  {detail}")


def refuses(data, mode="final"):
    """Return the ProvenanceError, or None if it rendered."""
    try:
        prepare(data, mode=mode)
        return None
    except ProvenanceError as exc:
        return exc


def main() -> int:
    print("doc_provenance (Gate 1) tests\n")

    # ---- the config is shared with Gate 2, so the gates cannot drift ----
    check("shares Gate 2's pattern config", DEFAULT_CONFIG.is_file(), str(DEFAULT_CONFIG))
    patterns, _ = load_patterns()
    gate2 = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    check("patterns identical to Gate 2's", patterns == gate2["patterns"])

    # ---- an unsourced bare number refuses ------------------------------
    err = refuses({"total": 7961.64})
    check(
        "bare number refuses",
        err is not None and "total" in str(err) and "no source" in str(err).lower(),
        str(err)[:120] if err else "rendered",
    )

    # ---- a sourced number renders, provenance stripped ------------------
    payload, audit = prepare({"total": sourced(7961.64, "PSCAA ledger 202603096, pulled 9/24")})
    check("sourced number renders", payload == {"total": 7961.64}, repr(payload))
    check(
        "provenance stripped from payload",
        "PSCAA" not in json.dumps(payload),
        repr(payload),
    )
    check(
        "provenance captured in audit",
        any("PSCAA ledger" in r.source for r in audit),
        repr([r.source for r in audit]),
    )

    # ---- an unsourced citation inside prose refuses ---------------------
    err = refuses({"scope": "Removal performed under WAC 296-62-07712."})
    check(
        "unsourced citation in prose refuses",
        err is not None and "WAC 296-62-07712" in str(err),
        str(err)[:140] if err else "rendered",
    )

    # ---- boilerplate is exempt, and recorded as such --------------------
    payload, audit = prepare({
        "notice": boilerplate("Work performed under WAC 296-62-077 and 29 CFR 1926.1101.")
    })
    check("boilerplate renders", "WAC 296-62-077" in payload["notice"])
    check(
        "boilerplate recorded, not silent",
        any(r.kind == "boilerplate" for r in audit),
        repr([r.kind for r in audit]),
    )

    # ---- an empty source is not a source -------------------------------
    err = refuses({"fee": sourced(315.00, "   ")})
    check(
        "empty source refuses",
        err is not None and "empty source" in str(err).lower(),
        str(err)[:120] if err else "rendered",
    )

    # ---- NOT_IN_RECORD: refuses in final, renders loudly in draft ------
    err = refuses({"clearance_date": NOT_IN_RECORD})
    check("NOT_IN_RECORD refuses in final mode", err is not None, str(err)[:120] if err else "rendered")

    payload, audit = prepare({"clearance_date": NOT_IN_RECORD}, mode="draft")
    check(
        "NOT_IN_RECORD visible in draft mode",
        payload["clearance_date"] == "NOT IN RECORD",
        repr(payload),
    )

    # ---- draft mode surfaces unsourced values instead of hiding them ----
    payload, audit = prepare({"total": 1234.56}, mode="draft")
    text = render_audit(audit, job="26-TEST", mode="draft")
    check(
        "draft audit names the unsourced value and forbids sending",
        "UNSOURCED" in text and "must not be sent" in text,
        text[:160],
    )

    # ---- every violation reported at once, not just the first -----------
    err = refuses({
        "total": 7961.64,
        "fee": 315.00,
        "date": "September 8, 2026",
        "case": "202603096",
    })
    check(
        "all violations reported in one pass",
        err is not None and len(err.violations) == 4,
        f"{len(err.violations) if err else 0} violations",
    )

    # ---- nested structures are walked, paths are useful -----------------
    err = refuses({
        "line_items": [
            {"desc": "Abatement", "amount": sourced(5000.00, "signed bid 26-6808")},
            {"desc": "Disposal", "amount": 1200.00},
        ]
    })
    check(
        "nested path identifies the offender",
        err is not None and "line_items[1].amount" in str(err),
        str(err)[:160] if err else "rendered",
    )

    # ---- a Sourced wrapper covers the structure it wraps ----------------
    payload, _ = prepare({
        "ledger": sourced({"initial": 275.00, "amendments": [20.00, 20.00]},
                          "PSCAA ledger 202603589, pulled 9/24")
    })
    check(
        "one source covers the structure it wraps",
        payload["ledger"] == {"initial": 275.00, "amendments": [20.00, 20.00]},
        repr(payload),
    )

    # ---- non-Class-2 text passes without ceremony ----------------------
    payload, _ = prepare({"client": "Tarun Phaugat", "note": "Attached please find the letter."})
    check("plain text needs no source", payload["client"] == "Tarun Phaugat")

    # ---- booleans and None are not numbers -----------------------------
    payload, _ = prepare({"occupied": False, "vacant": True, "middle": None})
    check("bools and None pass", payload == {"occupied": False, "vacant": True, "middle": None})

    # ---- ignore_keys from the shared config are not scanned -------------
    payload, _ = prepare({"messageId": "1a0c5d28ef093413", "threadId": "202603589"})
    check("ignored keys not scanned", payload["threadId"] == "202603589")

    # ---- the audit never carries provenance into the deliverable -------
    payload, audit = prepare({
        "total": sourced(7961.64, "PSCAA ledger 202603096"),
        "client": "Tarun Phaugat",
    })
    rendered = json.dumps(payload)
    check(
        "no source string can reach the renderer",
        "ledger" not in rendered and "202603096" not in rendered,
        rendered,
    )

    # ---- audit writes to the job file ----------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        target = write_audit(audit, Path(tmp) / "job" / "PROVENANCE.md", job="26-1834",
                             rendered="AAA-D_Invoice_26-1834.pdf")
        body = target.read_text(encoding="utf-8")
        check("audit file written", target.is_file())
        check(
            "audit states it is internal only",
            "never" in body and "job file" in body,
            body[:160],
        )
        check("audit names the source", "PSCAA ledger 202603096" in body, body[:200])

    # ---- a missing config refuses rather than passing everything -------
    err = refuses_config_missing()
    check(
        "missing config refuses (not fails open)",
        err is not None and "not found" in str(err).lower(),
        str(err)[:140] if err else "passed",
    )

    # ---- an unknown mode is a programming error, not a silent pass ------
    try:
        prepare({"x": sourced(1, "s")}, mode="whatever")
        bad_mode = False
    except ValueError:
        bad_mode = True
    check("unknown mode rejected", bad_mode)

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("failed: " + ", ".join(FAILED))
        return 1
    return 0


def refuses_config_missing():
    try:
        prepare({"total": 1.0}, config_path=Path("/nonexistent/gate_config.json"))
        return None
    except ProvenanceError as exc:
        return exc


if __name__ == "__main__":
    sys.exit(main())
