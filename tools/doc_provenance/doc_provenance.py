#!/usr/bin/env python3
"""Gate 1 — document provenance enforcement.

A per-job builder wraps each Class 2 value with its source. `prepare()` validates
the payload and, in final mode, **raises** rather than returning renderable data
when any value lacks one. Nothing downstream can opt out: an unsourced number
becomes a build error instead of a document.

This never touches the canonical renderers. It validates the data a builder hands
in, strips provenance back off, and returns plain values — so layout code is
unchanged and rule 6 holds: the audit goes to the job file, never into the product.

    from doc_provenance import sourced, boilerplate, prepare, write_audit

    data = {
        "total": sourced(7961.64, "PSCAA ledger 202603096, pulled 2026-09-24"),
        "completion_date": sourced("September 8, 2026", "LOC 26-4509, signed"),
        "regulatory_notice": boilerplate("Performed under WAC 296-62-077 ..."),
        "client": "Tarun Phaugat",
    }
    payload, audit = prepare(data)          # raises ProvenanceError if unsourced
    render_invoice(payload)                 # canonical renderer, untouched
    write_audit(audit, job_dir / "PROVENANCE.md", job="26-1834")

Modes:
    "final" (default) — any unsourced Class 2 value, empty source, or NOT_IN_RECORD
                        raises. Use for anything a client or regulator will see.
    "draft"           — violations are recorded and NOT_IN_RECORD renders as a loud
                        literal marker, so a human sees the gap on the page.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent

# One source of truth, shared with the Gate 2 hook so the two gates agree on what
# counts as a Class 2 value. Override with DOC_PROVENANCE_CONFIG or config_path.
DEFAULT_CONFIG = HERE.parent / "provenance_gate" / "gate_config.json"

MODES = ("final", "draft")
NOT_IN_RECORD_TEXT = "NOT IN RECORD"


class ProvenanceError(Exception):
    """Raised instead of returning renderable data. Carries every violation."""

    def __init__(self, violations: list["Violation"]) -> None:
        self.violations = violations
        super().__init__(format_violations(violations))


@dataclass(frozen=True)
class Violation:
    path: str
    value: str
    problem: str
    remedy: str


class _NotInRecord:
    """Sentinel for a value that was looked for and genuinely is not in the record.

    Explicit absence, distinct from a field nobody filled in. In final mode it
    raises; in draft mode it renders as a visible marker.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "NOT_IN_RECORD"


NOT_IN_RECORD = _NotInRecord()


@dataclass(frozen=True)
class Sourced:
    """A Class 2 value and where it came from."""

    value: Any
    source: str


@dataclass(frozen=True)
class Boilerplate:
    """Fixed canon text, exempt because it comes from the design constitution
    rather than from a lookup. Regulatory boilerplate cites WAC and CFR by
    design; without this every AHERA report would fail the gate. Recorded in the
    audit as claimed-boilerplate so the exemption is visible, not silent.
    """

    text: str


def sourced(value: Any, source: str) -> Sourced:
    return Sourced(value, source)


def boilerplate(text: str) -> Boilerplate:
    return Boilerplate(text)


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------

def load_patterns(config_path: Path | None = None) -> tuple[dict[str, str], set[str]]:
    path = Path(
        config_path
        or os.environ.get("DOC_PROVENANCE_CONFIG")
        or DEFAULT_CONFIG
    )
    if not path.is_file():
        raise ProvenanceError([
            Violation(
                path="<config>",
                value=str(path),
                problem="Class 2 pattern config not found, so nothing can be validated.",
                remedy=(
                    "Ship gate_config.json alongside this module, or set "
                    "DOC_PROVENANCE_CONFIG to its path. Refusing to render is "
                    "correct here: a gate that cannot load its rules must not "
                    "pass everything."
                ),
            )
        ])
    with path.open(encoding="utf-8") as fh:
        config = json.load(fh)
    return config["patterns"], set(config.get("ignore_keys", []))


def class2_tokens(text: str, patterns: dict[str, str]) -> list[str]:
    """Every Class 2 token in a string, as 'token (class)' labels."""
    found: list[str] = []
    for name, pattern in patterns.items():
        for match in re.finditer(pattern, text, re.I):
            token = match.group(0).strip()
            label = f"{token} ({name})"
            if label not in found:
                found.append(label)
    return found


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

@dataclass
class AuditRecord:
    path: str
    value: str
    source: str
    kind: str  # "sourced" | "boilerplate" | "not-in-record" | "plain"


