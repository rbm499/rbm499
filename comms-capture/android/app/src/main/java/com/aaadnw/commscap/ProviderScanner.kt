package com.aaadnw.commscap

import android.content.Context
import android.net.Uri
import android.provider.BaseColumns
import android.provider.Telephony

/**
 * Reads the system SMS and MMS stores. The stores are the single source of truth for SMS/MMS, in both directions:
 * every message gets the same timestamp (the store's own `date`) whichever path noticed it first, so its uid is the
 * same and the nightly reconcile can rebuild it. The SMS_RECEIVED broadcast, the ContentObserver and the 15-minute
 * worker only decide WHEN to scan.
 *
 * Per table a cursor (last seen _id) is persisted. A row that is not final yet (an outgoing message still queued, an
 * MMS that is only a download notification) is remembered in `pending_rows` and re-checked, so it is not skipped
 * forever just because the cursor moved past it.
 */
object ProviderScanner {
    private const val MAX_ROWS_PER_SCAN = 300
    private const val PENDING_GIVE_UP_MS = 6 * 3_600_000L

    private const val TBL_SMS = "sms"
    private const val TBL_MMS = "mms"

    // PduHeaders message types (not in the public SDK).
    private const val M_TYPE_SEND_REQ = 128
    private const val M_TYPE_RETRIEVE_CONF = 132

    // content://mms/{id}/addr "type" values.
    private val ADDR_FROM = setOf(137)
    private val ADDR_RECIPIENTS = setOf(151, 130, 129)

    private val MMS_PART_URI: Uri = Uri.parse("content://mms/part")

    /** Capturing needs the app to be set up, the privacy self-check to pass, and SMS + Contacts permissions. */
    fun ready(ctx: Context): Boolean = Prefs.get(ctx).isConfigured && Safety.ok() && Perms.missingForCapture(ctx) == null

    /** Processes every new row. Returns how many rows were handled. Exceptions leave the cursor where it was. */
    fun scan(ctx: Context): Int {
        if (!ready(ctx)) return 0
        return scanSms(ctx) + scanMms(ctx)
    }

    // ------------------------------------------------------------------ SMS

    private class SmsRow(val id: Long, val address: String?, val body: String?, val date: Long, val type: Int, val threadId: Long)

    private val SMS_PROJECTION = arrayOf(
        BaseColumns._ID, Telephony.Sms.ADDRESS, Telephony.Sms.BODY, Telephony.Sms.DATE, Telephony.Sms.TYPE, Telephony.Sms.THREAD_ID,
    )

    private fun isFinalSms(type: Int) = type == Telephony.Sms.MESSAGE_TYPE_INBOX || type == Telephony.Sms.MESSAGE_TYPE_SENT

    private fun querySms(ctx: Context, selection: String?, args: Array<String>?, limit: Int): List<SmsRow> {
        val out = ArrayList<SmsRow>()
        ctx.contentResolver.query(Telephony.Sms.CONTENT_URI, SMS_PROJECTION, selection, args, "_id ASC")?.use { c ->
            while (out.size < limit && c.moveToNext()) {
                out.add(SmsRow(c.getLong(0), c.getString(1), c.getString(2), c.getLong(3), c.getInt(4), c.getLong(5)))
            }
        }
        return out
    }

    private fun smsToRaw(row: SmsRow): RawMessage {
        val direction = if (row.type == Telephony.Sms.MESSAGE_TYPE_INBOX) "in" else "out"
        return RawMessage(
            direction, "sms", listOf(row.address ?: ""), row.body ?: "", row.date, emptyList(),
            if (row.threadId > 0) row.threadId.toString() else null,
        )
    }

