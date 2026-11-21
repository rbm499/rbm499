package com.aaadnw.commscap

import android.content.Context
import android.content.SharedPreferences

/**
 * All small persistent settings and state. Private app storage only (no backup, see the manifest).
 * Nothing in here is a message body or address of a dropped message.
 */
class Prefs private constructor(ctx: Context) {
    private val sp: SharedPreferences = ctx.getSharedPreferences("commscap", Context.MODE_PRIVATE)

    private fun str(key: String): String? = sp.getString(key, null)
    private fun put(key: String, v: String?) {
        val e = sp.edit()
        if (v == null) e.remove(key) else e.putString(key, v)
        e.apply()
    }
    private fun lng(key: String, def: Long = 0L): Long = sp.getLong(key, def)
    private fun putLng(key: String, v: Long) {
        sp.edit().putLong(key, v).apply()
    }

    // --- setup ---
    var serverUrl: String
        get() = str("server_url") ?: ""
        set(v) = put("server_url", v)
    var deviceId: String
        get() = str("device_id") ?: ""
        set(v) = put("device_id", v)
    var secret: String
        get() = str("secret") ?: ""
        set(v) = put("secret", v)
    val isConfigured: Boolean
        get() = serverUrl.isNotEmpty() && deviceId.isNotEmpty() && secret.isNotEmpty()

    // --- capture cursors (-1 = not initialised yet: the first scan starts from "now", never from history) ---
    var lastSeenSms: Long
        get() = lng("last_seen_sms", -1L)
        set(v) = putLng("last_seen_sms", v)
    var lastSeenMms: Long
        get() = lng("last_seen_mms", -1L)
        set(v) = putLng("last_seen_mms", v)

    /** When capture first started on this phone (0 = never). Nothing older than this is ever read, not even by the nightly check. */
    var captureStartedMs: Long
        get() = lng("capture_started")
        set(v) = putLng("capture_started", v)

    // --- status ---
    var lastCaptureTsMs: Long
        get() = lng("last_capture_ts")
        set(v) = putLng("last_capture_ts", v)
    var lastUploadOkMs: Long
        get() = lng("last_upload_ok")
        set(v) = putLng("last_upload_ok", v)
    var lastHeartbeatMs: Long
        get() = lng("last_heartbeat")
        set(v) = putLng("last_heartbeat", v)
    var lastReconcileMs: Long
        get() = lng("last_reconcile")
        set(v) = putLng("last_reconcile", v)
    var lastReconcileNote: String
        get() = str("last_reconcile_note") ?: ""
        set(v) = put("last_reconcile_note", v)

    // --- pause + counters (see :core PauseLog / RollingCounters) ---
    var pauseLog: String
        get() = str("pause_log") ?: ""
        set(v) = put("pause_log", v)
    var counters: String
        get() = str("counters") ?: ""
        set(v) = put("counters", v)

    // --- policy ---
    var policyJson: String?
        get() = str("policy_json")
        set(v) = put("policy_json", v)
    var policyVersion: String?
        get() = str("policy_version")
        set(v) = put("policy_version", v)
    var policyRefetchPending: Boolean
        get() = sp.getBoolean("policy_refetch", false)
        set(v) {
            sp.edit().putBoolean("policy_refetch", v).apply()
        }
    var lastPolicyFetchMs: Long
        get() = lng("last_policy_fetch")
        set(v) = putLng("last_policy_fetch", v)
    var overlayProvisional: List<String>
        get() = Json.stringsFromJson(str("overlay_provisional"))
        set(v) = put("overlay_provisional", Json.stringsToJson(v))
    var overlayExclude: List<String>
        get() = Json.stringsFromJson(str("overlay_exclude"))
        set(v) = put("overlay_exclude", Json.stringsToJson(v))

    // --- failures (shown on the status screen) ---
    /** "auth" | "net" | "client" | "" */
    var errorKind: String
        get() = str("error_kind") ?: ""
        set(v) = put("error_kind", v)
    var lastError: String
        get() = str("last_error") ?: ""
        set(v) = put("last_error", v)
    var backoffAttempt: Int
        get() = sp.getInt("backoff_attempt", 0)
        set(v) {
            sp.edit().putInt("backoff_attempt", v).apply()
        }
    var nextAttemptMs: Long
        get() = lng("next_attempt")
        set(v) = putLng("next_attempt", v)
    var failedBatches: Int
        get() = sp.getInt("failed_batches", 0)
        set(v) {
            sp.edit().putInt("failed_batches", v).apply()
        }
    var serverDrops: Int
        get() = sp.getInt("server_drops", 0)
        set(v) {
            sp.edit().putInt("server_drops", v).apply()
        }

    // --- nudges: ids waiting to be acked in the next heartbeat, and ids already displayed (id -> time shown) ---
    var pendingAcks: List<String>
        get() = Json.stringsFromJson(str("pending_acks"))
        set(v) = put("pending_acks", Json.stringsToJson(v))
    var handledNudges: List<String>
        get() = Json.stringsFromJson(str("handled_nudges"))
        set(v) = put("handled_nudges", Json.stringsToJson(v.takeLast(500)))

    fun clearErrors() {
        errorKind = ""
        lastError = ""
        backoffAttempt = 0
        nextAttemptMs = 0L
    }

    companion object {
        @Volatile
        private var instance: Prefs? = null

        fun get(ctx: Context): Prefs =
            instance ?: synchronized(this) {
                instance ?: Prefs(ctx.applicationContext).also { instance = it }
            }
    }
}
