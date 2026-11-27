package com.aaadnw.commscap

import android.content.Context
import android.database.ContentObserver
import android.os.Handler
import android.os.Looper
import android.provider.Telephony
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.ThreadFactory
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Two single-thread executors: `capture` (reading the system stores and gating; quick) and `net` (uploads, heartbeat,
 * reconcile; may block on the network). Everything that touches capture state or the network goes through them, so
 * triggers from the receiver, the content observers, the service timer and WorkManager can never run in parallel.
 */
object Engine {
    val capture: ScheduledExecutorService = Executors.newSingleThreadScheduledExecutor(named("cc-capture"))
    val net: ScheduledExecutorService = Executors.newSingleThreadScheduledExecutor(named("cc-net"))

    private val observersRegistered = AtomicBoolean(false)
    private val scanQueued = AtomicBoolean(false)
    private val syncQueued = AtomicBoolean(false)

    @Volatile
    private var forceHeartbeatNext = false

    private fun named(name: String) = ThreadFactory { r ->
        val t = Thread(r, name)
        t.isDaemon = true
        t
    }

    /** Idempotent. Called whenever the process starts a component. */
    fun init(ctx: Context) {
        val app = ctx.applicationContext
        Notifs.ensureChannels(app)
        registerObservers(app)
    }

    private fun registerObservers(app: Context) {
        if (!observersRegistered.compareAndSet(false, true)) return
        val observer = object : ContentObserver(Handler(Looper.getMainLooper())) {
            override fun onChange(selfChange: Boolean) {
                scanSoon(app)
            }
        }
        // The observer alone is not trusted (see the 15 minute worker), but it makes capture prompt.
        app.contentResolver.registerContentObserver(Telephony.Sms.CONTENT_URI, true, observer)
        app.contentResolver.registerContentObserver(Telephony.Mms.CONTENT_URI, true, observer)
    }

    /** Coalesced: many provider notifications for one message give one scan. */
    fun scanSoon(ctx: Context, delayMs: Long = 1500L) {
        val app = ctx.applicationContext
        if (!scanQueued.compareAndSet(false, true)) return
        capture.schedule(
            Runnable {
                scanQueued.set(false)
                scanNow(app)
            },
            delayMs, TimeUnit.MILLISECONDS,
        )
    }

    /** Runs on the capture thread (callers are already on it). */
    fun scanNow(ctx: Context) {
        try {
            val handled = ProviderScanner.scan(ctx)
            if (handled > 0 && Db.get(ctx).count(Db.T_QUEUE) > 0) syncSoon(ctx)
        } catch (t: Throwable) {
            // The cursor stays where it was; the next scan retries.
            Logx.e("scan failed", t)
        }
        CaptureService.refresh(ctx)
    }

    /** Coalesced network cycle on the net thread. */
    fun syncSoon(ctx: Context, forceHeartbeat: Boolean = false) {
        val app = ctx.applicationContext
        if (forceHeartbeat) forceHeartbeatNext = true
        if (!syncQueued.compareAndSet(false, true)) return
        net.execute {
            syncQueued.set(false)
            val force = forceHeartbeatNext
            forceHeartbeatNext = false
            Sync.cycle(app, force)
        }
    }

    /** For WorkManager: one scan, then one network cycle, waiting for both (bounded). */
    fun fullCycleBlocking(ctx: Context) {
        val app = ctx.applicationContext
        init(app)
        waitFor { capture.submit(Runnable { scanNow(app) }).get(4, TimeUnit.MINUTES) }
        waitFor { net.submit(Runnable { Sync.cycle(app) }).get(8, TimeUnit.MINUTES) }
    }

    fun reconcileBlocking(ctx: Context) {
        val app = ctx.applicationContext
        init(app)
        waitFor { capture.submit(Runnable { scanNow(app) }).get(4, TimeUnit.MINUTES) }
        waitFor { net.submit(Runnable { Logx.i("reconcile: " + Reconcile.run(app)) }).get(8, TimeUnit.MINUTES) }
    }

    /** Runs the reconcile in the background (status screen button). */
    fun reconcileSoon(ctx: Context) {
        val app = ctx.applicationContext
        net.execute {
            try {
                Reconcile.run(app)
            } catch (t: Throwable) {
                Logx.e("reconcile failed", t)
            }
        }
    }

    private fun waitFor(block: () -> Unit) {
        try {
            block()
        } catch (e: TimeoutException) {
            Logx.w("work is taking long; it continues in the background")
        }
    }
}
