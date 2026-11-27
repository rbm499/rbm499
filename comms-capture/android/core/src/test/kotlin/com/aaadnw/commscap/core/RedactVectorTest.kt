package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.DynamicTest
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory

class RedactVectorTest {
    private val v = Vectors.load("redact_vectors.json")

    @Test
    fun vectorFileHasCases() {
        assertTrue(Vectors.list(v, "redact").size >= 13)
        assertTrue(Vectors.list(v, "is_otp").size >= 10)
    }

    @TestFactory
    fun redact(): List<DynamicTest> = Vectors.list(v, "redact").map { c ->
        dynamicTest("redact '${c["input"]}'") {
            val r = Redact.redact(c["input"] as String)
            assertEquals(c["output"], r.text)
            assertEquals(Vectors.strings(c["tags"]), r.tags)
        }
    }

    @TestFactory
    fun isOtp(): List<DynamicTest> = Vectors.list(v, "is_otp").map { c ->
        dynamicTest("is_otp '${c["input"]}'") {
            assertEquals(c["otp"], Redact.isOtp(c["input"] as String))
        }
    }

    @Test
    fun nullSafe() {
        assertEquals("", Redact.redact(null).text)
        assertFalse(Redact.isOtp(null))
    }

    @Test
    fun replacementTextIsNotInterpretedAsRegexReplacement() {
        // "$" and "\" in the surrounding text must pass through untouched.
        val r = Redact.redact("cost \$5 \\ ssn 123-45-6789 \$1")
        assertEquals("cost \$5 \\ ssn [REDACTED:ssn] \$1", r.text)
    }
}
