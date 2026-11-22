# comms-capture — update backlog (collect first, then ship ONE comprehensive update)

Status 2026-11-22: nothing here is built. Sizes are the builder's rough estimates (INFERRED): **S** = a few hours, **M** = about a day,
**L** = several days. "Needs" = something only a person (or the real phone/real data) can supply. Cross out, add, reorder.

## A. Asked for, not done yet
1. **Reply / text from the app.** A: Claude drafts a suggested reply under each waiting text; you copy it or tap "Open in Messages"; Michael sends it (S–M, no new phone permission).
   B: send from the office page, via Michael's phone, with approval gates (phone shows every text sent in his name; only into existing business threads; rate limit; full log; plain SMS only) (M–L).
   C: a separate business number (Google Voice / Twilio) (L, different plan). *Needs:* which option; Michael's agreement for B; a legal view on texting clients.
2. **Show the live feed on the Claude app's home screen.** Today: the review page is installable on a phone home screen (not yet tried on the S25). Option: a pinned Claude page that reads `feed.json` from Drive when opened (M, not live). *Needs:* is the home-screen icon enough?
3. **Alerts that reach you when the page is closed.** Easiest: push to Ryan's phone through ntfy / Pushover / Slack (S). True browser push (M). *Needs:* which channel.

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
· the INFERRED defaults (business hours, reply minutes, match thresholds) · sensitive aside inside a business text: hide (default) or drop · unsaved numbers: screen all (default) or keyword-only.

## Parking lot (add yours below)
-
