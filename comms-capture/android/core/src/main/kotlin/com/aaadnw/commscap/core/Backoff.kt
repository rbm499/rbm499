package com.aaadnw.commscap.core

import kotlin.random.Random

/**
 * Retry delay after failure number [attempt] (0 = first failure): 15 s, 30 s, 60 s ... doubling up to a 15 minute cap.
 * [jitter] receives the un-jittered delay and returns the delay to use; the result is clamped to [1 ms, capMs] so
 * jitter can never push a retry past the cap. The default jitter spreads retries over 75-100 % of the delay.
 */
class Backoff(
    private val baseMs: Long = 15_000L,
    private val capMs: Long = 15 * 60_000L,
    private val jitter: (Long) -> Long = defaultJitter,
) {
    fun delayMs(attempt: Int): Long {
        val shift = attempt.coerceIn(0, 30)
        val raw = if (baseMs >= capMs) capMs else minOf(capMs, baseMs shl shift)
        return jitter(raw).coerceIn(1L, capMs)
    }

    companion object {
        val defaultJitter: (Long) -> Long = { d -> (d * (0.75 + Random.nextDouble() * 0.25)).toLong() }
        val noJitter: (Long) -> Long = { d -> d }
    }
}
