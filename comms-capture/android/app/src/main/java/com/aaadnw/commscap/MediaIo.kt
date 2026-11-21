package com.aaadnw.commscap

import android.content.Context
import android.net.Uri
import com.aaadnw.commscap.core.Wire
import java.io.InputStream
import java.security.MessageDigest

/** Reading attachments from the system MMS store. Always streamed; never the whole file in memory. */
object MediaIo {
    /** Streams the attachment once to learn its size and SHA-256. Null if it cannot be read. */
    fun describe(ctx: Context, ref: MediaRef): MediaRef? {
        return try {
            val input = ctx.contentResolver.openInputStream(Uri.parse(ref.uri)) ?: return null
            input.use { ins ->
                val md = MessageDigest.getInstance("SHA-256")
                val buf = ByteArray(64 * 1024)
                var total = 0L
                while (true) {
                    val n = ins.read(buf)
                    if (n < 0) break
                    md.update(buf, 0, n)
                    total += n
                }
                ref.copy(size = total, sha256 = Wire.toHex(md.digest()))
            }
        } catch (e: Exception) {
            Logx.e("attachment not readable", e)
            null
        }
    }

    fun describeAll(ctx: Context, refs: List<MediaRef>): List<MediaRef> = refs.mapNotNull { describe(ctx, it) }

    fun open(ctx: Context, uri: String): InputStream? = ctx.contentResolver.openInputStream(Uri.parse(uri))
}
