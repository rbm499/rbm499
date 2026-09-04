# AHERA Field Survey

A single-file web app for collecting site survey data in the field on a phone or
tablet — built for AHERA asbestos surveys plus general site survey observations.

**Live app:** open `ahera-survey.html` in any browser, or use the published
Claude artifact link from the session that created it.

## Features

- **Site tab** — facility, address, inspector, accreditation number, survey date, notes.
- **Rooms tab** — AHERA room capture: one entry per functional space, with any
  number of suspect materials inside it (Surfacing / TSI / Miscellaneous),
  quantity, condition (Good / Damaged / Significantly Damaged), friability,
  sample IDs, notes, and photos.
- **Survey tab** — general observations beyond asbestos: location, category,
  condition, notes, photos.
- **Sessions tab** — report preview, CSV and JSON export (copies to clipboard
  for pasting into Excel / Google Sheets), and an archive of past sessions.
- **New Session button** — archives the current survey and starts a clean one,
  so old data never blocks a new job.
- Works offline once loaded; everything saves automatically to the device
  (localStorage). Photos are compressed on-device to fit a full day of rooms.

## Getting it on a tablet or phone

Open the app link in the device's browser, then use the browser menu →
**Add to Home Screen**. It then opens like a regular app, works without signal,
and keeps its data on that device.

## Tech

No build step, no dependencies — one HTML file with vanilla JS and CSS,
Google Fonts (Barlow / Barlow Semi Condensed / IBM Plex Mono), light and dark
theme support.
