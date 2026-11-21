package com.aaadnw.commscap

import android.content.Context
import com.aaadnw.commscap.core.LookbackPlanner
import java.io.IOException

/**
 * One network cycle, always on the net thread (see Engine): housekeeping, policy, privacy marks, ingest, heartbeat, media.
 * A failure anywhere only postpones work; nothing is deleted because of it.
 */
object Sync {
    private const val HEARTBEAT_EVERY_MS = 10 * 60_000L
    private const val HEARTBEAT_AFTER_INGEST_MS = 5 * 60_000L

    @Synchronized
    fun cycle(ctx: Context, forceHeartbeat: Boolean = false) {
        val prefs = Prefs.get(ctx)
        if (!prefs.isConfigured) return
        try {
            maintenance(ctx)

            if (prefs.policyRefetchPending || prefs.policyJson == null) {
                try {
                    PolicyStore.fetch(ctx)
                } catch (e: IOException) {
                    Logx.w("policy fetch: network failure")
                }
            }

            var heartbeatDue = forceHeartbeat || System.currentTimeMillis() - prefs.lastHeartbeatMs >= HEARTBEAT_EVERY_MS
            if (System.currentTimeMillis() >= prefs.nextAttemptMs) {
                var ok = Marks.flush(ctx)
                if (ok) {
                    val r = Uploader.uploadQueue(ctx)
                    ok = r.ok
                    // After a successful ingest: heartbeat if the last one is older than 5 minutes.
                    if (r.ok && r.acked > 0 && System.currentTimeMillis() - prefs.lastHeartbeatMs > HEARTBEAT_AFTER_INGEST_MS) {
                        heartbeatDue = true
                    }
                }
            }

            // Heartbeats keep their normal cadence even while uploads are backing off (for example after a 401).
            if (heartbeatDue) Heartbeat.run(ctx)

            if (prefs.policyRefetchPending) {
                try {
                    PolicyStore.fetch(ctx)
                } catch (e: IOException) {
                    Logx.w("policy fetch: network failure")
                }
            }

            // Attachments the server asked for (possibly just now, in the heartbeat reply).
            if (System.currentTimeMillis() >= prefs.nextAttemptMs && Db.get(ctx).mediaJobCount() > 0) {
                Uploader.uploadMedia(ctx)
            }
        } catch (t: Throwable) {
            Logx.e("sync cycle failed", t)
        } finally {
            CaptureService.refresh(ctx)
        }
    }

    /** Expiry: deferred after defer_hours, held after hold_media_days, old sent-log rows after 48 h. */
    private fun maintenance(ctx: Context) {
        val db = Db.get(ctx)
        val now = System.currentTimeMillis()
        val policy = PolicyStore.current(ctx)
        db.delete(Db.T_DEFERRED, LookbackPlanner.expired(db.deferredRefs(Db.T_DEFERRED), now, policy.deferHours.toLong() * LookbackPlanner.HOUR_MS))
        db.delete(Db.T_HELD, LookbackPlanner.expired(db.deferredRefs(Db.T_HELD), now, policy.holdMediaDays.toLong() * LookbackPlanner.DAY_MS))
        db.pruneSentLog(now - 2 * LookbackPlanner.DAY_MS)
    }
}
