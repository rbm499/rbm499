package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

/** Contract section 7 (amended): a heartbeat response can carry media_wanted and thread_verdicts like ingest. */
class HeartbeatResponseApplierTest {
    private val sha1 = "c".repeat(64)
    private val sha2 = "d".repeat(64)

    private val full: Map<String, Any?> = mapOf(
        "ok" to true,
        "server_time_ms" to 1789999999500L,
        "policy_version" to "2026-11-21.2",
        "nudges" to listOf(
            mapOf(
                "id" to "n_123", "level" to 1, "title" to "Reply due: Heidi Walsh",
                "text" to "Bid question 2h ago (26-4708)", "address" to "+12065550101", "deadline_ms" to 1790003599000L,
            ),
            mapOf("id" to "n_124"),
        ),
        "media_wanted" to listOf(
            mapOf("uid" to "old-uid-acked-yesterday", "sha256" to sha1),
            mapOf("uid" to "another", "sha256" to sha2),
        ),
        "thread_verdicts" to listOf(
            mapOf("address" to "+12065550177", "verdict" to "private"),
            mapOf("address" to "+12065550150", "verdict" to "business"),
        ),
    )

    @Test
    fun parsesNudgesMediaAndVerdictsFromOneResponse() {
        val o = HeartbeatResponseApplier.apply(full, "2026-11-21.1")
        assertTrue(o.ok)
        assertEquals(2, o.nudgesToShow.size)
        assertEquals(
            Nudge("n_123", 1, "Reply due: Heidi Walsh", "Bid question 2h ago (26-4708)", "+12065550101", 1790003599000L),
            o.nudgesToShow[0],
        )
        assertEquals(Nudge("n_124", 1, "Reminder", "", null, null), o.nudgesToShow[1])
        assertEquals(listOf(MediaRequest("old-uid-acked-yesterday", sha1), MediaRequest("another", sha2)), o.mediaToUpload)
        assertEquals(
            listOf(ThreadVerdict("+12065550177", "private"), ThreadVerdict("+12065550150", "business")),
            o.threadVerdicts,
        )
        assertTrue(o.refetchPolicy)
        assertEquals("2026-11-21.2", o.serverPolicyVersion)
    }

    @Test
    fun mediaWantedIsNotRestrictedToAnyBatch() {
        // Unlike ingest there is no batch: the message may have been acknowledged long ago.
        val o = HeartbeatResponseApplier.apply(
            mapOf("ok" to true, "media_wanted" to listOf(mapOf("uid" to "whatever", "sha256" to sha1))), null,
        )
        assertEquals(listOf(MediaRequest("whatever", sha1)), o.mediaToUpload)
    }

    @Test
    fun heartbeatAndIngestParseTheSameFieldsTheSameWay() {
        val shared = mapOf(
            "ok" to true,
            "accepted" to listOf("u1"),
            "media_wanted" to listOf(mapOf("uid" to "u1", "sha256" to sha1.uppercase()), mapOf("uid" to "u1", "sha256" to "bad")),
            "thread_verdicts" to listOf(
                mapOf("address" to "+12065550177", "verdict" to "business"),
                mapOf("address" to "(206) 555-0177", "verdict" to "private"),
                mapOf("address" to "+12065550150", "verdict" to "nonsense"),
            ),
            "policy_version" to "v2",
        )
        val ingest = IngestResponseApplier.apply(shared, listOf("u1"), "v1")
        val heartbeat = HeartbeatResponseApplier.apply(shared, "v1")
        assertEquals(ingest.mediaToUpload, heartbeat.mediaToUpload)
        assertEquals(ingest.threadVerdicts, heartbeat.threadVerdicts)
        assertEquals(ingest.refetchPolicy, heartbeat.refetchPolicy)
    }

    @Test
    fun verdictsFromAHeartbeatApplyToTheOverlayExactlyLikeIngestVerdicts() {
        val o = HeartbeatResponseApplier.apply(full, "2026-11-21.2")
        val r = PolicyOverlay.applyVerdicts(Overlay(), o.threadVerdicts)
        assertEquals(listOf("+12065550177"), r.purgeAddresses)
        assertEquals(listOf("+12065550177"), r.overlay.excludeNumbers)
        assertEquals(listOf("+12065550150"), r.overlay.provisionalBusiness)
        assertFalse(o.refetchPolicy)
    }

    @Test
    fun alreadyHandledNudgesAreNotShownAgain() {
        val o = HeartbeatResponseApplier.apply(full, "x", alreadyHandledNudgeIds = setOf("n_123"))
        assertEquals(listOf("n_124"), o.nudgesToShow.map { it.id })
    }

    @Test
    fun duplicateNudgeIdsInOneResponseAreShownOnce() {
        val o = HeartbeatResponseApplier.apply(
            mapOf("ok" to true, "nudges" to listOf(mapOf("id" to "a"), mapOf("id" to "a", "title" to "again"))), null,
        )
        assertEquals(1, o.nudgesToShow.size)
        assertEquals("Reminder", o.nudgesToShow[0].title)
    }

    @Test
    fun notOkAppliesNothing() {
        val o = HeartbeatResponseApplier.apply(full + ("ok" to false), "v1")
        assertFalse(o.ok)
        assertEquals(emptyList<Nudge>(), o.nudgesToShow)
        assertEquals(emptyList<MediaRequest>(), o.mediaToUpload)
        assertEquals(emptyList<ThreadVerdict>(), o.threadVerdicts)
        assertFalse(o.refetchPolicy)
        assertNull(o.serverPolicyVersion)
        assertFalse(HeartbeatResponseApplier.apply(emptyMap(), null).ok)
    }

    @Test
    fun minimalResponseFromAnOlderServerStillWorks() {
        val o = HeartbeatResponseApplier.apply(mapOf("ok" to true, "server_time_ms" to 1L), "v1")
        assertTrue(o.ok)
        assertEquals(emptyList<Nudge>(), o.nudgesToShow)
        assertEquals(emptyList<MediaRequest>(), o.mediaToUpload)
        assertEquals(emptyList<ThreadVerdict>(), o.threadVerdicts)
        assertFalse(o.refetchPolicy)
    }

    @Test
    fun garbageFieldTypesDoNotThrow() {
        val o = HeartbeatResponseApplier.apply(
            mapOf("ok" to true, "nudges" to "x", "media_wanted" to 4, "thread_verdicts" to listOf(null, 1), "policy_version" to 7), "v1",
        )
        assertTrue(o.ok)
        assertEquals(emptyList<Nudge>(), o.nudgesToShow)
        assertNull(o.serverPolicyVersion)
    }
}
