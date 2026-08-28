# Progress

## Project: Fully Integrated Software for Ajera

### Beta Testing

| Workstream | Status |
|---|---|
| Logistical measurements | In progress |
| Complete field survey input data sweep | In progress |
| Bluetooth printer labeling (part of field sweep) | In active use / under test |

### Log

- **2026-07-31** — Memory bank initialized. Beta testing of the fully
  integrated Ajera software is underway. Running both the logistical
  measurements and the complete field survey input data sweep, including
  use of the Bluetooth printer for labeling.
- **2026-07-31 (later)** — Michael flagged job **26-6080** ("new shoe"
  property survey): plan is to beta test the current build on the
  property together, without waiting for completed samples. Claude is to
  preload property info from public database sites. Note: this session
  started from an EMPTY repo — a prior session's memory (which reportedly
  had the 26-6080 context) was never pushed here and could not be found
  in Gmail, Drive, or Calendar. Drive connector was erroring. Waiting on
  Michael for the property address/parcel to do the public-records
  preload. Standing instruction recorded: log every session start/end to
  this memory bank.

- **2026-07-31 (evening)** — Memory recovery from the prior session
  (session_01PXFUHG9rX24QDRbbcDAtft) never arrived: after three checks
  over ~40 minutes, no branch or commits were pushed by it. Recovery
  abandoned as moot — Michael supplied the address directly
  (6080 40th Ave NE, Seattle; house number still to be confirmed, see
  job-26-6080.md) and the public-records preload is done to the extent
  this environment's network allows.

