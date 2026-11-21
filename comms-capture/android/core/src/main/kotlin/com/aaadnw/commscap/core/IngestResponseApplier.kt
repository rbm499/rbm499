package com.aaadnw.commscap.core

data class Rejection(val uid: String, val reason: String)

/**
 * What to do after `POST /v1/ingest` returned 200.
 *
 * @property deleteUids batch uids the server has durably (accepted, duplicates) or refused for good (rejected):
 *   remove them from the upload queue. Never contains a uid that was not in the batch.
 * @property unacknowledgedUids batch uids the response did not mention: they stay queued and are retried.
 * @property mediaToUpload attachments the server wants, for messages of this batch it accepted or already had.
 * @property threadVerdicts verdicts to apply to the local overlay (and purge).
 * @property refetchPolicy the server's policy version differs from the stored one: `GET /v1/policy` soon.
 * @property serverGateDrops number of rejections with reason server_gate_drop (counted, not retried).
 */
data class IngestOutcome(
    val ok: Boolean,
    val acceptedUids: List<String>,
    val duplicateUids: List<String>,
    val rejected: List<Rejection>,
    val deleteUids: List<String>,
    val unacknowledgedUids: List<String>,
    val mediaToUpload: List<MediaRequest>,
    val threadVerdicts: List<ThreadVerdict>,
    val refetchPolicy: Boolean,
    val serverPolicyVersion: String?,
    val serverGateDrops: Int,
)

object IngestResponseApplier {
    const val SERVER_GATE_DROP = "server_gate_drop"

    /**
     * @param response the parsed 200 body as plain maps/lists.
     * @param batchUids the uids that were in the request.
     * @param storedPolicyVersion the policy version currently stored on the phone.
     *
     * A response without `"ok": true` deletes nothing and applies nothing.
     */
    fun apply(response: Map<String, Any?>, batchUids: List<String>, storedPolicyVersion: String?): IngestOutcome {
        if (response["ok"] != true) {
            return IngestOutcome(
                false, emptyList(), emptyList(), emptyList(), emptyList(), batchUids.distinct(),
                emptyList(), emptyList(), false, null, 0,
            )
        }
        val batch = batchUids.toHashSet()

        val accepted = ResponseParts.stringList(response["accepted"]).filter { it in batch }.distinct()
        val duplicates = ResponseParts.stringList(response["duplicates"]).filter { it in batch }.distinct()
        val rejected = ResponseParts.mapList(response["rejected"]).mapNotNull { m ->
            val uid = ResponseParts.str(m["uid"])
            if (uid == null || uid !in batch) null else Rejection(uid, ResponseParts.str(m["reason"]) ?: "unknown")
        }.distinctBy { it.uid }

        val acknowledged = (accepted + duplicates + rejected.map { it.uid }).toHashSet()
        val deleteUids = batchUids.distinct().filter { it in acknowledged }
        val unacknowledged = batchUids.distinct().filter { it !in acknowledged }

        val mediaAllowed = (accepted + duplicates).toHashSet()
        val serverVersion = ResponseParts.str(response["policy_version"])

        return IngestOutcome(
            ok = true,
            acceptedUids = accepted,
            duplicateUids = duplicates,
            rejected = rejected,
            deleteUids = deleteUids,
            unacknowledgedUids = unacknowledged,
            mediaToUpload = ResponseParts.mediaWanted(response["media_wanted"], mediaAllowed),
            threadVerdicts = ResponseParts.threadVerdicts(response["thread_verdicts"]),
            refetchPolicy = ResponseParts.policyChanged(serverVersion, storedPolicyVersion),
            serverPolicyVersion = serverVersion,
            serverGateDrops = rejected.count { it.reason == SERVER_GATE_DROP },
        )
    }
}
