package com.aaadnw.commscap.core

/**
 * @property missing uids the server does not have; the phone rebuilds each from the system SMS/MMS store
 *   (re-running the gate) and enqueues it again. Uids the phone never offered are ignored by the caller.
 * @property known how many of the offered uids the server already had (informational).
 */
data class ReconcileOutcome(val ok: Boolean, val missing: List<String>, val known: Int?)

object ReconcileResponseApplier {
    /** Parses `{"ok": true, "missing": ["<uid>"], "known": 17}`. A response without `"ok": true` asks for nothing. */
    fun apply(response: Map<String, Any?>, expectedUids: Collection<String>? = null): ReconcileOutcome {
        if (response["ok"] != true) return ReconcileOutcome(false, emptyList(), null)
        val offered = expectedUids?.toHashSet()
        val missing = ResponseParts.stringList(response["missing"]).distinct().filter { offered == null || it in offered }
        return ReconcileOutcome(true, missing, (response["known"] as? Number)?.toInt())
    }
}
