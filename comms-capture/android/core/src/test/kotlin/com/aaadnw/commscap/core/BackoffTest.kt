package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class BackoffTest {
    @Test
    fun doublesFromFifteenSecondsToFifteenMinuteCap() {
        val b = Backoff(jitter = Backoff.noJitter)
        val seconds = (0..9).map { b.delayMs(it) / 1000 }
        assertEquals(listOf(15L, 30, 60, 120, 240, 480, 900, 900, 900, 900), seconds)
    }

    @Test
    fun hugeAttemptNumbersDoNotOverflow() {
        val b = Backoff(jitter = Backoff.noJitter)
        assertEquals(900_000L, b.delayMs(10_000))
        assertEquals(15_000L, b.delayMs(-5))
    }

    @Test
    fun jitterIsInjectedAndClampedToTheCap() {
        val up = Backoff(jitter = { it * 2 })
        assertEquals(30_000L, up.delayMs(0))
        assertEquals(900_000L, up.delayMs(6))
        val down = Backoff(jitter = { it / 2 })
        assertEquals(7_500L, down.delayMs(0))
        assertEquals(1L, Backoff(jitter = { -5 }).delayMs(0))
    }

    @Test
    fun jitterSeesTheUnjitteredDelay() {
        val seen = ArrayList<Long>()
        val b = Backoff(jitter = { seen.add(it); it })
        b.delayMs(0); b.delayMs(1); b.delayMs(20)
        assertEquals(listOf(15_000L, 30_000L, 900_000L), seen)
    }

    @Test
    fun defaultJitterStaysWithin75To100Percent() {
        val b = Backoff()
        repeat(200) {
            val d = b.delayMs(2)
            assertTrue(d in 45_000L..60_000L, "delay $d")
        }
        repeat(200) { assertTrue(b.delayMs(12) in 675_000L..900_000L) }
    }
}
