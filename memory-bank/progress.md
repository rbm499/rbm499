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
