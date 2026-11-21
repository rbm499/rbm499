package com.aaadnw.commscap

import android.content.Context
import com.aaadnw.commscap.core.Backoff

/**
 * Failure bookkeeping for signed calls. Nothing here ever deletes queued messages: a failure only changes when the
 * next attempt happens and what the status screen says.
 */
object Net {
    private const val NORMAL_SCHEDULE_MS = 15 * 60_000L

    /** 5xx, 429, timeout, no network: exponential backoff 15 s ... 15 min with jitter. */
    fun failTransient(ctx: Context, why: String) {
        val p = Prefs.get(ctx)
        val attempt = p.backoffAttempt
        val delay = Backoff().delayMs(attempt)
        p.backoffAttempt = attempt + 1
        p.nextAttemptMs = System.currentTimeMillis() + delay
        p.errorKind = "net"
        p.lastError = "Cannot reach the office service ($why). Everything is kept and will be retried."
        Logx.w("transient failure ($why), retry in ${delay / 1000}s")
        Scheduler.scheduleRetry(ctx, delay)
    }

    /** 401: not authorised or the phone's clock is wrong. Do not hammer; heartbeats continue at the normal cadence. */
    fun failAuth(ctx: Context) {
        val p = Prefs.get(ctx)
        p.errorKind = "auth"
        p.lastError = "The office service does not accept this phone (check the secret and that the phone's date and time are correct). Nothing is deleted."
        p.nextAttemptMs = System.currentTimeMillis() + NORMAL_SCHEDULE_MS
        Logx.w("401 from server")
    }

    /** Another 4xx: mark the batch failed, show it, retry on the normal schedule (no hot loop). */
    fun failClient(ctx: Context, code: Int) {
        val p = Prefs.get(ctx)
        p.failedBatches = p.failedBatches + 1
        p.errorKind = "client"
        p.lastError = "The office service refused a batch (HTTP $code). Messages are kept and will be retried."
        p.nextAttemptMs = System.currentTimeMillis() + NORMAL_SCHEDULE_MS
        Logx.w("client error $code")
    }

    /** A signed request worked: connection and credentials are fine. A refused-batch notice stays until a batch goes through. */
    fun succeeded(ctx: Context) {
        val p = Prefs.get(ctx)
        if (p.errorKind != "client") p.clearErrors() else p.backoffAttempt = 0
    }

    /** An ingest batch was acknowledged: everything is fine again. */
    fun ingestSucceeded(ctx: Context) {
        Prefs.get(ctx).clearErrors()
    }
}
