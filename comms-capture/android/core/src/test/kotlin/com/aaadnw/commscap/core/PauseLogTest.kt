package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.util.TimeZone

class PauseLogTest {
    private val h = LookbackPlanner.HOUR_MS
    private val t0 = 1_790_000_000_000L

    @Test
    fun aPauseCoversItsOwnInterval() {
        val p = PauseLog().pause(t0, t0 + h)
        assertTrue(p.covers(t0))
        assertTrue(p.covers(t0 + h - 1))
        assertFalse(p.covers(t0 + h))
        assertFalse(p.covers(t0 - 1))
        assertEquals(t0 + h, p.activeUntil(t0 + 10))
        assertNull(p.activeUntil(t0 + h))
        assertNull(p.activeUntil(t0 - 1))
    }

    @Test
    fun resumeEndsARunningPauseButKeepsWhatAlreadyHappened() {
        val p = PauseLog().pause(t0, t0 + 10 * h).resume(t0 + 2 * h)
        assertTrue(p.covers(t0 + h))
        assertFalse(p.covers(t0 + 2 * h))
        assertNull(p.activeUntil(t0 + 2 * h))
    }

    @Test
    fun resumeWithNoRunningPauseChangesNothing() {
        val p = PauseLog().pause(t0, t0 + h)
        assertEquals(p.serialize(), p.resume(t0 + 5 * h).serialize())
        assertEquals(p.serialize(), p.resume(t0 - h).serialize())
    }

    @Test
    fun overlappingPausesReportTheLatestEnd() {
        val p = PauseLog().pause(t0, t0 + h).pause(t0 + 10, t0 + 3 * h)
        assertEquals(t0 + 3 * h, p.activeUntil(t0 + 20))
    }

    @Test
    fun emptyOrBackwardsPauseIsIgnored() {
        assertEquals("", PauseLog().pause(t0, t0).serialize())
        assertEquals("", PauseLog().pause(t0, t0 - 1).serialize())
    }

    @Test
    fun pruneForgetsOldPausesOnly() {
        val p = PauseLog().pause(t0, t0 + h).pause(t0 + 100 * h, t0 + 101 * h)
        val pruned = p.prune(t0 + 102 * h)
        assertFalse(pruned.covers(t0 + 1))
        assertTrue(pruned.covers(t0 + 100 * h + 1))
    }

    @Test
    fun serializeParseRoundTripAndGarbage() {
        val p = PauseLog().pause(t0, t0 + h).pause(t0 + 5 * h, t0 + 6 * h)
        assertEquals(p.serialize(), PauseLog.parse(p.serialize()).serialize())
        assertEquals("", PauseLog.parse(null).serialize())
        assertEquals("", PauseLog.parse("x-y,5-3,-,7").serialize())
        assertTrue(PauseLog.parse("1-5,junk").covers(2))
    }

    @Test
    fun localTimesNextOccurrenceAndTomorrow() {
        val la = TimeZone.getTimeZone("America/Los_Angeles")
        val cal = java.util.Calendar.getInstance(la)
        cal.clear(); cal.set(2026, java.util.Calendar.NOVEMBER, 21, 23, 10, 0)
        val now = cal.timeInMillis

        val next0230 = java.util.Calendar.getInstance(la).apply { timeInMillis = LocalTimes.nextOccurrenceMs(now, la, 2, 30) }
        assertEquals(22, next0230.get(java.util.Calendar.DAY_OF_MONTH))
        assertEquals(2, next0230.get(java.util.Calendar.HOUR_OF_DAY))
        assertEquals(30, next0230.get(java.util.Calendar.MINUTE))

        cal.set(2026, java.util.Calendar.NOVEMBER, 21, 1, 0, 0)
        val early = java.util.Calendar.getInstance(la).apply { timeInMillis = LocalTimes.nextOccurrenceMs(cal.timeInMillis, la, 2, 30) }
        assertEquals(21, early.get(java.util.Calendar.DAY_OF_MONTH))

        val tomorrow = java.util.Calendar.getInstance(la).apply { timeInMillis = LocalTimes.tomorrowAtMs(now, la, 6, 0) }
        assertEquals(22, tomorrow.get(java.util.Calendar.DAY_OF_MONTH))
        assertEquals(6, tomorrow.get(java.util.Calendar.HOUR_OF_DAY))
        assertEquals(0, tomorrow.get(java.util.Calendar.MINUTE))
    }
}
