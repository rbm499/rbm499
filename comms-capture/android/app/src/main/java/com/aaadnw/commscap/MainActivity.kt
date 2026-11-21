package com.aaadnw.commscap

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.text.InputType
import android.text.format.DateUtils
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import com.aaadnw.commscap.core.SetupString

/**
 * The status screen (contract section 11): is it capturing, what is missing (with fix buttons), counters, setup,
 * pause, and the last 20 messages sent to the office, each with a "This was private" button.
 */
class MainActivity : Activity() {
    private val ui = Handler(Looper.getMainLooper())
    private val refreshTick = object : Runnable {
        override fun run() {
            refresh()
            ui.postDelayed(this, 5000L)
        }
    }

    private lateinit var statusBox: LinearLayout
    private lateinit var permBox: LinearLayout
    private lateinit var sentBox: LinearLayout
    private lateinit var etUrl: EditText
    private lateinit var etDevice: EditText
    private lateinit var etSecret: EditText
    private lateinit var etPaste: EditText
    private lateinit var setupMessage: TextView

    // ------------------------------------------------------------------ lifecycle

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Engine.init(this)
        title = "Comms Capture"
        buildScreen()
        fillSetupFields()
    }

    override fun onResume() {
        super.onResume()
        Scheduler.ensureRunning(this) // also starts the foreground service (allowed: we are in the foreground)
        Engine.scanSoon(this, 500L)
        refresh()
        ui.postDelayed(refreshTick, 5000L)
    }

    override fun onPause() {
        ui.removeCallbacks(refreshTick)
        super.onPause()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        Engine.scanSoon(this, 500L)
        refresh()
    }

    // ------------------------------------------------------------------ building blocks

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

    private fun label(s: String, sizeSp: Float = 15f, bold: Boolean = false, color: Int = Color.parseColor("#222222")): TextView {
        val t = TextView(this)
        t.text = s
        t.textSize = sizeSp
        t.setTextColor(color)
        if (bold) t.setTypeface(null, Typeface.BOLD)
        t.setPadding(0, dp(3), 0, dp(3))
        return t
    }

    private fun button(s: String, onClick: () -> Unit): Button {
        val b = Button(this)
        b.text = s
        b.isAllCaps = false
        b.setOnClickListener { onClick() }
        return b
    }

    private fun card(): LinearLayout {
        val c = LinearLayout(this)
        c.orientation = LinearLayout.VERTICAL
        c.setPadding(dp(14), dp(12), dp(14), dp(12))
        val bg = GradientDrawable()
        bg.setColor(Color.parseColor("#F3F5F7"))
        bg.cornerRadius = dp(10).toFloat()
        c.background = bg
        val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        lp.setMargins(0, 0, 0, dp(12))
        c.layoutParams = lp
        return c
    }

    private fun row(): LinearLayout {
        val r = LinearLayout(this)
        r.orientation = LinearLayout.HORIZONTAL
        r.gravity = Gravity.CENTER_VERTICAL
        return r
    }

    private fun field(hint: String): EditText {
        val e = EditText(this)
        e.hint = hint
        e.setSingleLine(true)
        e.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
        return e
    }

    private fun toast(s: String) = Toast.makeText(this, s, Toast.LENGTH_LONG).show()

    private fun whenText(ms: Long): String =
        if (ms <= 0) "never" else DateUtils.formatDateTime(this, ms, DateUtils.FORMAT_SHOW_TIME or DateUtils.FORMAT_SHOW_DATE or DateUtils.FORMAT_ABBREV_ALL)

    // ------------------------------------------------------------------ screen

    private fun buildScreen() {
        val scroll = ScrollView(this)
        val root = LinearLayout(this)
        root.orientation = LinearLayout.VERTICAL
        root.setPadding(dp(16), dp(16), dp(16), dp(32))
        scroll.addView(root)

        root.addView(label("Comms Capture", 22f, bold = true))
        root.addView(label("Version ${BuildConfig.VERSION_NAME}", 12f, color = Color.GRAY))

        statusBox = card()
        permBox = card()
        sentBox = card()

        root.addView(statusBox)
        root.addView(permBox)
        root.addView(buildSetupCard())
        root.addView(label("Last 20 texts sent to the office", 17f, bold = true))
        root.addView(sentBox)

        setContentView(scroll)
    }

    private fun buildSetupCard(): LinearLayout {
        val c = card()
        c.addView(label("Setup", 17f, bold = true))
        c.addView(label("Paste the setup text you were given, or type the three details below.", 13f, color = Color.DKGRAY))

        etPaste = EditText(this)
        etPaste.hint = "commscap://setup?url=...&device=...&secret=..."
        etPaste.minLines = 2
        etPaste.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
        c.addView(etPaste)

        val pasteRow = row()
        pasteRow.addView(button("Paste from clipboard") { pasteFromClipboard() })
        pasteRow.addView(button("Use this text") { useSetupString() })
        c.addView(pasteRow)

        etUrl = field("Server address (https://...)")
        etDevice = field("Device name (for example michael-phone-1)")
        etSecret = field("Secret")
        etSecret.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        c.addView(etUrl)
        c.addView(etDevice)
        c.addView(etSecret)

        setupMessage = label("", 13f, color = Color.parseColor("#C62828"))
        c.addView(setupMessage)
        c.addView(button("Save setup") { saveSetup() })
        return c
    }

    private fun fillSetupFields() {
        val p = Prefs.get(this)
        etUrl.setText(p.serverUrl)
        etDevice.setText(p.deviceId)
        etSecret.setText("")
        etSecret.hint = if (p.secret.isNotEmpty()) "Secret (saved; leave empty to keep it)" else "Secret"
    }

    private fun pasteFromClipboard() {
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val text = cm.primaryClip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(this)?.toString()
        if (text.isNullOrBlank()) toast("The clipboard is empty.") else etPaste.setText(text)
    }

    private fun useSetupString() {
        val r = SetupString.parse(etPaste.text.toString())
        val config = r.config
        if (config == null) {
            setupMessage.text = r.error ?: "That setup text could not be read."
            return
        }
        etUrl.setText(config.url)
        etDevice.setText(config.deviceId)
        etSecret.setText(config.secret)
        etPaste.setText("")
        setupMessage.text = ""
        toast("Details filled in. Tap Save setup.")
    }

    private fun saveSetup() {
        val p = Prefs.get(this)
        val typedSecret = etSecret.text.toString()
        val secret = if (typedSecret.isEmpty() && p.secret.isNotEmpty()) p.secret else typedSecret
        val r = SetupString.validate(etUrl.text.toString(), etDevice.text.toString(), secret)
        val config = r.config
        if (config == null) {
            setupMessage.text = r.error ?: "Please check the details."
            return
        }
        p.serverUrl = config.url
        p.deviceId = config.deviceId
        p.secret = config.secret
        p.clearErrors()
        p.policyRefetchPending = true
        setupMessage.text = ""
        fillSetupFields()
        toast("Saved.")
        Scheduler.ensureRunning(this)
        Engine.scanSoon(this, 500L)
        Engine.syncSoon(this, forceHeartbeat = true)
        refresh()
    }

    // ------------------------------------------------------------------ refresh

    private fun refresh() {
        try {
            renderStatus()
            renderPermissions()
            renderSent()
        } catch (t: Throwable) {
            Logx.e("status screen refresh failed", t)
        }
    }

    private fun renderStatus() {
        statusBox.removeAllViews()
        val p = Prefs.get(this)
        val now = System.currentTimeMillis()
        val db = Db.get(this)
        val pausedUntil = Pause.activeUntil(this, now)
        val missing = Perms.missingForCapture(this)

        val green = Color.parseColor("#2E7D32")
        val amber = Color.parseColor("#E65100")
        val red = Color.parseColor("#C62828")
        when {
            !Safety.ok() -> {
                statusBox.addView(label("NOT capturing: the privacy self-check failed on this phone", 20f, true, red))
                statusBox.addView(label("Nothing is read or sent until this is fixed. Please contact the person who set this up. (${Safety.failures().size} rule checks failed.)", 13f, color = Color.DKGRAY))
            }
            !p.isConfigured -> statusBox.addView(label("Not set up yet", 22f, true, amber))
            missing != null -> statusBox.addView(label("NOT capturing: the $missing permission is missing", 20f, true, red))
            pausedUntil != null -> {
                val minutes = ((pausedUntil - now) / 60_000L).coerceAtLeast(1L)
                val left = if (minutes >= 90) "${(minutes + 30) / 60} h" else "$minutes min"
                statusBox.addView(label("Capture PAUSED ($left left)", 22f, true, amber))
                statusBox.addView(label("Back on at ${whenText(pausedUntil)}", 13f, color = Color.DKGRAY))
            }
            else -> statusBox.addView(label("Capturing: ON", 22f, true, green))
        }

        if (p.lastError.isNotEmpty()) statusBox.addView(label("Problem: ${p.lastError}", 14f, true, red))
        if (p.failedBatches > 0) statusBox.addView(label("Batches refused by the office service: ${p.failedBatches}", 13f, color = red))

        val c = Counters.snapshot(this, now)
        val seen = c[Counters.SEEN] ?: 0
        val sent = c[Counters.SENT] ?: 0
        val keptPrivate = (c[Counters.DROPPED] ?: 0) + (c[Counters.DEFERRED] ?: 0) + (c[Counters.HELD] ?: 0)
        statusBox.addView(label("Last text seen: ${whenText(p.lastCaptureTsMs)}", 14f))
        statusBox.addView(label("Last upload to the office: ${whenText(p.lastUploadOkMs)}", 14f))
        statusBox.addView(label("Waiting to upload: ${db.count(Db.T_QUEUE)}", 14f))
        statusBox.addView(label("Last 24 hours: $seen seen, $sent sent to the office, $keptPrivate kept private on this phone", 14f))
        val waiting = db.count(Db.T_DEFERRED)
        val held = db.count(Db.T_HELD)
        if (waiting > 0 || held > 0) {
            statusBox.addView(label("Kept on the phone for now: $waiting waiting, $held photos from unknown numbers", 13f, color = Color.DKGRAY))
        }
        if (p.lastReconcileNote.isNotEmpty()) {
            statusBox.addView(label("Nightly check (${whenText(p.lastReconcileMs)}): ${p.lastReconcileNote}", 13f, color = Color.DKGRAY))
        }

        val pauseRow = row()
        if (pausedUntil != null) {
            pauseRow.addView(button("Resume now") { Pause.resume(this); refresh() })
        } else {
            pauseRow.addView(button("Pause 1 hour") { Pause.pauseForOneHour(this); refresh() })
            pauseRow.addView(button("Pause until tomorrow") { Pause.pauseUntilTomorrow(this); refresh() })
        }
        statusBox.addView(pauseRow)
        if (pausedUntil == null) {
            statusBox.addView(label("While paused nothing is read or sent, and texts from that time are never captured later.", 12f, color = Color.GRAY))
        }

        val actions = row()
        actions.addView(button("Sync now") {
            Engine.scanSoon(this, 0L)
            Engine.syncSoon(this, forceHeartbeat = true)
            toast("Syncing...")
        })
        actions.addView(button("Run nightly check now") {
            Engine.reconcileSoon(this)
            toast("Checking the last 2 days...")
        })
        statusBox.addView(actions)
    }

    private fun renderPermissions() {
        permBox.removeAllViews()
        permBox.addView(label("What this phone needs", 17f, bold = true))

        val sms = Perms.sms(this)
        val contacts = Perms.contacts(this)
        val listener = Perms.notificationListener(this)
        val battery = Perms.batteryUnrestricted(this)
        val notifications = Perms.postNotifications(this)

        permRow("Read and receive texts (SMS)", sms, "Allow") {
            requestPermissions(arrayOf(Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_SMS), REQ_SMS)
        }
        permRow("Contacts (so private contacts are never captured)", contacts, "Allow") {
            requestPermissions(arrayOf(Manifest.permission.READ_CONTACTS), REQ_CONTACTS)
        }
        permRow("Chat (RCS) messages: notification access", listener, "Open settings") { openListenerSettings() }
        permRow("Battery: unrestricted, so Android does not stop the app", battery, "Allow") { requestBatteryExemption() }
        permRow("Notifications (reminders and status)", notifications, "Allow") {
            if (Build.VERSION.SDK_INT >= 33) {
                requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQ_NOTIFICATIONS)
            }
        }

        if (Build.VERSION.SDK_INT >= 33 && (!sms || !listener)) {
            val box = card()
            box.addView(label("If the Allow button does nothing: restricted settings", 14f, bold = true, color = Color.parseColor("#E65100")))
            box.addView(
                label(
                    "On Android 13 and newer, an app installed from a file (not from the Play Store) is blocked from SMS and " +
                        "notification access until you allow it by hand:\n" +
                        "1. Tap \"Open App info\" below.\n" +
                        "2. Tap the three dots in the top right corner.\n" +
                        "3. Tap \"Allow restricted settings\" (you may need to confirm with your PIN or fingerprint).\n" +
                        "4. Come back here and tap the Allow buttons again.",
                    13f,
                ),
            )
            box.addView(button("Open App info") { openAppInfo() })
            permBox.addView(box)
        }
        if (!listener) {
            permBox.addView(
                label(
                    "Without notification access, chat (RCS) messages are not captured. Best fix: in the Messages app turn " +
                        "\"RCS chats\" off, so every text, sent and received, is a normal SMS.",
                    12f, color = Color.DKGRAY,
                ),
            )
        }
    }

    private fun permRow(text: String, ok: Boolean, fixLabel: String, fix: () -> Unit) {
        val r = row()
        val t = label((if (ok) "OK   " else "MISSING   ") + text, 14f, bold = !ok, color = if (ok) Color.parseColor("#2E7D32") else Color.parseColor("#C62828"))
        r.addView(t, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        if (!ok) r.addView(button(fixLabel) { fix() })
        permBox.addView(r)
    }

    private fun renderSent() {
        sentBox.removeAllViews()
        val rows = Db.get(this).recentSent(20)
        if (rows.isEmpty()) {
            sentBox.addView(label("Nothing has been sent to the office yet.", 14f, color = Color.DKGRAY))
            return
        }
        for (m in rows) {
            val who = m.contactName ?: m.addressKey
            val r = row()
            val text = label("$who  -  ${whenText(m.tsMs)}\n${m.snippet ?: ""}", 13f)
            r.addView(text, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            r.addView(button("This was private") { confirmPrivate(m, who) })
            sentBox.addView(r)
            val divider = View(this)
            divider.setBackgroundColor(Color.parseColor("#DDDDDD"))
            sentBox.addView(divider, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 1))
        }
    }

    private fun confirmPrivate(m: StoredMsg, who: String) {
        AlertDialog.Builder(this)
            .setTitle("Mark as private?")
            .setMessage(
                "Everything from $who will be removed from the office system, deleted from this phone's waiting list, " +
                    "and never captured again.",
            )
            .setPositiveButton("Yes, it was private") { _, _ ->
                val app = applicationContext
                Engine.capture.execute {
                    Marks.markPrivate(app, m.addressKey, m.uid)
                    runOnUiThread {
                        refresh()
                        toast("Done. $who is now private.")
                    }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    // ------------------------------------------------------------------ settings screens

    private fun openListenerSettings() {
        try {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        } catch (e: ActivityNotFoundException) {
            toast("Open Settings > Notifications > Notification access and switch on Comms Capture.")
        }
    }

    private fun requestBatteryExemption() {
        try {
            startActivity(Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:$packageName")))
        } catch (e: Exception) {
            try {
                startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
            } catch (e2: ActivityNotFoundException) {
                openAppInfo()
            }
        }
    }

    private fun openAppInfo() {
        try {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
        } catch (e: ActivityNotFoundException) {
            toast("Open Settings > Apps > Comms Capture.")
        }
    }

    companion object {
        private const val REQ_SMS = 1
        private const val REQ_CONTACTS = 2
        private const val REQ_NOTIFICATIONS = 3
    }
}
