package com.aaadnw.commscap.core

/**
 * What to do after `POST /v1/heartbeat` returned 200 (contract section 7).
 *
 * Besides nudges, the heartbeat response may carry `media_wanted` and `thread_verdicts` with exactly the same
 * meaning and handling as in the ingest response: server screening is asynchronous, so a verdict (or a request for
 * an attachment) can arrive after the ingest call that delivered the message.
 *
 * @property nudgesToShow nudges not yet handled on this phone, in the order sent.
 * @property mediaToUpload attachments to upload (the message may have been acknowledged long ago).
 * @property threadVerdicts verdicts to apply to the local overlay (and purge).
 */
data class HeartbeatOutcome(
    val ok: Boolean,
    val nudgesToShow: List<Nudge>,
    val mediaToUpload: List<MediaRequest>,
    val threadVerdicts: List<ThreadVerdict>,
    val refetchPolicy: Boolean,
    val serverPolicyVersion: String?,
)

object HeartbeatResponseApplier {
    /**
     * @param alreadyHandledNudgeIds ids this phone has already displayed (acked or waiting to be acked); they are
     *   never shown a second time.
     * A response without `"ok": true` applies nothing.
     */
    fun apply(
        response: Map<String, Any?>,
        storedPolicyVersion: String?,
        alreadyHandledNudgeIds: Set<String> = emptySet(),
    ): HeartbeatOutcome {
        if (response["ok"] != true) {
            return HeartbeatOutcome(false, emptyList(), emptyList(), emptyList(), false, null)
        }
        val serverVersion = ResponseParts.str(response["policy_version"])
        return HeartbeatOutcome(
            ok = true,
            nudgesToShow = parseNudges(response["nudges"]).filter { it.id !in alreadyHandledNudgeIds },
            mediaToUpload = ResponseParts.mediaWanted(response["media_wanted"], allowedUids = null),
            threadVerdicts = ResponseParts.threadVerdicts(response["thread_verdicts"]),
            refetchPolicy = ResponseParts.policyChanged(serverVersion, storedPolicyVersion),
            serverPolicyVersion = serverVersion,
        )
    }

    internal fun parseNudges(v: Any?): List<Nudge> {
        val seen = HashSet<String>()
        val out = ArrayList<Nudge>()
        for (m in ResponseParts.mapList(v)) {
            val id = ResponseParts.str(m["id"]) ?: continue
            if (!seen.add(id)) continue
            out.add(
                Nudge(
                    id = id,
                    level = (m["level"] as? Number)?.toInt() ?: 1,
                    title = ResponseParts.str(m["title"]) ?: "Reminder",
                    text = (m["text"] as? String) ?: "",
                    address = ResponseParts.str(m["address"]),
                    deadlineMs = (m["deadline_ms"] as? Number)?.toLong(),
                ),
            )
        }
        return out
    }
}
