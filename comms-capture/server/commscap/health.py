"""Capture-health failsafes. Silence is the failure mode that matters most (a dead agent looks exactly
like a quiet day), so every layer reports on its own heartbeat and the daily digest is a proof of life.

Checks (each raises an alert while the condition holds and resolves it when it clears):
  heartbeat gap · missing/revoked permissions · paused too long · phone upload queue stuck ·
  nightly reconcile overdue / found missing texts · clock skew (signatures would start failing) ·
  AI backlog · filing backlog · review queue ageing · messages parked in _COMMS_UNFILED ·
  signature-uid mismatches (phone and server disagree on message ids)
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

from .clock import BusinessClock
from .config import Settings
from .notify import Notifier
from .sla import fmt_wait
from .store import Store

PERM_LEVEL = {
    "sms": ("critical", "Text-message permission was turned off on the phone — nothing is being captured."),
    "contacts": ("warning", "Contacts permission is off — the phone cannot tell saved contacts from strangers."),
    "notification_listener": ("warning", "Notification access is off — incoming RCS/chat messages are not captured."),
    "battery_unrestricted": ("warning", "Battery restriction is on — Android may stop the capture app in the background."),
    "post_notifications": ("warning", "The app cannot show reply reminders (notification permission off)."),
}


class HealthMonitor:
    def __init__(self, settings: Settings, store: Store, clock: BusinessClock, notifier: Notifier):
        self.s, self.store, self.clock, self.notifier = settings, store, clock, notifier

    def check_all(self, now_ms: int) -> List[Tuple[str, str, str, str]]:
        h = self.s.health
        active: List[Tuple[str, str, str, str]] = []  # (key, level, subject, body)
        is_open = self.clock.is_open(now_ms)
        started = int(self.store.kv_get("started_ms", str(now_ms)) or now_ms)
        devices = {d["device_id"]: d for d in self.store.devices()}

        for dev in self.s.device_secrets:
            d = devices.get(dev)
            if not d or not d.get("last_hb_ms"):
                if now_ms - started > 2 * 3600_000:
                    active.append((f"health:never-seen:{dev}", "critical", f"Phone '{dev}' has never checked in",
                                   "The capture agent has not contacted the office service since this service started."))
                continue
            gap_min = (now_ms - d["last_hb_ms"]) / 60000
            limit = h.heartbeat_gap_business_min if is_open else h.heartbeat_gap_off_hours_min
            if gap_min > limit:
                active.append((f"health:hb-gap:{dev}", "critical", f"Phone '{dev}' silent for {fmt_wait(now_ms - d['last_hb_ms'])}",
                               "No heartbeat from the capture agent. Phone off, no signal, app stopped, or permission revoked. "
                               "Texts received meanwhile stay on the phone and will upload when it reconnects."))
            p = d.get("payload") or {}
            for perm, ok in (p.get("permissions") or {}).items():
                if ok is False and perm in PERM_LEVEL:
                    lvl, why = PERM_LEVEL[perm]
                    active.append((f"health:perm:{dev}:{perm}", lvl, f"Phone '{dev}': {perm.replace('_', ' ')} missing", why))
            paused_until = p.get("capture_paused_until_ms")
            pk = f"paused_since:{dev}"
            if paused_until and paused_until > now_ms:
                since = int(self.store.kv_get(pk, str(now_ms)) or now_ms)
                self.store.kv_set(pk, str(since))
                if now_ms - since > h.paused_alert_hours * 3600_000 or paused_until - now_ms > h.paused_alert_hours * 3600_000:
                    active.append((f"health:paused:{dev}", "warning", f"Capture paused on '{dev}'",
                                   f"Capture has been paused for {fmt_wait(now_ms - since)} (until {self.clock.to_dt(paused_until).strftime('%a %H:%M')})."))
            else:
                self.store.kv_set(pk, "")
            oldest = p.get("oldest_queued_ms")
            if oldest and now_ms - oldest > h.phone_queue_stale_min * 60000 and gap_min <= limit:
                active.append((f"health:queue-stuck:{dev}", "critical", f"Phone '{dev}' cannot upload",
                               f"The phone is online but its oldest unsent text is {fmt_wait(now_ms - oldest)} old "
                               f"({p.get('queue_depth', '?')} waiting). Check the app's status screen."))
            skew = abs(int(p.get("ts_ms", now_ms)) - int(p.get("_server_ms", now_ms)))
            if skew > h.clock_skew_seconds * 1000:
                active.append((f"health:skew:{dev}", "warning", f"Phone clock is off by {skew // 1000}s",
                               "Request signatures are rejected when the clock drifts more than 5 minutes."))
            first_seen = d.get("first_seen_ms") or now_ms
            lr = d.get("last_reconcile_ms")
            if now_ms - first_seen > 24 * 3600_000 and (not lr or now_ms - lr > h.reconcile_overdue_hours * 3600_000):
                active.append((f"health:reconcile-overdue:{dev}", "warning", f"Nightly check missing for '{dev}'",
                               f"The phone has not completed its nightly completeness check in {h.reconcile_overdue_hours}h."))
            if d.get("last_reconcile_missing"):
                self.notifier.alert(f"info:reconcile-found:{dev}:{d['last_reconcile_ms']}", "info",
                                    f"Nightly check re-sent {d['last_reconcile_missing']} text(s) from '{dev}'",
                                    "The office service had not received these; they were requested again. Counts only.")

        for key, sql, subj, body, age_min in [
            ("health:ai-backlog", "SELECT COUNT(*) AS n, MIN(received_ms) AS t FROM messages WHERE state='pending_ai'",
             "Messages waiting for screening", "The AI screening service is unavailable; unknown-number texts are held unseen until it returns.", h.ai_backlog_min),
            ("health:filing-backlog", "SELECT COUNT(*) AS n, MIN(received_ms) AS t FROM messages WHERE state='file_failed'",
             "Messages could not be filed to the job folder", "The job-folder location is not writable. Texts are safe in the database and will retry.", h.filing_backlog_min),
        ]:
            r = self.store.q(sql)[0]
            if r["n"] and now_ms - r["t"] > age_min * 60000:
                active.append((key, "critical" if key.endswith("filing-backlog") else "warning", f"{r['n']} — {subj}", body))
        q = self.store.q("SELECT COUNT(*) AS n, MIN(ts_ms) AS t FROM messages WHERE state='queued'")[0]
        if q["n"] and is_open and now_ms - q["t"] > h.review_queue_alert_min * 60000:
            active.append(("health:review-queue", "warning", f"{q['n']} text(s) waiting for a job number",
                           f"Oldest has waited {fmt_wait(now_ms - q['t'])}. Open the review page."))
        u = self.store.q("SELECT COUNT(*) AS n FROM messages WHERE state='filed' AND filed_path LIKE '%_COMMS_UNFILED%'")[0]
        if u["n"]:
            jobs = sorted({r["job_no"] for r in self.store.q("SELECT DISTINCT job_no FROM messages WHERE state='filed' AND filed_path LIKE '%_COMMS_UNFILED%'")})
            active.append(("health:unfiled", "warning", f"{u['n']} text(s) filed in _COMMS_UNFILED",
                           f"No single job folder was found for: {', '.join(jobs)}. Create/rename the folder or move the files."))
        jobs_n = int(self.store.kv_get("register_jobs", "0") or 0)
        if jobs_n == 0:
            active.append(("health:register-empty", "critical", "No job/contact register loaded",
                           "Every client number looks like a stranger, so nothing can be filed automatically. "
                           "Set COMMSCAP_REGISTER to the current JOB_PIPELINE.json."))
        else:
            gen = self.store.kv_get("register_generated", "") or ""
            when_ms = None
            try:
                when_ms = int(datetime.fromisoformat(gen.replace("Z", "+00:00")).timestamp() * 1000) if gen else None
            except ValueError:
                when_ms = None
            if when_ms is None:
                when_ms = int(self.store.kv_get("register_mtime_ms", "0") or 0) or None
            if when_ms is not None and now_ms - when_ms > h.register_stale_days * 86_400_000:
                days = (now_ms - when_ms) // 86_400_000
                active.append(("health:register-stale", "warning", f"Job/contact register is {days} days old",
                               "Clients on jobs opened since then look like strangers (their texts are screened and queued "
                               "instead of filed automatically). Refresh JOB_PIPELINE.json."))
        if self.store.kv_get("register_error"):
            active.append(("health:register-load-failed", "warning", "Register file could not be read",
                           f"Keeping the previous register. Error: {self.store.kv_get('register_error')}."))
        mm = int(self.store.kv_get("uid_mismatch_count", "0") or 0)
        if mm:
            active.append(("health:uid-mismatch", "warning", f"{mm} message id(s) did not match between phone and office",
                           "Accepted anyway (nothing is dropped over this). Phone app and server id rules may have drifted."))

        keys = {a[0] for a in active}
        for a in self.store.active_alerts("health:"):
            if a["key"] not in keys:
                self.store.resolve_alert(a["key"], now_ms)
        for key, level, subject, body in active:
            self.notifier.alert(key, level, subject, body)
        self.notifier.flush()
        return active

    # ------------------------------------------------------------ proof of life
    def digest(self, now_ms: int) -> bool:
        """Once per local day after the digest hour. Counts only - never message text."""
        today = self.clock.local_date(now_ms)
        if self.clock.to_dt(now_ms).hour < self.s.health.digest_hour_local:
            return False
        if self.store.kv_get("last_digest_date") == today:
            return False
        since = now_ms - 24 * 3600_000
        audit = self.store.audit_counts(since)
        rows = self.store.q("SELECT state, assoc_method, COUNT(*) AS n FROM messages WHERE received_ms>=? GROUP BY state, assoc_method", [since])
        filed = sum(r["n"] for r in rows if r["state"] == "filed")
        auto = sum(r["n"] for r in rows if r["state"] == "filed" and (r["assoc_method"] or "") not in ("ryan", "ryan_assigned", ""))
        queued = self.store.q("SELECT COUNT(*) AS n FROM messages WHERE state='queued'")[0]["n"]
        held = self.store.q("SELECT COUNT(*) AS n FROM messages WHERE state='held'")[0]["n"]
        open_sla = self.store.sla_open()
        overdue = [s for s in open_sla if s["level_sent"] >= 3]
        devs = self.store.devices()
        lines = [
            f"Texts filed to job folders (24h): {filed} ({auto} automatically, {filed - auto} by hand)",
            f"Waiting for a job number: {queued} · held unseen (unclear): {held}",
            f"Discarded as private/automated/off-policy (24h, not stored): {sum(v for k, v in audit.items() if k in ('dropped', 'purged'))}",
            f"Client messages awaiting a reply: {len(open_sla)} ({len(overdue)} overdue)",
        ]
        for d in devs:
            lines.append(f"Phone '{d['device_id']}' last heard from {fmt_wait(now_ms - d['last_hb_ms'])} ago"
                         if d.get("last_hb_ms") else f"Phone '{d['device_id']}': never")
        active = self.store.active_alerts("health:")
        lines.append(f"Active health alerts: {len(active)}" + (": " + "; ".join(a['subject'] for a in active[:5]) if active else ""))
        self.notifier.alert(f"digest:{today}", "info", f"Daily text-capture summary {today}", "\n".join(lines))
        self.store.kv_set("last_digest_date", today)
        return True
