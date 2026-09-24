# Handoff prompt — wire Gate 1 into the canonical builders

Paste the block below into a **Cowork session with Desktop Commander connected**. It is written to
stand alone: it assumes no memory of the session that built the module.

---

```
Read STANDING_INSTRUCTIONS.md, SETTLED_CONCLUSIONS.md, STATEMENT_OF_UNDERSTANDING.md and
VERIFICATION_DECISION_TREE.md from the memory bank before doing anything else. Reach it through
Desktop Commander at G:\My Drive\_CLAUDE_MEMORY_CANONICAL (confirm by _CANONICAL_MEMORY_MARKER.md,
never by folder name). Also read the newest TASK_LOG_ADDENDUM files, including
TASK_LOG_ADDENDUM_2026-09-24_Provenance_Gate_And_Governing_Docs.md and
TASK_LOG_ADDENDUM_2026-09-24_Corrections_To_This_Sessions_Ledger.md.

TASK: wire Gate 1 (document provenance enforcement) into the canonical per-job builders so that a
client document cannot be rendered when any Class 2 value in it has no source of record.

Gate 1 already exists and is tested — 25/25 passing. Do not rewrite it. Get these two files:

  tools/doc_provenance/doc_provenance.py
  tools/provenance_gate/gate_config.json

from the repository rbm499/rbm499, branch claude/ai-data-human-history-98xsrq (draft PR #6). Clone or
fetch that branch if you have git access; otherwise download the two files from the PR's Files view
in a browser. Read doc_provenance.py and tools/doc_provenance/README.md before using either.

Install them so that gate_config.json sits at ..\provenance_gate\gate_config.json relative to
doc_provenance.py, or else set the DOC_PROVENANCE_CONFIG environment variable to its actual path.
Verify by running: python test_doc_provenance.py — expect "25 passed, 0 failed". If it does not pass,
stop and report; do not integrate a module whose own tests fail.

THE TARGET CODE is the canonical document folder:
  Desktop\aaadnwinc.templates claude start here\
Its CLAUDE.md is the design constitution. Read it first. The renderers are _invoice_render.py,
_bid_render_letter.py and _loc_render.py. The per-job builders are data-only.

HARD CONSTRAINTS — these are not negotiable and override any convenience:

1. DO NOT EDIT THE RENDERERS. No layout changes, no formatting changes, nothing inside
   _invoice_render.py, _bid_render_letter.py, _loc_render.py or letterhead.py. Gate 1 sits one step
   earlier, on the data a builder hands in. If you find yourself editing a renderer, you have taken
   the wrong approach — stop and reconsider.

2. NEVER INVENT A SOURCE. This is the single most important instruction. The builders contain
   hardcoded values whose origin you will not know. For each one, find the real source of record:
     - PSCAA fee or case -> the public ledger,
       https://secure.pscleanair.org/pscaa.api/api/public/asbestos/notifications/<case#>/invoices
     - L&I filing status -> the portal print-notice PDF and its Submitted stamp, in Downloads\ or the
       job folder. Never an email, present or absent.
     - Lab result or fee -> the lab report; fees at actual per the paid lab invoice, never per-layer
       arithmetic
     - completion or clearance date -> the signed LOC or clearance report
     - scope or price -> the SIGNED bid
     - owner or parties -> county assessor / recorded deed, SOS for entities
   If you cannot establish where a value came from, DO NOT write a plausible-looking source string.
   Use NOT_IN_RECORD, or leave that builder untouched, and add the field to a list for Ryan at the
   end. A fabricated provenance line is worse than no gate at all: it launders a guess into an audit
   trail. This whole gate exists to prevent exactly that.

3. PROVENANCE NEVER REACHES THE DELIVERABLE. prepare() strips it and returns plain values; the audit
   goes to the job folder as PROVENANCE.md. Do not add citations, "per the field log" phrasing, or
   source notes to any rendered document. Rule 6 / S-07.

4. ACCEPTANCE TEST — BYTE-IDENTICAL OUTPUT. Gate 1 changes what is allowed to render, never what
   rendering produces. For each builder you touch: re-render a known-good past document, and compare
   the new PDF to the original with sha256sum or fc. If they differ, you changed rendering behavior —
   revert and find out why. Do this for EVERY builder you modify, not a sample. Report each hash pair.

PER-BUILDER CHANGE, the expected shape:
  a. from doc_provenance import sourced, boilerplate, prepare, write_audit
  b. wrap each Class 2 value in the builder's data dict: sourced(value, "<real source of record>")
  c. wrap fixed regulatory text with boilerplate(...) — regulatory boilerplate cites WAC and CFR by
     design and would otherwise fail the gate. Only genuine canon text from the design constitution
     qualifies; do not use boilerplate() to silence a value you could not source.
  d. replace render_x(data) with:  payload, audit = prepare(data)   then   render_x(payload)
  e. write_audit(audit, <job folder>\PROVENANCE.md, job="<job#>", rendered="<pdf name>")

ORDER OF WORK: do ONE builder first, end to end, including the byte-identical diff. Show me that
result and wait before doing the rest. A batch of six half-verified integrations is worse than one
proven one.

WHEN YOU HIT A VALUE YOU CANNOT SOURCE: stop on that field, not the whole job. Record it. Continue
with what you can source. Report the list at the end — those are decisions for Ryan, not for you.

AT THE END: append a dated TASK_LOG_ADDENDUM_YYYY-MM-DD_Gate1_Integration.md to the memory bank
recording which builders were changed, the sha256 pairs proving byte-identical output, every value
you could not source, and anything still open. Do not close the loop with a summary in chat alone —
the addendum is the record.

DO NOT: send anything to a client or an agency, file anything with L&I or PSCAA, or render a final
document for delivery during this task. This is an infrastructure change. If a real document needs to
go out, that is a separate decision by Ryan.
```

---

## Why the prompt is shaped this way

- **"Never invent a source" is the load-bearing instruction.** The integration requires attaching a
  provenance string to values whose origin is not in the code. That is precisely the condition under
  which a model produces a fluent, plausible, wrong answer — and here the wrong answer would be
  written into an audit trail, which is worse than having none. Hence the explicit prohibition, the
  named sources of record, and the instruction to escalate rather than fill the gap.
- **Byte-identical output as the acceptance test** makes "I didn't break the renderers" checkable
  instead of asserted. It is the only claim about this change that a hash can settle.
- **One builder, then stop** keeps the blast radius one file wide until the approach is proven.
- **The addendum requirement** exists because a chat summary evaporates and the job files do not.
