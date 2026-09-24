# Provenance gate — Gate 2

A `PreToolUse` hook that **denies** an outbound action when it carries a value with no
tool result behind it in the current session.

This is a stoppage, not a reminder. The deny is executed by the Claude Code harness before the
tool runs, so the model does not get a vote and cannot talk its way past it. Compare with the
`UserPromptSubmit` reminder, which only biases behavior.

Companion documents in the memory bank: `STATEMENT_OF_UNDERSTANDING.md` (why this is necessary)
and `SETTLED_CONCLUSIONS.md`.

## What it checks

Every string in the tool payload is scanned for Class 2 tokens — the categories that are expensive
to store and first to be lost, so the ones most likely to be confidently wrong:

| Class | Examples |
|---|---|
| `money` | `$7,961.64` |
| `wac_rcw` | `WAC 296-62-07712`, `RCW 49.17` |
| `cfr` | `29 CFR 1926.1101` |
| `subpart` | `Subpart M` |
| `date_numeric` / `date_written` | `9/14/2026`, `September 7, 2026` |
| `job_number` | `26-6808` |
| `pscaa_case` | `202603589` |
| `lni_notice` | `250965` |
| `phone` | `(425) 786-8366` |
| `quantity` | `1,240 sq ft`, `0.01 f/cc` |

Each token is then resolved against the session transcript:

- found in a **tool result** → BACKED, passes silently
- found only in the **operator's own typed message** → OPERATOR-ASSERTED, passes with a note
- found in **neither** → UNSOURCED, the tool call is **denied** and each value is named

The assistant's own earlier prose is deliberately excluded from both. A number Claude stated
before does not corroborate the same number stated again — that is the commitment cascade, not
evidence.

Comparison is formatting-insensitive: `$7,961.64` in an email matches `7961.64` in a ledger response.

## Escape hatch

Put this anywhere in the payload:

```
[[VERIFIED BY HUMAN: Ryan - read off the paper invoice]]
```

The call passes and the override is surfaced in the session. This exists because a gate with no
escape hatch gets uninstalled within a week. Every override is visible in the transcript.

## Fail direction

**Fails closed.** A missing transcript, an unreadable transcript, an unparseable payload, or a bad
config all produce a deny, because the guarded boundary is transmission to a client or a regulator.
Set `"fail_closed": false` in `gate_config.json` to invert this — not recommended for outbound.

Patterns are deliberately over-inclusive. A false positive costs one retrieval. A false negative
costs a wrong number in front of L&I, PSCAA, a client, or a crew.

## Install

### Linux / macOS

Copy `provenance_gate.py` and `gate_config.json` to `~/.claude/hooks/provenance_gate/`, then merge
into `~/.claude/settings.json` (merge — do not replace an existing `hooks` block):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__Gmail__send_message|mcp__Gmail__reply|mcp__Gmail__forward",
        "hooks": [
          {
            "type": "command",
            "command": "python3",
            "args": ["/home/YOU/.claude/hooks/provenance_gate/provenance_gate.py"],
            "timeout": 20,
            "statusMessage": "Provenance gate"
          }
        ]
      }
    ]
  }
}
```

### Windows

Copy both files to `%USERPROFILE%\.claude\hooks\provenance_gate\`. Use the **exec form** (`args`)
rather than a shell string — it spawns the executable directly, so Windows paths with spaces and
backslashes never reach a shell parser:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__Gmail__send_message|mcp__Gmail__reply|mcp__Gmail__forward",
        "hooks": [
          {
            "type": "command",
            "command": "python",
            "args": ["C:\\Users\\YOU\\.claude\\hooks\\provenance_gate\\provenance_gate.py"],
            "timeout": 20,
            "statusMessage": "Provenance gate"
          }
        ]
      }
    ]
  }
}
```

Requires Python 3.9+ on PATH. No third-party packages.

## Optional wider coverage

Add to the `matcher` string, pipe-separated, once the narrow version has proven itself:

- `mcp__Gmail__create_draft|mcp__Gmail__update_draft` — catches the error at staging rather than at
  send. Noisier, because staging a draft for review is a normal workflow.
- `Write|Edit` — guards writes into `Desktop\Job sites\`. **Expect heavy friction:** routine log
  entries legitimately restate figures retrieved in earlier sessions, and those are unsourced in
  *this* one. Scope it with an `if` condition before trying this.

## Verify the install

Three steps, in order. Do not skip step 3 — a hook that silently does nothing is worse than no hook.

**1. Unit tests**

```
python3 test_provenance_gate.py
```
Expect `11 passed, 0 failed`.

**2. Pipe test against a real transcript**

```
echo '{"session_id":"SID","transcript_path":"PATH","tool_name":"mcp__Gmail__send_message","tool_input":{"body":"Total $98,765.43."}}' | python3 provenance_gate.py
```
Expect JSON containing `"permissionDecision": "deny"`.

**3. Prove the harness executes the deny**

Temporarily change the matcher to `Write`, then ask Claude to write a file containing
`Invoice total $98,765.43 under WAC 296-62-00000, completed April 1, 2026.`

The Write must be **refused by the harness** — the error appears as a `PreToolUse:Write hook error`,
not as Claude declining. Then add `[[VERIFIED BY HUMAN: you - test]]` and confirm it succeeds.
Restore the production matcher afterward.

If nothing fires: open `/hooks` once to reload configuration, or restart the session. The settings
watcher only watches directories that had a settings file when the session started.

## Verified 2026-09-22

On Claude Code (Linux container, Python 3.11.15):

- 11/11 unit tests pass.
- Against the live session transcript: `$7,961.64` — a figure genuinely returned by a Drive read —
  passed; `$12,345.67`, `WAC 296-62-99999` and `March 4, 2026` were all denied and named.
- **Live harness deny confirmed.** A `Write` carrying three fabricated values was refused with
  `PreToolUse:Write hook error`, naming each value.
- **Live harness override confirmed.** The identical write with `[[VERIFIED BY HUMAN: ...]]` succeeded.
- Transcript discovery by `session_id` under `~/.claude/projects/` works; `transcript_path` is
  preferred when the harness supplies it.

## What this does not do

- It does not verify that a retrieved value is *correct*, only that it came from somewhere outside
  the model this session. A misread ledger still passes.
- It does not check effective dates. A correctly-retrieved but superseded regulation passes. That is
  the stale-but-real failure mode and needs its own guard.
- It cannot see values that are paraphrased rather than quoted (`"about eight thousand"`).
- It guards the tools named in `matcher` and nothing else. Anything Ryan types and sends himself is
  outside it entirely.
- It is not a substitute for Gate 1 (renderers refusing to emit an unsourced field) or Gate 3
  (a human signature on Class 3 decisions).
