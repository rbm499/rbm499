package com.aaadnw.commscap.core

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Loads the shared vector JSON files (directory given by the `vectors.dir` system property) into plain Kotlin maps/lists. */
object Vectors {
    private val dir: File by lazy {
        val p = System.getProperty("vectors.dir") ?: error("system property vectors.dir is not set")
        File(p).also { require(it.isDirectory) { "vectors.dir does not exist: $p" } }
    }

    @Suppress("UNCHECKED_CAST")
    fun load(name: String): Map<String, Any?> {
        val text = File(dir, name).readText(Charsets.UTF_8)
        return convert(JSONObject(text)) as Map<String, Any?>
    }

    fun convert(v: Any?): Any? = when (v) {
        null, JSONObject.NULL -> null
        is JSONObject -> {
            val m = LinkedHashMap<String, Any?>()
            for (k in v.keys()) m[k] = convert(v.get(k))
            m
        }
        is JSONArray -> (0 until v.length()).map { convert(v.get(it)) }
        else -> v
    }

    @Suppress("UNCHECKED_CAST")
    fun list(m: Map<String, Any?>, key: String): List<Map<String, Any?>> = m[key] as List<Map<String, Any?>>

    fun strings(v: Any?): List<String> = (v as List<*>).map { it as String }
}
