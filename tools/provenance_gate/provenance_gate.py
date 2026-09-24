#!/usr/bin/env python3
"""Provenance gate — a PreToolUse hook that denies outbound actions carrying
unsourced facts.

Reads a Claude Code PreToolUse hook payload on stdin. Extracts every Class 2
token from the outbound payload (money, regulatory citation, date, case or job
number, phone, measured quantity), then checks each one against the session
transcript. A token that appears in a prior tool result is BACKED. A token that
appears only in the operator's own typed message is OPERATOR-ASSERTED and passes
with a note. A token that appears in neither is UNSOURCED, and the tool call is
denied.

This is a stoppage, not a reminder: the deny is executed by the harness, so the
model does not get a vote.

Exit code is always 0 — the decision travels in the JSON on stdout.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "gate_config.json"

# A payload carrying this marker passes with the override recorded in the
# transcript. It exists because a gate with no escape hatch gets uninstalled.
OVERRIDE_RE = re.compile(r"\[\[VERIFIED BY HUMAN:\s*(?P<who>[^\]]+?)\s*\]\]", re.I)

MAX_REPORTED = 25


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# payload extraction
# --------------------------------------------------------------------------

def collect_strings(node, ignore_keys: set[str], out: list[str]) -> None:
    """Walk a tool_input tree and collect every string that could reach a reader."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ignore_keys:
                continue
            collect_strings(value, ignore_keys, out)
    elif isinstance(node, list):
        for item in node:
            collect_strings(item, ignore_keys, out)
    elif isinstance(node, str):
        out.append(node)


def extract_tokens(text: str, patterns: dict[str, str]) -> dict[str, set[str]]:
    """Return {class_name: {token, ...}} for every Class 2 pattern that matched."""
    found: dict[str, set[str]] = {}
    for name, pattern in patterns.items():
        hits = {m.group(0).strip() for m in re.finditer(pattern, text, re.I)}
        if hits:
            found[name] = hits
    return found


# --------------------------------------------------------------------------
# transcript reading
# --------------------------------------------------------------------------

