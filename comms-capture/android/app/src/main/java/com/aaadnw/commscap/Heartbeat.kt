package com.aaadnw.commscap

import android.content.Context
import com.aaadnw.commscap.core.HeartbeatResponseApplier
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException

/** POST /v1/heartbeat (contract section 7): health, counters and acks out; nudges, media requests and verdicts back. */
object Heartbeat {
    /** Returns true when the server answered 200 ok. */
    fun run(ctx: Context): Boolean {
        val prefs = Prefs.get(ctx)
        val db = Db.get(ctx)
        val now = System.currentTimeMillis()
        val acks = prefs.pendingAcks

        val body = JSONObject()
        body.put("schema", 1)
        body.put("device_id", prefs.deviceId)
        body.put("ts_ms", now)
        body.put("app_version", BuildConfig.VERSION_NAME)
        body.put("policy_version", prefs.policyVersion ?: "default-0")
        body.put("queue_depth", db.count(Db.T_QUEUE))
        body.put("deferred_depth", db.count(Db.T_DEFERRED))
        body.put("held_depth", db.count(Db.T_HELD))
        body.put("oldest_queued_ms", db.oldestQueuedMs() ?: JSONObject.NULL)
        body.put("last_capture_ts_ms", if (prefs.lastCaptureTsMs > 0) prefs.lastCaptureTsMs else JSONObject.NULL)
        body.put("last_upload_ok_ms", if (prefs.lastUploadOkMs > 0) prefs.lastUploadOkMs else JSONObject.NULL)
        val perms = JSONObject()
        for ((k, v) in Perms.asMap(ctx)) perms.put(k, v)
        body.put("permissions", perms)
        val counters = JSONObject()
        val snapshot = Counters.snapshot(ctx, now)
        for (k in Counters.HEARTBEAT_KEYS) counters.put(k, snapshot[k] ?: 0)
        body.put("counters_24h", counters)
        body.put("capture_paused_until_ms", Pause.activeUntil(ctx, now) ?: JSONObject.NULL)
        body.put("nudge_acks", JSONArray(acks))

        val res = try {
            Http.call(ctx, "POST", "/v1/heartbeat", body.toString().toByteArray(Charsets.UTF_8))
        } catch (e: IOException) {
            Logx.w("heartbeat: network failure")
            return false
        }
        if (res.code == 401) {
            Net.failAuth(ctx)
            return false
        }
        if (res.code != 200) {
            Logx.w("heartbeat: HTTP ${res.code}")
            return false
        }
        val map = Json.parseObject(res.body) ?: return false
        val outcome = HeartbeatResponseApplier.apply(map, prefs.policyVersion, prefs.handledNudges.toSet())
        if (!outcome.ok) return false

        prefs.lastHeartbeatMs = now
        prefs.pendingAcks = prefs.pendingAcks.filter { it !in acks }

        // Same handling as for an ingest response: attachments the server wants, verdicts, a changed policy.
        Uploader.registerMediaWanted(ctx, outcome.mediaToUpload)
        PolicyStore.applyVerdicts(ctx, outcome.threadVerdicts)
        if (outcome.refetchPolicy) prefs.policyRefetchPending = true

        val shown = Notifs.showNudges(ctx, outcome.nudgesToShow)
        if (shown.isNotEmpty()) {
            prefs.handledNudges = prefs.handledNudges + shown
            prefs.pendingAcks = (prefs.pendingAcks + shown).distinct() // acked in the NEXT heartbeat
        }
        Net.succeeded(ctx)
        return true
    }
}
