package com.aaadnw.commscap

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony

/**
 * SMS_RECEIVED (the system delivers it only to apps holding RECEIVE_SMS; the manifest requires BROADCAST_SMS so nobody
 * else can fake it). It is used as a prompt to scan the system SMS store rather than as a second capture path:
 *  - the broadcast carries the network timestamp while the SMS store records the arrival time, so a message captured
 *    from the broadcast would get a different uid than the same message found in the store (a duplicate upload, and
 *    the nightly reconcile could not rebuild it);
 *  - multipart messages are already reassembled by the store, so nothing needs stitching here.
 * It also restarts the process if Android had killed it, which registers the content observers again.
 */
class SmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        val app = context.applicationContext
        Engine.init(app)
        val pending = goAsync()
        Engine.capture.execute {
            try {
                // The default messaging app writes the message to the store a moment after the broadcast.
                Engine.scanNow(app)
                Thread.sleep(3000)
                Engine.scanNow(app)
            } catch (t: Throwable) {
                Logx.e("sms receiver", t)
            } finally {
                pending.finish()
            }
        }
        Scheduler.runSoon(app, 30_000L) // backstop if the store was slow
    }
}
