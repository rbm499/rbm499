package com.aaadnw.commscap

import android.content.Context
import com.aaadnw.commscap.core.Decision
import com.aaadnw.commscap.core.Gate
import com.aaadnw.commscap.core.LookbackPlanner
import com.aaadnw.commscap.core.Policy
import com.aaadnw.commscap.core.Redact
import com.aaadnw.commscap.core.Wire
import org.json.JSONArray
import org.json.JSONObject

/**
 * A message as read from a source (SMS store, MMS store, chat notification), before redaction and gating.
 * [addresses] are the counterparts (the sender for incoming, the recipients for outgoing).
 */
class RawMessage(
    val direction: String,
    val transport: String,
    val addresses: List<String>,
    val body: String,
    val tsMs: Long,
    val media: List<MediaRef>,
    val threadKey: String?,
)

/**
 * Redact -> gate -> (queue | deferred | held | nothing). This is the privacy-critical path:
 *  - the body is redacted before anything is stored;
 *  - a dropped message leaves no trace except a counter (no body, address or hash);
 *  - a message in a pause is skipped entirely.
 */
object Pipeline {
    const val DEDUPE_WINDOW_MS = 60_000L

    enum class Outcome { PAUSED, NO_ADDRESS, DUPLICATE, SENT, DROPPED, DEFERRED, HELD }

    class Evaluated(
        val raw: RawMessage,
        val redacted: String,
        val tags: List<String>,
        val decision: Decision,
        /** The first counterpart as the system store gave it (sent to the server raw; the server normalises it). */
        val address: String,
        val addressKey: String,
        val uid: String,
        val contact: Contacts.Info,
    )

    /** Pure evaluation: redaction, contact lookup, gate, uid. No side effects and no counters. Null if there is no address. */
    fun evaluate(ctx: Context, raw: RawMessage, policy: Policy): Evaluated? {
        check(Safety.ok()) { "privacy self-check failed" } // never gate with rules that do not behave as tested
        val addresses = raw.addresses.map { it.trim() }.filter { it.isNotEmpty() }.distinct()
        if (addresses.isEmpty()) return null
        val redaction = Redact.redact(raw.body)
        val hasMedia = raw.media.isNotEmpty()
        val infos = addresses.map { Contacts.lookup(ctx, it) }
        val decisions = addresses.indices.map { i ->
            Gate.decide(policy, addresses[i], redaction.text, hasMedia, infos[i].saved, infos[i].labels)
        }
        val decision = Gate.combine(decisions)
        val deviceId = Prefs.get(ctx).deviceId
        val uid = Wire.msgUid(deviceId, raw.direction, addresses[0], raw.tsMs, redaction.text, raw.media.size)
        return Evaluated(raw, redaction.text, redaction.tags, decision, addresses[0], Wire.canonicalAddress(addresses[0]), uid, infos[0])
    }

    /** Handles one message from a live source. Called on the capture thread. */
    fun handle(ctx: Context, raw: RawMessage): Outcome {
        val prefs = Prefs.get(ctx)
        val now = System.currentTimeMillis()

        if (Pause.log(ctx).covers(raw.tsMs)) {
            Counters.inc(ctx, Counters.PAUSED, now)
            return Outcome.PAUSED
        }
        val ev = evaluate(ctx, raw, PolicyStore.current(ctx))
        if (ev == null) {
            Counters.inc(ctx, Counters.SEEN, now)
            Counters.inc(ctx, Counters.DROPPED, now)
            return Outcome.NO_ADDRESS
        }
        val db = Db.get(ctx)
        if (db.has(ev.uid)) return Outcome.DUPLICATE

        Counters.inc(ctx, Counters.SEEN, now)
        if (raw.tsMs > prefs.lastCaptureTsMs) prefs.lastCaptureTsMs = raw.tsMs

        when (ev.decision.decision) {
            Gate.SEND -> {
                enqueue(ctx, ev, now)
                Counters.inc(ctx, Counters.SENT, now)
                lookback(ctx, ev, now)
                return Outcome.SENT
            }
            Gate.DEFER -> {
                db.insertMsg(Db.T_DEFERRED, stored(ev, Gate.DEFER, now, ev.raw.media))
                Counters.inc(ctx, Counters.DEFERRED, now)
                return Outcome.DEFERRED
            }
            Gate.HOLD -> {
                db.insertMsg(Db.T_HELD, stored(ev, Gate.HOLD, now, ev.raw.media))
                Counters.inc(ctx, Counters.HELD, now)
                return Outcome.HELD
            }
            else -> {
                // DROP: nothing is stored. Only the counter above.
                Counters.inc(ctx, Counters.DROPPED, now)
                return Outcome.DROPPED
            }
        }
    }

