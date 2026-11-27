package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class PolicyOverlayTest {
    private val a = "+12065550177"
    private val b = "+12065550150"

    @Test
    fun mergeUnionsListsAndKeepsOtherFields() {
        val base = Policy(version = "v9", provisionalBusiness = listOf(b), excludeNumbers = listOf("+12065550199"))
        val m = PolicyOverlay.merge(base, Overlay(provisionalBusiness = listOf(a, b), excludeNumbers = listOf("+12065550198")))
        assertEquals("v9", m.version)
        assertEquals(listOf(b, a), m.provisionalBusiness)
        assertEquals(listOf("+12065550199", "+12065550198"), m.excludeNumbers)
    }

    @Test
    fun mergeNeverLeavesAnExcludedNumberProvisional() {
        val base = Policy(provisionalBusiness = listOf(a))
        val m = PolicyOverlay.merge(base, Overlay(excludeNumbers = listOf(a)))
        assertEquals(emptyList<String>(), m.provisionalBusiness)
        assertEquals(listOf(a), m.excludeNumbers)
    }

    @Test
    fun mergedPolicyGatesWithOverlay() {
        val merged = PolicyOverlay.merge(Policy(), Overlay(provisionalBusiness = listOf(a)))
        assertEquals("send", Gate.decide(merged, a, "ok sounds good").decision)
        val merged2 = PolicyOverlay.merge(merged, Overlay(excludeNumbers = listOf(a)))
        assertEquals("drop", Gate.decide(merged2, a, "bid").decision)
    }

    @Test
    fun privateVerdictRemovesFromProvisionalAddsToExcludeAndReturnsPurge() {
        val r = PolicyOverlay.applyVerdict(Overlay(provisionalBusiness = listOf(a, b)), "(206) 555-0177", "private")
        assertEquals(listOf(b), r.overlay.provisionalBusiness)
        assertEquals(listOf(a), r.overlay.excludeNumbers)
        assertEquals(listOf(a), r.purgeAddresses)
    }

    @Test
    fun privateVerdictIsIdempotent() {
        val once = PolicyOverlay.applyVerdict(Overlay(), a, "private")
        val twice = PolicyOverlay.applyVerdict(once.overlay, a, "private")
        assertEquals(once.overlay, twice.overlay)
        assertEquals(listOf(a), twice.purgeAddresses)
    }

    @Test
    fun businessVerdictAddsToProvisionalWithoutPurge() {
        val r = PolicyOverlay.applyVerdict(Overlay(), a, "business")
        assertEquals(listOf(a), r.overlay.provisionalBusiness)
        assertEquals(emptyList<String>(), r.overlay.excludeNumbers)
        assertEquals(emptyList<String>(), r.purgeAddresses)
    }

    @Test
    fun serverBusinessVerdictNeverOverridesLocalPrivate() {
        val priv = PolicyOverlay.applyVerdict(Overlay(), a, "private").overlay
        val r = PolicyOverlay.applyVerdict(priv, a, "business")
        assertEquals(priv, r.overlay)
    }

    @Test
    fun userCorrectionToBusinessLiftsLocalPrivate() {
        val priv = PolicyOverlay.applyVerdict(Overlay(), a, "private").overlay
        val r = PolicyOverlay.applyVerdict(priv, a, "business", userInitiated = true)
        assertEquals(listOf(a), r.overlay.provisionalBusiness)
        assertEquals(emptyList<String>(), r.overlay.excludeNumbers)
    }

    @Test
    fun nonPhoneAddressStillPurgesButDoesNotTouchOverlay() {
        val r = PolicyOverlay.applyVerdict(Overlay(), " CHASE ", "private")
        assertEquals(Overlay(), r.overlay)
        assertEquals(listOf("CHASE"), r.purgeAddresses)
        assertEquals(Overlay(), PolicyOverlay.applyVerdict(Overlay(), "CHASE", "business").overlay)
    }

    @Test
    fun unknownVerdictAndBlankAddressChangeNothing() {
        assertEquals(VerdictResult(Overlay(), emptyList()), PolicyOverlay.applyVerdict(Overlay(), a, "maybe"))
        assertEquals(VerdictResult(Overlay(), emptyList()), PolicyOverlay.applyVerdict(Overlay(), "  ", "private"))
        assertEquals(VerdictResult(Overlay(), emptyList()), PolicyOverlay.applyVerdict(Overlay(), a, null))
    }

    @Test
    fun applyVerdictsAccumulatesPurgeList() {
        val r = PolicyOverlay.applyVerdicts(
            Overlay(),
            listOf(ThreadVerdict(a, "business"), ThreadVerdict(b, "private"), ThreadVerdict(a, "private")),
        )
        assertEquals(listOf(b, a), r.overlay.excludeNumbers)
        assertEquals(emptyList<String>(), r.overlay.provisionalBusiness)
        assertEquals(listOf(b, a), r.purgeAddresses)
    }
}
