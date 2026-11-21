package com.aaadnw.commscap.core

import java.util.concurrent.ConcurrentHashMap
import java.util.regex.Pattern
import java.util.regex.PatternSyntaxException

/** The downloaded (plus locally overlaid) on-device gate policy. Same shape as gate_vectors.json -> "policy". */
data class Policy(
    val version: String = "default-0",
    val numbers: Map<String, String> = emptyMap(), // e164 -> role
    val excludeNumbers: List<String> = emptyList(),
    val provisionalBusiness: List<String> = emptyList(),
    val clientLabels: List<String> = emptyList(),
    val dropSenderKinds: List<String> = listOf("alpha", "shortcode", "email"),
    val businessTerms: List<String> = Gate.DEFAULT_BUSINESS_TERMS,
    val jobNumberPattern: String = Gate.JOB_NUMBER_PATTERN,
    val addressPattern: String = Gate.ADDRESS_PATTERN,
    val deferHours: Int = 24,
    val holdMediaDays: Int = 7,
) {
    fun toMap(): Map<String, Any?> = linkedMapOf(
        "version" to version,
        "numbers" to LinkedHashMap(numbers),
        "exclude_numbers" to ArrayList(excludeNumbers),
        "provisional_business" to ArrayList(provisionalBusiness),
        "client_labels" to ArrayList(clientLabels),
        "drop_sender_kinds" to ArrayList(dropSenderKinds),
        "business_terms" to ArrayList(businessTerms),
        "job_number_pattern" to jobNumberPattern,
        "address_pattern" to addressPattern,
        "defer_hours" to deferHours,
        "hold_media_days" to holdMediaDays,
    )

    companion object {
        /**
         * Builds a Policy from plain maps/lists (the app parses JSON with org.json and converts it; core never touches
         * JSON). Missing or null fields keep their defaults; unknown keys are ignored. A field of the wrong type keeps
         * its default rather than throwing, so a malformed download can never crash the capture path.
         */
        fun fromMap(d: Map<String, Any?>): Policy {
            val base = Policy()
            return Policy(
                version = (d["version"] as? String) ?: base.version,
                numbers = stringMap(d["numbers"]) ?: base.numbers,
                excludeNumbers = stringList(d["exclude_numbers"]) ?: base.excludeNumbers,
                provisionalBusiness = stringList(d["provisional_business"]) ?: base.provisionalBusiness,
                clientLabels = stringList(d["client_labels"]) ?: base.clientLabels,
                dropSenderKinds = stringList(d["drop_sender_kinds"]) ?: base.dropSenderKinds,
                businessTerms = stringList(d["business_terms"]) ?: base.businessTerms,
                jobNumberPattern = (d["job_number_pattern"] as? String) ?: base.jobNumberPattern,
                addressPattern = (d["address_pattern"] as? String) ?: base.addressPattern,
                deferHours = (d["defer_hours"] as? Number)?.toInt() ?: base.deferHours,
                holdMediaDays = (d["hold_media_days"] as? Number)?.toInt() ?: base.holdMediaDays,
            )
        }

        private fun stringList(v: Any?): List<String>? =
            (v as? Iterable<*>)?.mapNotNull { it?.toString() }

        private fun stringMap(v: Any?): Map<String, String>? {
            val m = v as? Map<*, *> ?: return null
            val out = LinkedHashMap<String, String>()
            for ((k, value) in m) {
                if (k != null && value != null) out[k.toString()] = value.toString()
            }
            return out
        }
    }
}

data class Decision(val decision: String, val reason: String, val kind: String, val e164: String?)

/**
 * The capture gate: decides, per message and BEFORE any upload, what may leave the phone. Mirrors
 * server/commscap/gate.py and is tested against shared/vectors/gate_vectors.json.
 */
object Gate {
    const val RULE_VERSION = "gate-1"

    const val SEND = "send"
    const val DROP = "drop"
    const val DEFER = "defer"
    const val HOLD = "hold"

    val DEFAULT_BUSINESS_TERMS: List<String> = listOf(
        "bid", "estimate", "quote", "proposal", "invoice", "change order", "scope of work", "work order",
        "asbestos", "ahera", "abatement", "remediation", "mold", "lead paint", "vermiculite",
        "popcorn ceiling", "survey", "inspection", "clearance", "test results", "lab results",
        "pscaa", "l&i", "permit", "demolition", "contractor", "sq ft", "square feet",
    )
    const val JOB_NUMBER_PATTERN = """(?<![\d-])\d{2}-\d{3,5}(?![\d-])"""
    const val ADDRESS_PATTERN =
        """(?i)\b\d{3,5}\s+(?:[NSEW]{1,2}\s+)?(?:\d{1,3}(?:st|nd|rd|th)|[A-Za-z]+)\s+""" +
            """(?:ave|avenue|st|street|rd|road|blvd|way|ln|lane|dr|drive|ct|court|pl|place|pkwy|hwy)\b"""

