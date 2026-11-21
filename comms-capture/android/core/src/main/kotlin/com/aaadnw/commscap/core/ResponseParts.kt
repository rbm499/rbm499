package com.aaadnw.commscap.core

/** An attachment the server asked for ("media_wanted"). Upload only what is listed. */
data class MediaRequest(val uid: String, val sha256: String)

/** A server verdict about a thread. [verdict] is "business" or "private". */
data class ThreadVerdict(val address: String, val verdict: String)

/** A reminder from the office to display once. */
data class Nudge(
    val id: String,
    val level: Int,
    val title: String,
    val text: String,
    val address: String?,
    val deadlineMs: Long?,
)

/**
 * Parsers for the response fields that mean the same thing in the ingest response (section 4) and the heartbeat
 * response (section 7): `media_wanted`, `thread_verdicts`, `policy_version`. Input is the parsed JSON as plain
 * Kotlin maps/lists; everything is read defensively because the data comes from the network.
 */
internal object ResponseParts {
    private val SHA256 = Regex("^[0-9a-f]{64}$")

    fun str(v: Any?): String? = (v as? String)?.trim()?.takeIf { it.isNotEmpty() }

    fun stringList(v: Any?): List<String> = (v as? Iterable<*>)?.mapNotNull { str(it) } ?: emptyList()

    fun mapList(v: Any?): List<Map<*, *>> = (v as? Iterable<*>)?.mapNotNull { it as? Map<*, *> } ?: emptyList()

    /**
     * @param allowedUids when non-null, entries for other uids are ignored (ingest: only messages of this batch that
     *   the server accepted); null accepts any uid (heartbeat: the message may have been acknowledged earlier, the
     *   app looks it up locally and ignores uids it no longer has).
     */
    fun mediaWanted(v: Any?, allowedUids: Set<String>?): List<MediaRequest> {
        val out = LinkedHashSet<MediaRequest>()
        for (m in mapList(v)) {
            val uid = str(m["uid"]) ?: continue
            val sha = str(m["sha256"])?.lowercase() ?: continue
            if (!SHA256.matches(sha)) continue
            if (allowedUids != null && uid !in allowedUids) continue
            out.add(MediaRequest(uid, sha))
        }
        return out.toList()
    }

    /** One verdict per address; if the list contradicts itself the privacy-safe `private` wins. */
    fun threadVerdicts(v: Any?): List<ThreadVerdict> {
        val order = ArrayList<String>()
        val byAddress = HashMap<String, ThreadVerdict>()
        for (m in mapList(v)) {
            val address = str(m["address"]) ?: continue
            val verdict = str(m["verdict"])?.lowercase() ?: continue
            if (verdict != PolicyOverlay.BUSINESS && verdict != PolicyOverlay.PRIVATE) continue
            val key = Wire.canonicalAddress(address)
            val existing = byAddress[key]
            if (existing == null) {
                order.add(key)
                byAddress[key] = ThreadVerdict(address, verdict)
            } else if (existing.verdict != PolicyOverlay.PRIVATE && verdict == PolicyOverlay.PRIVATE) {
                byAddress[key] = ThreadVerdict(address, verdict)
            }
        }
        return order.mapNotNull { byAddress[it] }
    }

    /** True when the server reports a policy version different from the stored one. */
    fun policyChanged(serverVersion: String?, storedVersion: String?): Boolean =
        serverVersion != null && serverVersion != storedVersion
}
