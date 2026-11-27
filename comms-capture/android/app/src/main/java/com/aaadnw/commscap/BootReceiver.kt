package com.aaadnw.commscap

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** After boot or an app update: schedule the periodic work, scan once, and (re)start the foreground service. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action
        if (action != Intent.ACTION_BOOT_COMPLETED && action != Intent.ACTION_MY_PACKAGE_REPLACED) return
        val app = context.applicationContext
        Engine.init(app)
        Scheduler.schedulePeriodic(app)
        Scheduler.runSoon(app) // the boot catch-up scan
        if (Prefs.get(app).isConfigured) CaptureService.start(app) // may be refused by the OS; that is fine
    }
}
