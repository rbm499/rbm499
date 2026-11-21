package com.aaadnw.commscap

import android.content.Context
import com.aaadnw.commscap.core.Gate
import com.aaadnw.commscap.core.LookbackPlanner
import com.aaadnw.commscap.core.ReconcileResponseApplier
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException

/**
 * Nightly check (~02:30, and from the status screen): rescan the last 48 hours of the system SMS/MMS store, list every
 * uid the gate says `send` (including ones already acknowledged), and re-enqueue whatever the server reports missing.
 * Messages inside a pause are skipped, exactly as on the live path.
 */
object Reconcile {
    private const val WINDOW_MS = 48 * LookbackPlanner.HOUR_MS

    /** Returns a one-line result for the status screen. */
    fun run(ctx: Context): String {
        val prefs = Prefs.get(ctx)
        if (!prefs.isConfigured) return "Not set up yet."
        if (!Safety.ok()) return "Skipped: the privacy self-check failed on this phone."
        val missingPermission = Perms.missingForCapture(ctx)
        if (missingPermission != null) return "Skipped: $missingPermission permission is off."

        val now = System.currentTimeMillis()
        // Last 48 hours, but never from before capture was switched on: older texts were never meant to be captured.
        val started = prefs.captureStartedMs
        if (started == 0L) return "Capture has not started yet."
        val start = maxOf(now - WINDOW_MS, started)
        val policy = PolicyStore.current(ctx)
        val pauses = Pause.log(ctx)

        val expected = LinkedHashMap<String, Pipeline.Evaluated>()
        for (raw in ProviderScanner.windowMessages(ctx, start, now)) {
            if (pauses.covers(raw.tsMs)) continue
            val ev = Pipeline.evaluate(ctx, raw, policy) ?: continue
            if (ev.decision.decision == Gate.SEND) expected[ev.uid] = ev
        }

        val body = JSONObject()
        body.put("schema", 1)
        body.put("device_id", prefs.deviceId)
        body.put("window_start_ms", start)
        body.put("window_end_ms", now)
        body.put("expected_uids", JSONArray(expected.keys))

        val res = try {
            Http.call(ctx, "POST", "/v1/reconcile", body.toString().toByteArray(Charsets.UTF_8))
        } catch (e: IOException) {
            return finish(prefs, now, "Could not reach the office service.")
        }
        if (res.code == 401) {
            Net.failAuth(ctx)
            return finish(prefs, now, "The office service does not accept this phone.")
        }
        val map = if (res.code == 200) Json.parseObject(res.body) else null
        if (map == null) return finish(prefs, now, "The office service answered with an error (HTTP ${res.code}).")
        val outcome = ReconcileResponseApplier.apply(map, expected.keys)
        if (!outcome.ok) return finish(prefs, now, "The office service did not accept the check.")

        var resent = 0
        for (uid in outcome.missing) {
            val ev = expected[uid] ?: continue
            if (Pipeline.enqueue(ctx, ev, now)) resent++
        }
        if (resent > 0) Engine.syncSoon(ctx)
        Net.succeeded(ctx)
        return finish(prefs, now, "Checked ${expected.size} texts from the last 2 days; sent ${resent} that were missing.")
    }

    private fun finish(prefs: Prefs, now: Long, note: String): String {
        prefs.lastReconcileMs = now
        prefs.lastReconcileNote = note
        return note
    }
}
