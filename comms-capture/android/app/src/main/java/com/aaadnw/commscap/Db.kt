package com.aaadnw.commscap

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.aaadnw.commscap.core.DeferredRef
import com.aaadnw.commscap.core.QueueRef

/**
 * One message row. [payload] is the ingest JSON of the message (redacted body); it is null once the message has been
 * sent (the sent log only keeps what the status screen and the de-duplication need).
 */
data class StoredMsg(
    val uid: String,
    val tsMs: Long,
    val addressKey: String,
    val direction: String,
    val bodySha: String,
    val payload: String?,
    val mediaJson: String?,
    val contactName: String?,
    val snippet: String?,
    val createdMs: Long,
)

data class MediaJob(
    val uid: String,
    val sha256: String,
    val uri: String,
    val mime: String,
    val size: Long,
    val addressKey: String,
    val attempts: Int,
)

data class PendingMark(val id: Long, val address: String, val verdict: String, val uid: String?, val attempts: Int)

/**
 * Durable storage. The four message tables have the same schema:
 *  - queue:    messages that passed the gate and wait for upload (deleted only after the server acknowledged them)
 *  - deferred: kept on the phone for up to policy.defer_hours, promoted only by the thread lookback
 *  - held:     media with no text from an unknown number, kept up to policy.hold_media_days, never uploaded
 *  - sent_log: acknowledged messages (no body), for the status screen, de-duplication and later media requests
 * Dropped messages are never written anywhere.
 */
class Db private constructor(ctx: Context) : SQLiteOpenHelper(ctx, "commscap.db", null, 1) {

    override fun onCreate(db: SQLiteDatabase) {
        for (t in MSG_TABLES) {
            db.execSQL(
                "CREATE TABLE $t (" +
                    "uid TEXT PRIMARY KEY NOT NULL, ts_ms INTEGER NOT NULL, address_key TEXT NOT NULL, " +
                    "direction TEXT NOT NULL, body_sha TEXT NOT NULL, payload TEXT, media_json TEXT, " +
                    "contact_name TEXT, snippet TEXT, created_ms INTEGER NOT NULL)",
            )
            db.execSQL("CREATE INDEX idx_${t}_addr ON $t(address_key)")
        }
        db.execSQL(
            "CREATE TABLE media_jobs (uid TEXT NOT NULL, sha256 TEXT NOT NULL, uri TEXT NOT NULL, mime TEXT NOT NULL, " +
                "size INTEGER NOT NULL, address_key TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, " +
                "PRIMARY KEY (uid, sha256))",
        )
        db.execSQL(
            "CREATE TABLE pending_rows (tbl TEXT NOT NULL, row_id INTEGER NOT NULL, first_seen_ms INTEGER NOT NULL, " +
                "PRIMARY KEY (tbl, row_id))",
        )
        db.execSQL(
            "CREATE TABLE marks (id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT NOT NULL, verdict TEXT NOT NULL, " +
                "uid TEXT, created_ms INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0)",
        )
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // Version 1 only.
    }

    private inline fun <T> tx(block: (SQLiteDatabase) -> T): T {
        val db = writableDatabase
        db.beginTransaction()
        try {
            val r = block(db)
            db.setTransactionSuccessful()
            return r
        } finally {
            db.endTransaction()
        }
    }

    // ------------------------------------------------------------------ messages

    private fun values(m: StoredMsg): ContentValues {
        val cv = ContentValues()
        cv.put("uid", m.uid)
        cv.put("ts_ms", m.tsMs)
        cv.put("address_key", m.addressKey)
        cv.put("direction", m.direction)
        cv.put("body_sha", m.bodySha)
        cv.put("payload", m.payload)
        cv.put("media_json", m.mediaJson)
        cv.put("contact_name", m.contactName)
        cv.put("snippet", m.snippet)
        cv.put("created_ms", m.createdMs)
        return cv
    }

    private fun str(c: Cursor, i: Int): String? = if (c.isNull(i)) null else c.getString(i)

    private fun readMsg(c: Cursor) = StoredMsg(
        uid = c.getString(0),
        tsMs = c.getLong(1),
        addressKey = c.getString(2),
        direction = c.getString(3),
        bodySha = c.getString(4),
        payload = str(c, 5),
        mediaJson = str(c, 6),
        contactName = str(c, 7),
        snippet = str(c, 8),
        createdMs = c.getLong(9),
    )

    /** Inserts the row; returns false when the uid was already there (unless [replace]). */
    fun insertMsg(table: String, m: StoredMsg, replace: Boolean = false): Boolean {
        val algo = if (replace) SQLiteDatabase.CONFLICT_REPLACE else SQLiteDatabase.CONFLICT_IGNORE
        return writableDatabase.insertWithOnConflict(table, null, values(m), algo) != -1L
    }

