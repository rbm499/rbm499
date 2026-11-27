package com.aaadnw.commscap.core

import java.util.Calendar
import java.util.TimeZone

/** Wall-clock arithmetic in the phone's time zone (DST-safe via Calendar). */
object LocalTimes {
    /** The next occurrence of [hour]:[minute] strictly after [nowMs]. */
    fun nextOccurrenceMs(nowMs: Long, tz: TimeZone, hour: Int, minute: Int): Long {
        val cal = Calendar.getInstance(tz)
        cal.timeInMillis = nowMs
        cal.set(Calendar.HOUR_OF_DAY, hour)
        cal.set(Calendar.MINUTE, minute)
        cal.set(Calendar.SECOND, 0)
        cal.set(Calendar.MILLISECOND, 0)
        if (cal.timeInMillis <= nowMs) cal.add(Calendar.DAY_OF_MONTH, 1)
        return cal.timeInMillis
    }

    /** [hour]:[minute] on the calendar day after [nowMs]'s day ("until tomorrow"). */
    fun tomorrowAtMs(nowMs: Long, tz: TimeZone, hour: Int, minute: Int): Long {
        val cal = Calendar.getInstance(tz)
        cal.timeInMillis = nowMs
        cal.add(Calendar.DAY_OF_MONTH, 1)
        cal.set(Calendar.HOUR_OF_DAY, hour)
        cal.set(Calendar.MINUTE, minute)
        cal.set(Calendar.SECOND, 0)
        cal.set(Calendar.MILLISECOND, 0)
        return cal.timeInMillis
    }
}
