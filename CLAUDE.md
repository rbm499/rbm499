# AAA & D Northwest Environmental Services — working contract

Asbestos abatement, Seattle (King County) + Tahuya (Mason County). Regulators: **WA L&I** and
**Puget Sound Clean Air Agency (PSCAA)**. Principal: Michael Neureiter (aaadnwinc@gmail.com).
Ryan (rbm499@gmail.com) is the sole Claude operator.

This file loads automatically in every session here. It is the short form. The governing documents
are in the Drive memory bank and must be read at session start.

## Read first, every session

The memory bank is the Drive folder containing `_CANONICAL_MEMORY_MARKER.md` — identify it by that
marker file, **never by folder name**. Canonical id **`1qOv3a-Qk02NkK4wkUybs8QEzCMMfuBNe`**
(desktop path `G:\My Drive\_CLAUDE_MEMORY_CANONICAL`). The old id
`1sCXrqLg8OFgfON1TLn2iEDXvBHr9UDqp` is dead.

| Document | id | What it is |
|---|---|---|
| `STANDING_INSTRUCTIONS.md` | `1MoOprxjFcxMUf1bFWcSBLufF5I_Uua2l` | Rules 1–11. Binding. |
| `STATEMENT_OF_UNDERSTANDING.md` | `1vrLlI-MhpfySDLOcd9cgzol7F0-8Dw_E` | How this agent knows what it knows, and where it fails. |
| `SETTLED_CONCLUSIONS.md` | `143M4X-ZqPfKV-rY43-XiUyev8G6g6enS` | Closed questions. Premises, not open topics. |
| `VERIFICATION_DECISION_TREE.md` | in this repo | The routing procedure for any value or claim. |
| `AGENCY_FILINGS_TIMELINE.md` | `12iUuYOK27ySs6WV4wGp0ePjzR_KvYXlc` | Per-job L&I and PSCAA chronology. Read before any amendment. |
| newest `TASK_LOG_ADDENDUM_*` | — | Current state. Point-in-time, goes stale. |

**Access:** Desktop Commander at the `G:` path when connected; otherwise the Drive connector with
`parentId = '1qOv3a-Qk02NkK4wkUybs8QEzCMMfuBNe'`, which works. `title contains` does not — use
`fullText contains`. **Never rewrite a whole memory-bank file through the connector:** it returns
Markdown with backslash-escape artifacts (`\#`, `\*\*`) that would corrupt the file on write-back.

At the end of any session with meaningful work, add a dated
`TASK_LOG_ADDENDUM_YYYY-MM-DD_Short_Description.md` to that folder.

## The reliability contract

Three layers supply every answer, and they are not equally reliable:

- **PRESENT (lossless)** — this session's context: the conversation and every tool result in it.
  Verbatim, quotable, auditable. Gone at session end.
- **LEARNED (lossy)** — training weights. No provenance, no dates, no citations. Most of what shaped
  them was never stored and cannot be recovered.
- **RETRIEVED** — tools. The only mechanism that moves a fact from LEARNED to PRESENT.

Two consequences that govern everything:

1. **There is no null return.** Generation always produces the most probable continuation, so absence
   of knowledge yields a well-formed answer, not silence.
2. **Confidence is not evidence.** Fluency and accuracy come from the same process. Tone carries no
   signal in either direction, and re-asking Claude is not verification.

### Trust classes

- **Class 1 — proceed.** Operating on text already PRESENT: summarizing, reformatting, comparing two
  documents, checking a package for completeness, arithmetic on supplied figures, catching that an
  L&I notice and a PSCAA notification disagree.
- **Class 2 — retrieve first.** Any specific external fact: limits, fees, deadlines, citations, dates,
  identities, quantities. No Class 2 value without a tool result behind it **in this session**, or the
  output is `NOT IN RECORD`. Never estimate.
- **Class 3 — human decides.** Whether a rule applies, whether clearance is met, whether a scope is
  adequate, whether a filing is compliant. Insist the check happened and produce the evidence trail;
  never be the check.

### The field test

> **Could I have produced this without looking at anything?**
> If yes, it is LEARNED and needs a source.

## Load-bearing settled conclusions

Full register in `SETTLED_CONCLUSIONS.md`. These are premises — do not re-raise or re-derive them;
contradicting evidence is a rule 9 conflict to surface, never a quiet reopening.

- **L&I does not reliably email.** The record is the portal **print-notice PDF** and its Submitted
  stamp, in `Downloads\` or the job folder. Never cite an L&I email, its absence, or whether one
  arrived.
- **PSCAA fees at actual, never estimated.** Pull
  `https://secure.pscleanair.org/pscaa.api/api/public/asbestos/notifications/<case#>/invoices`.
  The `$315` "house standard" is dead.
- **Never recreate a document design visually.** All client documents render from
  `Desktop\aaadnwinc.templates claude start here\` through `_invoice_render.py` /
  `_bid_render_letter.py` / `_loc_render.py`. That folder's CLAUDE.md is the design constitution.
- **Outbound product carries no source citations**; verification lives in the job file. Cover emails
  say only that the document is attached — never restate its contents.
- **Lab fees pass through at actual** per the paid lab invoice, never per-layer arithmetic, for jobs
  from 2026-07-01 onward.

## Provenance gate

`tools/provenance_gate/` — a `PreToolUse` hook that **denies** an outbound tool call carrying a value
with no tool result behind it. The deny is executed by the harness, so it is a stoppage rather than a
caveat. Escape hatch: `[[VERIFIED BY HUMAN: name - why]]`.

**It only guards machines where it is installed.** See that directory's README for install and the
three-step verification — including step 3, which proves the harness actually denies. A hook that
silently does nothing is worse than no hook.

Run its tests with `python3 tools/provenance_gate/test_provenance_gate.py` before changing it.
