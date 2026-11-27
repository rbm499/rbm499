package com.aaadnw.commscap.core

/** A queued message as the planner sees it. */
data class QueueRef(val uid: String, val tsMs: Long)

/** Upload batches: at most 20 messages per request, oldest first. */
object UploadPlanner {
    const val MAX_BATCH = 20

    private val ORDER = compareBy<QueueRef> { it.tsMs }.thenBy { it.uid }

    /** The uids of the next batch to send. */
    fun nextBatch(queue: List<QueueRef>, max: Int = MAX_BATCH): List<String> =
        queue.sortedWith(ORDER).take(max.coerceAtLeast(1)).map { it.uid }

    /** The whole queue as consecutive batches (oldest first). */
    fun batches(queue: List<QueueRef>, max: Int = MAX_BATCH): List<List<String>> =
        queue.sortedWith(ORDER).map { it.uid }.chunked(max.coerceAtLeast(1))
}
