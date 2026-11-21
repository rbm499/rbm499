package com.aaadnw.commscap.core

/** The two local lists that survive policy refreshes. Addresses are E.164. */
data class Overlay(
    val provisionalBusiness: List<String> = emptyList(),
    val excludeNumbers: List<String> = emptyList(),
)

/**
 * @property purgeAddresses canonical addresses whose queued / deferred / held (and already-sent log) messages the
 *   app must now delete from the phone.
 */
data class VerdictResult(val overlay: Overlay, val purgeAddresses: List<String>)

/**
 * Merges the downloaded policy with the local overlays and applies thread verdicts (from the server, or from
 * Michael's "This was private" button).
 */
object PolicyOverlay {
    const val BUSINESS = "business"
    const val PRIVATE = "private"

    /** Downloaded lists + overlay lists. An excluded number is never also provisional; exclude always wins in the gate. */
    fun merge(base: Policy, overlay: Overlay): Policy {
        val exclude = (base.excludeNumbers + overlay.excludeNumbers).distinct()
        val excludeSet = exclude.toHashSet()
        val provisional = (base.provisionalBusiness + overlay.provisionalBusiness).distinct().filter { it !in excludeSet }
        return base.copy(excludeNumbers = exclude, provisionalBusiness = provisional)
    }

    /**
     * `private`: remove from provisional, add to exclude, purge that address. Always applied.
     * `business`: add to provisional. A business verdict from the server never overrides a local exclusion
     * (Michael's "private" is sticky); a business verdict that [userInitiated] (a correction he made himself)
     * lifts the local exclusion. Unknown verdicts and non-phone addresses change nothing in the overlay (the gate
     * only matches E.164 numbers), but a `private` verdict still returns the address to purge.
     */
    fun applyVerdict(overlay: Overlay, address: String?, verdict: String?, userInitiated: Boolean = false): VerdictResult {
        val canonical = Wire.canonicalAddress(address)
        if (canonical.isEmpty()) return VerdictResult(overlay, emptyList())
        val e164 = PhoneNumber.toE164(address)
        return when (verdict?.trim()?.lowercase()) {
            PRIVATE -> {
                val provisional = overlay.provisionalBusiness.filter { it != e164 }
                val exclude = if (e164 != null) (overlay.excludeNumbers + e164).distinct() else overlay.excludeNumbers
                VerdictResult(Overlay(provisional, exclude), listOf(canonical))
            }
            BUSINESS -> {
                if (e164 == null) return VerdictResult(overlay, emptyList())
                val excluded = e164 in overlay.excludeNumbers
                when {
                    excluded && !userInitiated -> VerdictResult(overlay, emptyList())
                    excluded -> VerdictResult(
                        Overlay((overlay.provisionalBusiness + e164).distinct(), overlay.excludeNumbers.filter { it != e164 }),
                        emptyList(),
                    )
                    else -> VerdictResult(Overlay((overlay.provisionalBusiness + e164).distinct(), overlay.excludeNumbers), emptyList())
                }
            }
            else -> VerdictResult(overlay, emptyList())
        }
    }

    fun applyVerdicts(overlay: Overlay, verdicts: List<ThreadVerdict>): VerdictResult {
        var current = overlay
        val purge = LinkedHashSet<String>()
        for (v in verdicts) {
            val r = applyVerdict(current, v.address, v.verdict)
            current = r.overlay
            purge.addAll(r.purgeAddresses)
        }
        return VerdictResult(current, purge.toList())
    }
}
