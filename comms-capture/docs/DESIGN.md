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
| Unknown (unsaved) number, any text | **send** (`unknown_policy = ai_all`, the default) | AI screen decides; personal → deleted | only if business |
| …same, strict mode (`unknown_policy = keyword`) | send only with a business signal (bid, asbestos, address, job no. …); otherwise **defer** ≤24 h, sent only if the thread later proves business | AI screen | only if business |
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
| The whole thing silently stops | Daily digest at 7 PM (counts only) + optional dead-man ping URL | Silence of the digest is itself the alarm; `COMMSCAP_DEADMAN_URL` pings an external monitor each tick (the ping code is **untested** — it needs a real URL). |
| Misfiled by the automatic matcher | "Wrong job?" on the review page | Correction appended to the old transcript (history never rewritten), filed to the right job. |

## 4. Privacy model

* Nothing leaves the phone unless the on-device gate says `send`. The boundary is "people Michael has saved
  are never captured unless they are clients; strangers are screened". Dropped messages are never stored —
  not even a hash — only a counter.
* The server stores a message only after it passes screening (or while waiting for screening). Private
  verdict → row deleted. Held unclear texts expire after 72 h without a trace.
* **Known gap (found 2026-11-27 by audit):** a text that was already filed to a job's transcript is **not** removed when someone later marks that
  contact private; the database row and any filed media are deleted, but the transcript is append-only. AI "private" verdicts are unaffected (they
  happen before anything is filed). Policy and a fix (a tombstone line in the transcript) are on the backlog.
* Alerts, digests and nudges never contain message text — only counts, masked numbers, contact names, job
  numbers and a topic label.
* Michael sees what was sent on his phone, can mark any contact private, and can pause capture; a pause is
  reported (alerts if > 4 h).
* The review page builds the DOM from text nodes only (message text is attacker-controlled).
* **Residual exposure (honest):** with the default `ai_all`, *every* text from an unsaved number is read by
  the AI screen before it is judged private (that is what "screen new customers by content" requires: a
  synthetic check found the keyword-only alternative silently deferred 13 of 20 plausible first texts from
  new customers). Most private contacts are saved, so the population is small, and a private verdict deletes
  it at once and excludes the number — but it is not zero. `COMMSCAP_UNKNOWN_POLICY=keyword` trades coverage
  for less exposure. A new customer Michael has already saved as a contact is treated as a saved contact:
  mark it as a client in the app (or give it the "AAAD Clients" label).
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
| Gate, redaction, phone normalisation, signing, message ids | Python reference passes its own shared vectors (RECORD: `pytest` in `server/`, 219 tests passing at last run). |
| Screening / association / filing / reply clock / health / API / review page | Tested end to end with synthetic data and a scripted screener; page loaded in headless Chromium at phone and desktop width, no console errors. |
| **Live Claude call** | **NOT RUN** — no API key in this environment. Request shape follows the current API reference (JSON-schema output, no forced tool choice, refusal handled, fallback beta with a plain retry). First real call will tell. |
| Android `core` (gate, redaction, phone numbers, signing, policy overlay, lookback, backoff, response handling) | **241 Kotlin tests pass** (RECORD: re-run from scratch by the main session, `gradle :core:test`, 0 failures). Both gate-vector sets (ai_all and keyword), the phone, redaction and signing vectors are asserted case by case. The builder also ran ~42,000 random inputs against the Python reference with 0 mismatches (throwaway test, reported not re-run). |
| **Android `:app` module** | **Compiled and assembled by CI** (RECORD: GitHub Actions run 44962502328 on commit 4052769; step "Core tests and debug APK" succeeded in ~88 s; artifact `commscap-debug-apk`, 2,536,682 bytes, digest `sha256:a7967da3…d76d`; the same job re-ran the 241 core tests). The manifest merged and resources built under AGP 8.7.3. **Never run on a device.** The APK could not be downloaded from this environment (artifact host unreachable): get it from the run page. Manifest requests only INTERNET, network state, SMS receive/read, Contacts, notifications, foreground-service (data sync), boot, and battery-optimisation exemption; no location, camera, microphone, call log or storage; `allowBackup=false`; HTTPS only (`usesCleartextTraffic=false`). |
| Phone regex engine | Android's regex engine differs from the JVM and cannot be exercised here. The core drops an unsupported flag if the engine rejects it, and the app runs a **self-check on the phone and refuses to capture** if any gate/redaction case fails — a failure is visible on the status screen, not silent. |
| Michael's phone | **RECORD (Ryan, 2026-11-22, in session): a Samsung Galaxy S25** (he first typed "s35 ultra", then corrected to "s25"; Ultra vs base does not matter here). Android, so the `android/` agent applies. OS version and which messages app it uses were not checked. Samsung-specific setup (Auto Blocker, sleeping apps) is in `android/README.md` step 9 and is **unverified on the device**. |
| Windows deployment (MSI laptop) | Not tested; paths are plain `pathlib`. The laptop has logged five unexpected shutdowns (10/22 inventory) — the phone queue is the durable buffer, and the digest/dead-man ping covers a dead server. |
| Drive API filer | **Not built.** The filer writes to a local folder (the Drive-synced `Job sites` directory); a cloud-hosted server would need a Drive-API filer. |
| Calls / voicemail | Out of scope; "Handled" button covers a phone-call reply. |
| RCS | Inbound only, via notifications. Outgoing RCS cannot be captured; recommended setting is RCS chats **off** on Michael's phone. |
| Media-only texts from unknown numbers | Held on the phone, not uploaded (a vision screen is a later option). Lesson in the record (10/22): empty-body sends from a new client can only be found by sender, not keyword. |

