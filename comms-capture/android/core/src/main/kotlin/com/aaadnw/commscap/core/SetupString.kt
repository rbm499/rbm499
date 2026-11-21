package com.aaadnw.commscap.core

import java.net.URLDecoder

data class SetupConfig(val url: String, val deviceId: String, val secret: String)

/** Either a valid [config] or a plain-language [error] (never both). */
data class SetupResult(val config: SetupConfig?, val error: String?)

/**
 * Parses and validates the setup a helper pastes into the app:
 * `commscap://setup?url=https%3A%2F%2Fcomms.example.com&device=michael-phone-1&secret=...`
 * Values are percent-decoded; a literal `+` stays a plus (it is not treated as a space) so secrets survive.
 */
object SetupString {
    private const val PREFIX = "commscap://setup?"
    private val DEVICE_ID = Regex("^[A-Za-z0-9._-]{1,64}$")

    fun parse(text: String?): SetupResult {
        val t = Text.strip(text ?: "")
        if (t.isEmpty()) return fail("Nothing to read. Paste the setup text you were given.")
        if (!t.startsWith(PREFIX, ignoreCase = true)) {
            return fail("This does not look like a setup string. It should start with commscap://setup?")
        }
        val query = t.substring(PREFIX.length).substringBefore('#')
        val values = HashMap<String, String>()
        for (pair in query.split('&')) {
            if (pair.isEmpty()) continue
            val eq = pair.indexOf('=')
            val key = (if (eq < 0) pair else pair.substring(0, eq)).lowercase()
            val raw = if (eq < 0) "" else pair.substring(eq + 1)
            val decoded = try {
                URLDecoder.decode(raw.replace("+", "%2B"), "UTF-8")
            } catch (e: IllegalArgumentException) {
                return fail("The setup string has a damaged value for \"$key\".")
            }
            values[key] = decoded
        }
        return validate(values["url"], values["device"], values["secret"])
    }

    fun validate(url: String?, deviceId: String?, secret: String?): SetupResult {
        var u = Text.strip(url ?: "")
        val d = Text.strip(deviceId ?: "")
        val s = secret ?: ""
        if (u.isEmpty()) return fail("The server address is missing.")
        if (!u.startsWith("https://", ignoreCase = true)) return fail("The server address must start with https://")
        if (u.any { it.isWhitespace() }) return fail("The server address must not contain spaces.")
        u = u.trimEnd('/')
        if (u.length <= "https://".length) return fail("The server address is incomplete.")
        if (d.isEmpty()) return fail("The device name is missing.")
        if (!DEVICE_ID.matches(d)) return fail("The device name may only use letters, digits, dot, dash and underscore (max 64).")
        if (s.isEmpty()) return fail("The secret is missing.")
        if (s.length < 8 || s.any { it.isWhitespace() || it.isISOControl() }) {
            return fail("The secret looks wrong (too short, or it contains spaces).")
        }
        return SetupResult(SetupConfig(u, d, s), null)
    }

    private fun fail(msg: String) = SetupResult(null, msg)
}