def find_transcript(payload: dict) -> Path | None:
    """Locate the session transcript.

    Prefers the transcript_path the harness supplies. Falls back to searching
    ~/.claude/projects for <session_id>.jsonl, because that field is not
    guaranteed by the documented hook input.
    """
    direct = payload.get("transcript_path")
    if direct:
        candidate = Path(direct).expanduser()
        if candidate.is_file():
            return candidate

    session_id = payload.get("session_id")
    if not session_id:
        return None

    projects = Path(
        os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")
    ).expanduser() / "projects"
    if not projects.is_dir():
        return None

    matches = sorted(
        projects.glob(f"*/{session_id}.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def read_sources(transcript: Path) -> tuple[str, str]:
    """Split the transcript into retrieved text and operator-typed text.

    Returns (tool_result_text, operator_text). The assistant's own prose is
    deliberately excluded from both: a number the model previously stated does
    not corroborate the same number stated again.
    """
    tool_chunks: list[str] = []
    operator_chunks: list[str] = []

    with transcript.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Tool results arrive out-of-band on some versions.
            if "toolUseResult" in entry:
                tool_chunks.append(json.dumps(entry["toolUseResult"]))

            message = entry.get("message") or {}
            if message.get("role") != "user":
                continue

            content = message.get("content")
            if isinstance(content, str):
                operator_chunks.append(content)
                continue
            if not isinstance(content, list):
                continue

            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result":
                    tool_chunks.append(json.dumps(block.get("content", "")))
                elif block.get("type") == "text":
                    operator_chunks.append(block.get("text", ""))

    return "\n".join(tool_chunks), "\n".join(operator_chunks)


# --------------------------------------------------------------------------
# matching
# --------------------------------------------------------------------------

def normalize(token: str) -> str:
    """Strip formatting so '$7,961.64' matches '7961.64' in a ledger response."""
    return re.sub(r"[\s,$()\-./]", "", token).lower()


def is_present(token: str, haystack: str, haystack_norm: str) -> bool:
    if token.lower() in haystack.lower():
        return True
    norm = normalize(token)
    return len(norm) >= 3 and norm in haystack_norm


# --------------------------------------------------------------------------
# decision
# --------------------------------------------------------------------------

def deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        "systemMessage": "PROVENANCE GATE: outbound action blocked.",
    }


def allow(note: str | None = None) -> dict:
    out: dict = {"suppressOutput": True}
    if note:
        out["systemMessage"] = note
    return out


def evaluate(payload: dict, config: dict) -> dict:
    tool_name = payload.get("tool_name", "<unknown>")
    ignore_keys = set(config.get("ignore_keys", []))
    patterns: dict[str, str] = config["patterns"]
    fail_closed = config.get("fail_closed", True)

    strings: list[str] = []
    collect_strings(payload.get("tool_input", {}), ignore_keys, strings)
    payload_text = "\n".join(strings)

    override = OVERRIDE_RE.search(payload_text)
    if override:
        return allow(
            "PROVENANCE GATE: passed by human override "
            f"({override.group('who')}) on {tool_name}. Recorded."
        )

    found = extract_tokens(payload_text, patterns)
    if not found:
        return allow()

    transcript = find_transcript(payload)
    if transcript is None:
        msg = (
            f"Cannot verify provenance for {tool_name}: session transcript not found. "
            "Either retrieve the values through a tool in this session, or mark the "
            "payload [[VERIFIED BY HUMAN: <name> - <why>]]."
        )
        return deny(msg) if fail_closed else allow("PROVENANCE GATE: no transcript; failed open.")

    try:
        tool_text, operator_text = read_sources(transcript)
    except OSError as exc:  # unreadable transcript
        msg = f"Cannot verify provenance for {tool_name}: transcript unreadable ({exc})."
        return deny(msg) if fail_closed else allow("PROVENANCE GATE: transcript unreadable; failed open.")

    tool_norm = normalize(tool_text)
    operator_norm = normalize(operator_text)

    unsourced: list[str] = []
    operator_only: list[str] = []

    for cls, tokens in sorted(found.items()):
        for token in sorted(tokens):
            if is_present(token, tool_text, tool_norm):
                continue
            if is_present(token, operator_text, operator_norm):
                operator_only.append(f"{token} ({cls})")
            else:
                unsourced.append(f"{token} ({cls})")

    if unsourced:
        shown = unsourced[:MAX_REPORTED]
        more = len(unsourced) - len(shown)
        lines = [
            f"{tool_name} carries {len(unsourced)} value(s) with no tool result behind "
            "them in this session:",
            "",
        ]
        lines += [f"  - {item}" for item in shown]
        if more:
            lines.append(f"  ... and {more} more")
        lines += [
            "",
            "Retrieve each one from its source of record (PSCAA invoice ledger, the L&I "
            "print-notice PDF, the lab invoice, the signed bid, Gmail), or replace it with "
            "NOT IN RECORD.",
            "If you are the source, mark the payload [[VERIFIED BY HUMAN: <name> - <why>]].",
        ]
        if operator_only:
            lines += ["", f"Operator-asserted (not blocking): {', '.join(operator_only[:10])}"]
        return deny("\n".join(lines))

    if operator_only:
        return allow(
            "PROVENANCE GATE: passed. Operator-asserted, not retrieved: "
            + ", ".join(operator_only[:10])
        )

    return allow()


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        # A malformed payload must not become a silent bypass.
        print(json.dumps(deny("Provenance gate received an unparseable hook payload.")))
        return 0

    config_path = Path(os.environ.get("PROVENANCE_GATE_CONFIG", DEFAULT_CONFIG))
    try:
        config = load_config(config_path)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps(deny(f"Provenance gate config unreadable at {config_path}: {exc}")))
        return 0

    print(json.dumps(evaluate(payload, config)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
