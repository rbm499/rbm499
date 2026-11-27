package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class UploadPlannerTest {
    private fun refs(n: Int, shuffle: Boolean = false): List<QueueRef> {
        val l = (1..n).map { QueueRef("u%03d".format(it), 1_000L + it) }
        return if (shuffle) l.reversed() else l
    }

    @Test
    fun nextBatchIsAtMostTwentyOldestFirst() {
        val b = UploadPlanner.nextBatch(refs(45, shuffle = true))
        assertEquals(20, b.size)
        assertEquals((1..20).map { "u%03d".format(it) }, b)
    }

    @Test
    fun batchesChunkTheWholeQueueInOrder() {
        val bs = UploadPlanner.batches(refs(45, shuffle = true))
        assertEquals(listOf(20, 20, 5), bs.map { it.size })
        assertEquals("u021", bs[1].first())
        assertEquals("u045", bs[2].last())
    }

    @Test
    fun emptyAndSmallQueues() {
        assertEquals(emptyList<String>(), UploadPlanner.nextBatch(emptyList()))
        assertEquals(emptyList<List<String>>(), UploadPlanner.batches(emptyList()))
        assertEquals(listOf("u001"), UploadPlanner.nextBatch(refs(1)))
    }

    @Test
    fun sameTimestampBreaksTiesOnUidAndMaxIsHonoured() {
        val q = listOf(QueueRef("b", 5), QueueRef("a", 5), QueueRef("c", 1))
        assertEquals(listOf("c", "a", "b"), UploadPlanner.nextBatch(q))
        assertEquals(listOf("c", "a"), UploadPlanner.nextBatch(q, max = 2))
        assertEquals(listOf("c"), UploadPlanner.nextBatch(q, max = 0))
    }
}
