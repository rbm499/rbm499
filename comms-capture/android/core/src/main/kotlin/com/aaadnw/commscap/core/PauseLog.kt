package com.aaadnw.commscap.core

/**
 * Michael's pauses as time intervals [startMs, endMs). A message whose own timestamp falls inside any pause is
 * never captured, no matter when the phone gets around to reading it (the nightly rescan and the catch-up scan
 * must not resurrect texts from a pause). Immutable.
 */
class PauseLog private constructor(private val intervals: List<Pair<Long, Long>>) {
    constructor() : this(emptyList())

    /** Start a pause covering [nowMs, untilMs). */
    fun pause(nowMs: Long, untilMs: Long): PauseLog =
        if (untilMs <= nowMs) this else PauseLog(intervals + (nowMs to untilMs))

    /** End every pause that is running at [nowMs] right now. */
    fun resume(nowMs: Long): PauseLog =
        PauseLog(intervals.map { (s, e) -> if (s <= nowMs && nowMs < e) s to nowMs else s to e }.filter { it.second > it.first })

    /** Was the phone paused at the moment [tsMs]? */
    fun covers(tsMs: Long): Boolean = intervals.any { (s, e) -> tsMs in s until e }

    /** If a pause is running at [nowMs], the time it ends (latest end when several overlap); otherwise null. */
    fun activeUntil(nowMs: Long): Long? =
        intervals.filter { (s, e) -> s <= nowMs && nowMs < e }.maxOfOrNull { it.second }

    /** Forget pauses that ended more than [keepMs] ago (the reconcile window is 48 h). */
    fun prune(nowMs: Long, keepMs: Long = 72 * LookbackPlanner.HOUR_MS): PauseLog =
        PauseLog(intervals.filter { it.second >= nowMs - keepMs })

    /** `start-end,start-end` (epoch milliseconds, ASCII). */
    fun serialize(): String = intervals.joinToString(",") { "${it.first}-${it.second}" }

    companion object {
        fun parse(s: String?): PauseLog {
            if (s.isNullOrEmpty()) return PauseLog()
            val list = s.split(',').mapNotNull { part ->
                val a = part.substringBefore('-').toLongOrNull()
                val b = part.substringAfter('-', "").toLongOrNull()
                if (a != null && b != null && b > a) a to b else null
            }
            return PauseLog(list)
        }
    }
}
