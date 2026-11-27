package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test

class ReconcileResponseApplierTest {
    @Test
    fun parsesMissingAndKnown() {
        val o = ReconcileResponseApplier.apply(mapOf("ok" to true, "missing" to listOf("a", "b", "a"), "known" to 17))
        assertEquals(ReconcileOutcome(true, listOf("a", "b"), 17), o)
    }

    @Test
    fun onlyUidsThePhoneOfferedAreAccepted() {
        val o = ReconcileResponseApplier.apply(mapOf("ok" to true, "missing" to listOf("a", "zzz")), expectedUids = listOf("a", "b"))
        assertEquals(listOf("a"), o.missing)
        assertNull(o.known)
    }

    @Test
    fun notOkOrGarbageAsksForNothing() {
        assertFalse(ReconcileResponseApplier.apply(mapOf("ok" to false, "missing" to listOf("a"))).ok)
        assertEquals(emptyList<String>(), ReconcileResponseApplier.apply(emptyMap()).missing)
        assertEquals(emptyList<String>(), ReconcileResponseApplier.apply(mapOf("ok" to true, "missing" to "x")).missing)
    }
}
