package com.aaadnw.commscap

import android.Manifest
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.PowerManager
import android.provider.Settings

object Perms {
    fun has(ctx: Context, permission: String): Boolean =
        ctx.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED

    fun sms(ctx: Context): Boolean =
        has(ctx, Manifest.permission.RECEIVE_SMS) && has(ctx, Manifest.permission.READ_SMS)

    fun contacts(ctx: Context): Boolean = has(ctx, Manifest.permission.READ_CONTACTS)

    fun postNotifications(ctx: Context): Boolean =
        Build.VERSION.SDK_INT < 33 || has(ctx, Manifest.permission.POST_NOTIFICATIONS)

    fun notificationListener(ctx: Context): Boolean {
        val flat = Settings.Secure.getString(ctx.contentResolver, "enabled_notification_listeners") ?: return false
        return flat.split(":").any { ComponentName.unflattenFromString(it)?.packageName == ctx.packageName }
    }

    fun batteryUnrestricted(ctx: Context): Boolean {
        val pm = ctx.getSystemService(Context.POWER_SERVICE) as PowerManager
        return pm.isIgnoringBatteryOptimizations(ctx.packageName)
    }

    /**
     * The two permissions without which capturing must NOT run. Contacts is one of them on purpose: the gate's
     * privacy boundary is "a saved contact is never captured unless a client", so without Contacts every
     * personal contact would look like an unknown number. Capture waits (cursors do not advance) until fixed.
     */
    fun missingForCapture(ctx: Context): String? = when {
        !sms(ctx) -> "SMS"
        !contacts(ctx) -> "Contacts"
        else -> null
    }

    /** The `permissions` object of the heartbeat. */
    fun asMap(ctx: Context): Map<String, Boolean> = linkedMapOf(
        "sms" to sms(ctx),
        "contacts" to contacts(ctx),
        "notification_listener" to notificationListener(ctx),
        "battery_unrestricted" to batteryUnrestricted(ctx),
        "post_notifications" to postNotifications(ctx),
    )
}