    private fun scanSms(ctx: Context): Int {
        val prefs = Prefs.get(ctx)
        val db = Db.get(ctx)
        val now = System.currentTimeMillis()
        val last = prefs.lastSeenSms
        if (last < 0) {
            // First run: start from now. The history is never uploaded.
            if (prefs.captureStartedMs == 0L) prefs.captureStartedMs = now
            prefs.lastSeenSms = maxId(ctx, Telephony.Sms.CONTENT_URI)
            return 0
        }
        var handled = 0

        for ((id, firstSeen) in db.pending(TBL_SMS)) {
            val row = querySms(ctx, "_id=?", arrayOf(id.toString()), 1).firstOrNull()
            if (row == null || now - firstSeen > PENDING_GIVE_UP_MS) {
                db.removePending(TBL_SMS, id)
            } else if (isFinalSms(row.type)) {
                Pipeline.handle(ctx, smsToRaw(row))
                db.removePending(TBL_SMS, id)
                handled++
            }
        }

        val rows = querySms(ctx, "_id>?", arrayOf(last.toString()), MAX_ROWS_PER_SCAN)
        if (rows.isEmpty()) {
            val max = maxId(ctx, Telephony.Sms.CONTENT_URI)
            if (max < last) prefs.lastSeenSms = max // the store was reset
            return handled
        }
        for (row in rows) {
            if (isFinalSms(row.type)) {
                Pipeline.handle(ctx, smsToRaw(row))
                handled++
            } else {
                db.addPending(TBL_SMS, row.id, now)
            }
            prefs.lastSeenSms = row.id
        }
        return handled
    }

    // ------------------------------------------------------------------ MMS

    private class MmsRow(val id: Long, val dateSec: Long, val box: Int, val mType: Int, val threadId: Long)

    private val MMS_PROJECTION = arrayOf(
        BaseColumns._ID, Telephony.Mms.DATE, Telephony.Mms.MESSAGE_BOX, Telephony.Mms.MESSAGE_TYPE, Telephony.Mms.THREAD_ID,
    )

    private fun isFinalMms(row: MmsRow) =
        (row.box == Telephony.Mms.MESSAGE_BOX_INBOX && row.mType == M_TYPE_RETRIEVE_CONF) ||
            (row.box == Telephony.Mms.MESSAGE_BOX_SENT && row.mType == M_TYPE_SEND_REQ)

    private fun queryMms(ctx: Context, selection: String?, args: Array<String>?, limit: Int): List<MmsRow> {
        val out = ArrayList<MmsRow>()
        ctx.contentResolver.query(Telephony.Mms.CONTENT_URI, MMS_PROJECTION, selection, args, "_id ASC")?.use { c ->
            while (out.size < limit && c.moveToNext()) {
                out.add(MmsRow(c.getLong(0), c.getLong(1), c.getInt(2), c.getInt(3), c.getLong(4)))
            }
        }
        return out
    }

    private class Parts(val text: String, val media: List<MediaRef>)

    /** Text parts become the body; every other part except the SMIL layout is an attachment (metadata only). */
    private fun readParts(ctx: Context, mmsId: Long): Parts {
        val texts = ArrayList<String>()
        val media = ArrayList<MediaRef>()
        ctx.contentResolver.query(
            MMS_PART_URI, arrayOf("_id", "ct", "text", "_data"), "mid=?", arrayOf(mmsId.toString()), "_id ASC",
        )?.use { c ->
            while (c.moveToNext()) {
                val partId = c.getLong(0)
                val ct = (if (c.isNull(1)) "" else c.getString(1)).lowercase()
                if (ct == "text/plain") {
                    var t: String? = if (c.isNull(2)) null else c.getString(2)
                    if (t == null && !c.isNull(3)) t = readPartText(ctx, partId)
                    if (!t.isNullOrEmpty()) texts.add(t)
                } else if (ct.isNotEmpty() && ct != "application/smil") {
                    media.add(MediaRef("content://mms/part/$partId", ct))
                }
            }
        }
        return Parts(texts.joinToString("\n"), media)
    }

    private fun readPartText(ctx: Context, partId: Long): String? =
        try {
            ctx.contentResolver.openInputStream(Uri.parse("content://mms/part/$partId"))?.use { it.readBytes().toString(Charsets.UTF_8) }
        } catch (e: Exception) {
            null
        }

