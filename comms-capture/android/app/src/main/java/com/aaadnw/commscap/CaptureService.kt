package com.aaadnw.commscap

import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper

/**
 * Foreground service (type dataSync) that keeps the process alive and shows the persistent low-priority notification
 * with the last sync. Capture does NOT depend on it: the SMS broadcast, the notification listener and WorkManager
 * work without it, and Android may refuse to start it from the background (that is caught, not fatal).
 */
class CaptureService : Service() {
    private val handler = Handler(Looper.getMainLooper())
    private val tick = object : Runnable {
        override fun run() {
            // Every 15 minutes while alive: scan, sync, heartbeat (WorkManager is the backstop).
            Engine.capture.execute { Engine.scanNow(applicationContext) }
            Engine.syncSoon(applicationContext)
            handler.postDelayed(this, TICK_MS)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        Engine.init(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        try {
            val notification = Notifs.status(this)
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(Notifs.ID_STATUS, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
            } else {
                startForeground(Notifs.ID_STATUS, notification)
            }
        } catch (e: Exception) {
            // For example ForegroundServiceStartNotAllowedException when started from the background.
            Logx.e("cannot run in the foreground", e)
            stopSelf()
            return START_NOT_STICKY
        }
        running = true
        handler.removeCallbacks(tick)
        handler.postDelayed(tick, TICK_MS)
        return START_STICKY
    }

    override fun onDestroy() {
        running = false
        handler.removeCallbacks(tick)
        super.onDestroy()
    }

    companion object {
        private const val TICK_MS = 15 * 60_000L

        @Volatile
        private var running = false

        /** Safe to call from anywhere; a refusal by the system is logged and ignored. */
        fun start(ctx: Context) {
            try {
                ctx.applicationContext.startForegroundService(Intent(ctx.applicationContext, CaptureService::class.java))
            } catch (e: Exception) {
                Logx.e("foreground service not started", e)
            }
        }

        /** Updates the persistent notification (only while the service is running). */
        fun refresh(ctx: Context) {
            if (!running) return
            try {
                val nm = ctx.getSystemService(NotificationManager::class.java)
                nm.notify(Notifs.ID_STATUS, Notifs.status(ctx))
            } catch (e: Exception) {
                Logx.e("status notification not updated", e)
            }
        }
    }
}
