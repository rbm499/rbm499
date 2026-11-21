# comms-capture — design, decisions, and what is and is not verified

Purpose: client texts to Michael's phone number are business records (bids, change orders, timelines,
invoicing). This captures them automatically, keeps private and sensitive texts out entirely, files the
rest into the job's electronic folder, asks a person only when a job number cannot be determined, and
makes sure no client message that needs an answer sits unnoticed.

Labels used below follow the house rules: **RECORD** = a tool result or document this session said it;
**INFERRED** = converged reasoning, with the points named; **NOT IN RECORD** = nothing supports it.
Numbers marked *(INFERRED default)* are starting values the builder chose, not decisions — they live in
`server/commscap/config.py` and are Ryan's to set.

## 1. Flow

```
Michael's phone (Android agent)                      Office service                      Job folder
────────────────────────────────                     ──────────────                      ──────────
every SMS / MMS / RCS notification
  → redact (cards, SSN, accounts, passwords)
  → ON-DEVICE GATE ─ drop ─────────────► nothing leaves; a counter ticks
       │ defer (wait for thread to prove business)
       │ hold  (photo only, unknown number)
       └ send ──► durable queue ──signed──► ingest: re-redact, SERVER GATE (re-check)
                  (kept until acked)          → durable commit, answer "accepted"
                                              → AI screen (Claude; keyword fallback)
                                                 personal / sensitive / automated ─► delete row,
                                                      keep only a content-free audit line;
                                                      unknown number excluded from then on
                                                 unclear (unknown) ─► held unseen ≤72 h
                                                 business ─► associate to a job
                                                       sure ─► file ───────────────► Communications/
                                                       not sure ─► review queue (Ryan, one tap)
                                              → reply clock starts (independent of the job match)
nudges, policy, "send me this photo"  ◄──────  heartbeat reply
```

## 2. Screening policy (who sees what)

| Situation | On phone | Server | Shown to office? |
|---|---|---|---|
| Number matches a client in the job register | send | screen (heuristic if AI down) → file/queue | yes |
| Crew / vendor / agency number (set in review page) | send | **AI screen required** (crew texts include private chatter) | only if business |
| Unknown number, text has a business signal (bid, asbestos, address, job no. …) | send | AI screen | only if business |
| Unknown number, no signal ("ok", "yes") | **defer** ≤24 h; sent only if that thread later proves business | – | no |
| Unknown number, photo only | **hold** ≤7 days, never auto-uploaded | – | no (counted in the daily digest) |
| Saved personal contact, not a client | **drop** (unless the text carries a job number `26-####`) | – | never |
| Short-code / alphabetic / email sender, one-time codes | drop | re-checked | never |
| Business text containing a sensitive aside | send | filed, **text hidden** in every screen/alert (policy `file_hidden`; `drop` also available) | no, topic only |
| AI says personal / sensitive / automated | – | row deleted, audit line only; unknown number excluded; its earlier held texts purged | never |
| Michael taps **This was private** | purge + exclude | same, on the server | never |

Site access information (gate/door codes) is deliberately **not** treated as a secret or a one-time code.

## 3. Failsafes ("multiple" — each layer reports on a different failure)

| Failure | Layer that catches it | What happens |
|---|---|---|
| Server down / network down | Phone queue | Phone keeps every unsent text; retries with backoff to 15 min; deletes only on `accepted`. Server outage never loses data. |
| Phone app killed, permission revoked, battery restriction | Heartbeat every 15 min carries permission/battery state | Alert to office after 45 min (business hours) / 3 h (off hours); specific alert per revoked permission. |
| Observer missed a message | 15-min catch-up scan + boot scan on phone | Re-reads the system SMS store from a persisted cursor. |
| Anything still missed | Nightly reconcile (phone lists uids it passed; server answers what it lacks) | Missing texts re-sent; a count is reported; overdue reconcile alerts after 36 h. |
| Rejected/private text coming back | `seen_uids` | Purged and rejected uids are "known" to reconcile, so a deliberate drop is never resurrected. |
| AI down / refuses / garbage | Screener never raises | Known clients keep flowing via keyword heuristic (flagged for AI re-screen); unknown numbers wait unseen in `pending_ai`; alert after 30 min. |
| Job folder missing / Drive offline | Filer | Message goes to `_COMMS_UNFILED/<job>/` (never invents a job folder) or `file_failed` retried every tick; alert raised. |
| Client message nobody answered | Reply clock | Ladder: nudge Michael's phone → alert Ryan → overdue alert repeated every 12 h. Urgent messages run on the wall clock and alert at once. |
| Nudge never displayed | Ack in next heartbeat | Phone online but no ack after 30 min → alert Ryan. |
| Reminder after Michael already replied | Reply detection + "Handled" | Outgoing text to that number resolves the item and withdraws queued reminders. |
| Text waiting for a job number too long | Review-queue ageing | Alert after 4 business hours. |
| Phone and server disagree on ids / clocks drift | uid check, skew check | Accepted anyway (nothing dropped over an integrity check) but alerted. |
| The whole thing silently stops | Daily digest at 7 PM (counts only) + optional dead-man ping URL | Silence of the digest is itself the alarm; `COMMSCAP_DEADMAN_URL` pings an external monitor each tick. |
| Misfiled by the automatic matcher | "Wrong job?" on the review page | Correction appended to the old transcript (history never rewritten), filed to the right job. |

