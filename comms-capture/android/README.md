# Comms Capture: the phone app

This app lives on the owner's Android phone. It reads business text messages and sends them to the office
service so they can be filed with the right job. Texts that are private are **kept on the phone** and never
sent. It is installed from a file (a "sideload"), not from the Play Store.

**What it does**

- Reads incoming and outgoing texts (SMS and picture messages). Chat messages (RCS) can only be read as they
  arrive, see step 7.
- Before anything leaves the phone, it hides card numbers, social security numbers, passwords and one-time codes.
- It never sends texts from people saved in the phone's Contacts, unless they are marked as clients. It never
  sends one-time codes or texts from shops, banks and short codes.
- It shows the owner exactly what was sent, and every sent text has a **"This was private"** button.

**What it never does:** upload the contact list, read call history, use location, or send anything to
anyone except the office service.

---

## Setting up a phone (for the person helping)

You need: the phone, about 15 minutes, and the **setup text** from the office. It looks like
`commscap://setup?url=https%3A%2F%2F...&device=michael-phone-1&secret=...`. Treat it like a password.

> **Important before you start:** the app decides what is private by looking at the phone's **Contacts**.
> Family, friends and anyone personal must be saved as contacts, otherwise their texts look like new customers
> and are sent for screening. Check that the people Michael texts most are in his Contacts. Clients can be
> labelled "AAAD Clients" in Contacts.

### 1. Download the app

1. On a computer, open the GitHub page of this project, then **Actions**, then the latest green run of
   **Comms Capture Android**.
2. At the bottom, under **Artifacts**, download **commscap-debug-apk**. It is a zip file; unzip it. Inside is
   `app-debug.apk`.
3. Get that file onto the phone (email it to yourself, use a USB cable, or a shared drive).

### 2. Install it

1. On the phone, open the file (from **Files** or **Downloads**).
2. Android asks to **allow installing from this source** (unknown apps). Tap **Settings**, switch **Allow from
   this source** on, go back, and tap **Install**.
3. If Play Protect warns about an unknown app, tap **More details**, then **Install anyway**. This is expected
   for an app that is not from the Play Store.
4. **Updating later:** just install the newer file over the old one. Nothing is lost.

### 3. Allow restricted settings (Android 13 and newer)

Android blocks SMS and notification access for apps installed from a file, until you allow it by hand. Do
this *before* the permission steps, or the Allow buttons will do nothing.

1. Long-press the app icon, tap **App info** (the (i) icon). Or open the app and tap **Open App info**.
2. Tap the **three dots** in the top right corner.
3. Tap **Allow restricted settings** and confirm with the phone's PIN or fingerprint.

If you do not see the three dots, try to switch on a permission first (step 4); the dots appear after the
first blocked attempt.

### 4. Give the permissions

Open **Comms Capture**. The screen lists what the app needs. For each line marked **MISSING**, tap its button:

| Line | What to do |
|---|---|
| Read and receive texts (SMS) | **Allow** |
| Contacts | **Allow** |
| Chat (RCS) messages: notification access | Opens Settings. Switch **Comms Capture** on and confirm. |
| Battery: unrestricted | **Allow** (or choose **Unrestricted** under Battery in App info). On Samsung also add the app to **Never sleeping apps**. |
| Notifications | **Allow** |

When everything says **OK**, the top of the screen should change to **Capturing: ON** (once step 5 is done).

### 5. Enter the setup text

1. Copy the setup text (from the email or message the office sent).
2. In the app, in the **Setup** box, tap **Paste from clipboard**, then **Use this text**. The three fields
   fill themselves in. (You can also type them by hand.)
3. Tap **Save setup**.
4. Tap **Sync now**. Within a minute **Last upload to the office** should show a time and there should be no red
   "Problem" line. If there is one, see Troubleshooting.

### 6. Check it works

Ask someone to text the phone from a number that is **not** in Contacts, with a message such as
"Can you give me an estimate for my attic?". Within a minute or two the text appears in
**Last 20 texts sent to the office**. Ask the office to confirm they received it.

### 7. Turn RCS chats off (recommended)

Newer phones send "chat" messages (RCS) that Android does not keep in the normal text database. The app can
catch *incoming* chat messages from the notification, but never the owner's *outgoing* ones. To capture both
directions, turn RCS off so everything is a normal text:

