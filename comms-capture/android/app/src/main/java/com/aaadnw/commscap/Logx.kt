package com.aaadnw.commscap

import android.util.Log

/**
 * The only place the app logs. Callers must never pass message bodies, addresses, the secret or signatures in [msg].
 * Exceptions are logged by class name only, because their messages can echo data (SQL arguments, parsed text).
 */
object Logx {
    private const val TAG = "CommsCap"

    fun i(msg: String) {
        Log.i(TAG, msg)
    }

    fun w(msg: String) {
        Log.w(TAG, msg)
    }

    fun e(msg: String, t: Throwable? = null) {
        Log.w(TAG, if (t == null) msg else msg + " [" + t.javaClass.simpleName + "]")
    }
}
