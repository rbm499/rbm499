package com.aaadnw.commscap.core

import java.security.MessageDigest
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * Wire-level helpers shared with the server: request signing and stable message ids. Mirrors
 * server/commscap/wire.py and is tested against shared/vectors/wire_vectors.json.
 *
 *   signature = hex HMAC-SHA256(secret, "{ts}.{device_id}.{sha256_hex(body_bytes)}")
 *   uid       = sha256_hex("{device_id}|{direction}|{address}|{ts_ms}|{sha256_hex(body_utf8)}|{media_count}")
 */
object Wire {
    const val MAX_CLOCK_SKEW_SECONDS = 300L

    private val HEX = "0123456789abcdef".toCharArray()

    fun toHex(bytes: ByteArray): String {
        val out = CharArray(bytes.size * 2)
        for (i in bytes.indices) {
            val v = bytes[i].toInt() and 0xFF
            out[i * 2] = HEX[v ushr 4]
            out[i * 2 + 1] = HEX[v and 0x0F]
        }
        return String(out)
    }

    fun sha256Hex(data: ByteArray): String = toHex(MessageDigest.getInstance("SHA-256").digest(data))

    fun sha256Hex(text: String): String = sha256Hex(text.toByteArray(Charsets.UTF_8))

    fun sign(secret: String, ts: Long, deviceId: String, body: ByteArray): String =
        signWithBodyHash(secret, ts, deviceId, sha256Hex(body))

    /** Same as [sign] when the body's SHA-256 is already known (streamed media uploads). */
    fun signWithBodyHash(secret: String, ts: Long, deviceId: String, bodySha256Hex: String): String {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(secret.toByteArray(Charsets.UTF_8), "HmacSHA256"))
        val msg = "$ts.$deviceId.$bodySha256Hex".toByteArray(Charsets.UTF_8)
        return toHex(mac.doFinal(msg))
    }

    fun verify(
        secret: String, ts: Long, deviceId: String, body: ByteArray, signature: String?, now: Long,
        skewSeconds: Long = MAX_CLOCK_SKEW_SECONDS,
    ): Boolean {
        if (Math.abs(now - ts) > skewSeconds) return false
        val expected = sign(secret, ts, deviceId, body).toByteArray(Charsets.UTF_8)
        val given = (signature ?: "").lowercase().toByteArray(Charsets.UTF_8)
        return MessageDigest.isEqual(expected, given)
    }

    /** E.164 when the address is a phone number, otherwise the trimmed raw address. */
    fun canonicalAddress(raw: String?): String = PhoneNumber.toE164(raw) ?: Text.strip(raw ?: "")

    fun msgUid(
        deviceId: String, direction: String, addressRaw: String?, tsMs: Long, body: String?, mediaCount: Int,
    ): String {
        val addr = canonicalAddress(addressRaw)
        val bodyHash = sha256Hex(body ?: "")
        return sha256Hex("$deviceId|$direction|$addr|$tsMs|$bodyHash|$mediaCount")
    }
}
