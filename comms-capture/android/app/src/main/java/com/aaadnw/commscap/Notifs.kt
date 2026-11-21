package com.aaadnw.commscap

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.text.format.DateUtils
import com.aaadnw.commscap.core.Nudge

/** Notification channels, the persistent status notification and the reminder ("nudge") notifications. */
object Notifs {
    const val CH_CAPTURE = "capture"
    const val CH_NUDGES = "nudges"
    const val ID_STATUS = 1

    fun ensureChannels(ctx: Context) {
        val nm = ctx.getSystemService(NotificationManager::class.java)
        val capture = NotificationChannel(CH_CAPTURE, "Capture status", NotificationManager.IMPORTANCE_LOW)
        capture.description = "Shows that business texts are being captured and when the last sync happened."
        capture.setShowBadge(false)
        nm.createNotificationChannel(capture)
        val nudges = NotificationChannel(CH_NUDGES, "Reminders from the office", NotificationManager.IMPORTANCE_HIGH)
        nudges.description = "Reminders about customer texts that are waiting for a reply."
        nm.createNotificationChannel(nudges)
    }

    private fun openApp(ctx: Context): PendingIntent {
        val intent = Intent(ctx, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        return PendingIntent.getActivity(ctx, 0, intent, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    }

    private fun time(ctx: Context, ms: Long): String =
        DateUtils.formatDateTime(ctx, ms, DateUtils.FORMAT_SHOW_TIME or DateUtils.FORMAT_ABBREV_ALL)

    /** The persistent low-priority notification: last sync, queue, pause or what needs attention. */
    fun status(ctx: Context): Notification {
        val p = Prefs.get(ctx)
        val pausedUntil = Pause.activeUntil(ctx)
        val missing = Perms.missingForCapture(ctx)
        val text = when {
            !p.isConfigured -> "Not set up yet. Open the app to finish setup."
            !Safety.ok() -> "STOPPED: privacy self-check failed. Open the app."
            missing != null -> "Needs attention: $missing permission is off"
            pausedUntil != null -> "Paused until ${time(ctx, pausedUntil)}"
            else -> {
                val last = if (p.lastUploadOkMs > 0) "Last sync ${time(ctx, p.lastUploadOkMs)}" else "No sync yet"
                "$last, ${Db.get(ctx).count(Db.T_QUEUE)} waiting"
            }
        }
        return Notification.Builder(ctx, CH_CAPTURE)
            .setSmallIcon(R.drawable.ic_stat_capture)
            .setContentTitle("Business texts are being captured")
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(Notification.CATEGORY_SERVICE)
            .setContentIntent(openApp(ctx))
            .build()
    }

    /**
     * Shows each nudge once as a high-importance notification; tapping opens the SMS thread for its address in the
     * default messaging app. Returns the ids that were actually displayed (only those may be acked): when notifications
     * or the channel are switched off nothing is shown and nothing is acked, so the office hears about it.
     */
    fun showNudges(ctx: Context, nudges: List<Nudge>): List<String> {
        if (nudges.isEmpty()) return emptyList()
        val nm = ctx.getSystemService(NotificationManager::class.java)
        if (!nm.areNotificationsEnabled()) return emptyList()
        val channel = nm.getNotificationChannel(CH_NUDGES)
        if (channel != null && channel.importance == NotificationManager.IMPORTANCE_NONE) return emptyList()
        val shown = ArrayList<String>()
        for (n in nudges) {
            val requestCode = n.id.hashCode() and 0x7FFFFFFF
            val address = n.address
            val tap = if (address != null) {
                val sms = Intent(Intent.ACTION_SENDTO, Uri.fromParts("sms", address, null)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                PendingIntent.getActivity(ctx, requestCode, sms, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            } else {
                openApp(ctx)
            }
            val notification = Notification.Builder(ctx, CH_NUDGES)
                .setSmallIcon(R.drawable.ic_stat_capture)
                .setContentTitle(n.title)
                .setContentText(n.text)
                .setStyle(Notification.BigTextStyle().bigText(n.text))
                .setContentIntent(tap)
                .setAutoCancel(true)
                .setCategory(Notification.CATEGORY_REMINDER)
                .build()
            try {
                nm.notify(100 + (requestCode % 1_000_000), notification)
                shown.add(n.id)
            } catch (e: Exception) {
                Logx.e("could not show a reminder", e)
            }
        }
        return shown
    }
}