def _walk(
    node: Any,
    path: str,
    patterns: dict[str, str],
    ignore_keys: set[str],
    mode: str,
    audit: list[AuditRecord],
    violations: list[Violation],
) -> Any:
    """Validate and unwrap in one pass. Returns the plain value for the renderer."""

    if isinstance(node, Sourced):
        if not str(node.source).strip():
            violations.append(Violation(
                path=path,
                value=_short(node.value),
                problem="Wrapped with an empty source.",
                remedy="Name the source of record: ledger URL, print-notice PDF and "
                       "its Submitted stamp, message id, lab invoice, or signed bid.",
            ))
            return node.value
        audit.append(AuditRecord(path, _short(node.value), node.source, "sourced"))
        # Recurse: a Sourced may wrap a structure, and its source covers all of it.
        return _unwrap_only(node.value)

    if isinstance(node, Boilerplate):
        audit.append(AuditRecord(
            path, _short(node.text), "canon boilerplate (design constitution)", "boilerplate"
        ))
        return node.text

    if isinstance(node, _NotInRecord):
        audit.append(AuditRecord(path, NOT_IN_RECORD_TEXT, "absent from the record", "not-in-record"))
        if mode == "final":
            violations.append(Violation(
                path=path,
                value=NOT_IN_RECORD_TEXT,
                problem="Marked NOT IN RECORD, and this is a final render.",
                remedy="Retrieve the value, or remove the field from the document. A "
                       "document that goes to a client or a regulator does not carry "
                       "an acknowledged blank.",
            ))
        return NOT_IN_RECORD_TEXT

    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            if key in ignore_keys:
                out[key] = _unwrap_only(value)
                continue
            out[key] = _walk(value, child, patterns, ignore_keys, mode, audit, violations)
        return out

    if isinstance(node, (list, tuple)):
        items = [
            _walk(item, f"{path}[{i}]", patterns, ignore_keys, mode, audit, violations)
            for i, item in enumerate(node)
        ]
        return type(node)(items) if isinstance(node, tuple) else items

    # A bare leaf. Numbers are Class 2 by nature; strings only if they carry a token.
    if isinstance(node, bool) or node is None:
        return node

    if isinstance(node, (int, float)):
        violations.append(Violation(
            path=path,
            value=_short(node),
            problem="Bare number with no source.",
            remedy=f"Wrap it: sourced({node!r}, '<source of record>'). If it is arithmetic "
                   "on values already sourced in this payload, wrap it with that derivation "
                   "as the source.",
        ))
        return node

    if isinstance(node, str):
        tokens = class2_tokens(node, patterns)
        if tokens:
            violations.append(Violation(
                path=path,
                value=_short(node),
                problem="Unsourced Class 2 value(s): " + ", ".join(tokens[:6]),
                remedy="Wrap with sourced(...), or boilerplate(...) if it is fixed canon text "
                       "from the design constitution rather than a looked-up fact.",
            ))
        else:
            audit.append(AuditRecord(path, _short(node), "-", "plain"))
        return node

    return node


def _unwrap_only(node: Any) -> Any:
    """Strip Sourced/Boilerplate wrappers without re-validating."""
    if isinstance(node, Sourced):
        return _unwrap_only(node.value)
    if isinstance(node, Boilerplate):
        return node.text
    if isinstance(node, _NotInRecord):
        return NOT_IN_RECORD_TEXT
    if isinstance(node, dict):
        return {k: _unwrap_only(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_unwrap_only(v) for v in node]
    if isinstance(node, tuple):
        return tuple(_unwrap_only(v) for v in node)
    return node


def _short(value: Any, limit: int = 80) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_violations(violations: list[Violation]) -> str:
    lines = [
        f"Refusing to render: {len(violations)} value(s) have no source of record.",
        "",
    ]
    for v in violations:
        lines += [
            f"  {v.path}",
            f"    value:   {v.value}",
            f"    problem: {v.problem}",
            f"    remedy:  {v.remedy}",
            "",
        ]
    lines += [
        "Every value a client or a regulator reads is traceable to a record, or the",
        "document does not get built. To render anyway for internal review, pass",
        'mode="draft" — that stamps the gaps on the page instead of hiding them.',
    ]
    return "\n".join(lines)


def prepare(
    data: dict,
    mode: str = "final",
    config_path: Path | None = None,
) -> tuple[dict, list[AuditRecord]]:
    """Validate `data`, then return (plain payload for the renderer, audit records).

    Raises ProvenanceError in final mode if any value lacks a source. Every
    violation is reported at once, so one pass fixes them all.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")

    patterns, ignore_keys = load_patterns(config_path)
    audit: list[AuditRecord] = []
    violations: list[Violation] = []

    payload = _walk(data, "", patterns, ignore_keys, mode, audit, violations)

    if violations and mode == "final":
        raise ProvenanceError(violations)

    if violations:  # draft mode: keep them, surfaced by write_audit
        for v in violations:
            audit.append(AuditRecord(v.path, v.value, f"UNSOURCED — {v.problem}", "plain"))

    return payload, audit


# --------------------------------------------------------------------------
# audit sidecar
# --------------------------------------------------------------------------

def render_audit(
    audit: list[AuditRecord],
    job: str | None = None,
    rendered: str | None = None,
    mode: str = "final",
) -> str:
    """The provenance record for the job file. Never for the deliverable."""
    lines = [
        f"# Provenance — {job or 'unspecified job'}",
        "",
        "Audit trail for the values in the rendered document. Internal only: this never",
        "appears in the deliverable (rule 6 / S-07 — outbound product carries no source",
        "citations; verification lives in the job file).",
        "",
        f"- Render mode: **{mode}**",
    ]
    if rendered:
        lines.append(f"- Document: `{rendered}`")
    lines += ["", "| Field | Value | Source | Kind |", "|---|---|---|---|"]

    for rec in audit:
        if rec.kind == "plain" and not rec.source.startswith("UNSOURCED"):
            continue  # non-Class-2 text needs no provenance line
        value = rec.value.replace("|", "\\|")
        source = rec.source.replace("|", "\\|")
        lines.append(f"| `{rec.path}` | {value} | {source} | {rec.kind} |")

    unsourced = [r for r in audit if r.source.startswith("UNSOURCED")]
    if unsourced:
        lines += [
            "",
            f"## {len(unsourced)} UNSOURCED value(s) — draft only",
            "",
            "This document must not be sent. Retrieve each value, then re-render in final mode.",
        ]
    return "\n".join(lines) + "\n"


def write_audit(
    audit: list[AuditRecord],
    path: str | Path,
    job: str | None = None,
    rendered: str | None = None,
    mode: str = "final",
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_audit(audit, job, rendered, mode), encoding="utf-8")
    return target
