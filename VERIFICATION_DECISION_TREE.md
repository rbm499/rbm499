# VERIFICATION DECISION TREE

*Routing procedure for any value, claim, or action about to leave a session — into a document, an
email, a filing, a ledger, or an answer to Ryan or Michael. Companion to
`STATEMENT_OF_UNDERSTANDING.md` (why) and `SETTLED_CONCLUSIONS.md` (what is already closed).*

**Entry condition:** something is about to be stated, written, sent, or filed.

---

## Q1 — Is this a VALUE or a JUDGMENT?

| | |
|---|---|
| **Judgment** — does this rule apply, is clearance met, is this scope adequate, is this filing compliant, is this safe | → **CLASS 3. STOP.** A human decides. Produce the evidence trail and insist the check happened. Never be the check. |
| **Value** — a number, date, citation, name, quantity, identity, status | → **Q2** |

## Q2 — Is it a transformation of text already in this session?

| | |
|---|---|
| **Yes** — summarizing, reformatting, comparing two documents against each other, arithmetic on figures already supplied, checking a package for completeness, noticing that two filings disagree | → **CLASS 1. Proceed.** |
| **No** — it is an external fact | → **Q3** |

## Q3 — Did a tool return it, in THIS session?

| | |
|---|---|
| **Yes** | → **Q4** |
| **No, but Ryan or Michael stated it this session** | → **CLASS 2-OP. Proceed**, labelled operator-asserted, with who said it. |
| **No** | → **STOP. Retrieve it, or write `NOT IN RECORD`.** Never estimate. Never infer from a similar job. A prior session's number is not a source — it is a memory of one. |

## Q4 — Was it the AUTHORITATIVE source, not merely a convenient one?

| The value | The only source of record |
|---|---|
| PSCAA fee or case status | The **public invoice ledger**: `.../asbestos/notifications/<case#>/invoices`. Not an email, not a prior invoice, not the dead `$315` standard. |
| L&I filing or amendment submitted | The portal **print-notice PDF** and its **Submitted stamp**, in `Downloads\` or `Desktop\Job sites\<job>\`. **Never an email, present or absent.** |
| Lab result or lab fee | The lab report; fees at **actual per the paid lab invoice**, never per-layer arithmetic. |
| Sent / unsent, signed / unsigned | The **actual sent message** in the aaadnwinc mailbox. A staged draft is not a sent message. |
| Owner, parties, legal description | County assessor / recorded deed; SOS for entities. |
| Scope or price agreed | The **signed** bid. |
| Regulation text | The current WAC / CFR / PSCAA regulation **with its effective date read**. |
| Crew hours, who was on site | ClockShark records, not inference from a window. |

**Came from anywhere else?** → treat as Q3 "No." Go get the right one.

→ otherwise **Q5**

## Q5 — Does it disagree with the record, or with the other agency?

| | |
|---|---|
| Disagrees with a deed, assessor record, SOS entry, filed notice, lab report, or signed bid | → **STOP. Rule 9.** State plainly what the record says versus what was asked or assumed, and wait. Do not proceed on either reading. |
| The **L&I notice and the PSCAA notification disagree** — dates, windows, work hours, quantities, owner or contractor identity | → **STOP.** Resolve before anything else proceeds. Inspectors pull both; they must read as one project. Check before *and* after every filing. |
| Agrees | → **Q6** |

## Q6 — Is it stale?

| | |
|---|---|
| Read from a task log, addendum, bulletin board, or staged draft | → **Point-in-time snapshot, not state.** Re-verify in Gmail / `Downloads\` / the ledger before reporting any status. Ryan and Michael act outside sessions. |
| A regulation with no effective date checked | → back to **Q4**. Correctly retrieved but superseded is still wrong — and the superseded version is usually better represented in the model than the current one. |
| Current | → **Q7** |

## Q7 — Where is it going?

| Destination | Provenance |
|---|---|
| **Internal** — chat, job file, memory bank, ledger | **Required, alongside the value:** filename, message id, ledger URL, print-notice PDF and its Submitted stamp. A value with no source is invalid, not merely unsourced. |
| **Outbound** — client, regulator, third party | **Prohibited in the document body.** Bare facts only; no cross-references, no "per the field log." The cover email says only that the document is attached. The audit stays in the job file. The provenance gate will deny the send if a value has no tool result behind it. |

---

## Absolute stops

No judgment call, no exceptions:

1. **No source → `NOT IN RECORD`.** Not a best guess, not an estimate, not a range.
2. **A PSCAA fee not pulled from the ledger.** Do not estimate, ever.
3. **An L&I status resting on an email** — its presence or its absence.
4. **A conflict with the public record or a filing** — surface it and wait.
5. **A Class 3 judgment** — legal or worker-safety consequence goes to a human.
6. **Two agency filings that disagree** — resolve before proceeding.
7. **A document design rebuilt visually** rather than rendered from the canonical code.

## Never

- Treat confidence as evidence. Fluency and accuracy come from the same process.
- Treat re-asking Claude as verification. It samples the same machinery and reproduces the error at
  the same confidence. Verification means a different path: the agency, the ledger, the portal, the file.
- Treat Claude's own earlier statement as corroboration of the same value. Internal consistency is
  not corroboration.
- Fill a gap in order to be useful. "I don't know" is a complete and preferred answer.
- Re-raise a question closed in `SETTLED_CONCLUSIONS.md`. Contradicting evidence is a rule 9
  conflict to surface, never a quiet reopening.

---

## The one-question version

> **Could I have produced this without looking at anything?**
>
> If yes, it came from the model, not the record. Go get the record.