    /** Puts a message that passed the gate into the upload queue (hashing its attachments first). */
    fun enqueue(ctx: Context, ev: Evaluated, now: Long): Boolean {
        val described = MediaIo.describeAll(ctx, ev.raw.media)
        return Db.get(ctx).insertMsg(Db.T_QUEUE, stored(ev, Gate.SEND, now, described))
    }

    /**
     * Thread lookback: address A just produced `send`, so A's deferred messages that are still within `defer_hours` are
     * promoted (they are older, so the oldest-first upload order puts them before this one); aged-out ones are deleted.
     */
    private fun lookback(ctx: Context, ev: Evaluated, now: Long) {
        val db = Db.get(ctx)
        val policy = PolicyStore.current(ctx)
        val plan = LookbackPlanner.plan(db.deferredRefs(Db.T_DEFERRED), ev.address, now, policy.deferHours)
        for (uid in plan.promoteUids) {
            val m = db.get(Db.T_DEFERRED, uid) ?: continue
            val payload = m.payload ?: continue
            val media = MediaIo.describeAll(ctx, Json.mediaFromJson(m.mediaJson))
            val promoted = m.copy(
                payload = IngestJson.withGate(payload, Gate.SEND, "thread_lookback"),
                mediaJson = Json.mediaToJson(media),
                createdMs = now,
            )
            db.promote(promoted)
            Counters.inc(ctx, Counters.SENT, now)
        }
        db.delete(Db.T_DEFERRED, plan.expireUids)
    }

    private fun stored(ev: Evaluated, gateDecision: String, now: Long, media: List<MediaRef>): StoredMsg =
        StoredMsg(
            uid = ev.uid,
            tsMs = ev.raw.tsMs,
            addressKey = ev.addressKey,
            direction = ev.raw.direction,
            bodySha = Wire.sha256Hex(ev.redacted),
            payload = IngestJson.message(ev, gateDecision).toString(),
            mediaJson = if (media.isEmpty()) null else Json.mediaToJson(media),
            contactName = ev.contact.name,
            snippet = firstChars(ev.redacted, 40),
            createdMs = now,
        )

    /** First [n] characters without cutting a surrogate pair in half. */
    fun firstChars(s: String, n: Int): String {
        if (s.codePointCount(0, s.length) <= n) return s
        return s.substring(0, s.offsetByCodePoints(0, n))
    }
}

/** Builds the JSON of an ingest message (contract section 4), minus `media`, which is added at upload time. */
object IngestJson {
    fun message(ev: Pipeline.Evaluated, gateDecision: String): JSONObject {
        val o = JSONObject()
        o.put("uid", ev.uid)
        o.put("direction", ev.raw.direction)
        o.put("transport", ev.raw.transport)
        o.put("address", ev.address)
        o.put("contact_name", ev.contact.name ?: JSONObject.NULL)
        o.put("contact_saved", ev.contact.saved)
        o.put("contact_labels", JSONArray(ev.contact.labels))
        o.put("ts_ms", ev.raw.tsMs)
        o.put("body", ev.redacted)
        o.put("redactions", JSONArray(ev.tags))
        o.put("thread_key", ev.raw.threadKey ?: JSONObject.NULL)
        o.put("gate", gate(gateDecision, ev.decision.reason))
        return o
    }

    private fun gate(decision: String, reason: String): JSONObject {
        val g = JSONObject()
        g.put("decision", decision)
        g.put("reason", reason)
        g.put("rule_version", Gate.RULE_VERSION)
        return g
    }

    /** Rewrites the gate block of a stored payload (used when a deferred message is promoted). */
    fun withGate(payload: String, decision: String, reason: String): String {
        val o = JSONObject(payload)
        o.put("gate", gate(decision, reason))
        return o.toString()
    }
}
