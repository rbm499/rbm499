"""Response-time engine: no client message that needs an answer waits unnoticed.

Ladder for a message that needs a reply (clock starts when the CLIENT sent it, independent of
whether the text has been matched to a job yet):

  level 1  nudge Michael on his own phone (notification from the capture agent)
  level 2  alert the office (Ryan): client waiting
  level 3  overdue: alert, repeated every `repeat_overdue_hours` until resolved
  +        if the level-1 nudge was never displayed (phone online but no ack) -> alert the office

Urgent messages (safety, "emergency", inspector on site, same-day) use wall-clock time and fire
level 1 at once. Normal messages use business-hours time, so a 9 PM text is not "late" at 9:30 PM.

A reply is any outgoing text to the same number after the client's message; the office can also
press "handled" (phone call, email, in person). Default minutes are INFERRED starting values.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .clock import BusinessClock
from .config import Settings
from .notify import Notifier
from .phone import mask
from .store import Store

TOPIC_LABEL = {
    "bid_request": "bid/estimate request", "bid_response": "bid response", "change_order": "change order",
    "schedule": "scheduling", "access_logistics": "site access", "invoice_payment": "invoice/payment",
    "results_report": "results/report", "permit_regulatory": "permit/agency", "complaint_problem": "problem/complaint",
    "safety_urgent": "URGENT safety", "new_inquiry": "new inquiry", "other": "message",
}


def fmt_wait(ms: int) -> str:
    mins = max(0, int(ms // 60000))
    h, m = divmod(mins, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


class SlaEngine:
    def __init__(self, settings: Settings, store: Store, clock: BusinessClock, notifier: Notifier):
        self.s, self.store, self.clock, self.notifier = settings, store, clock, notifier

    # ------------------------------------------------------------ open / resolve
    def open_item(self, msg: Dict[str, Any], verdict: Dict[str, Any], job_no: Optional[str], contact_name: str) -> None:
        urgent = verdict.get("reply_urgency") == "high" or "safety_urgent" in (verdict.get("topics") or [])
        levels = self.s.sla.urgent_levels_min if urgent else self.s.sla.normal_levels_min
        start = int(msg["ts_ms"])
        if urgent:
            dues = [start + m * 60000 for m in levels]
        else:
            dues = [self.clock.add_business_minutes(start, m) for m in levels]
        topics = verdict.get("topics") or ["other"]
        self.store.sla_add({
            "uid": msg["uid"], "address": msg["address"], "job_no": job_no, "contact_name": contact_name,
            "topic": topics[0], "urgency": "high" if urgent else "normal", "started_ms": start,
            "due1": dues[0], "due2": dues[1], "due3": dues[2], "level_sent": 0,
        })

    def on_outbound(self, address: str, ts_ms: int, now_ms: int) -> int:
        n = self.store.sla_resolve_address(address, ts_ms, now_ms, "reply")
        if n:
            self._clear_alerts(address, now_ms)
        return n

    def handled(self, uid: str, now_ms: int, by: str = "office") -> None:
        rows = self.store.q("SELECT address FROM sla WHERE uid=?", [uid])
        self.store.sla_resolve(uid, now_ms, by)
        if rows:
            self._clear_alerts(rows[0]["address"], now_ms)

    def set_job(self, address: str, job_no: str) -> None:
        self.store.x("UPDATE sla SET job_no=? WHERE address=? AND resolved_ms IS NULL", [job_no, address])

    def _clear_alerts(self, address: str, now_ms: int) -> None:
        if not self.store.q("SELECT 1 FROM sla WHERE address=? AND resolved_ms IS NULL LIMIT 1", [address]):
            self.store.cancel_nudges_for_address(address, now_ms)  # nothing left waiting on this client
        for a in self.store.active_alerts("sla"):
            if f":{address}:" in a["key"] + ":":
                self.store.resolve_alert(a["key"], now_ms)

    # ------------------------------------------------------------ tick
    def _title(self, it: Dict[str, Any]) -> str:
        return it.get("contact_name") or mask(it["address"])

    def _describe(self, it: Dict[str, Any], now_ms: int) -> str:
        topic = TOPIC_LABEL.get(it.get("topic") or "other", "message")
        job = f" · job {it['job_no']}" if it.get("job_no") else " · no job number yet"
        return f"{topic}{job} · waiting {fmt_wait(now_ms - it['started_ms'])}"

    def tick(self, now_ms: int, device_ids: Optional[List[str]] = None) -> None:
        devices = device_ids or list(self.s.device_secrets.keys()) or ["unknown-device"]
        for it in self.store.sla_open():
            for level in (1, 2, 3):
                if now_ms >= it[f"due{level}"] and it["level_sent"] < level:
                    self._fire(it, level, now_ms, devices)
                    self.store.sla_update(it["uid"], level_sent=level, last_alert_ms=now_ms)
                    it["level_sent"] = level
            if it["level_sent"] >= 3 and it.get("last_alert_ms") and \
                    now_ms - it["last_alert_ms"] >= self.s.sla.repeat_overdue_hours * 3600_000:
                bucket = (now_ms - it["started_ms"]) // (self.s.sla.repeat_overdue_hours * 3600_000)
                self.notifier.alert(f"sla3:{it['address']}:{it['uid'][:8]}:r{bucket}", "warning",
                                    f"STILL OVERDUE: {self._title(it)}", self._describe(it, now_ms))
                self.store.sla_update(it["uid"], last_alert_ms=now_ms)
        self._check_unacked_nudges(now_ms)

    def _fire(self, it: Dict[str, Any], level: int, now_ms: int, devices: List[str]) -> None:
        title, desc = self._title(it), self._describe(it, now_ms)
        urgent = it["urgency"] == "high"
        if level == 1:
            for d in devices:
                self.store.add_nudge(d, 1, f"{'URGENT ' if urgent else ''}Reply due: {title}", desc, it["address"],
                                     it["due2"], now_ms, it["uid"])
            if urgent:
                self.notifier.alert(f"sla1:{it['address']}:{it['uid'][:8]}", "critical", f"URGENT client message: {title}", desc)
        elif level == 2:
            self.notifier.alert(f"sla2:{it['address']}:{it['uid'][:8]}", "warning", f"Client waiting: {title}", desc)
            for d in devices:
                self.store.add_nudge(d, 2, f"Still waiting: {title}", desc, it["address"], it["due3"], now_ms, it["uid"])
        else:
            self.notifier.alert(f"sla3:{it['address']}:{it['uid'][:8]}", "critical", f"OVERDUE reply: {title}", desc)
            for d in devices:
                self.store.add_nudge(d, 3, f"OVERDUE: {title}", desc, it["address"], None, now_ms, it["uid"])

    def _check_unacked_nudges(self, now_ms: int) -> None:
        cutoff = now_ms - self.s.sla.nudge_unacked_min * 60000
        online = {d["device_id"]: d for d in self.store.devices()
                  if d.get("last_hb_ms") and now_ms - d["last_hb_ms"] <= 30 * 60000}
        for n in self.store.unacked_nudges_older_than(cutoff):
            if n["device_id"] in online and n["level"] == 1:
                self.notifier.alert(f"nudge-unacked:{n['id']}", "warning",
                                    "Reminder not shown on Michael's phone",
                                    f"The reminder '{n['title']}' was sent {fmt_wait(now_ms - n['created_ms'])} ago and the phone "
                                    f"has been online but has not confirmed showing it. Check notifications on the phone.")
