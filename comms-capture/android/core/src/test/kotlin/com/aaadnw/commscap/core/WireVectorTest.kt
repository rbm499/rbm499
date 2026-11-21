package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.DynamicTest
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory

class WireVectorTest {
    private val v = Vectors.load("wire_vectors.json")
    private val secret = v["secret"] as String

    @Test
    fun vectorFileHasCases() {
        assertTrue(Vectors.list(v, "signatures").size >= 2)
        assertTrue(Vectors.list(v, "uids").size >= 3)
    }

    @TestFactory
    fun signatures(): List<DynamicTest> = Vectors.list(v, "signatures").map { c ->
        val ts = (c["ts"] as Number).toLong()
        val device = c["device_id"] as String
        val body = (c["body"] as String).toByteArray(Charsets.UTF_8)
        dynamicTest("signature $device ts=$ts") {
            assertEquals(c["body_sha256"], Wire.sha256Hex(body))
            assertEquals(c["signature"], Wire.sign(secret, ts, device, body))
            assertEquals(c["signature"], Wire.signWithBodyHash(secret, ts, device, c["body_sha256"] as String))
            assertTrue(Wire.verify(secret, ts, device, body, c["signature"] as String, now = ts))
            assertTrue(Wire.verify(secret, ts, device, body, (c["signature"] as String).uppercase(), now = ts + 300))
            assertFalse(Wire.verify(secret, ts, device, body, c["signature"] as String, now = ts + 301))
            assertFalse(Wire.verify(secret, ts, device, body + 1, c["signature"] as String, now = ts))
            assertFalse(Wire.verify("other-secret", ts, device, body, c["signature"] as String, now = ts))
            assertFalse(Wire.verify(secret, ts, device, body, null, now = ts))
        }
    }

    @TestFactory
    fun uids(): List<DynamicTest> = Vectors.list(v, "uids").mapIndexed { i, c ->
        dynamicTest("uid #$i ${c["direction"]} ${c["address"]}") {
            val uid = Wire.msgUid(
                c["device_id"] as String,
                c["direction"] as String,
                c["address"] as String,
                (c["ts_ms"] as Number).toLong(),
                c["body"] as String,
                (c["media_count"] as Number).toInt(),
            )
            assertEquals(c["uid"], uid)
        }
    }

    @Test
    fun canonicalAddress() {
        assertEquals("+12065550101", Wire.canonicalAddress("(206) 555-0101"))
        assertEquals("CHASE", Wire.canonicalAddress("  CHASE "))
        assertEquals("", Wire.canonicalAddress(null))
    }
}
