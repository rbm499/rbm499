package com.aaadnw.commscap

import android.content.Context
import com.aaadnw.commscap.core.LocalTimes
import com.aaadnw.commscap.core.LookbackPlanner
import com.aaadnw.commscap.core.PauseLog
import java.util.TimeZone

/** Michael's pause control. A message whose own timestamp is inside a pause is never captured, even much later. */
object Pause {
    fun log(ctx: Context): PauseLog = PauseLog.parse(Prefs.get(ctx).pauseLog)

    fun activeUntil(ctx: Context, nowMs: Long = System.currentTimeMillis()): Long? = log(ctx).activeUntil(nowMs)

    fun pauseForOneHour(ctx: Context) = start(ctx, System.currentTimeMillis() + LookbackPlanner.HOUR_MS)

    /** Until 6 am on the next calendar day (local time). */
    fun pauseUntilTomorrow(ctx: Context) =
        start(ctx, LocalTimes.tomorrowAtMs(System.currentTimeMillis(), TimeZone.getDefault(), 6, 0))

    fun resume(ctx: Context) {
        val now = System.currentTimeMillis()
        Prefs.get(ctx).pauseLog = log(ctx).resume(now).serialize()
        changed(ctx)
    }

    private fun start(ctx: Context, untilMs: Long) {
        val now = System.currentTimeMillis()
        Prefs.get(ctx).pauseLog = log(ctx).prune(now).pause(now, untilMs).serialize()
        changed(ctx)
    }

    private fun changed(ctx: Context) {
        CaptureService.refresh(ctx)
        // The server alerts the office when a pause lasts too long, so report it right away.
        Engine.syncSoon(ctx, forceHeartbeat = true)
    }
}
