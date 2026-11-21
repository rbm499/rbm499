package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class RollingCountersTest {
    private val h = 3_600_000L
    private val t0 = 1_790_000_000_000L

    @Test
    fun countsWithinTheWindowAndForgetsOlderHours() {
        val c = RollingCounters()
        c.increment("seen", t0)
        c.increment("seen", t0 + 5 * h, 2)
        c.increment("sent", t0 + 5 * h)
        assertEquals(3, c.total("seen", t0 + 6 * h))
        assertEquals(1, c.total("sent", t0 + 6 * h))
        assertEquals(0, c.total("dropped", t0 + 6 * h))
        // 24 hours after the first hour's bucket it has fallen out of the window.
        assertEquals(2, c.total("seen", t0 + 24 * h))
        assertEquals(0, c.total("seen", t0 + 29 * h))
    }

    @Test
    fun totalsReturnsEveryRequestedKey() {
        val c = RollingCounters()
        c.increment("seen", t0)
        assertEquals(mapOf("seen" to 1, "sent" to 0), c.totals(listOf("seen", "sent"), t0))
    }

    @Test
    fun serializeAndParseRoundTrip() {
        val c = RollingCounters()
        c.increment("seen", t0, 3)
        c.increment("dropped", t0)
        c.increment("seen", t0 + 2 * h)
        val s = c.serialize()
        val back = RollingCounters.parse(s)
        assertEquals(s, back.serialize())
        assertEquals(4, back.total("seen", t0 + 3 * h))
        assertEquals(1, back.total("dropped", t0 + 3 * h))
    }

    @Test
    fun incrementPrunesOldBuckets() {
        val c = RollingCounters()
        c.increment("seen", t0)
        c.increment("seen", t0 + 100 * h)
        assertEquals(1, RollingCounters.parse(c.serialize()).total("seen", t0 + 100 * h))
        assertEquals(false, c.serialize().contains(RollingCounters.hourOf(t0).toString() + "|"))
    }

    @Test
    fun parseIgnoresGarbage() {
        assertEquals("", RollingCounters.parse(null).serialize())
        assertEquals("", RollingCounters.parse("").serialize())
        assertEquals("", RollingCounters.parse("junk;1|=x;|a=1").serialize())
    }

    @Test
    fun containsNothingButNumbersAndKeyNames() {
        val c = RollingCounters()
        c.increment("seen", t0)
        assertEquals(true, Regex("^[0-9|=,;a-z_-]*$").matches(c.serialize()))
    }
}
