package com.aaadnw.commscap

import android.content.Context
import com.aaadnw.commscap.core.Wire
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL

/** Signed HTTPS calls (contract section 1). HttpURLConnection only; no third-party HTTP library. */
object Http {
    class Result(val code: Int, val body: String)

    private const val CONNECT_TIMEOUT_MS = 15_000
    private const val READ_TIMEOUT_MS = 30_000
    private const val MAX_RESPONSE_BYTES = 1 shl 20

    /** JSON (or empty) request. [body] is the exact byte string that is signed and sent. Throws IOException on network trouble. */
    @Throws(IOException::class)
    fun call(ctx: Context, method: String, path: String, body: ByteArray?): Result {
        val p = Prefs.get(ctx)
        val bytes = body ?: ByteArray(0)
        val conn = open(p, method, path)
        try {
            sign(conn, p, Wire.sha256Hex(bytes))
            conn.setRequestProperty("Accept", "application/json")
            if (body != null) {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                conn.setFixedLengthStreamingMode(bytes.size)
                conn.outputStream.use { it.write(bytes) }
            }
            return readResult(conn)
        } finally {
            conn.disconnect()
        }
    }

    /**
     * Streams [input] (exactly [size] bytes whose SHA-256 is [sha256]) as the request body. The signature uses the known
     * hash, so the file is never held in memory and never read twice.
     */
    @Throws(IOException::class)
    fun putStream(ctx: Context, path: String, mime: String, size: Long, sha256: String, input: InputStream): Result {
        val p = Prefs.get(ctx)
        val conn = open(p, "PUT", path)
        try {
            sign(conn, p, sha256)
            conn.setRequestProperty("Content-Type", mime)
            conn.doOutput = true
            conn.setFixedLengthStreamingMode(size)
            conn.outputStream.use { out ->
                val buf = ByteArray(64 * 1024)
                while (true) {
                    val n = input.read(buf)
                    if (n < 0) break
                    out.write(buf, 0, n)
                }
            }
            return readResult(conn)
        } finally {
            conn.disconnect()
        }
    }

    private fun open(p: Prefs, method: String, path: String): HttpURLConnection {
        val base = p.serverUrl
        if (!base.startsWith("https://", ignoreCase = true)) throw IOException("server address is not https")
        val conn = URL(base + path).openConnection() as HttpURLConnection
        conn.requestMethod = method
        conn.connectTimeout = CONNECT_TIMEOUT_MS
        conn.readTimeout = READ_TIMEOUT_MS
        conn.instanceFollowRedirects = false
        conn.useCaches = false
        return conn
    }

    private fun sign(conn: HttpURLConnection, p: Prefs, bodySha256: String) {
        val ts = System.currentTimeMillis() / 1000
        conn.setRequestProperty("X-Device-Id", p.deviceId)
        conn.setRequestProperty("X-Timestamp", ts.toString())
        conn.setRequestProperty("X-Signature", Wire.signWithBodyHash(p.secret, ts, p.deviceId, bodySha256))
    }

    private fun readResult(conn: HttpURLConnection): Result {
        val code = conn.responseCode
        val stream = if (code >= 400) conn.errorStream else conn.inputStream
        val text = if (stream == null) "" else stream.use { readCapped(it) }
        return Result(code, text)
    }

    private fun readCapped(input: InputStream): String {
        val out = ByteArrayOutputStream()
        val buf = ByteArray(8192)
        while (out.size() < MAX_RESPONSE_BYTES) {
            val n = input.read(buf)
            if (n < 0) break
            out.write(buf, 0, n)
        }
        return out.toString("UTF-8")
    }
}
