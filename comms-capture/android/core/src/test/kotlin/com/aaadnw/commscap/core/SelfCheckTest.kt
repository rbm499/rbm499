package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import java.util.regex.Pattern

class SelfCheckTest {
    @Test
    fun selfCheckPassesOnTheJvm() {
        assertEquals(emptyList<String>(), SelfCheck.run())
    }

    @Test
    fun unicodeCharacterClassFlagIsUsedWhenTheEngineAcceptsIt() {
        assertEquals(Pattern.UNICODE_CHARACTER_CLASS, Text.supportedFlags())
    }

    @Test
    fun enginesThatRejectTheFlagGetNoFlag() {
        // Android's ICU-based Pattern throws IllegalArgumentException for it.
        val androidLike: (Int) -> Pattern = { flags ->
            if (flags != 0) throw IllegalArgumentException("Unsupported flags: $flags") else Pattern.compile("a")
        }
        assertEquals(0, Text.supportedFlags(androidLike))
    }

    @Test
    fun theRulesAlsoWorkWithoutTheFlag() {
        // On Android the patterns are compiled with no flags at all; the ASCII inputs of the self-check must still pass.
        val p = Pattern.compile("""(?i)\b(password|passcode|passwd|pin)\b(\s*(?:is|:|=)\s*)(\S+)""")
        assertEquals(true, p.matcher("PIN: 4455").find())
        val otp = Pattern.compile("""(?i)\b(?:(?:verification|one[\- ]time)\s+(?:code|passcode|pin)|otp|2fa)\b[^\d]{0,30}(?<!\d)\d{4,8}(?!\d)""")
        assertEquals(true, otp.matcher("Your one-time passcode: 99887766").find())
        assertEquals(true, otp.matcher("Your one time passcode: 99887766").find())
    }
}
