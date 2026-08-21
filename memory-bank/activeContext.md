# Active Context

_Last updated: 2026-08-21_

## Current Focus

Beta testing of the **fully integrated software for Ajera**.

We are currently mid-beta, running two workstreams in parallel:

1. **Logistical measurements** — capturing and validating the logistics-side
   measurement data through the integrated system.
2. **Complete field survey input data sweep** — a full end-to-end pass of all
   field survey input data through the software, exercising every input path.

The field sweep includes live use of the **Bluetooth printer for labeling**,
verifying that label printing works as part of the integrated field workflow.

## State

- Beta testing: **in progress** (not yet complete).
- Both the logistical measurements and the field survey data sweep are
  actively underway.
- Bluetooth printer labeling is part of the current test scope.

## Active Job: 26-6080 — "New Shoe" property survey

- Job number: **26-6080** (name as spoken: "new shoe" property — exact
  spelling/address NOT yet confirmed in writing; get this from Michael).
- Plan: run beta testing of the integrated software **on the property,
  together**, using the current build — this can proceed even though the
  samples are not completed yet.
- Claude's task: **preload the property information from public,
  verifiable database sites** (county assessor / parcel records, permits,
  etc.) into the job before the on-site visit.
- BLOCKED on: property address (or parcel number + county) — not found in
  Gmail, Drive, or Calendar as of 2026-07-31. Google Drive connector was
  also erroring ("operation not enabled") this session.

## Job 26-3011 — 3011 70th Ave SE, Mercer Island — **COMPLETE**

Closed out 2026-08-20: Letter of Completion + invoice ($7,198.45) sent to
Sam Ardekani. Notifications finished clean (L&I 7/27–8/17; PSCAA
202603095-6). See `job-26-3011.md`.

- ⚠️ **Open**: Sam wants the invoice re-issued to the homeowner,
  **Manni Batra, mannibatra@gmail.com**, same amount. Not yet sent.

## Active Job: 25-4509 — 4509 Eastern Ave N, Seattle ("the 4plex")

See `job-25-4509.md`. Prime Development / Andrey Gidenko, demolition
abatement. PSCAA 202603370-1, L&I form 250366#271950864.

- Was on hold 8/15–8/16, back on 8/17. PSCAA went to **-2** and L&I was
  amended 8/14, but the **dates were left at 8/15–8/21** — the start
  never moved and the hold was never recorded as an exception.
- ⚠️ **The notice expires 8/21.** Any work on 8/22+ needs an amendment
  filed first. Completion status unconfirmed — ask Michael.

## Known Environment Limits (recheck each session)

- No computer-use / desktop-control tool is connected. Claude cannot
  operate Michael's machine or browser. Requests to "take over the
  desktop" cannot be fulfilled — Claude prepares the values instead.
- Agency portals are blocked by network policy: `secure.lni.wa.gov` and
  `secure.pscleanair.org` both return 403 at the agent proxy. Regulatory
  filings therefore cannot be submitted from a Claude session at all.

## Standing Instructions from Michael (PERMANENT)

- **No invoice numbers (set 2026-08-21).** The **job number** is the single
  controlling identifier for a job — site, notifications, invoice, payment,
  and the ACH auto-responder all key off it. A separate invoice number is a
  confusing second identifier for the same thing and is no longer used.
  Invoices carry the job number only. Do not reintroduce one, and do not go
  looking for historical invoice numbers when re-issuing.

- At the **end of every session** (and check at the **beginning** of every
  session), log everything we did into this memory bank and push it to the
  `rbm499/rbm499` repo so nothing is lost between sessions. A copy may
  also be kept in Google Drive when the Drive connector works.
- Claude sessions do not retain memory on their own — this repo is the
  memory. Read `memory-bank/` FIRST at the start of every session.

## Next Steps

- Get the exact property address (or parcel #/county) for job 26-6080
  from Michael, then preload public-record property data into the memory
  bank and the job.
- Do the on-property beta test of the integrated software with Michael
  (current build, samples not yet required).
- Continue the field survey input data sweep and logistical measurements.
- Log any issues found with the Ajera integration or the Bluetooth printer
  labeling in `progress.md` as they surface.