    /** Counterparts: the sender of an incoming MMS; the recipients of an outgoing one (a group MMS has several). */
    private fun readAddresses(ctx: Context, mmsId: Long, incoming: Boolean): List<String> {
        val wanted = if (incoming) ADDR_FROM else ADDR_RECIPIENTS
        val out = ArrayList<String>()
        ctx.contentResolver.query(Uri.parse("content://mms/$mmsId/addr"), arrayOf("address", "type"), null, null, null)?.use { c ->
            while (c.moveToNext()) {
                if (c.getInt(1) !in wanted) continue
                val a = (if (c.isNull(0)) "" else c.getString(0)).trim()
                if (a.isEmpty() || a == "insert-address-token") continue
                out.add(a)
            }
        }
        return out.distinct()
    }

    private fun mmsToRaw(ctx: Context, row: MmsRow): RawMessage {
        val incoming = row.box == Telephony.Mms.MESSAGE_BOX_INBOX
        val parts = readParts(ctx, row.id)
        return RawMessage(
            if (incoming) "in" else "out", "mms", readAddresses(ctx, row.id, incoming), parts.text,
            row.dateSec * 1000L, parts.media, if (row.threadId > 0) row.threadId.toString() else null,
        )
    }

    private fun scanMms(ctx: Context): Int {
        val prefs = Prefs.get(ctx)
        val db = Db.get(ctx)
        val now = System.currentTimeMillis()
        val last = prefs.lastSeenMms
        if (last < 0) {
            if (prefs.captureStartedMs == 0L) prefs.captureStartedMs = now
            prefs.lastSeenMms = maxId(ctx, Telephony.Mms.CONTENT_URI)
            return 0
        }
        var handled = 0

        for ((id, firstSeen) in db.pending(TBL_MMS)) {
            val row = queryMms(ctx, "_id=?", arrayOf(id.toString()), 1).firstOrNull()
            if (row == null || now - firstSeen > PENDING_GIVE_UP_MS) {
                db.removePending(TBL_MMS, id)
            } else if (isFinalMms(row)) {
                Pipeline.handle(ctx, mmsToRaw(ctx, row))
                db.removePending(TBL_MMS, id)
                handled++
            }
        }

        val rows = queryMms(ctx, "_id>?", arrayOf(last.toString()), MAX_ROWS_PER_SCAN)
        if (rows.isEmpty()) {
            val max = maxId(ctx, Telephony.Mms.CONTENT_URI)
            if (max < last) prefs.lastSeenMms = max
            return handled
        }
        for (row in rows) {
            if (isFinalMms(row)) {
                Pipeline.handle(ctx, mmsToRaw(ctx, row))
                handled++
            } else {
                db.addPending(TBL_MMS, row.id, now)
            }
            prefs.lastSeenMms = row.id
        }
        return handled
    }

    // ------------------------------------------------------------------ nightly reconcile

    /** Every final SMS and MMS in [startMs, endMs] (read-only: no cursor changes, no counters), oldest first. */
    fun windowMessages(ctx: Context, startMs: Long, endMs: Long): List<RawMessage> {
        val out = ArrayList<RawMessage>()
        for (row in querySms(ctx, "date>=? AND date<=?", arrayOf(startMs.toString(), endMs.toString()), Int.MAX_VALUE)) {
            if (isFinalSms(row.type)) out.add(smsToRaw(row))
        }
        val mms = queryMms(ctx, "date>=? AND date<=?", arrayOf((startMs / 1000).toString(), (endMs / 1000).toString()), Int.MAX_VALUE)
        for (row in mms) {
            if (isFinalMms(row)) out.add(mmsToRaw(ctx, row))
        }
        return out.sortedBy { it.tsMs }
    }

    private fun maxId(ctx: Context, uri: Uri): Long =
        ctx.contentResolver.query(uri, arrayOf(BaseColumns._ID), null, null, "_id DESC")?.use { c ->
            if (c.moveToFirst()) c.getLong(0) else 0L
        } ?: 0L
}
