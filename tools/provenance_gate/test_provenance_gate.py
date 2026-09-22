#!/usr/bin/env python3
"""Self-contained tests for provenance_gate.py. Run: python3 test_provenance_gate.py

No pytest dependency — this has to be runnable on the Windows box with nothing
installed but Python.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE = HERE / "provenance_gate.py"

PASSED: list[str] = []
FAILED: list[str] = []


def run_gate(payload, raw: str | None = None, env_extra: dict | None = None) -> dict:
    import os

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    stdin = raw if raw is not None else json.dumps(payload)
    proc = subprocess.run(
        [sys.executable, str(GATE)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, f"gate exited {proc.returncode}: {proc.stderr}"
    return json.loads(proc.stdout)


def is_deny(result: dict) -> bool:
    return result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def reason(result: dict) -> str:
    return result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")


def write_transcript(path: Path, tool_results=(), operator=(), assistant=()) -> None:
    lines = []
    for text in tool_results:
        lines.append(json.dumps({
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "t1", "content": text}],
            }
        }))
    for text in operator:
        lines.append(json.dumps({
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}
        }))
    for text in assistant:
        lines.append(json.dumps({
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}
        }))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  {detail}")


def main() -> int:
    print("provenance_gate tests\n")

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)

        # ---- 1. unbacked money is denied -------------------------------
        t = tmpdir / "empty.jsonl"
        write_transcript(t, tool_results=["ls: no results"])
        res = run_gate({
            "session_id": "s1",
            "transcript_path": str(t),
            "tool_name": "mcp__Gmail__send_message",
            "tool_input": {"to": "client@example.com", "body": "Balance due is $7,961.64."},
        })
        check("unbacked money denied", is_deny(res) and "7,961.64" in reason(res), reason(res)[:120])

        # ---- 2. money backed by a tool result passes -------------------
        t = tmpdir / "backed.jsonl"
        write_transcript(t, tool_results=["invoice total 7961.64 outstanding"])
        res = run_gate({
            "session_id": "s2",
            "transcript_path": str(t),
            "tool_name": "mcp__Gmail__send_message",
            "tool_input": {"body": "Balance due is $7,961.64."},
        })
        check("tool-backed money allowed", not is_deny(res), json.dumps(res)[:120])

        # ---- 3. operator-asserted passes, with a note ------------------
        t = tmpdir / "operator.jsonl"
        write_transcript(t, operator=["bill the survey at $850 flat"])
        res = run_gate({
            "session_id": "s3",
            "transcript_path": str(t),
            "tool_name": "mcp__Gmail__send_message",
            "tool_input": {"body": "Survey fee $850."},
        })
        check(
            "operator-asserted allowed with note",
            not is_deny(res) and "Operator-asserted" in res.get("systemMessage", ""),
            json.dumps(res)[:160],
        )

        # ---- 4. assistant's own prior text is NOT corroboration --------
        t = tmpdir / "assistant.jsonl"
        write_transcript(t, tool_results=["nothing relevant"], assistant=["the total is $4,242.42"])
        res = run_gate({
            "session_id": "s4",
            "transcript_path": str(t),
            "tool_name": "mcp__Gmail__send_message",
            "tool_input": {"body": "Total $4,242.42."},
        })
        check("assistant text does not back a value", is_deny(res), reason(res)[:120])

        # ---- 5. human override passes ----------------------------------
        res = run_gate({
            "session_id": "s5",
            "transcript_path": str(tmpdir / "missing.jsonl"),
            "tool_name": "mcp__Gmail__send_message",
            "tool_input": {"body": "Total $1,234.56. [[VERIFIED BY HUMAN: Ryan - read off the paper invoice]]"},
        })
        check(
            "human override allowed",
            not is_deny(res) and "override" in res.get("systemMessage", "").lower(),
            json.dumps(res)[:160],
        )

        # ---- 6. missing transcript fails CLOSED ------------------------
        res = run_gate({
            "session_id": "no-such-session-xyz",
            "tool_name": "mcp__Gmail__send_message",
            "tool_input": {"body": "Fee was $315.00."},
        })
        check("missing transcript fails closed", is_deny(res), reason(res)[:120])

        # ---- 7. payload with no Class 2 tokens passes silently ---------
        t = tmpdir / "clean.jsonl"
        write_transcript(t, tool_results=["nothing"])
        res = run_gate({
            "session_id": "s7",
            "transcript_path": str(t),
            "tool_name": "mcp__Gmail__send_message",
            "tool_input": {"body": "Attached please find the letter of completion."},
        })
        check("no tokens, no note", not is_deny(res) and "systemMessage" not in res, json.dumps(res)[:120])

        # ---- 8. regulatory citation must be retrieved ------------------
        t = tmpdir / "reg.jsonl"
        write_transcript(t, tool_results=["unrelated output"])
        res = run_gate({
            "session_id": "s8",
            "transcript_path": str(t),
            "tool_name": "mcp__Gmail__send_message",
            "tool_input": {"body": "Work performed under WAC 296-62-07712 and 29 CFR 1926.1101."},
        })
        r = reason(res)
        check(
            "unretrieved citations denied",
            is_deny(res) and "WAC 296-62-07712" in r and "CFR" in r,
            r[:160],
        )

        # ---- 9. transcript discovery via CLAUDE_CONFIG_DIR -------------
        cfg = tmpdir / "fakeconfig"
        proj = cfg / "projects" / "-home-user-rbm499"
        proj.mkdir(parents=True)
        write_transcript(proj / "s9.jsonl", tool_results=["PSCAA ledger shows 202603589 paid in full"])
        res = run_gate(
            {
                "session_id": "s9",
                "tool_name": "mcp__Gmail__send_message",
                "tool_input": {"body": "Case 202603589 is closed."},
            },
            env_extra={"CLAUDE_CONFIG_DIR": str(cfg)},
        )
        check("transcript found by session_id", not is_deny(res), json.dumps(res)[:160])

        # ---- 10. unparseable stdin fails closed ------------------------
        res = run_gate(None, raw="{not json at all")
        check("malformed payload fails closed", is_deny(res), reason(res)[:120])

        # ---- 11. dates are Class 2 too ---------------------------------
        t = tmpdir / "dates.jsonl"
        write_transcript(t, tool_results=["clearance performed"])
        res = run_gate({
            "session_id": "s11",
            "transcript_path": str(t),
            "tool_name": "mcp__Gmail__reply",
            "tool_input": {"body": "Completed September 7, 2026."},
        })
        check("unbacked date denied", is_deny(res) and "September 7, 2026" in reason(res), reason(res)[:140])

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("failed: " + ", ".join(FAILED))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