    // Patterns come from a downloaded policy: compile once, and never let a bad pattern throw into the capture path.
    private val patternCache = ConcurrentHashMap<String, Pattern>()
    private val NEVER_MATCHES: Pattern = Pattern.compile("(?!)")

    private fun cached(key: String, build: () -> String): Pattern {
        patternCache[key]?.let { return it }
        if (patternCache.size > 64) patternCache.clear()
        val p = try {
            Text.compile(build())
        } catch (e: PatternSyntaxException) {
            // Fail closed: a pattern we cannot compile contributes no business signal (messages stay on the phone).
            NEVER_MATCHES
        }
        patternCache[key] = p
        return p
    }

    /** Python: re.escape(term.strip()).replace(r"\ ", r"\s+"), joined with "|". */
    private fun termPattern(terms: List<String>): Pattern? {
        if (terms.isEmpty()) return null
        return cached("T:" + terms.joinToString("\u0000")) {
            val parts = terms.map { Text.strip(it) }.filter { it.isNotEmpty() }.map { escapeTerm(it) }
            """(?i)(?<![A-Za-z0-9])(?:""" + parts.joinToString("|") + """)(?![A-Za-z0-9])"""
        }
    }

    private fun escapeTerm(term: String): String {
        val sb = StringBuilder()
        for (c in term) {
            when {
                c == ' ' -> sb.append("\\s+")
                c in 'a'..'z' || c in 'A'..'Z' || c in '0'..'9' || c.code >= 128 -> sb.append(c)
                else -> sb.append('\\').append(c)
            }
        }
        return sb.toString()
    }

    private fun userPattern(p: String): Pattern = cached("P:$p") { p }

    /** Names of the signals present in the text: "term", "address", "job_number". */
    fun businessSignals(policy: Policy, body: String): List<String> {
        val out = ArrayList<String>()
        val rx = termPattern(policy.businessTerms)
        if (rx != null && rx.matcher(body).find()) out.add("term")
        if (policy.addressPattern.isNotEmpty() && userPattern(policy.addressPattern).matcher(body).find()) out.add("address")
        if (policy.jobNumberPattern.isNotEmpty() && userPattern(policy.jobNumberPattern).matcher(body).find()) out.add("job_number")
        return out
    }

    fun decide(
        policy: Policy,
        addressRaw: String?,
        body: String?,
        hasMedia: Boolean = false,
        contactSaved: Boolean = false,
        contactLabels: Collection<String> = emptyList(),
    ): Decision {
        val c = PhoneNumber.classify(addressRaw)
        val kind = c.kind
        val e164 = c.e164
        val text = body ?: ""
        val addr = e164 ?: ""

        if (addr.isNotEmpty() && addr in policy.excludeNumbers.toHashSet()) {
            return Decision(DROP, "explicit_exclude", kind, e164)
        }
        if (addr.isNotEmpty()) {
            val role = policy.numbers[addr]
            if (role != null) return Decision(SEND, "allow_$role", kind, e164)
        }
        if (addr.isNotEmpty() && addr in policy.provisionalBusiness.toHashSet()) {
            return Decision(SEND, "thread_business", kind, e164)
        }
        if (contactLabels.toHashSet().intersect(policy.clientLabels.toHashSet()).isNotEmpty()) {
            return Decision(SEND, "label_client", kind, e164)
        }
        if (kind in policy.dropSenderKinds) return Decision(DROP, "automated_sender", kind, e164)
        if (Redact.isOtp(text)) return Decision(DROP, "otp_code", kind, e164)

        val signals = businessSignals(policy, text)
        if (contactSaved) {
            return if ("job_number" in signals) {
                Decision(SEND, "saved_contact_job_number", kind, e164)
            } else {
                Decision(DROP, "saved_contact_not_allowlisted", kind, e164)
            }
        }

        // Unknown, unsaved number.
        if (signals.isNotEmpty()) return Decision(SEND, "unknown_business_signal", kind, e164)
        if (Text.strip(text).isEmpty() && hasMedia) return Decision(HOLD, "media_only_unknown", kind, e164)
        return Decision(DEFER, "no_business_signal", kind, e164)
    }

    /**
     * Group MMS: the gate runs once per counterpart and the message may only leave the phone if EVERY counterpart
     * says send. Otherwise the most private non-send outcome wins: drop, then defer, then hold. (Not part of the
     * Python reference or the vectors; phone-only behaviour for multi-recipient MMS.)
     */
    fun combine(decisions: List<Decision>): Decision {
        require(decisions.isNotEmpty()) { "no decisions to combine" }
        for (kind in listOf(DROP, DEFER, HOLD)) {
            decisions.firstOrNull { it.decision == kind }?.let { return it }
        }
        return decisions.first()
    }
}
