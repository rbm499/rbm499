package com.aaadnw.commscap.core

/**
 * Deterministic redaction and automated-message (one-time code) detection. Mirrors server/commscap/redact.py and is
 * tested against shared/vectors/redact_vectors.json. Site access codes ("gate code is 4821") are business
 * information and are NOT redacted.
 */
object Redact {
    data class Result(val text: String, val tags: List<String>)

    private val SSN = Text.compile("""(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)""")
    private val CARD_CANDIDATE = Text.compile("""(?<!\d)(?:\d[ \-]?){12,18}\d(?!\d)""")
    private val SECRET = Text.compile("""(?i)\b(password|passcode|passwd|pin)\b(\s*(?:is|:|=)\s*)(\S+)""")
    private val ROUTING = Text.compile("""(?i)\b(routing)\b([^\d]{0,15})(\d{9})(?!\d)""")
    private val ACCOUNT = Text.compile("""(?i)\b(account|acct)\b([^\d]{0,15})(\d{6,17})(?!\d)""")

    // Phrase-based on purpose: a bare "code" is not enough.
    private const val OTP_KEY =
        """(?:(?:verification|security|confirmation|login|log-in|sign-in|authentication|one[- ]time)""" +
            """\s+(?:code|passcode|pin)|otp|2fa)"""
    private val OTP_A = Text.compile("""(?i)\b""" + OTP_KEY + """\b[^\d]{0,30}(?<!\d)\d{4,8}(?!\d)""")
    private val OTP_B = Text.compile("""(?i)\byour\s+(?:\w+\s+){0,2}code\s+(?:is|:)\s*\d{4,8}(?!\d)""")
    private val OTP_C = Text.compile("""(?i)(?<!\d)\d{4,8}(?!\d)[^\d]{0,30}\b""" + OTP_KEY + """\b""")

    private fun luhnOk(digits: String): Boolean {
        var total = 0
        var i = 0
        for (ch in digits.reversed()) {
            var d = ch - '0'
            if (i % 2 == 1) {
                d *= 2
                if (d > 9) d -= 9
            }
            total += d
            i++
        }
        return total % 10 == 0
    }

    fun isOtp(text: String?): Boolean {
        val t = text ?: ""
        return OTP_A.matcher(t).find() || OTP_B.matcher(t).find() || OTP_C.matcher(t).find()
    }

    /** Returns the redacted text and the sorted unique tags that fired. */
    fun redact(text: String?): Result {
        val tags = ArrayList<String>()
        var out = text ?: ""

        out = Text.sub(SSN, out) { tags.add("ssn"); "[REDACTED:ssn]" }

        out = Text.sub(CARD_CANDIDATE, out) { m ->
            val digits = Text.digitsOnly(m.group())
            if (digits.length in 13..19 && luhnOk(digits)) {
                tags.add("card")
                "[REDACTED:card]"
            } else {
                m.group()
            }
        }

        out = Text.sub(ROUTING, out) { m -> tags.add("routing"); m.group(1) + m.group(2) + "[REDACTED:routing]" }
        out = Text.sub(ACCOUNT, out) { m -> tags.add("account"); m.group(1) + m.group(2) + "[REDACTED:account]" }
        out = Text.sub(SECRET, out) { m -> tags.add("secret"); m.group(1) + m.group(2) + "[REDACTED:secret]" }

        return Result(out, tags.toSortedSet().toList())
    }
}
