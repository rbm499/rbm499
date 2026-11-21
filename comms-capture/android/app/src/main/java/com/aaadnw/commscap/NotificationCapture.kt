package com.aaadnw.commscap

import android.app.Notification
import android.app.Person
import android.content.ComponentName
import android.content.Context
import android.os.Build
import android.os.Bundle
import android.os.Parcelable
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import com.aaadnw.commscap.core.Redact
import com.aaadnw.commscap.core.Wire
import java.util.concurrent.TimeUnit

/**
 * RCS / "chat" messages never reach the SMS store, so incoming ones are read from the default messaging apps'
 * notifications (transport "notification"). Inbound only. De-duplicated against SMS/MMS by (counterpart, body, +-60 s):
 * the scan runs first, so an SMS that the notification also announced is captured once, via the store.
 */
class NotificationCapture : NotificationListenerService() {

    override fun onListenerConnected() {
        Engine.init(applicationContext)
    }

    override fun onListenerDisconnected() {
        if (Build.VERSION.SDK_INT >= 24) requestRebind(ComponentName(this, NotificationCapture::class.java))
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName !in PACKAGES) return
        val app = applicationContext
        val messages = try {
            parse(sbn)
        } catch (e: Exception) {
            Logx.e("notification not readable", e)
            return
        }
        if (messages.isEmpty()) return
        // Give the SMS store a moment to record the same message, then let the scan win.
        Engine.capture.schedule(Runnable { process(app, messages) }, 8, TimeUnit.SECONDS)
    }

    private class Incoming(val title: String, val body: String, val tsMs: Long, val key: String)

    @Suppress("DEPRECATION")
    private fun parse(sbn: StatusBarNotification): List<Incoming> {
        val n = sbn.notification ?: return emptyList()
        if (n.flags and Notification.FLAG_GROUP_SUMMARY != 0) return emptyList()
        val category = n.category
        if (category != null && category != Notification.CATEGORY_MESSAGE) return emptyList()
        val extras = n.extras ?: return emptyList()

        val conversationTitle = extras.getCharSequence(Notification.EXTRA_CONVERSATION_TITLE)?.toString()?.trim()
        val title = if (!conversationTitle.isNullOrEmpty()) conversationTitle else extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()?.trim() ?: ""
        val out = ArrayList<Incoming>()

        val bundles = extras.getParcelableArray(Notification.EXTRA_MESSAGES)
        if (bundles != null && bundles.isNotEmpty()) {
            val list = Notification.MessagingStyle.Message.getMessagesFromBundleArray(bundles as Array<Parcelable>)
            for (m in list) {
                if (isSelf(m, extras)) continue
                val ts = if (m.timestamp > 0) m.timestamp else sbn.postTime
                if (sbn.postTime - ts > RECENT_MS) continue // older messages of the conversation re-listed in the notification
                val text = m.text?.toString() ?: continue
                out.add(Incoming(title, text, ts, sbn.packageName + "|" + title + "|" + ts + "|" + Wire.sha256Hex(text)))
            }
        } else {
            val text = (extras.getCharSequence(Notification.EXTRA_BIG_TEXT) ?: extras.getCharSequence(Notification.EXTRA_TEXT))?.toString()
            if (!text.isNullOrBlank()) {
                out.add(Incoming(title, text, sbn.postTime, sbn.packageName + "|" + title + "|" + sbn.postTime + "|" + Wire.sha256Hex(text)))
            }
        }
        return out
    }

    /** Messages written by the phone's owner appear in the conversation history of the notification; skip them. */
    @Suppress("DEPRECATION")
    private fun isSelf(m: Notification.MessagingStyle.Message, extras: Bundle): Boolean {
        if (Build.VERSION.SDK_INT < 28) return m.sender == null // Person and getSenderPerson() need API 28
        val sender = m.senderPerson ?: return true // no sender person means "me"
        val self = extras.getParcelable<Person>(Notification.EXTRA_MESSAGING_PERSON) ?: return false
        val sameKey = sender.key != null && sender.key == self.key
        val sameName = sender.key == null && self.key == null && sender.name?.toString() == self.name?.toString()
        return sameKey || sameName
    }

    private fun process(app: Context, messages: List<Incoming>) {
        try {
            if (!ProviderScanner.ready(app)) return
            ProviderScanner.scan(app) // an SMS announced by this notification is captured through the store first
            val policy = PolicyStore.current(app)
            val known = policy.numbers.keys + policy.provisionalBusiness
            for (m in messages) {
                if (!remember(m.key)) continue // the same message in a re-posted notification
                val address = Contacts.resolveNotificationTitle(app, m.title, known.toSet())
                val addressKey = Wire.canonicalAddress(address)
                val bodySha = Wire.sha256Hex(Redact.redact(m.body).text)
                if (Db.get(app).existsNear(addressKey, "in", bodySha, m.tsMs, Pipeline.DEDUPE_WINDOW_MS)) continue
                Pipeline.handle(app, RawMessage("in", "notification", listOf(address), m.body, m.tsMs, emptyList(), null))
            }
            if (Db.get(app).count(Db.T_QUEUE) > 0) Engine.syncSoon(app)
        } catch (t: Throwable) {
            Logx.e("notification capture failed", t)
        }
    }

    companion object {
        private val PACKAGES = setOf("com.google.android.apps.messaging", "com.samsung.android.messaging")
        private const val RECENT_MS = 120_000L

        // Volatile memory only (no persistence): keys of notification messages already handled.
        private val recent = object : LinkedHashMap<String, Boolean>(64, 0.75f, false) {
            override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, Boolean>?): Boolean = size > 300
        }

        @Synchronized
        private fun remember(key: String): Boolean = recent.put(key, true) == null
    }
}
