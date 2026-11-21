package com.aaadnw.commscap.core

/**
 * Known-answer check of the privacy rules, run by the app on the phone itself at start-up.
 *
 * The JVM tests prove the rules on a desktop JVM; Android's regex engine (ICU) is a different implementation, and a
 * difference there would silently weaken redaction or the gate. If any case here fails on the phone the app refuses
 * to capture anything and says so on the status screen. Every case is taken from shared/vectors (fictional numbers).
 */
object SelfCheck {
    /** Returns a description of each failed case; empty means all good. */
    fun run(): List<String> {
        val failures = ArrayList<String>()
        fun expect(name: String, expected: Any?, actual: () -> Any?) {
            val got = try {
                actual()
            } catch (t: Throwable) {
                "threw ${t.javaClass.simpleName}"
            }
            if (got != expected) failures.add(name)
        }

        // --- redaction (redact_vectors.json)
        fun red(s: String) = Redact.redact(s)
        expect("card", "my card is [REDACTED:card] exp 12/27") { red("my card is 4111 1111 1111 1111 exp 12/27").text }
        expect("card-not-luhn", "card 4111-1111-1111-1112 typo") { red("card 4111-1111-1111-1112 typo").text }
        expect("ssn", "ssn [REDACTED:ssn] thanks") { red("ssn 123-45-6789 thanks").text }
        expect("secret", "password is [REDACTED:secret] ok") { red("password is hunter2 ok").text }
        expect("pin", "PIN: [REDACTED:secret]") { red("PIN: 4455").text }
        expect("pin-word", "pin the location on the map") { red("pin the location on the map").text }
        expect("routing+account", "routing number [REDACTED:routing] and account number [REDACTED:account]") {
            red("routing number 123456789 and account number 98765432").text
        }
        expect("tags", listOf("account", "routing")) { red("routing number 123456789 and account number 98765432").tags }
        expect("gate-code-kept", "gate code is 4821") { red("gate code is 4821").text }
        expect("dollar-sign-safe", "cost \$5 [REDACTED:ssn] \$1") { red("cost \$5 123-45-6789 \$1").text }

        // --- one-time codes
        expect("otp-a", true) { Redact.isOtp("Your verification code is 483920") }
        expect("otp-c", true) { Redact.isOtp("483920 is your verification code") }
        expect("otp-b", true) { Redact.isOtp("Your Acme login code is: 118822") }
        expect("otp-one-time", true) { Redact.isOtp("Your one-time passcode: 99887766") }
        expect("otp-not-gate-code", false) { Redact.isOtp("the code is 4821") }

        // --- addresses
        expect("phone", PhoneNumber.Classification("phone", "+12065550101")) { PhoneNumber.classify("(206) 555-0101") }
        expect("alpha", "alpha") { PhoneNumber.classify("CHASE").kind }
        expect("shortcode", "shortcode") { PhoneNumber.classify("5551234").kind }
        expect("extract", listOf("+12065550101", "+12065550102")) { PhoneNumber.extractPhones("cell (206) 555-0101; office (206) 555-0102") }

        // --- gate (gate_vectors.json)
        val keyword = Policy(
            numbers = mapOf("+12065550101" to "client"), excludeNumbers = listOf("+12065550199"),
            clientLabels = listOf("AAAD Clients"), unknownPolicy = Gate.UNKNOWN_KEYWORD,
        )
        val aiAll = keyword.copy(unknownPolicy = Gate.UNKNOWN_AI_ALL)
        fun d(p: Policy, a: String, b: String, saved: Boolean = false, media: Boolean = false) = Gate.decide(p, a, b, media, saved).let { it.decision + ":" + it.reason }
        expect("exclude", "drop:explicit_exclude") { d(keyword, "+12065550199", "I need a bid for 4708 8th Ave NE") }
        expect("client", "send:allow_client") { d(keyword, "(206) 555-0101", "can you come tuesday") }
        expect("automated", "drop:automated_sender") { d(keyword, "CHASE", "Your invoice is ready") }
        expect("otp-dropped", "drop:otp_code") { d(keyword, "+12065550177", "Your verification code is 483920") }
        expect("term", "send:unknown_business_signal") { d(keyword, "+12065550177", "We need an asbestos survey") }
        expect("term-l&i", "send:unknown_business_signal") { d(keyword, "+12065550177", "L&I inspector is here") }
        expect("term-word-boundary", "defer:no_business_signal") { d(keyword, "+12065550177", "moldy bread again") }
        expect("address", "send:unknown_business_signal") { d(keyword, "+12065550177", "we are at 6527 32nd Ave NW") }
        expect("job-number-saved", "send:saved_contact_job_number") { d(keyword, "+12065550177", "need a bid for 26-4708", saved = true) }
        expect("saved-private", "drop:saved_contact_not_allowlisted") { d(keyword, "+12065550177", "dinner at 6?", saved = true) }
        expect("date-not-job-number", "defer:no_business_signal") { d(keyword, "+12065550177", "2026-11-21 dinner?") }
        expect("keyword-defers", "defer:no_business_signal") { d(keyword, "+12065550177", "ok") }
        expect("ai_all-sends", "send:unknown_unsaved") { d(aiAll, "+12065550177", "happy birthday! love you") }
        expect("media-only-held", "hold:media_only_unknown") { d(aiAll, "+12065550177", "", media = true) }
        return failures
    }
}
