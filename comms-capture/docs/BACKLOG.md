# comms-capture — update backlog (collect first, then ship ONE comprehensive update)

Status 2026-11-22: nothing here is built. Sizes are the builder's rough estimates (INFERRED): **S** = a few hours, **M** = about a day,
**L** = several days. "Needs" = something only a person (or the real phone/real data) can supply. Cross out, add, reorder.

## A. Asked for, not done yet
1. **Reply / text from the app.** A: Claude drafts a suggested reply under each waiting text; you copy it or tap "Open in Messages"; Michael sends it (S–M, no new phone permission).
   B: send from the office page, via Michael's phone, with approval gates (phone shows every text sent in his name; only into existing business threads; rate limit; full log; plain SMS only) (M–L).
   C: a separate business number (Google Voice / Twilio) (L, different plan). *Needs:* which option; Michael's agreement for B; a legal view on texting clients.
2. **Show the live feed on the Claude app's home screen.** Today: the review page is installable on a phone home screen (not yet tried on the S25). Option: a pinned Claude page that reads `feed.json` from Drive when opened (M, not live). *Needs:* is the home-screen icon enough?
3. **Alerts that reach you when the page is closed.** Easiest: push to Ryan's phone through ntfy / Pushover / Slack (S). True browser push (M). *Needs:* which channel.

24. **Backfill: use 2026 (Jan 1 to today) as the text backlog** (asked 2026-11-27). Today the phone app starts from "now" and never uploads history
    (verified in the source), and the nightly check never looks before capture was switched on, so this is a separate, deliberate feature (L):
    - *Phone:* an "Import 2026 history" button that walks the SMS/MMS store month by month (the scanner already has a read-only window reader), runs every
      message through the same gate (saved contacts never leave; unsaved numbers are screened), and uploads them flagged `backfill`. Michael sees progress
      and a summary, can cancel, and it is a one-time action that needs his explicit OK.
    - *Server:* backfilled texts are screened and filed with their original dates, but never start the reply clock, never alert or nudge per message, and
      never count as "new" in the live view. Bulk screening through the batch API (half price); the model choice is Ryan's.
    - *Matching:* the register holds only open jobs as of 2026-10-21 (closed jobs are excluded by its own definition) and lacks the five newest. Needs a
      fuller 2026 job list (the 9/18 jobs list plus the `Job sites` folder names) and "date overlap" evidence (a text dated inside a job's active window
      points to that job).
    - *Review:* a year of ambiguous multi-job clients means a large queue, so it needs bulk tools (assign a whole thread or date range to a job; "not
      business" in bulk).
    - *Expected gaps (INFERRED):* chat (RCS) conversations are not in the phone's SMS/MMS store, so any 2026 conversation held over RCS cannot be recovered
      this way; MMS photos need a per-file upload; texts deleted earlier are gone.
    - *Needs:* Michael's explicit OK for a one-time read of his 2026 messages; the fuller job list; a model/cost decision; whether RCS chats were on in 2026.

25. **Beta safety kit** (needed before the first real beta): a **pilot-only mode** (`unknown_policy = "off"`: unsaved numbers that are not on the pilot list
    never leave the phone; Python + Kotlin + shared vectors); a **shadow / dry-run mode** (screen and match but write only to a sandbox folder, nothing into real job
    folders); a **sandbox switch** for `COMMSCAP_JOBS_ROOT`; an **integrity report** command (phone vs server counts, duplicates, each pilot text compared with its
    filed copy, redaction-only differences listed); and a **rollback script** that removes only what the system created (`Communications/` folders and
    `_COMMS_UNFILED`) (M).
26. **Remove-on-private for filed text:** when a contact is marked private after filing, remove or tombstone those blocks in the job transcript (and say so in the
    transcript), keeping the append-only guarantee for everything else. *Needs:* a policy decision (a filed record being edited at all) (S–M).

## B. Gaps found while building/testing
4. Street-name matching: "the Phinney job" should be a strong hint toward that job (it is not matched today) (S).
5. Run the server tests in CI (CI builds and tests only the Android side today) (S).
6. "New job" from the review queue, for new customers (create a stub / link to the register) (M).
7. Set crew / vendor / agency numbers from the page (the API exists, there is no button) (S).
8. In-app "this is a client" button on the phone (README currently relies on a Contacts label) (S–M; check what the app already offers).
9. Search and history: find any text by client / job / date / keyword; export a job's texts as a PDF (M).
10. Photo-only texts from new numbers: screen the image (today they are held on the phone, not uploaded) (M).
11. Group texts, multi-recipient and large/MMS attachments — needs testing on the device (M).

## C. To serve what you said matters: bids, invoicing, change orders, timelines
12. **Commitments extractor:** pull prices, dates and "approved / go ahead" out of the texts, each linked to its source message and labelled INFERRED (M–L).
13. **Feed the job pipeline:** "approved / signed" proposes a stage move; client silence after a bid raises a nudge (uses the pipeline's own thresholds) (M).
14. Schedule changes in texts propose a calendar update (the MASTER calendar went stale after 7/8) (M).
15. Response-time stats per client per week in the daily summary (S).
16. Escalate to a second person if Michael doesn't reply; quiet hours / Sunday rules editable from the page (S–M).

## D. Needed to run it for real
17. Deployment package: Windows auto-start, HTTPS tunnel, database backup (M).
18. Drive-API filer, so it need not run on the office PC (M–L).
19. Keep the job/contact register fresh automatically (today's copy is as of 2026-10-21) or read jobs straight from the folders (S–M).
20. A real Claude test with labelled example texts, to measure misses and false alarms and set the thresholds (S to build). *Needs:* an API key and some real example texts.
21. A device test plan on the S25: install, Auto Blocker, permissions, sleep, restart, RCS (needs the phone).
22. Security: a real login instead of one shared token, encrypted database, per-user views, record of who assigned what (M).
23. Phone app: QR setup, a smoother update path, regenerate the committed signing key if the repo is public (M).

## E. Decisions only people can make
Michael's agreement to install · the legal question (recording / texting) · Anthropic data-retention terms for this account · where the office program runs
· the INFERRED defaults (business hours, reply minutes, match thresholds) · sensitive aside inside a business text: hide (default) or drop · unsaved numbers: screen all (default) or keyword-only · model and cost for screening a year of history · who is in the pilot (Ryan's own numbers plus any clients who agree) and whether a second phone is available.

## Parking lot (add yours below)
-