## 9. Phone-app behaviours worth knowing (from the build report; builder's words, not yet observed on a device)

* An incoming-SMS broadcast is only a trigger to scan the system store: the broadcast timestamp differs from the store's `date`, which would have produced a second uid and broken the nightly reconcile.
* **Capture stops (cursors do not advance) while the Contacts permission is missing**, because under `ai_all` Contacts is the privacy boundary. Texts arriving meanwhile are picked up when it is restored.
* Group MMS: every counterpart must pass the gate. A server "business" verdict never lifts a local "private" mark.
* "Pause until tomorrow" ends at 6 am. The reconcile window never starts before capture was first enabled.
* RCS/chat notifications are mapped to numbers by contact name; a title that cannot be resolved is dropped (incoming RCS from an unsaved sender with no number in the notification may therefore be missed — another reason to turn RCS chats off).
* A permanent 4xx on a batch blocks the head of the upload queue (the contract forbids deleting unsent texts); the status screen shows it. Needs a person if it ever happens.
* `targetSdk` is 34, and must stay there: **verified** against the official Android docs ("Behavior changes: Apps targeting Android 15 or higher", read 2026-11-22) that for apps targeting Android 15+ a `dataSync` foreground service is capped at 6 h per 24 h and may not be started from a `BOOT_COMPLETED` receiver — this design relies on both.
* A debug keystore is committed on purpose so each CI build installs over the previous one without uninstalling (uninstalling would delete the queue and setup). It protects nothing and is not a release key. **If this repository is or becomes public, anyone could build an update signed with that key — regenerate it and keep the private copy outside the repo.**

## 10. Live conversation view and per-message alerts (added 2026-11-22 at Ryan's request)

The review page opens on **Live conversations**: every business text in and out, grouped by client, oldest-to-newest inside each conversation, newest conversation first, polled every 10 s. Each conversation shows its job (or "no job number yet") and whether it is answered or still waiting. It lists only texts that passed screening — never dropped, held or unscreened ones — and masks sensitive text. "Mark all seen" clears the "new since you last looked" highlight (kept per browser). "Alert me on this device" uses the browser's notification permission and fires **only while the page is open** (no background push: that needs a push service and keys, not built). `COMMSCAP_ALERT_EACH_MESSAGE=on` also raises an info alert per business text through the normal alert channels (outbox file, email, webhook), carrying who/job/topic only. `COMMSCAP_FEED_EXPORT` writes the same feed as JSON so a different viewer could show it.

* **Not built:** a view inside the Claude app's own home screen. The Claude app cannot receive a live feed pushed from this service. Two real options, both small: install the review page as a home-screen app on Michael's/Ryan's phone (done: manifest + icon), or a pinned Claude page that reads `feed.json` from Drive on demand (not live; needs the service running first).
* **Verified:** 227 server tests including the feed; the page rendered in headless Chromium at phone width with no console errors. **Not verified:** the page on a real phone, the browser notification prompt, "Add to Home screen" on the S25.
* **Known limit seen in the demo:** a client who says "the Phinney job" is not matched by street name alone (the matcher needs a full address or job number), so that text goes to the one-tap queue with weak suggestions. Using a distinctive street name as a strong hint is a small, worthwhile improvement.