    fun get(table: String, uid: String): StoredMsg? =
        readableDatabase.query(table, MSG_COLS, "uid=?", arrayOf(uid), null, null, null).use { c ->
            if (c.moveToFirst()) readMsg(c) else null
        }

    /** Rows for [uids], in the order of [uids]; missing ones are skipped. */
    fun getMany(table: String, uids: List<String>): List<StoredMsg> = uids.mapNotNull { get(table, it) }

    /** True if this uid is in any message table. */
    fun has(uid: String): Boolean = MSG_TABLES.any { t ->
        readableDatabase.query(t, arrayOf("uid"), "uid=?", arrayOf(uid), null, null, null, "1").use { it.moveToFirst() }
    }

    /**
     * De-duplication of the same message seen through two paths (SMS store and a chat notification): same counterpart,
     * direction and body hash within [windowMs] of [tsMs], in any table.
     */
    fun existsNear(addressKey: String, direction: String, bodySha: String, tsMs: Long, windowMs: Long): Boolean =
        MSG_TABLES.any { t ->
            readableDatabase.query(
                t, arrayOf("uid"),
                "address_key=? AND direction=? AND body_sha=? AND ts_ms>=? AND ts_ms<=?",
                arrayOf(addressKey, direction, bodySha, (tsMs - windowMs).toString(), (tsMs + windowMs).toString()),
                null, null, null, "1",
            ).use { it.moveToFirst() }
        }

    fun deferredRefs(table: String): List<DeferredRef> =
        readableDatabase.query(table, arrayOf("uid", "address_key", "ts_ms"), null, null, null, null, "ts_ms ASC").use { c ->
            val out = ArrayList<DeferredRef>()
            while (c.moveToNext()) out.add(DeferredRef(c.getString(0), c.getString(1), c.getLong(2)))
            out
        }

    fun queueRefs(): List<QueueRef> =
        readableDatabase.query(T_QUEUE, arrayOf("uid", "ts_ms"), null, null, null, null, "ts_ms ASC").use { c ->
            val out = ArrayList<QueueRef>()
            while (c.moveToNext()) out.add(QueueRef(c.getString(0), c.getLong(1)))
            out
        }

    fun delete(table: String, uids: Collection<String>) {
        if (uids.isEmpty()) return
        tx { db -> for (u in uids) db.delete(table, "uid=?", arrayOf(u)) }
    }

    /** Moves a deferred row into the queue (with its updated payload and media list). */
    fun promote(m: StoredMsg) {
        tx { db ->
            db.insertWithOnConflict(T_QUEUE, null, values(m), SQLiteDatabase.CONFLICT_IGNORE)
            db.delete(T_DEFERRED, "uid=?", arrayOf(m.uid))
        }
    }

    /** The server has this message: move it from the queue to the sent log (payload dropped, media list kept). */
    fun markSent(uid: String) {
        tx { db ->
            val row = db.query(T_QUEUE, MSG_COLS, "uid=?", arrayOf(uid), null, null, null).use { c ->
                if (c.moveToFirst()) readMsg(c) else null
            }
            if (row != null) {
                db.insertWithOnConflict(T_SENT, null, values(row.copy(payload = null)), SQLiteDatabase.CONFLICT_REPLACE)
            }
            db.delete(T_QUEUE, "uid=?", arrayOf(uid))
        }
    }

    fun count(table: String): Int =
        readableDatabase.rawQuery("SELECT COUNT(*) FROM $table", null).use { c -> if (c.moveToFirst()) c.getInt(0) else 0 }

    /** Oldest time a message entered the upload queue, or null when the queue is empty. */
    fun oldestQueuedMs(): Long? =
        readableDatabase.rawQuery("SELECT MIN(created_ms) FROM $T_QUEUE", null).use { c ->
            if (c.moveToFirst() && !c.isNull(0)) c.getLong(0) else null
        }

    /** The newest [limit] messages the office has received (for the status screen). */
    fun recentSent(limit: Int): List<StoredMsg> =
        readableDatabase.query(T_SENT, MSG_COLS, null, null, null, null, "ts_ms DESC", limit.toString()).use { c ->
            val out = ArrayList<StoredMsg>()
            while (c.moveToNext()) out.add(readMsg(c))
            out
        }

    /** Deletes everything held for this counterpart: queue, deferred, held, sent log and pending media uploads. */
    fun purgeAddress(addressKey: String) {
        tx { db ->
            for (t in MSG_TABLES) db.delete(t, "address_key=?", arrayOf(addressKey))
            db.delete("media_jobs", "address_key=?", arrayOf(addressKey))
        }
    }

    /** Sent-log housekeeping: forget rows created before [olderThanMs]. */
    fun pruneSentLog(olderThanMs: Long) {
        writableDatabase.delete(T_SENT, "created_ms<?", arrayOf(olderThanMs.toString()))
    }

