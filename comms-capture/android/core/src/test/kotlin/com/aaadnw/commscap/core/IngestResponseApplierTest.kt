package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class IngestResponseApplierTest {
    private val sha1 = "a".repeat(64)
    private val sha2 = "b".repeat(64)
    private val batch = listOf("u1", "u2", "u3", "u4", "u5")

    private fun response(vararg extra: Pair<String, Any?>): Map<String, Any?> =
        mapOf<String, Any?>("ok" to true) + extra

    @Test
    fun acceptedDuplicatesAndRejectedAreDeletedInBatchOrder() {
        val o = IngestResponseApplier.apply(
            response(
                "accepted" to listOf("u3", "u1"),
                "duplicates" to listOf("u2"),
                "rejected" to listOf(mapOf("uid" to "u5", "reason" to "server_gate_drop")),
            ),
            batch, "v1",
        )
        assertTrue(o.ok)
        assertEquals(listOf("u1", "u2", "u3", "u5"), o.deleteUids)
        assertEquals(listOf("u4"), o.unacknowledgedUids)
        assertEquals(listOf("u3", "u1"), o.acceptedUids)
        assertEquals(1, o.serverGateDrops)
        assertEquals(listOf(Rejection("u5", "server_gate_drop")), o.rejected)
    }

    @Test
    fun otherRejectionReasonsAreDeletedButNotCountedAsServerGateDrops() {
        val o = IngestResponseApplier.apply(
            response(
                "rejected" to listOf(
                    mapOf("uid" to "u1", "reason" to "bad_schema"),
                    mapOf("uid" to "u2", "reason" to "stale"),
                    mapOf("uid" to "u3"),
                ),
            ),
            batch, null,
        )
        assertEquals(listOf("u1", "u2", "u3"), o.deleteUids)
        assertEquals(0, o.serverGateDrops)
        assertEquals("unknown", o.rejected.last().reason)
    }

    @Test
    fun uidsNotInTheBatchAreNeverDeleted() {
        val o = IngestResponseApplier.apply(
            response("accepted" to listOf("zzz", "u1"), "duplicates" to listOf("yyy"), "rejected" to listOf(mapOf("uid" to "xxx"))),
            batch, null,
        )
        assertEquals(listOf("u1"), o.deleteUids)
    }

    @Test
    fun notOkDeletesNothingAndAppliesNothing() {
        val o = IngestResponseApplier.apply(
            mapOf("ok" to false, "accepted" to listOf("u1"), "thread_verdicts" to listOf(mapOf("address" to "+12065550177", "verdict" to "private"))),
            batch, "v1",
        )
        assertFalse(o.ok)
        assertEquals(emptyList<String>(), o.deleteUids)
        assertEquals(batch, o.unacknowledgedUids)
        assertEquals(emptyList<ThreadVerdict>(), o.threadVerdicts)
        assertFalse(o.refetchPolicy)
        assertFalse(IngestResponseApplier.apply(emptyMap(), batch, "v1").ok)
        assertFalse(IngestResponseApplier.apply(mapOf("ok" to "true"), batch, "v1").ok)
    }

    @Test
    fun mediaWantedOnlyForAcceptedOrDuplicateBatchMessages() {
        val o = IngestResponseApplier.apply(
            response(
                "accepted" to listOf("u1"), "duplicates" to listOf("u2"), "rejected" to listOf(mapOf("uid" to "u3", "reason" to "stale")),
                "media_wanted" to listOf(
                    mapOf("uid" to "u1", "sha256" to sha1),
                    mapOf("uid" to "u2", "sha256" to sha2.uppercase()),
                    mapOf("uid" to "u3", "sha256" to sha1),   // rejected: not wanted
                    mapOf("uid" to "u4", "sha256" to sha1),   // not acknowledged
                    mapOf("uid" to "zzz", "sha256" to sha1),  // not in batch
                    mapOf("uid" to "u1", "sha256" to "short"),
                    mapOf("uid" to "u1"),
                    mapOf("uid" to "u1", "sha256" to sha1),   // duplicate entry
                ),
            ),
            batch, null,
        )
        assertEquals(listOf(MediaRequest("u1", sha1), MediaRequest("u2", sha2)), o.mediaToUpload)
    }

    @Test
    fun policyVersionDecidesRefetch() {
        assertTrue(IngestResponseApplier.apply(response("policy_version" to "v2"), batch, "v1").refetchPolicy)
        assertTrue(IngestResponseApplier.apply(response("policy_version" to "v2"), batch, null).refetchPolicy)
        assertFalse(IngestResponseApplier.apply(response("policy_version" to "v1"), batch, "v1").refetchPolicy)
        assertFalse(IngestResponseApplier.apply(response(), batch, "v1").refetchPolicy)
        assertEquals("v2", IngestResponseApplier.apply(response("policy_version" to "v2"), batch, "v1").serverPolicyVersion)
    }

    @Test
    fun threadVerdictsAreParsedValidatedAndPrivateWins() {
        val o = IngestResponseApplier.apply(
            response(
                "thread_verdicts" to listOf(
                    mapOf("address" to "+12065550177", "verdict" to "business"),
                    mapOf("address" to "(206) 555-0177", "verdict" to "PRIVATE"),
                    mapOf("address" to "+12065550150", "verdict" to "business"),
                    mapOf("address" to "+12065550151", "verdict" to "weird"),
                    mapOf("verdict" to "private"),
                    "junk",
                ),
            ),
            batch, null,
        )
        assertEquals(
            listOf(ThreadVerdict("(206) 555-0177", "private"), ThreadVerdict("+12065550150", "business")),
            o.threadVerdicts,
        )
    }

    @Test
    fun garbageFieldTypesDoNotThrow() {
        val o = IngestResponseApplier.apply(
            response("accepted" to "u1", "duplicates" to 5, "rejected" to listOf(1, "x", null), "media_wanted" to "no", "thread_verdicts" to 3),
            batch, "v1",
        )
        assertTrue(o.ok)
        assertEquals(emptyList<String>(), o.deleteUids)
        assertEquals(batch, o.unacknowledgedUids)
    }

    @Test
    fun verdictsFromTheResponseDriveTheOverlayEndToEnd() {
        val o = IngestResponseApplier.apply(
            response("thread_verdicts" to listOf(mapOf("address" to "+12065550177", "verdict" to "private"))), batch, null,
        )
        val r = PolicyOverlay.applyVerdicts(Overlay(), o.threadVerdicts)
        assertEquals(listOf("+12065550177"), r.purgeAddresses)
        assertEquals(listOf("+12065550177"), r.overlay.excludeNumbers)
    }
}
