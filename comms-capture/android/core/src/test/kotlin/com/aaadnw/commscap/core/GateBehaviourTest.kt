package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

/** Behaviour beyond the shared vectors: robustness of Policy.fromMap and the group-MMS combiner. */
class GateBehaviourTest {
    private fun d(decision: String, reason: String = "r") = Decision(decision, reason, "phone", null)

    @Test
    fun emptyMapGivesDefaultPolicy() {
        val p = Policy.fromMap(emptyMap())
        assertEquals(Policy(), p)
        assertEquals("default-0", p.version)
        assertEquals(Gate.DEFAULT_BUSINESS_TERMS, p.businessTerms)
        assertEquals(24, p.deferHours)
        assertEquals(7, p.holdMediaDays)
    }

    @Test
    fun wrongTypesAndNullsKeepDefaults() {
        val p = Policy.fromMap(
            mapOf(
                "version" to 5, "numbers" to "nope", "exclude_numbers" to null, "defer_hours" to "x",
                "hold_media_days" to 3.0, "unknown_key" to 1, "client_labels" to listOf("A", null, 7),
            ),
        )
        assertEquals("default-0", p.version)
        assertEquals(emptyMap<String, String>(), p.numbers)
        assertEquals(emptyList<String>(), p.excludeNumbers)
        assertEquals(24, p.deferHours)
        assertEquals(3, p.holdMediaDays)
        assertEquals(listOf("A", "7"), p.clientLabels)
    }

    @Test
    fun defaultPolicyGatesLikeTheReference() {
        val p = Policy()
        assertEquals("defer", Gate.decide(p, "+12065550177", "ok").decision)
        assertEquals("send", Gate.decide(p, "+12065550177", "need a bid for 26-4708").decision)
        assertEquals("drop", Gate.decide(p, "CHASE", "invoice").decision)
        assertEquals("hold", Gate.decide(p, "+12065550177", "", hasMedia = true).decision)
    }

    @Test
    fun excludeBeatsEverythingElse() {
        val p = Policy(
            numbers = mapOf("+12065550101" to "client"), excludeNumbers = listOf("+12065550101"),
            provisionalBusiness = listOf("+12065550101"), clientLabels = listOf("L"),
        )
        val r = Gate.decide(p, "(206) 555-0101", "bid", contactLabels = listOf("L"))
        assertEquals("drop", r.decision)
        assertEquals("explicit_exclude", r.reason)
    }

    @Test
    fun brokenPatternFromServerFailsClosedAndNeverThrows() {
        val p = Policy(addressPattern = "([unclosed", jobNumberPattern = "(?<=a+)b", businessTerms = emptyList())
        assertEquals(emptyList<String>(), Gate.businessSignals(p, "4708 8th Ave NE 26-4708"))
        assertEquals("defer", Gate.decide(p, "+12065550177", "4708 8th Ave NE").decision)
    }

    @Test
    fun termsWithSpacesMatchAcrossWhitespaceRuns() {
        val p = Policy(businessTerms = listOf("change order", "l&i"))
        assertEquals(listOf("term"), Gate.businessSignals(p, "the change   order is in").filter { it == "term" })
        assertEquals(listOf("term"), Gate.businessSignals(p, "L&I is here"))
        assertEquals(emptyList<String>(), Gate.businessSignals(p, "change orders"))
    }

    @Test
    fun combineGroupDecisions() {
        assertEquals("send", Gate.combine(listOf(d("send"), d("send"))).decision)
        assertEquals("defer", Gate.combine(listOf(d("send"), d("defer"), d("hold"))).decision)
        assertEquals("hold", Gate.combine(listOf(d("send"), d("hold"))).decision)
        assertEquals("drop", Gate.combine(listOf(d("send"), d("defer"), d("drop", "explicit_exclude"))).decision)
        assertEquals("explicit_exclude", Gate.combine(listOf(d("send"), d("drop", "explicit_exclude"))).reason)
        assertThrows(IllegalArgumentException::class.java) { Gate.combine(emptyList()) }
    }
}