- **Google Messages:** tap the profile picture, then **Messages settings**, then **RCS chats** (or "Chat
  features"), and switch **Turn on RCS chats** off.
- **Samsung Messages:** open **Settings** (three dots), then **Chat settings**, and switch **Chat features**
  off.

### 8. Battery: unrestricted

Done in step 4. If texts arrive late, also check **Settings > Apps > Comms Capture > Battery** is set to
**Unrestricted**.

---

## Everyday use (for the owner)

- **Capturing: ON** means all is well. A red or orange line says what to fix; the **Allow** button next to it
  does it.
- **Pause 1 hour** / **Pause until tomorrow** (6 am): nothing is read or sent during the pause, and texts from
  that time are never captured later, even after the pause ends. The office is told the phone is paused and
  gets an alert if the pause lasts more than 4 hours.
- **This was private:** tap it on any sent text. Everything from that person is deleted from the office system
  and from this phone's waiting list, and they are never captured again.
- **Last 24 hours** shows how many texts were seen, sent to the office, and kept private on the phone. These
  are only numbers; the app stores nothing about texts it decided to keep private.

## Troubleshooting

| What you see | What it means / what to do |
|---|---|
| NOT capturing: the SMS (or Contacts) permission is missing | Tap **Allow**. If nothing happens, do step 3 first. Nothing is lost meanwhile; the app catches up. |
| NOT capturing: the privacy self-check failed | The app tested its own privacy rules on this phone and one failed, so it stopped. Contact the developer. |
| Problem: The office service does not accept this phone | Wrong secret, or the phone's date and time are wrong. Set Date & time to **automatic**, or re-enter the setup text. Nothing is deleted. |
| Problem: Cannot reach the office service | No internet or the service is down. The app keeps every text and retries on its own. |
| "Last upload" is old but texts are arriving | Check **Waiting to upload**. Open the app and tap **Sync now**. Check battery is **Unrestricted**. |
| The Allow button does nothing | Do step 3 (restricted settings). |

---

## For developers

Layout: `core/` is a pure Kotlin/JVM module (no Android, no JSON library): phone-number classification, redaction,
the gate, request signing, and the small decision helpers (policy overlay, thread lookback, backoff, upload
batching, response appliers, pause log, counters, setup-string parsing, an on-device self-check). `app/` is the
Android application (plain `Activity`, `SQLiteOpenHelper`, `HttpURLConnection`, WorkManager; no Compose, Room,
Hilt, Retrofit, OkHttp or analytics). The contract is `../docs/WIRE_CONTRACT.md`; the Python reference
implementations are in `../server/commscap/`; the shared test vectors are in `../shared/vectors/`.

**Run the core tests** (no Android SDK, no Google repositories needed):

```
cd comms-capture/android
gradle :core:test          # or ./gradlew :core:test (wrapper: Gradle 8.14.3)
```

The tests load every case of the four vector files (directory passed as the `vectors.dir` system property,
default `../shared/vectors`; override with `-Pvectors.dir=/path`). `:app` is only part of the build when
`-PwithApp` is given, because it needs Google's Maven repository (Android Gradle Plugin, androidx).

**CI** (`.github/workflows/comms-capture-android.yml`) runs
`gradle -p comms-capture/android -PwithApp :core:test :app:assembleDebug` on every push or pull request that touches
`comms-capture/android/**` or `comms-capture/shared/**`, and uploads the debug APK and the core test report.
Build locally with the Android SDK installed: `gradle -PwithApp :app:assembleDebug`.

**Things worth knowing**

- The debug APK is signed with the committed `app/debug.keystore` so updates install over older builds. It is a
  public-by-design debug key; do not reuse it for anything that matters.
- SMS and MMS are read from the system store (the single source of truth, so uids are stable and reconcile can
  rebuild them). `SMS_RECEIVED`, the content observers, the 15 minute worker and boot only decide *when* to scan.
- If the gate policy changes, run `python tools/gen_vectors.py` in the repository root and fix both
  `core/.../Gate.kt` and the Python reference; the tests fail until they agree.
- The nightly check never looks further back than 48 hours, nor before the moment capture was first switched on.
- `targetSdk` is 34. Moving to 35 means Android limits `dataSync` foreground services (about 6 hours per day) and
  forbids starting them from a boot receiver; the service would need an `onTimeout` handler.
