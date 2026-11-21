package com.aaadnw.commscap

import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

/** A reference to an attachment in the system MMS store (not the bytes). */
data class MediaRef(val uri: String, val mime: String, val size: Long = -1L, val sha256: String? = null)

/** org.json (the Android platform one) <-> plain Kotlin maps and lists, which is what :core works with. */
object Json {
    fun toKotlin(v: Any?): Any? {
        if (v == null || v == JSONObject.NULL) return null
        if (v is JSONObject) {
            val m = LinkedHashMap<String, Any?>()
            val keys = v.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                m[k] = toKotlin(v.opt(k))
            }
            return m
        }
        if (v is JSONArray) {
            val l = ArrayList<Any?>(v.length())
            for (i in 0 until v.length()) l.add(toKotlin(v.opt(i)))
            return l
        }
        return v
    }

    /** Parses a JSON object into plain maps/lists; null when [text] is not a JSON object. */
    @Suppress("UNCHECKED_CAST")
    fun parseObject(text: String?): Map<String, Any?>? {
        if (text == null) return null
        return try {
            toKotlin(JSONObject(text)) as? Map<String, Any?>
        } catch (e: JSONException) {
            null
        }
    }

    fun stringsToJson(list: Collection<String>): String = JSONArray(list).toString()

    fun stringsFromJson(text: String?): List<String> {
        if (text.isNullOrEmpty()) return emptyList()
        return try {
            val a = JSONArray(text)
            (0 until a.length()).mapNotNull { a.optString(it, "").takeIf { s -> s.isNotEmpty() } }
        } catch (e: JSONException) {
            emptyList()
        }
    }

    fun mediaToJson(list: List<MediaRef>): String {
        val a = JSONArray()
        for (m in list) {
            val o = JSONObject()
            o.put("uri", m.uri)
            o.put("mime", m.mime)
            o.put("size", m.size)
            o.put("sha256", m.sha256 ?: JSONObject.NULL)
            a.put(o)
        }
        return a.toString()
    }

    fun mediaFromJson(text: String?): List<MediaRef> {
        if (text.isNullOrEmpty()) return emptyList()
        return try {
            val a = JSONArray(text)
            val out = ArrayList<MediaRef>()
            for (i in 0 until a.length()) {
                val o = a.optJSONObject(i) ?: continue
                val sha = if (o.isNull("sha256")) null else o.optString("sha256", "").ifEmpty { null }
                out.add(MediaRef(o.optString("uri", ""), o.optString("mime", "application/octet-stream"), o.optLong("size", -1L), sha))
            }
            out
        } catch (e: JSONException) {
            emptyList()
        }
    }

    /** The `media` array of an ingest message: only what the server needs (mime, size, hash), never the uri. */
    fun ingestMedia(refs: List<MediaRef>): JSONArray {
        val a = JSONArray()
        for (m in refs) {
            val sha = m.sha256 ?: continue
            val o = JSONObject()
            o.put("mime", m.mime)
            o.put("size", m.size)
            o.put("sha256", sha)
            a.put(o)
        }
        return a
    }
}
