package com.aaadnw.commscap

import android.content.Context
import com.aaadnw.commscap.core.IngestOutcome
import com.aaadnw.commscap.core.IngestResponseApplier
import com.aaadnw.commscap.core.MediaRequest
import com.aaadnw.commscap.core.UploadPlanner
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import java.io.IOException

/**
 * Ingest and media uploads. Rule number one: nothing is ever deleted because of a failure. Queue rows are removed
 * only when the server's response says it has them (accepted / duplicates) or refused them for good (rejected).
 */
object Uploader {
    /** @property ok false when a failure was recorded (see Net) and the caller should stop for now. @property acked messages acknowledged. */
    class Result(val ok: Boolean, val acked: Int)

    private const val MAX_MEDIA_ATTEMPTS = 5

    fun uploadQueue(ctx: Context): Result {
        val prefs = Prefs.get(ctx)
        val db = Db.get(ctx)
        var acked = 0
        while (true) {
            val batch = UploadPlanner.nextBatch(db.queueRefs())
            if (batch.isEmpty()) return Result(true, acked)

            val rows = db.getMany(Db.T_QUEUE, batch)
            val messages = JSONArray()
            val sentUids = ArrayList<String>()
            val unusable = ArrayList<String>()
            for (r in rows) {
                try {
                    val o = JSONObject(r.payload ?: throw JSONException("no payload"))
                    o.put("media", Json.ingestMedia(Json.mediaFromJson(r.mediaJson)))
                    messages.put(o)
                    sentUids.add(r.uid)
                } catch (e: JSONException) {
                    unusable.add(r.uid) // a corrupt row can never be uploaded; do not let it block the queue
                }
            }
            if (unusable.isNotEmpty()) {
                Logx.w("dropping ${unusable.size} unreadable queue row(s)")
                db.delete(Db.T_QUEUE, unusable)
            }
            if (sentUids.isEmpty()) continue

            val body = JSONObject()
            body.put("schema", 1)
            body.put("device_id", prefs.deviceId)
            body.put("sent_at_ms", System.currentTimeMillis())
            body.put("policy_version", prefs.policyVersion ?: "default-0")
            body.put("messages", messages)

            val res = try {
                Http.call(ctx, "POST", "/v1/ingest", body.toString().toByteArray(Charsets.UTF_8))
            } catch (e: IOException) {
                Net.failTransient(ctx, "network")
                return Result(false, acked)
            }
            when {
                res.code == 200 -> {
                    val map = Json.parseObject(res.body)
                    if (map == null) {
                        Net.failTransient(ctx, "unreadable reply")
                        return Result(false, acked)
                    }
                    val outcome = IngestResponseApplier.apply(map, sentUids, prefs.policyVersion)
                    if (!outcome.ok || outcome.deleteUids.isEmpty()) {
                        Net.failTransient(ctx, "no acknowledgement")
                        return Result(false, acked)
                    }
                    applyIngest(ctx, outcome)
                    acked += outcome.deleteUids.size
                }
                res.code == 401 -> {
                    Net.failAuth(ctx)
                    return Result(false, acked)
                }
                res.code == 429 || res.code >= 500 -> {
                    Net.failTransient(ctx, "HTTP ${res.code}")
                    return Result(false, acked)
                }
                else -> {
                    Net.failClient(ctx, res.code)
                    return Result(false, acked)
                }
            }
        }
    }

    private fun applyIngest(ctx: Context, o: IngestOutcome) {
        val db = Db.get(ctx)
        val prefs = Prefs.get(ctx)
        for (uid in o.acceptedUids + o.duplicateUids) db.markSent(uid)
        db.delete(Db.T_QUEUE, o.rejected.map { it.uid })
        if (o.serverGateDrops > 0) prefs.serverDrops = prefs.serverDrops + o.serverGateDrops
        registerMediaWanted(ctx, o.mediaToUpload)
        PolicyStore.applyVerdicts(ctx, o.threadVerdicts) // also purges, so it comes after the media bookkeeping
        if (o.refetchPolicy) prefs.policyRefetchPending = true
        prefs.lastUploadOkMs = System.currentTimeMillis()
        Net.ingestSucceeded(ctx)
    }

    /**
     * The server asked for these attachments (ingest response or heartbeat response, same handling). Media is uploaded
     * only when asked for. The message may have been acknowledged long ago, so look in the sent log first.
     */
    fun registerMediaWanted(ctx: Context, requests: List<MediaRequest>) {
        val db = Db.get(ctx)
        for (r in requests) {
            val m = db.get(Db.T_SENT, r.uid) ?: db.get(Db.T_QUEUE, r.uid) ?: continue
            val ref = Json.mediaFromJson(m.mediaJson).firstOrNull { it.sha256 == r.sha256 } ?: continue
            db.addMediaJob(MediaJob(r.uid, r.sha256, ref.uri, ref.mime, ref.size, m.addressKey, 0))
        }
    }

    /** PUT /v1/media/{uid}/{sha256}, streamed from the system store. Returns false when a failure was recorded. */
    fun uploadMedia(ctx: Context): Boolean {
        val db = Db.get(ctx)
        for (job in db.mediaJobs(20)) {
            val input = try {
                MediaIo.open(ctx, job.uri)
            } catch (e: Exception) {
                null
            }
            if (input == null) {
                giveUpOrCount(db, job)
                continue
            }
            val res = try {
                input.use { Http.putStream(ctx, "/v1/media/${job.uid}/${job.sha256}", job.mime, job.size, job.sha256, it) }
            } catch (e: IOException) {
                giveUpOrCount(db, job)
                Net.failTransient(ctx, "media upload")
                return false
            }
            when {
                res.code == 200 -> db.deleteMediaJob(job.uid, job.sha256)
                res.code == 401 -> {
                    Net.failAuth(ctx)
                    return false
                }
                res.code == 429 || res.code >= 500 -> {
                    Net.failTransient(ctx, "HTTP ${res.code}")
                    return false
                }
                else -> {
                    Logx.w("media refused with HTTP ${res.code}")
                    db.deleteMediaJob(job.uid, job.sha256) // a refusal will not change by repeating it
                }
            }
        }
        return true
    }

    private fun giveUpOrCount(db: Db, job: MediaJob) {
        if (job.attempts + 1 >= MAX_MEDIA_ATTEMPTS) {
            Logx.w("giving up on an attachment that cannot be read or sent")
            db.deleteMediaJob(job.uid, job.sha256)
        } else {
            db.bumpMediaJob(job.uid, job.sha256)
        }
    }
}
