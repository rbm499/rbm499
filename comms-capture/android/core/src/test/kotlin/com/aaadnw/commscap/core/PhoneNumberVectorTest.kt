package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.DynamicTest
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory

class PhoneNumberVectorTest {
    private val v = Vectors.load("phone_vectors.json")

    @Test
    fun vectorFileHasCases() {
        assertTrue(Vectors.list(v, "classify").size >= 19)
        assertTrue(Vectors.list(v, "extract").size >= 7)
    }

    @TestFactory
    fun classify(): List<DynamicTest> = Vectors.list(v, "classify").map { c ->
        dynamicTest("classify '${c["input"]}'") {
            val r = PhoneNumber.classify(c["input"] as String)
            assertEquals(c["kind"], r.kind)
            assertEquals(c["e164"], r.e164)
            assertEquals(c["e164"], PhoneNumber.toE164(c["input"] as String))
        }
    }

    @TestFactory
    fun extract(): List<DynamicTest> = Vectors.list(v, "extract").map { c ->
        dynamicTest("extract '${c["input"]}'") {
            assertEquals(Vectors.strings(c["numbers"]), PhoneNumber.extractPhones(c["input"] as String))
        }
    }

    @Test
    fun nullAndMask() {
        assertEquals("unknown", PhoneNumber.classify(null).kind)
        assertNull(PhoneNumber.toE164(null))
        assertEquals("+1206•••0101", PhoneNumber.mask("+12065550101"))
        assertEquals("(unknown)", PhoneNumber.mask(null))
        assertEquals("+1234", PhoneNumber.mask("+1234"))
    }
}
