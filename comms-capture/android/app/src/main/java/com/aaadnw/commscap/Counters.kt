package com.aaadnw.commscap

import android.content.Context
import com.aaadnw.commscap.core.RollingCounters

/** Content-free 24 h counters. Numbers only: nothing about any message is ever stored here. */
object Counters {
    const val SEEN = "seen"
    const val SENT = "sent"
    const val DROPPED = "dropped"
    const val DEFERRED = "deferred"
    const val HELD = "held"
    const val PAUSED = "paused_skipped"

    /** The keys the heartbeat reports (contract section 7). */
    val HEARTBEAT_KEYS = listOf(SEEN, SENT, DROPPED, DEFERRED, HELD)

    private val lock = Any()

    fun inc(ctx: Context, key: String, nowMs: Long = System.currentTimeMillis()) {
        synchronized(lock) {
            val p = Prefs.get(ctx)
            val c = RollingCounters.parse(p.counters)
            c.increment(key, nowMs)
            p.counters = c.serialize()
        }
    }

    fun snapshot(ctx: Context, nowMs: Long = System.currentTimeMillis()): Map<String, Int> =
        synchronized(lock) {
            RollingCounters.parse(Prefs.get(ctx).counters).totals(HEARTBEAT_KEYS + PAUSED, nowMs)
        }
}
