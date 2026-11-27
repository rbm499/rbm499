package com.aaadnw.commscap

import android.app.Application

class CommsApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // Runs whenever the process starts for any reason (SMS broadcast, notification access, WorkManager, UI):
        // channels exist and the SMS/MMS content observers are registered.
        Engine.init(this)
    }
}
