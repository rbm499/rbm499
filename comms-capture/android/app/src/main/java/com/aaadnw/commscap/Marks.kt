package com.aaadnw.commscap

import android.content.Context
import com.aaadnw.commscap.core.PolicyOverlay
import org.json.JSONObject
import java.io.IOException

/** Michael's one-tap privacy control (contract section 9): local change first, then POST /v1/mark (queued if offline). */
object Marks {
    private const val MAX_BAD_REQUEST_ATTEMPTS = 3

    /** "This was private": exclude the address, delete everything stored from it on the phone, tell the office. */
    fun markPrivate(ctx: Context, address: String, uid: String?) {
        PolicyStore.applyUserVerdict(ctx, address, PolicyOverlay.PRIVATE)
        Db.get(ctx).addMark(address, PolicyOverlay.PRIVATE, uid, System.currentTimeMillis())
        Engine.syncSoon(ctx)
    }

    /** Posts queued marks. Returns false when a failure was recorded and the caller should stop for now. */
    fun flush(ctx: Context): Boolean {
        val db = Db.get(ctx)
        val prefs = Prefs.get(ctx)
        for (m in db.marks()) {
            val body = JSONObject()
            body.put("schema", 1)
            body.put("device_id", prefs.deviceId)
            body.put("address", m.address)
            body.put("verdict", m.verdict)
            if (m.uid != null) body.put("uid", m.uid)
            val res = try {
                Http.call(ctx, "POST", "/v1/mark", body.toString().toByteArray(Charsets.UTF_8))
            } catch (e: IOException) {
                Net.failTransient(ctx, "network")
                return false
            }
            when {
                res.code == 200 -> db.deleteMark(m.id)
                res.code == 401 -> {
                    Net.failAuth(ctx)
                    return false
                }
                res.code == 429 || res.code >= 500 -> {
                    Net.failTransient(ctx, "HTTP ${res.code}")
                    return false
                }
                else -> {
                    // The local purge already happened. A request the server calls invalid will not improve by repeating.
                    if (m.attempts + 1 >= MAX_BAD_REQUEST_ATTEMPTS) db.deleteMark(m.id) else db.bumpMark(m.id)
                }
            }
        }
        return true
    }
}
