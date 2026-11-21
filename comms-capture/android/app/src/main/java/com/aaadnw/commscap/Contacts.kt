package com.aaadnw.commscap

import android.content.Context
import android.net.Uri
import android.provider.ContactsContract
import com.aaadnw.commscap.core.PhoneNumber
import com.aaadnw.commscap.core.Wire

/**
 * Contact lookups for the gate (READ_CONTACTS). Results stay on the phone: `saved` and `labels` feed the gate, and the
 * contact's name is uploaded only for messages that pass it. Lookup failures are NOT swallowed: an exception here
 * stops the capture of that message (it is retried later) instead of pretending the sender is an unknown number.
 */
object Contacts {
    data class Info(val saved: Boolean, val name: String?, val labels: List<String>)

    private const val CACHE_MS = 60_000L
    private val NOT_A_CONTACT = Info(false, null, emptyList())

    private val cache = object : LinkedHashMap<String, Pair<Long, Info>>(64, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, Pair<Long, Info>>?): Boolean = size > 200
    }
    private var groupTitles: Pair<Long, Map<Long, String>>? = null

    /** Lookup by number. Only real phone numbers can be saved contacts; short codes, emails and names cannot. */
    @Synchronized
    fun lookup(ctx: Context, addressRaw: String): Info {
        val e164 = PhoneNumber.toE164(addressRaw) ?: return NOT_A_CONTACT
        val now = System.currentTimeMillis()
        cache[e164]?.let { (at, info) -> if (now - at < CACHE_MS) return info }
        val info = query(ctx, e164)
        cache[e164] = now to info
        return info
    }

    private fun query(ctx: Context, e164: String): Info {
        val uri = Uri.withAppendedPath(ContactsContract.PhoneLookup.CONTENT_FILTER_URI, Uri.encode(e164))
        val projection = arrayOf(ContactsContract.PhoneLookup._ID, ContactsContract.PhoneLookup.DISPLAY_NAME)
        val ids = ArrayList<Long>()
        var name: String? = null
        ctx.contentResolver.query(uri, projection, null, null, null)?.use { c ->
            while (c.moveToNext()) {
                ids.add(c.getLong(0))
                if (name == null && !c.isNull(1)) name = c.getString(1)
            }
        }
        if (ids.isEmpty()) return NOT_A_CONTACT
        val titles = groups(ctx)
        val labels = LinkedHashSet<String>()
        for (id in ids) {
            ctx.contentResolver.query(
                ContactsContract.Data.CONTENT_URI,
                arrayOf(ContactsContract.CommonDataKinds.GroupMembership.GROUP_ROW_ID),
                ContactsContract.Data.CONTACT_ID + "=? AND " + ContactsContract.Data.MIMETYPE + "=?",
                arrayOf(id.toString(), ContactsContract.CommonDataKinds.GroupMembership.CONTENT_ITEM_TYPE),
                null,
            )?.use { c ->
                while (c.moveToNext()) {
                    titles[c.getLong(0)]?.let { labels.add(it) }
                }
            }
        }
        return Info(true, name, labels.toList())
    }

    private fun groups(ctx: Context): Map<Long, String> {
        val now = System.currentTimeMillis()
        groupTitles?.let { (at, m) -> if (now - at < 5 * CACHE_MS) return m }
        val m = HashMap<Long, String>()
        ctx.contentResolver.query(
            ContactsContract.Groups.CONTENT_URI,
            arrayOf(ContactsContract.Groups._ID, ContactsContract.Groups.TITLE),
            ContactsContract.Groups.DELETED + "=0", null, null,
        )?.use { c ->
            while (c.moveToNext()) {
                if (!c.isNull(1)) m[c.getLong(0)] = c.getString(1)
            }
        }
        groupTitles = now to m
        return m
    }

    /**
     * Chat notifications show the contact's NAME as the title, not the number. Turns a notification title into the
     * address to gate: a title that is a phone number is used as is; a title that is exactly a saved contact's display
     * name becomes one of that contact's numbers (preferring one the policy knows); anything else stays as text, which
     * the gate treats as a non-phone sender (dropped by default), never as an unsaved number.
     */
    fun resolveNotificationTitle(ctx: Context, title: String, knownNumbers: Set<String>): String {
        val t = title.trim()
        if (t.isEmpty()) return t
        if (PhoneNumber.toE164(t) != null) return t
        val numbers = LinkedHashSet<String>()
        ctx.contentResolver.query(
            ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
            arrayOf(ContactsContract.CommonDataKinds.Phone.NUMBER),
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + "=?", arrayOf(t), null,
        )?.use { c ->
            while (c.moveToNext()) {
                val e164 = PhoneNumber.toE164(c.getString(0))
                if (e164 != null) numbers.add(e164)
            }
        }
        if (numbers.isEmpty()) return t
        return numbers.firstOrNull { it in knownNumbers } ?: numbers.first()
    }

    /** Canonical key used to group messages by counterpart in the database. */
    fun key(addressRaw: String): String = Wire.canonicalAddress(addressRaw)
}