    // ------------------------------------------------------------------ media jobs

    fun addMediaJob(j: MediaJob) {
        val cv = ContentValues()
        cv.put("uid", j.uid)
        cv.put("sha256", j.sha256)
        cv.put("uri", j.uri)
        cv.put("mime", j.mime)
        cv.put("size", j.size)
        cv.put("address_key", j.addressKey)
        cv.put("attempts", j.attempts)
        writableDatabase.insertWithOnConflict("media_jobs", null, cv, SQLiteDatabase.CONFLICT_IGNORE)
    }

    fun mediaJobs(limit: Int): List<MediaJob> =
        readableDatabase.query("media_jobs", null, null, null, null, null, "rowid ASC", limit.toString()).use { c ->
            val out = ArrayList<MediaJob>()
            while (c.moveToNext()) {
                out.add(
                    MediaJob(
                        c.getString(c.getColumnIndexOrThrow("uid")), c.getString(c.getColumnIndexOrThrow("sha256")),
                        c.getString(c.getColumnIndexOrThrow("uri")), c.getString(c.getColumnIndexOrThrow("mime")),
                        c.getLong(c.getColumnIndexOrThrow("size")), c.getString(c.getColumnIndexOrThrow("address_key")),
                        c.getInt(c.getColumnIndexOrThrow("attempts")),
                    ),
                )
            }
            out
        }

    fun deleteMediaJob(uid: String, sha256: String) {
        writableDatabase.delete("media_jobs", "uid=? AND sha256=?", arrayOf(uid, sha256))
    }

    fun bumpMediaJob(uid: String, sha256: String) {
        writableDatabase.execSQL("UPDATE media_jobs SET attempts=attempts+1 WHERE uid=? AND sha256=?", arrayOf<Any>(uid, sha256))
    }

    fun mediaJobCount(): Int = count("media_jobs")

    // ------------------------------------------------------------------ rows that were not final yet

    fun addPending(table: String, rowId: Long, nowMs: Long) {
        val cv = ContentValues()
        cv.put("tbl", table)
        cv.put("row_id", rowId)
        cv.put("first_seen_ms", nowMs)
        writableDatabase.insertWithOnConflict("pending_rows", null, cv, SQLiteDatabase.CONFLICT_IGNORE)
    }

    /** (row id, first seen) for rows of [table] that were seen before they were complete. */
    fun pending(table: String): List<Pair<Long, Long>> =
        readableDatabase.query("pending_rows", arrayOf("row_id", "first_seen_ms"), "tbl=?", arrayOf(table), null, null, "row_id ASC").use { c ->
            val out = ArrayList<Pair<Long, Long>>()
            while (c.moveToNext()) out.add(c.getLong(0) to c.getLong(1))
            out
        }

    fun removePending(table: String, rowId: Long) {
        writableDatabase.delete("pending_rows", "tbl=? AND row_id=?", arrayOf(table, rowId.toString()))
    }

    // ------------------------------------------------------------------ privacy marks waiting to be posted

    fun addMark(address: String, verdict: String, uid: String?, nowMs: Long) {
        val cv = ContentValues()
        cv.put("address", address)
        cv.put("verdict", verdict)
        cv.put("uid", uid)
        cv.put("created_ms", nowMs)
        writableDatabase.insert("marks", null, cv)
    }

    fun marks(): List<PendingMark> =
        readableDatabase.query("marks", arrayOf("id", "address", "verdict", "uid", "attempts"), null, null, null, null, "id ASC").use { c ->
            val out = ArrayList<PendingMark>()
            while (c.moveToNext()) out.add(PendingMark(c.getLong(0), c.getString(1), c.getString(2), str(c, 3), c.getInt(4)))
            out
        }

    fun deleteMark(id: Long) {
        writableDatabase.delete("marks", "id=?", arrayOf(id.toString()))
    }

    fun bumpMark(id: Long) {
        writableDatabase.execSQL("UPDATE marks SET attempts=attempts+1 WHERE id=?", arrayOf<Any>(id))
    }

    companion object {
        const val T_QUEUE = "queue"
        const val T_DEFERRED = "deferred"
        const val T_HELD = "held"
        const val T_SENT = "sent_log"
        val MSG_TABLES = listOf(T_QUEUE, T_DEFERRED, T_HELD, T_SENT)

        private val MSG_COLS = arrayOf(
            "uid", "ts_ms", "address_key", "direction", "body_sha", "payload", "media_json", "contact_name", "snippet", "created_ms",
        )

        @Volatile
        private var instance: Db? = null

        fun get(ctx: Context): Db =
            instance ?: synchronized(this) {
                instance ?: Db(ctx.applicationContext).also { instance = it }
            }
    }
}
