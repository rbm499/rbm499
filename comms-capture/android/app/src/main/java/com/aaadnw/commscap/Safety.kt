package com.aaadnw.commscap

import com.aaadnw.commscap.core.SelfCheck

/**
 * Runs the privacy rules' known-answer check once per process on this phone's own regex engine (Android's differs from
 * the JVM the tests run on). If it fails, nothing is captured: the cursors stay put, so nothing is lost either.
 */
object Safety {
    @Volatile
    private var result: List<String>? = null

    fun failures(): List<String> =
        result ?: synchronized(this) {
            result ?: SelfCheck.run().also {
                result = it
                if (it.isNotEmpty()) Logx.w("privacy self-check FAILED: " + it.joinToString(", "))
            }
        }

    fun ok(): Boolean = failures().isEmpty()
}