- **2026-08-03** — FIELD DATA RECEIVED for job 26-6808. The app's
  "upload to server" uploads to Google Drive → "Field Uploads" →
  "26-6808" (folder https://drive.google.com/drive/folders/1NXaYamRn2iJeVi7GlQCJB3uyVtgdThI4).
  Inspection was done on-site 2026-07-31 (GPS 47.677876,-122.284993).
  Received: data.json manifest, generated AHERA report HTML, front photo
  (20.6 MB), exterior spin video (24.5 MB). Job number confirmed
  **26-6808** by the app itself.
  BETA FINDINGS: (1) app says "download ZIP" but user can't locate the
  ZIP on the phone; (2) upload succeeds but app gives no link/confirmation
  of WHERE it went — Michael thought it failed; (3) two duplicate upload
  batches (20:41 and 21:05 UTC) created duplicate files — no dedupe;
  (4) Dining-room video is listed in the manifest but was NOT uploaded
  (only exterior video arrived) — possible large-file upload failure;
  (5) samples[] is empty (expected — beta run without samples);
  report HTML shows placeholders for narrative and lab summary.

- **2026-08-03 (later)** — Full review of 26-6808 field data completed
  (44 verified findings, see beta-findings-26-6808.md). Headline:
  Dining-room video was recorded but lost by the upload pipeline —
  recover from phone ASAP. Client/contact fields blank; interior
  coverage 2 of ~11 rooms; app needs upload verification/receipts/
  dedupe. Data that arrived is internally consistent and correct.

- **2026-08-04** — CORRECTIONS APPLIED (what was fixable remotely):
  (1) `26-6808-data-CORRECTED.json` uploaded to Drive Field Uploads/
  26-6808 — client/contact filled (SREG, Heidi Walsh, Adrian Chu),
  address completed with ZIP 98115, inspector full name + AHERA cert
  #NES-BIR-20260313-31 exp 03/13/2027, room names trimmed, per-file
  upload status marked (dining video flagged missing). Originals kept.
  (2) `26-6808-ahera-survey-CORRECTED-DRAFT.html` uploaded — full
  house-style report draft with corrected cover, all boilerplate
  sections restored, clear DRAFT banner and pending-work placeholders,
  media table linking Drive files. (3) Gmail DRAFT (not sent) created
  replying to the SREG thread with a status update — Michael must fill
  the bracketed dates and 5525 35th status, then send.
  NOT fixable remotely: recovering the dining-room video (on the
  phone), the remaining interior survey/stills, sampling, narrative
  dictation, in-app field values (app DB is on the phone), app code
  fixes, Drive duplicate cleanup (no delete access — left in place).

- **2026-08-14 (Fri, PT)** — Job **26-3011** (3011 70th Ave SE, Mercer
  Island). _[Superseded — Michael filed everything himself that night;
  see the 2026-08-21 entry.]_ Michael asked Claude to take over the desktop and extend both the L&I
  and PSCAA notifications through **August 17**, work hours **11:00am to
  8:00pm**. **NOT FILED** — no desktop/computer-use tool is connected,
  and this environment's network policy denies both agency hosts at the
  proxy (`secure.lni.wa.gov:443` and `secure.pscleanair.org:443` each
  answered `403 to CONNECT`), so headless access is blocked too. All
  identifiers, current filed values, and the exact fields to change are
  written up in `job-26-3011.md` for Michael to enter himself.
  **Flagged a live compliance gap**: the L&I notice (form
  249615#452111284) still ends **8/11** — its last amendment was 8/4 —
  while PSCAA went to revision **-5** on 8/12 and the calendar carries
  work entries on **8/12 and 8/14**. The L&I extension needs to cover
  8/12–8/17, not just 8/15 forward.

- **2026-08-14 (Fri evening PT)** — HOLD SCHEDULE from Michael:
  - **26-3011** (3011 70th Ave SE): both the L&I and PSCAA notifications
    **on hold Sat 8/15**. Work resumes Sun 8/16 and Mon 8/17. So the
    pending extension should list work days 8/12, 8/13, 8/14, 8/16,
    8/17 — **not** 8/15.
  - **"The 4plex" = job 25-4509**, 4509 Eastern Ave N, Seattle 98103
    (confirmed by Michael; the L&I notice records prior use as
    "Residential - fourplex (4 units)"). On hold **Sat 8/15 and Sun
    8/16**, **off hold Mon 8/17**. ⚠️ Its filed notice runs **8/15 to
    8/21** — work was noticed to START 8/15, the first held day — so
    both filings need the start moved **8/15 → 8/17** (end 8/21 and
    hours 11:00am–8:00pm unchanged), leaving work days 8/17–8/21.
    Time-sensitive: a delayed start is normally reported before the
    noticed start date, so this wanted filing 8/14 evening, not after
    the weekend. See `job-25-4509.md`.
  - Nothing filed — agency portals remain blocked from Claude sessions
    (see Known Environment Limits). Michael files; Claude records.
  - Timezone note: Michael speaks Pacific; session clocks read UTC and
    can already be on the next date. "Tomorrow" said Fri evening 8/14
    PT = **Sat 8/15**.

- **2026-08-21** — 26-3011 CLOSED OUT. Michael sent the **Letter of
  Completion (clearance letter)** and the **invoice** to Sam Ardekani on
  **8/20**; invoice `Invoice_26-3011_TrendNW.pdf`, **$7,198.45** (ACM
  removal + WA sales tax + PSCAA notification fee passed through).
  Verified against Gmail. All four filings from the 8/14 request went
  through: L&I 249615#452111284 amended 8/16 to **7/27–8/17, 11am–8pm,
  except 8/2, 8/3, 8/10, 8/13, 8/15** (Saturday hold correctly
  excluded), and PSCAA **202603095-6** approved 8/16. The 8/11-vs-8/12
  coverage gap flagged on 8/14 is resolved.
  ⚠️ **OPEN — invoice re-issue**: Sam replied 8/20 10:37 PM PT asking
  for the bill to be re-written to **Manni Batra, mannibatra@gmail.com**
  (homeowner, same address) — he writes the check. Same amount. Reply
  was still unread and no re-issued invoice sent as of this update.
  ⚠️ **OPEN — 25-4509 (4plex) end date**: its 8/14 L&I amendment left
  the dates at **8/15–8/21** — the start was never moved to 8/17 and no
  exception list was recorded for the 8/15–8/16 hold. The unrecorded
  hold is harmless (noticed-but-not-worked), but the notice **expires
  today, 8/21**. If the hold pushed work later, an amendment is needed
  before any work on 8/22+. Completion status unconfirmed.

### Open Decisions

- **2026-07-31** — Michael is considering a dedicated Google account just
  for the Ajera survey app (survey data + client files only), separate
  from personal (rbm499@gmail.com) and company (aaadnwinc@gmail.com)
  accounts. Motivation: too many Google accounts involved; yesterday's
  memory notes may be stranded in a different account's Drive. Claude's
  recommendation: keep this GitHub repo as the memory source of truth;
  a dedicated account (or dedicated shared Drive folder) is fine for
  client files, but pick ONE and connect only that one. Not yet decided.

### Known Issues

- **2026-07-31** — Google Drive connector erroring on all calls
  ("operation not implemented/enabled"). Note the connected Gmail in this
  session is aaadnwinc@gmail.com while the session profile email is
  rbm499@gmail.com — account mismatch is the likely cause of both the
  Drive errors and the missing memory from yesterday's session.

_None recorded yet._
