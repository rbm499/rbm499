# First install and first run (beta)

Goal: get the office program running on the office PC and the app on Michael's S25, then watch it for a day with the safest settings.
**What was tested:** the Python steps (3–6) were run on Linux from a clean checkout on 2026-11-27: install, `new-secret`, `serve`, a signed upload over
real HTTP (accepted), a wrong signature (rejected, 401), and the review page with its token. **Not tested:** Windows, the tunnel, the phone, real texts.

## What "pull the data" means today
The app captures texts from the moment it is switched on. It does **not** import old texts (the 2026 history import is backlog item 24).
So the first run is live capture going forward.

## Before you start (people decisions, not technical)
1. **Michael agrees** to install it. He sees everything it sends and can pause or uninstall at any time.
2. **Legal:** Washington's recording statute was not retrieved (DESIGN.md section 5). Decide before real traffic.
3. An **Anthropic API key**. Without one, texts from numbers not in your job register sit unscreened in the database (hidden, never filed, not expiring).

## Safe first-run settings
* **Sandbox job folders:** make a folder such as `C:\commscap-test\Job sites` containing empty folders named like real jobs (e.g. `26-4708 1021`). Point
  `COMMSCAP_JOBS_ROOT` there. Nothing is written into the real `Job sites` until you change it.
* **Strict unsaved-number mode:** `COMMSCAP_UNKNOWN_POLICY=keyword` (only texts with a business word from unsaved numbers leave the phone).
* **Phone Contacts complete:** family and friends saved, or their texts look like new customers.
* Use `JOB_PIPELINE.json` from Drive (it is dated 2026-10-21 and is missing five newer jobs; expect more texts in the review queue).

## Steps on the office PC (PowerShell)
1. Install Python 3.11+ and Git. Get the code: `git clone -b claude/bold-cerf-ayfhww https://github.com/rbm499/rbm499 C:\comms-capture`
2. Get an HTTPS address the phone can reach (the app refuses plain http). Example: a Cloudflare quick tunnel, `cloudflared tunnel --url http://localhost:8787`,
   which prints an `https://...` address (**untested here; the address changes each time the tunnel restarts**, and then the phone's setup text must be redone).
   Tailscale Funnel or a reverse proxy also work.
3. `cd C:\comms-capture\comms-capture\server` then `py -3 -m venv .venv`, `.venv\Scripts\Activate.ps1`, `pip install -e .`
4. `commscap new-secret --device michael-phone-1 --url https://YOUR-HTTPS-ADDRESS` prints a secret line and the **setup text** for the phone. Treat both as passwords.
5. Set the settings (same PowerShell window):
   `$env:COMMSCAP_DEVICE_SECRETS="michael-phone-1:<the secret>"`, `$env:COMMSCAP_UI_TOKEN="<a long random string>"`, `$env:COMMSCAP_JOBS_ROOT="C:\commscap-test\Job sites"`,
   `$env:COMMSCAP_REGISTER="C:\path\to\JOB_PIPELINE.json"`, `$env:COMMSCAP_UNKNOWN_POLICY="keyword"`, `$env:COMMSCAP_DATA_DIR="C:\commscap-data"`, `$env:ANTHROPIC_API_KEY="<key>"`
6. `commscap serve --host 127.0.0.1 --port 8787` (leave it running; the PC must not sleep).

## Steps on Michael's S25
Follow `android/README.md` steps 1 to 9 (download the APK from the CI run, allow install, Allow restricted settings, permissions, paste the setup text,
turn RCS chats off, Samsung battery settings). The status screen should say **Capturing: ON** and show a recent upload.

## What to check
* **After 5 minutes:** open `https://YOUR-HTTPS-ADDRESS/ui` (enter the token). Capture health shows the phone heard from within the last 15 minutes.
* **A test text:** from your own number (unsaved on Michael's phone) send "Can you give me a bid for asbestos testing?". It appears under Live conversations
  and, if it names a known job or client, a transcript appears under `...\Job sites\<job>\Communications\`.
* **A private text:** send something personal with no business words from an unsaved number. Expect it **not** to appear anywhere.
* **After a day:** the 7 PM summary (outbox folder in the data directory) counts what was filed, queued and discarded. Spot-check a few filed texts against the phone, word for word.

## Stopping and rolling back
Pause in the app (or uninstall: that removes everything the app holds; Michael's texts are untouched). Stop the server. Delete the sandbox `Communications` folders.
