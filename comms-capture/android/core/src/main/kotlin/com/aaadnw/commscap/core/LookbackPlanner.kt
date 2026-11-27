package com.aaadnw.commscap.core

/** A deferred (or held) message as the planner sees it: no body, just enough to decide. */
data class DeferredRef(val uid: String, val addressKey: String, val tsMs: Long)

data class LookbackPlan(val promoteUids: List<String>, val expireUids: List<String>)

/**
 * The "thread lookback": when address A produces `send`, A's deferred messages that are still younger than
 * `defer_hours` are promoted (oldest first, so they are enqueued before the new message); deferred messages that
 * have aged out are deleted. Age is measured from the message's own timestamp.
 */
object LookbackPlanner {
    const val HOUR_MS = 3_600_000L
    const val DAY_MS = 24 * HOUR_MS

    fun plan(deferred: List<DeferredRef>, sendAddress: String?, nowMs: Long, deferHours: Int): LookbackPlan {
        val windowMs = deferHours.toLong() * HOUR_MS
        val target = Wire.canonicalAddress(sendAddress)
        val promote = if (target.isEmpty()) {
            emptyList()
        } else {
            deferred
                .filter { Wire.canonicalAddress(it.addressKey) == target && nowMs - it.tsMs < windowMs }
                .sortedWith(compareBy<DeferredRef> { it.tsMs }.thenBy { it.uid })
                .map { it.uid }
        }
        return LookbackPlan(promote, expired(deferred, nowMs, windowMs))
    }

    /** Uids whose age is at least [maxAgeMs]. Used for deferred (defer_hours) and held (hold_media_days) messages. */
    fun expired(refs: List<DeferredRef>, nowMs: Long, maxAgeMs: Long): List<String> =
        refs.filter { nowMs - it.tsMs >= maxAgeMs }.sortedBy { it.tsMs }.map { it.uid }
}
