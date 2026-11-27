package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.DynamicTest
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory

/** gate_vectors.json holds two sets: `policy` + `cases` (unknown_policy ai_all) and `policy_keyword` + `cases_keyword`. */
class GateVectorTest {
    private val v = Vectors.load("gate_vectors.json")

    @Suppress("UNCHECKED_CAST")
    private fun policyMap(key: String) = v[key] as Map<String, Any?>

    private val aiAll = Policy.fromMap(policyMap("policy"))
    private val keyword = Policy.fromMap(policyMap("policy_keyword"))

    @Test
    fun vectorFileHasBothSets() {
        assertEquals(setOf("policy", "cases", "policy_keyword", "cases_keyword"), v.keys)
        assertTrue(Vectors.list(v, "cases").size >= 45)
        assertTrue(Vectors.list(v, "cases_keyword").size >= 45)
    }

    @Test
    fun policiesReadUnknownPolicyAndRoundTripThroughMap() {
        assertEquals("ai_all", aiAll.unknownPolicy)
        assertEquals("keyword", keyword.unknownPolicy)
        assertEquals("vector-policy-1", aiAll.version)
        assertEquals("vector-policy-keyword-1", keyword.version)
        assertEquals(policyMap("policy"), aiAll.toMap())
        assertEquals(policyMap("policy_keyword"), keyword.toMap())
        // Everything except the mode and version is shared between the two policies.
        assertEquals(aiAll.copy(version = keyword.version, unknownPolicy = "keyword"), keyword)
    }

    @Test
    fun builtInDefaultPolicyIsAiAllAndAbsentFieldDefaultsToAiAll() {
        assertEquals("ai_all", Policy().unknownPolicy)
        assertEquals("ai_all", Policy.fromMap(emptyMap()).unknownPolicy)
        val withoutField = policyMap("policy") - "unknown_policy"
        assertEquals("ai_all", Policy.fromMap(withoutField).unknownPolicy)
    }

    @TestFactory
    fun casesAiAll(): List<DynamicTest> = cases("ai_all", "cases", aiAll)

    @TestFactory
    fun casesKeyword(): List<DynamicTest> = cases("keyword", "cases_keyword", keyword)

    @Test
    fun theTwoSetsActuallyDiffer() {
        // Guards against the keyword set silently being run against the ai_all policy (or vice versa).
        val a = Vectors.list(v, "cases")
        val k = Vectors.list(v, "cases_keyword")
        assertEquals(a.size, k.size)
        val differing = a.indices.count { a[it]["decision"] != k[it]["decision"] || a[it]["reason"] != k[it]["reason"] }
        assertTrue(differing >= 5, "expected the modes to disagree on several cases, got $differing")
        assertNotEquals(aiAll, keyword)
    }

    private fun cases(label: String, key: String, policy: Policy): List<DynamicTest> =
        Vectors.list(v, key).mapIndexed { i, c ->
            dynamicTest("gate[$label] #$i ${c["address"]} '${c["body"]}'") {
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
