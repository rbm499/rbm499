package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.DynamicTest
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory

class GateVectorTest {
    private val v = Vectors.load("gate_vectors.json")

    @Suppress("UNCHECKED_CAST")
    private val policyMap = v["policy"] as Map<String, Any?>
    private val policy = Policy.fromMap(policyMap)

    @Test
    fun vectorFileHasCases() {
        assertTrue(Vectors.list(v, "cases").size >= 40)
    }

    @Test
    fun policyRoundTripsThroughMap() {
        assertEquals(policyMap, policy.toMap())
        assertEquals("vector-policy-1", policy.version)
    }

    @TestFactory
    fun cases(): List<DynamicTest> = Vectors.list(v, "cases").mapIndexed { i, c ->
        dynamicTest("gate #$i ${c["address"]} '${c["body"]}'") {
            val d = Gate.decide(
                policy,
                c["address"] as String,
                c["body"] as String,
                c["has_media"] as Boolean,
                c["contact_saved"] as Boolean,
                Vectors.strings(c["contact_labels"]),
            )
            assertEquals(c["decision"], d.decision, "decision")
            assertEquals(c["reason"], d.reason, "reason")
            assertEquals(c["kind"], d.kind, "kind")
            assertEquals(c["e164"], d.e164, "e164")
        }
    }
}
