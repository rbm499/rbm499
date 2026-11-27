package com.aaadnw.commscap.core

/**
 * Address classification and E.164 normalisation. Mirrors server/commscap/phone.py and is tested against
 * shared/vectors/phone_vectors.json.
 */
object PhoneNumber {
    const val KIND_PHONE = "phone"
    const val KIND_SHORTCODE = "shortcode"
    const val KIND_ALPHA = "alpha"
    const val KIND_EMAIL = "email"
    const val KIND_UNKNOWN = "unknown"

    data class Classification(val kind: String, val e164: String?)

    private val LETTER = Text.compile("[A-Za-z]")

    // North-American numbers inside free text.
    private val PHONE_IN_TEXT = Text.compile(
        """(?<!\d)(?:\+?1[\s.\-]*)?\(?([2-9]\d{2})\)?[\s.\-]*([2-9]\d{2})[\s.\-]*(\d{4})(?!\d)"""
    )

    /** Returns (kind, e164). e164 is only set when kind == "phone". */
    fun classify(raw: String?): Classification {
        val s = Text.strip(raw ?: "")
        if (s.isEmpty()) return Classification(KIND_UNKNOWN, null)
        if (s.contains('@')) return Classification(KIND_EMAIL, null)
        if (LETTER.matcher(s).find()) return Classification(KIND_ALPHA, null)
        val digits = Text.digitsOnly(s)
        if (digits.isEmpty()) return Classification(KIND_UNKNOWN, null)
        val n = digits.codePointCount(0, digits.length)
        if (s.startsWith("+")) {
            return if (n in 8..15) Classification(KIND_PHONE, "+$digits") else Classification(KIND_UNKNOWN, null)
        }
        if (n == 10) return Classification(KIND_PHONE, "+1$digits")
        if (n == 11 && digits[0] == '1') return Classification(KIND_PHONE, "+$digits")
        if (n in 3..8) return Classification(KIND_SHORTCODE, null)
        return Classification(KIND_UNKNOWN, null)
    }

    fun toE164(raw: String?): String? {
        val c = classify(raw)
        return if (c.kind == KIND_PHONE) c.e164 else null
    }

    /** All North-American phone numbers found in free text, normalised, order kept, de-duplicated. */
    fun extractPhones(text: String?): List<String> {
        val out = ArrayList<String>()
        val m = PHONE_IN_TEXT.matcher(text ?: "")
        while (m.find()) {
            val n = "+1" + m.group(1) + m.group(2) + m.group(3)
            if (n !in out) out.add(n)
        }
        return out
    }

    /** Display form that is safe for alerts: +1206•••0101. */
    fun mask(e164: String?): String {
        if (e164.isNullOrEmpty()) return "(unknown)"
        if (e164.length <= 6) return e164
        return e164.substring(0, 5) + "•••" + e164.substring(e164.length - 4)
    }
}
