# Beta Test Findings — Job 26-6808 Field Data Review (2026-08-03)

Full multi-agent review of the app's data export, the generated AHERA
report draft, field coverage, and the upload pipeline. 44 findings
confirmed by adversarial verification. Deduplicated summary below.
Raw results: session workflow wf_12fef8d7-7a7.

## 🚨 URGENT — data recovery

1. **The Dining-room walk-through video was recorded on-site but never
   uploaded** (3 upload attempts, none contains it; GPS timestamp
   2026-07-31T20:24 proves it was captured). It is the ONLY interior
   video for this job. **Recover it from the phone before it is lost**
   (app storage / camera roll), then re-upload or transfer manually.

## Blockers for delivering the 26-6808 report

- `client` and `contact` are blank in the export → report cover
  "PREPARED FOR:" and "CONTACT:" render empty, and the $850+lab invoice
  has no bill-to. Fill: Specialty Real Estate Group / Heidi Walsh
  (heidi.walsh@sregusa.com, 425-229-9375) / Adrian Chu.
- Narrative (building description) empty — placeholder remains in
  report. Dictate in app: Review → Survey report details.
- Interior coverage: only 2 of ~11 spaces logged (Dining room, Family
  room). No bedrooms (4), bathrooms (2), kitchen, basement/crawl, or
  attic. Zero interior stills anywhere; Family room has no media at all.
- Samples deferred (intentional for beta) — full sampling visit still
  required for the deliverable.
- Inspector recorded as surname only ("Neureiter"), no AHERA cert
  number/expiration anywhere in the export or draft.
- Address missing ZIP: "6808 40th Ave NE Seattle WA" → should be
  "6808 40th Ave NE, Seattle, WA 98115" (propagates to cover, COC,
  invoice).
- Reports were committed to Heidi for Jul 28–29; now 5+ days past.
  Consider a status note to Heidi/Adrian.

## App defects (developer punch list, ranked)

1. **Manifest written before upload confirmation and never reconciled**
   against what actually landed → silent data loss (the lost video).
   Fix: verify each file after upload, retry failures, and only then
   write/refresh the manifest; surface per-file status.
2. **No upload receipt** — app never shows WHERE files went (Drive →
   Field Uploads/26-6808) or a link → user thinks upload failed and
   retries (root cause of the triple-upload thrash). Fix: success screen
   with folder link + file checklist.
3. **Retries create full duplicate batches** — no idempotency/dedupe/
   versioning. Fix: overwrite-or-version by filename, or content hash.
4. **ZIP "download" unfindable on the phone.** Fix: use share sheet or
   show the saved path; on Android it likely lands in Files → Downloads.
5. **27.5 MB report HTML** (20.6 MB photo base64-embedded) — unmailable,
   slow to open. Fix: compress/resize embedded images (~200 KB each),
   link large media instead of embedding.
6. Report references walk-through videos that were never delivered.
7. Unsanitized input: trailing space in "Dining room " propagates into
   IDs, filenames, captions — plausible contributor to the lost-file bug.
8. Export allowed with required client fields empty — no validation
   warning; likewise a room with zero media exports silently.
9. Raw full-res media uploaded (20 MB photo, 24 MB video) — add a
   field-appropriate compression tier for cell uploads.
10. Timestamps rendered in local time without timezone; duplicate
    batches distinguishable only by exportedAt.

## Report-template gaps vs house style (26-5917 benchmark)

- Cover missing: Project/Job No., "Prepared By" block, phone/email
  header, inspector cert #/expiration.
- Structurally absent (in readable portion): Sampling Requirements
  (minimum counts), Survey & Analytical Reference Guide (terms table),
  report-kept-on-site statement.
- Unverifiable (report text after PROPERTY PHOTOGRAPHS not retrievable —
  27 MB embed): results tables, disclaimer, certification, signatures,
  appendix index. Check these on-screen in the app.
- Style: ISO dates vs house MM/DD/YYYY; address punctuation.
- New (good) additions not in house style: on-site GPS verification
  field, photo grid, report key.

## What checked out fine

- Both upload batches byte-identical — no data divergence from the
  duplicate uploads. Job number (26-6808), inspection date (7/31), GPS
  (matches 6808 40th Ave NE), lab block (Triangle/TESC, PLM
  EPA 600/R-93/116), reg/contractor numbers all correct and consistent.
