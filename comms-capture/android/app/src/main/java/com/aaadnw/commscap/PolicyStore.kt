package com.aaadnw.commscap

import android.content.Context
import com.aaadnw.commscap.core.Overlay
import com.aaadnw.commscap.core.Policy
import com.aaadnw.commscap.core.PolicyOverlay
import com.aaadnw.commscap.core.ThreadVerdict

/** The downloaded policy plus the local overlays (provisional_business / exclude) that survive policy refreshes. */
object PolicyStore {
    private const val MIN_FETCH_GAP_MS = 30_000L

    @Volatile
    private var merged: Policy? = null

    /** What the gate uses right now. Until the first download this is the built-in default policy. */
    fun current(ctx: Context): Policy {
        merged?.let { return it }
        val built = PolicyOverlay.merge(downloaded(ctx), overlay(ctx))
        merged = built
        return built
    }

    private fun downloaded(ctx: Context): Policy {
        val map = Json.parseObject(Prefs.get(ctx).policyJson) ?: return Policy()
        return Policy.fromMap(map)
    }

    fun overlay(ctx: Context): Overlay {
        val p = Prefs.get(ctx)
        return Overlay(p.overlayProvisional, p.overlayExclude)
    }

    private fun saveOverlay(ctx: Context, o: Overlay) {
        val p = Prefs.get(ctx)
        p.overlayProvisional = o.provisionalBusiness
        p.overlayExclude = o.excludeNumbers
        merged = null
    }

    /**
     * Applies verdicts from the server (ingest or heartbeat response) or from Michael's button, then deletes
     * everything held on the phone for the addresses that must be purged. Returns the purged addresses.
     */
    @Synchronized
    fun applyVerdicts(ctx: Context, verdicts: List<ThreadVerdict>): List<String> {
        if (verdicts.isEmpty()) return emptyList()
        val r = PolicyOverlay.applyVerdicts(overlay(ctx), verdicts)
        saveOverlay(ctx, r.overlay)
        purge(ctx, r.purgeAddresses)
        return r.purgeAddresses
    }

    /** Michael's "This was private": same overlay change as a server `private` verdict (user-initiated). */
    @Synchronized
    fun applyUserVerdict(ctx: Context, address: String, verdict: String): List<String> {
        val r = PolicyOverlay.applyVerdict(overlay(ctx), address, verdict, userInitiated = true)
        saveOverlay(ctx, r.overlay)
        purge(ctx, r.purgeAddresses)
        return r.purgeAddresses
    }

    private fun purge(ctx: Context, addresses: List<String>) {
        val db = Db.get(ctx)
        for (a in addresses) db.purgeAddress(a)
    }

    /** `GET /v1/policy`. Returns true when a new policy was stored. */
    fun fetch(ctx: Context): Boolean {
        val p = Prefs.get(ctx)
        val now = System.currentTimeMillis()
        if (now - p.lastPolicyFetchMs < MIN_FETCH_GAP_MS) return false
        p.lastPolicyFetchMs = now
        val res = Http.call(ctx, "GET", "/v1/policy", null)
        if (res.code == 401) {
            Net.failAuth(ctx)
            return false
        }
        if (res.code != 200) {
            Logx.w("policy fetch failed: HTTP ${res.code}")
            return false
        }
        val map = Json.parseObject(res.body) ?: return false
        val policy = Policy.fromMap(map)
        p.policyJson = res.body
        p.policyVersion = policy.version
        p.policyRefetchPending = false
        merged = null
        Net.succeeded(ctx)
        Logx.i("policy updated to ${policy.version}")
        return true
    }
}
