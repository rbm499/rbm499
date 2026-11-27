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
    fun defaultPolicyIsAiAllAndSendsEveryNonBlankTextFromAnUnsavedNumber() {
        val p = Policy()
        assertEquals("send", Gate.decide(p, "+12065550177", "ok").decision)
        assertEquals("unknown_unsaved", Gate.decide(p, "+12065550177", "ok").reason)
        assertEquals("unknown_business_signal", Gate.decide(p, "+12065550177", "need a bid for 26-4708").reason)
        assertEquals("drop", Gate.decide(p, "CHASE", "invoice").decision)
        assertEquals("hold", Gate.decide(p, "+12065550177", "", hasMedia = true).decision)
        assertEquals("send", Gate.decide(p, "+12065550177", "here you go", hasMedia = true).decision)
    }

    @Test
    fun blankTextFromAnUnsavedNumberIsDeferredInBothModes() {
        for (mode in listOf("ai_all", "keyword")) {
            val p = Policy(unknownPolicy = mode)
            assertEquals("defer", Gate.decide(p, "+12065550177", "").decision, mode)
            assertEquals("defer", Gate.decide(p, "+12065550177", "  \n\t ").decision, mode)
            assertEquals("hold", Gate.decide(p, "+12065550177", "   ", hasMedia = true).decision, mode)
        }
    }

    @Test
    fun keywordModeDefersTextWithoutABusinessSignal() {
        val p = Policy(unknownPolicy = "keyword")
        assertEquals("defer", Gate.decide(p, "+12065550177", "ok").decision)
        assertEquals("send", Gate.decide(p, "+12065550177", "need a bid for 26-4708").decision)
    }

    @Test
    fun anyOtherUnknownPolicyBehavesLikeKeyword() {
        // The reference compares to "ai_all" exactly, so a typo can only make the phone stricter.
        for (mode in listOf("AI_ALL", "ai-all", "", "nonsense")) {
            assertEquals("defer", Gate.decide(Policy(unknownPolicy = mode), "+12065550177", "ok").decision, mode)
        }
    }

    @Test
    fun savedContactsAreNeverCapturedUnlessClientsInEitherMode() {
        // The privacy boundary under ai_all: a saved contact is dropped no matter what the text says.
        for (mode in listOf("ai_all", "keyword")) {
            val p = Policy(unknownPolicy = mode, clientLabels = listOf("AAAD Clients"))
            assertEquals("drop", Gate.decide(p, "+12065550177", "ok", contactSaved = true).decision, mode)
            assertEquals("drop", Gate.decide(p, "+12065550177", "need a bid", contactSaved = true).decision, mode)
            assertEquals("send", Gate.decide(p, "+12065550177", "the 26-4708 job", contactSaved = true).decision, mode)
            assertEquals("send", Gate.decide(p, "+12065550177", "hi", contactSaved = true, contactLabels = listOf("AAAD Clients")).decision, mode)
        }
    }

    @Test
    fun unknownPolicyFromMapKeepsDefaultOnWrongType() {
        assertEquals("ai_all", Policy.fromMap(mapOf("unknown_policy" to 3)).unknownPolicy)
        assertEquals("keyword", Policy.fromMap(mapOf("unknown_policy" to "keyword")).unknownPolicy)
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
        val p = Policy(addressPattern = "([unclosed", jobNumberPattern = "(?<=a+)b", businessTerms = emptyList(), unknownPolicy = "keyword")
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
