package com.aaadnw.commscap.core

/**
 * Content-free counters over the last 24 hours, kept in one-hour buckets. Numbers only: nothing about any message
 * (no body, address or hash) ever goes in here. Not thread-safe; the app guards it with a lock.
 */
class RollingCounters private constructor(private val buckets: MutableMap<Long, MutableMap<String, Int>>) {
    constructor() : this(HashMap())

    fun increment(key: String, nowMs: Long, by: Int = 1) {
        val bucket = buckets.getOrPut(hourOf(nowMs)) { HashMap() }
        bucket[key] = (bucket[key] ?: 0) + by
        prune(nowMs)
    }

    /** Sum over the last 24 hourly buckets (so between 23 and 24 hours of history). */
    fun total(key: String, nowMs: Long): Int {
        val oldest = hourOf(nowMs) - (WINDOW_HOURS - 1)
        var sum = 0
        for ((hour, bucket) in buckets) {
            if (hour in oldest..hourOf(nowMs)) sum += bucket[key] ?: 0
        }
        return sum
    }

    fun totals(keys: List<String>, nowMs: Long): Map<String, Int> =
        keys.associateWith { total(it, nowMs) }

    fun prune(nowMs: Long) {
        val oldest = hourOf(nowMs) - (WINDOW_HOURS - 1)
        buckets.keys.removeAll { it < oldest }
    }

    /** `hour|key=count,key=count;hour|...` (ASCII only). */
    fun serialize(): String = buckets.entries.sortedBy { it.key }.joinToString(";") { (hour, bucket) ->
        hour.toString() + "|" + bucket.entries.sortedBy { it.key }.joinToString(",") { "${it.key}=${it.value}" }
    }

    companion object {
        const val WINDOW_HOURS = 24L
        private const val HOUR_MS = 3_600_000L

        fun hourOf(ms: Long): Long = Math.floorDiv(ms, HOUR_MS)

        fun parse(s: String?): RollingCounters {
            val out = RollingCounters()
            if (s.isNullOrEmpty()) return out
            for (part in s.split(';')) {
                val hour = part.substringBefore('|').toLongOrNull() ?: continue
                val bucket = HashMap<String, Int>()
                for (kv in part.substringAfter('|', "").split(',')) {
                    val key = kv.substringBefore('=')
                    val n = kv.substringAfter('=', "").toIntOrNull() ?: continue
                    if (key.isNotEmpty()) bucket[key] = n
                }
                if (bucket.isNotEmpty()) out.buckets[hour] = bucket
            }
            return out
        }
    }
}
