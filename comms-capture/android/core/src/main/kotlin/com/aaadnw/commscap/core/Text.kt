package com.aaadnw.commscap.core

import java.util.regex.Matcher
import java.util.regex.Pattern

/**
 * Small text helpers that make Java behave like the Python reference (Python 3 `str` regexes are Unicode-aware:
 * `\d`, `\w`, `\s`, `\b` and `(?i)` all work on Unicode, so every pattern here is compiled with
 * UNICODE_CHARACTER_CLASS).
 */
internal object Text {
    /**
     * Android's java.util.regex is ICU-based: it throws IllegalArgumentException for UNICODE_CHARACTER_CLASS, but its
     * \d \w \s \b and (?i) are already Unicode-aware, which is exactly what Python's `re` does for str patterns.
     * So: ask for the flag where the JVM supports it, and use no flag where it is rejected.
     */
    internal fun supportedFlags(probe: (Int) -> Pattern = { Pattern.compile("a", it) }): Int =
        try {
            probe(Pattern.UNICODE_CHARACTER_CLASS)
            Pattern.UNICODE_CHARACTER_CLASS
        } catch (e: IllegalArgumentException) {
            0
        }

    private val flags: Int by lazy { supportedFlags() }

    fun compile(pattern: String): Pattern = Pattern.compile(pattern, flags)

    /** Same set of characters as Python's `str.isspace()`. */
    fun isPySpace(c: Char): Boolean {
        val n = c.code
        return n in 0x09..0x0D || n in 0x1C..0x20 || n == 0x85 || n == 0xA0 || n == 0x1680 ||
            n in 0x2000..0x200A || n == 0x2028 || n == 0x2029 || n == 0x202F || n == 0x205F || n == 0x3000
    }

    /** Python `str.strip()`. */
    fun strip(s: String): String {
        var start = 0
        var end = s.length
        while (start < end && isPySpace(s[start])) start++
        while (end > start && isPySpace(s[end - 1])) end--
        return s.substring(start, end)
    }

    /** Python `re.sub(pattern, fn, text)` for patterns that cannot match the empty string. */
    inline fun sub(pattern: Pattern, text: String, replacement: (Matcher) -> String): String {
        val m = pattern.matcher(text)
        val sb = StringBuilder()
        var last = 0
        while (m.find()) {
            sb.append(text, last, m.start())
            sb.append(replacement(m))
            last = m.end()
        }
        sb.append(text, last, text.length)
        return sb.toString()
    }

    /** Python `re.sub(r"\D", "", s)`: keep only Unicode decimal digits. */
    fun digitsOnly(s: String): String {
        val sb = StringBuilder()
        var i = 0
        while (i < s.length) {
            val cp = s.codePointAt(i)
            if (Character.isDigit(cp)) sb.appendCodePoint(cp)
            i += Character.charCount(cp)
        }
        return sb.toString()
    }
}
