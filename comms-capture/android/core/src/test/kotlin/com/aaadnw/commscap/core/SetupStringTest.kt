package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class SetupStringTest {
    @Test
    fun parsesAPercentEncodedSetupString() {
        val r = SetupString.parse("commscap://setup?url=https%3A%2F%2Fcomms.example.com%2F&device=michael-phone-1&secret=s3cr3t-value")
        assertNull(r.error)
        assertEquals(SetupConfig("https://comms.example.com", "michael-phone-1", "s3cr3t-value"), r.config)
    }

    @Test
    fun toleratesWhitespaceNewlinesAndUnencodedUrl() {
        val r = SetupString.parse("  \ncommscap://setup?url=https://comms.example.com&device=dev_1&secret=abcdefgh12\n ")
        assertEquals(SetupConfig("https://comms.example.com", "dev_1", "abcdefgh12"), r.config)
    }

    @Test
    fun plusInTheSecretStaysAPlusAndPercentSequencesDecode() {
        val r = SetupString.parse("commscap://setup?url=https://c.example&device=d1&secret=ab%2Bcd+ef%3Dgh")
        assertEquals("ab+cd+ef=gh", r.config?.secret)
    }

    @Test
    fun schemeIsCaseInsensitiveAndKeysToo() {
        assertNotNull(SetupString.parse("COMMSCAP://SETUP?URL=https://c.example&Device=d1&SECRET=abcdefgh").config)
    }

    @Test
    fun rejectsBadInputWithAPlainMessage() {
        for (bad in listOf(
            null, "", "hello",
            "commscap://setup?device=d1&secret=abcdefgh",
            "commscap://setup?url=https://c.example&secret=abcdefgh",
            "commscap://setup?url=https://c.example&device=d1",
            "commscap://setup?url=http://c.example&device=d1&secret=abcdefgh",
            "commscap://setup?url=https://&device=d1&secret=abcdefgh",
            "commscap://setup?url=https://c.example&device=bad%20name&secret=abcdefgh",
            "commscap://setup?url=https://c.example&device=d1&secret=short",
            "commscap://setup?url=https://c.example&device=d1&secret=has%20space1",
            "commscap://setup?url=https://c.example&device=d1&secret=%ZZ",
        )) {
            val r = SetupString.parse(bad)
            assertNull(r.config, "should reject: $bad")
            assertTrue(!r.error.isNullOrBlank(), "needs a message: $bad")
        }
    }

    @Test
    fun manualFieldsAreValidatedTheSameWay() {
        assertEquals("https://c.example/v1", SetupString.validate(" https://c.example/v1// ", "d.1", "abcdefgh").config?.url)
        assertNull(SetupString.validate("ftp://x", "d", "abcdefgh").config)
        assertNull(SetupString.validate("https://x.example", "d|x", "abcdefgh").config)
    }
}
