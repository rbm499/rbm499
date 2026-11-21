package com.aaadnw.commscap

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequest
import androidx.work.PeriodicWorkRequest
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import com.aaadnw.commscap.core.LocalTimes
import java.util.TimeZone
import java.util.concurrent.TimeUnit

/** The 15-minute catch-up worker: scan the system stores, upload, heartbeat. Runs offline too (the upload just backs off). */
class SyncWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result {
        return try {
            Engine.fullCycleBlocking(applicationContext)
            Result.success()
        } catch (t: Throwable) {
            Logx.e("sync worker failed", t)
            Result.retry()
        }
    }
}

/** The nightly reconcile (~02:30 local). */
class ReconcileWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result {
        return try {
            Engine.reconcileBlocking(applicationContext)
            Result.success()
        } catch (t: Throwable) {
            Logx.e("reconcile worker failed", t)
            Result.retry()
        }
    }
}

object Scheduler {
    private const val PERIODIC_SYNC = "commscap-sync"
    private const val PERIODIC_RECONCILE = "commscap-reconcile"
    private const val RETRY = "commscap-sync-retry"
    private const val NOW = "commscap-sync-now"

    /** Unique periodic work: calling this again (boot, app start, app update) never creates a second copy. */
    fun schedulePeriodic(ctx: Context) {
        val wm = WorkManager.getInstance(ctx.applicationContext)
        val sync = PeriodicWorkRequest.Builder(SyncWorker::class.java, 15, TimeUnit.MINUTES).build()
        wm.enqueueUniquePeriodicWork(PERIODIC_SYNC, ExistingPeriodicWorkPolicy.KEEP, sync)

        val now = System.currentTimeMillis()
        val untilNightly = LocalTimes.nextOccurrenceMs(now, TimeZone.getDefault(), 2, 30) - now
        val nightly = PeriodicWorkRequest.Builder(ReconcileWorker::class.java, 24, TimeUnit.HOURS)
            .setInitialDelay(untilNightly, TimeUnit.MILLISECONDS)
            .build()
        wm.enqueueUniquePeriodicWork(PERIODIC_RECONCILE, ExistingPeriodicWorkPolicy.KEEP, nightly)
    }

    /** A retry after a network failure, delayed by the backoff. Replaces any earlier retry. */
    fun scheduleRetry(ctx: Context, delayMs: Long) {
        val onlineOnly = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
        val req = OneTimeWorkRequest.Builder(SyncWorker::class.java)
            .setInitialDelay(delayMs, TimeUnit.MILLISECONDS)
            .setConstraints(onlineOnly)
            .build()
        WorkManager.getInstance(ctx.applicationContext).enqueueUniqueWork(RETRY, ExistingWorkPolicy.REPLACE, req)
    }

    /** A catch-up scan as soon as possible (boot, app update, or shortly after an SMS arrived). */
    fun runSoon(ctx: Context, delayMs: Long = 0L) {
        val req = OneTimeWorkRequest.Builder(SyncWorker::class.java)
            .setInitialDelay(delayMs, TimeUnit.MILLISECONDS)
            .build()
        WorkManager.getInstance(ctx.applicationContext).enqueueUniqueWork(NOW, ExistingWorkPolicy.REPLACE, req)
    }

    /** Used by BootReceiver / MainActivity: schedule everything and start the foreground service. */
    fun ensureRunning(ctx: Context) {
        schedulePeriodic(ctx)
        if (Prefs.get(ctx).isConfigured) CaptureService.start(ctx)
    }
}