## 4. Privacy model

* Nothing leaves the phone unless the on-device gate says `send`. Dropped messages are never stored — not
  even a hash — only a counter.
* The server stores a message only after it passes screening (or while waiting for screening). Private
  verdict → row deleted. Held unclear texts expire after 72 h without a trace.
* Alerts, digests and nudges never contain message text — only counts, masked numbers, contact names, job
  numbers and a topic label.
* Michael sees what was sent on his phone, can mark any contact private, and can pause capture; a pause is
  reported (alerts if > 4 h).
* The review page builds the DOM from text nodes only (message text is attacker-controlled).
* **Residual exposure (honest):** a text from an *unknown* number that contains a business word is read by
  the AI screen before it is judged private. The gate keeps that list specific, but it is not zero.
* **NOT IN RECORD:** Anthropic's data-retention terms for this account's API traffic were not looked up.
  Messages that pass the gate are sent to the Claude API for screening; confirm the account's retention
  setting before relying on "private texts never leave".

## 5. Legal — Class 3, a human decides (evidence trail)

* This tool records communications of third parties (clients) and, if enabled, Michael's replies.
* Washington regulates recording of private communications; **the statute text was NOT retrieved**:
  `app.leg.wa.gov`, `apps.leg.wa.gov`, `law.justia.com`, `courts.wa.gov` and `atg.wa.gov` all failed to
  resolve from this session on 2026-11-21 (network allow-list). So no statement of what the law requires is
  made here. Needed: allow one of those hosts and retrieve the text, or have counsel review, **before** this
  is switched on for real traffic. Candidate mitigations for a lawyer to weigh (not advice): a notice in
  Michael's signature / bid template that texts are kept as business records; limiting capture to the
  business line.

## 6. Defaults that are mine, not Ryan's *(INFERRED defaults — change in `config.py`)*

Business hours Mon–Sat 07:00–19:00 PT · reply ladder 120 / 240 / 480 business minutes (urgent: 0 / 60 /
180 wall-clock) · overdue repeat 12 h · auto-file threshold 0.80 with 0.25 margin over the runner-up ·
heartbeat gap 45 min (hours) / 180 min (off) · held-unclear 72 h · defer 24 h · business-term list
(`gate.py`). The house's own pipeline thresholds (bid sent → nudge at 5 days etc.) were set by Ryan on
2026-10-21 and are a different clock; they are not reused here.

## 7. Real-register check (RECORD: loader run on JOB_PIPELINE.json as of 2026-10-21; aggregates only)

43 jobs; 40 with a phone; the loader extracts **26 distinct client numbers** (8 phone fields held several
labelled numbers each); 41 of 43 sites are address-matchable; one job has no contact, one has no job number;
`26-1036` is shared by two jobs. Jobs per client number: 7, 6, 6, 3, 2, 2, 2, 2, 2, then sixteen with 1.
**A bare text with no job number, address or history auto-files for 17 of 26 numbers — the single-job
clients. The 9 that go to the review queue are the busiest clients.** Expect Ryan's one-tap queue to be
used mainly by them, until a conversation has been assigned once (then thread continuity carries it for
36 h) or the client names an address/job number.

## 8. Verification status

| Piece | Status |
|---|---|
| Gate, redaction, phone normalisation, signing, message ids | Python reference passes its own shared vectors (RECORD: pytest, 158 tests). |
| Screening / association / filing / reply clock / health / API / review page | Tested end to end with synthetic data and a scripted screener; page loaded in headless Chromium at phone and desktop width, no console errors. |
| **Live Claude call** | **NOT RUN** — no API key in this environment. Request shape follows the current API reference (JSON-schema output, no forced tool choice, refusal handled, fallback beta with a plain retry). First real call will tell. |
| Android core logic (gate etc.) | See `android/` report — Kotlin core tested against the same vectors here if the agent report below says so. |
| **Android app module** | **NOT COMPILED HERE** — Google's Maven (`dl.google.com`) is unreachable from this environment. Compiles only in CI (GitHub Actions); never run on a device. |
| **Michael's phone type** | **NOT IN RECORD.** Everything phone-side assumes Android. |
| Windows deployment (MSI laptop) | Not tested; paths are plain `pathlib`. The laptop has logged five unexpected shutdowns (10/22 inventory) — the phone queue is the durable buffer, and the digest/dead-man ping covers a dead server. |
| Drive API filer | **Not built.** The filer writes to a local folder (the Drive-synced `Job sites` directory); a cloud-hosted server would need a Drive-API filer. |
| Calls / voicemail | Out of scope; "Handled" button covers a phone-call reply. |
| RCS | Inbound only, via notifications. Outgoing RCS cannot be captured; recommended setting is RCS chats **off** on Michael's phone. |
| Media-only texts from unknown numbers | Held on the phone, not uploaded (a vision screen is a later option). Lesson in the record (10/22): empty-body sends from a new client can only be found by sender, not keyword. |
