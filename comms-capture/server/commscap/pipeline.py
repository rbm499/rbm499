"""The pipeline: accept -> server gate -> screen -> associate -> file or queue -> reply clock.

Design rules this file enforces
  * Durable first: a message is committed to the database before anything slow (AI, disk) happens,
    and ingest answers `accepted` only after that commit. The phone deletes its copy on `accepted`.
  * Private content is not kept: a `drop` verdict deletes the row (and media) and leaves only a
    content-free audit line plus the uid in `seen_uids`, so nightly reconcile cannot resurrect it.
  * Known client numbers are never lost to an AI outage (heuristic verdict, flagged for re-screen);
    unknown numbers are never shown to anyone unscreened (they wait in `pending_ai`).
  * The reply clock starts whether or not a job number has been found yet.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .associate import associate
from .clock import BusinessClock
from .config import Settings
from .filer import LocalFolderFiler
from .gate import DROP, RULE_VERSION, Policy, decide
from .health import HealthMonitor
from .notify import Notifier
from .phone import KIND_PHONE, classify_address, mask
from .redact import redact
from .register import Register
from .screen import BUSINESS_CATEGORIES, DROP_CATEGORIES, ScreenInput, Screener, Verdict, heuristic_verdict
from .sla import SlaEngine
from .store import Store
from .wire import msg_uid, sha256_hex

ROLES = ("client", "crew", "vendor", "agency")
KNOWN_FLOW_ROLES = ("client", "vendor", "agency")  # keep flowing (heuristic) if the AI is down


class Reject(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class Pipeline:
    def __init__(self, settings: Settings, store: Store, register: Register, screener: Screener,
                 filer: LocalFolderFiler, notifier: Notifier, now_fn: Callable[[], float] = time.time):
        self.s, self.store, self.reg, self.screener, self.filer, self.notifier = settings, store, register, screener, filer, notifier
        self.now = now_fn
        self.clock = BusinessClock(settings)
        self.sla = SlaEngine(settings, store, self.clock, notifier)
        self.health = HealthMonitor(settings, store, self.clock, notifier)
        self._busy: set = set()
        self._busy_lock = threading.Lock()
        self._reg_mtime: Optional[float] = None
        self._record_register_state()
        if self.store.kv_get("started_ms") is None:
            self.store.kv_set("started_ms", str(self.now_ms()))

    # ================================================================== register (client numbers + jobs)
    def _record_register_state(self, error: str = "") -> None:
        self.store.kv_set("register_generated", str(self.reg.generated or ""))
        self.store.kv_set("register_jobs", str(len(self.reg.jobs)))
        self.store.kv_set("register_error", error)
        p = self.s.register_path
        if p and Path(p).exists():
            self._reg_mtime = Path(p).stat().st_mtime
            self.store.kv_set("register_mtime_ms", str(int(self._reg_mtime * 1000)))

    def reload_register_if_changed(self) -> bool:
        """Pick up a refreshed JOB_PIPELINE.json without a restart. A broken file keeps the old register."""
        p = self.s.register_path
        if not p or not Path(p).exists():
            return False
        mt = Path(p).stat().st_mtime
        if self._reg_mtime is not None and mt == self._reg_mtime:
            return False
        try:
            self.reg = Register.from_file(Path(p))
        except (ValueError, OSError, KeyError, TypeError) as e:
            self._reg_mtime = mt  # do not re-parse the same broken file every minute
            self._record_register_state(error=type(e).__name__)
            return False
        self._record_register_state()
        return True

    def now_ms(self) -> int:
        return int(self.now() * 1000)

    # ================================================================== policy
    def policy(self) -> Policy:
        numbers: Dict[str, str] = dict(self.reg.phone_roles())
        excluded: List[str] = []
        provisional: List[str] = []
        for n in self.store.all_numbers():
            a = n["address"]
            if n["status"] == "excluded":
                excluded.append(a)
            elif n["status"] == "business":
                if n.get("role") in ROLES:
                    numbers.setdefault(a, n["role"])
                elif a not in numbers:
                    provisional.append(a)
            elif n.get("role") in ROLES:
                numbers.setdefault(a, n["role"])
        p = Policy(numbers=numbers, exclude_numbers=sorted(set(excluded) - set(numbers)),
                   provisional_business=sorted(provisional), client_labels=["AAAD Clients"], defer_hours=self.s.defer_hours)
        blob = json.dumps(p.to_dict(), sort_keys=True)
        p.version = hashlib.sha1(blob.encode()).hexdigest()[:10] + "." + RULE_VERSION
        return p

    def _role(self, e164: Optional[str]) -> str:
        if e164 and self.reg.jobs_for_phone(e164):
            return "client"
        n = self.store.get_number(e164) if e164 else None
        if n and n.get("role") in ROLES and n["status"] != "excluded":
            return n["role"]
        return "unknown"

    # ================================================================== ingest
    def _accept(self, device_id: str, m: Dict[str, Any], pol: Policy, now: int) -> str:
        uid = m.get("uid")
        if not (isinstance(uid, str) and re.fullmatch(r"[0-9a-f]{64}", uid)):
            raise Reject("bad_schema")
        direction = m.get("direction")
        ts_ms = m.get("ts_ms")
        if direction not in ("in", "out") or not isinstance(ts_ms, int) or isinstance(ts_ms, bool):
            raise Reject("bad_schema")
        if self.store.known_uids([uid]):
            return "dup"
        address_raw = str(m.get("address") or "")
        body = str(m.get("body") or "")[:4000]
        media: List[Dict[str, Any]] = []
        for it in (m.get("media") if isinstance(m.get("media"), list) else []):
            if isinstance(it, dict) and re.fullmatch(r"[0-9a-f]{64}", str(it.get("sha256") or "")):
                media.append({"mime": str(it.get("mime") or "application/octet-stream")[:80],
                              "size": int(it.get("size") or 0), "sha256": it["sha256"]})
        kind, e164 = classify_address(address_raw)
        body2, tags = redact(body)
        tags = sorted(set(tags) | {str(t) for t in (m.get("redactions") or [])})
        if msg_uid(device_id, direction, address_raw, ts_ms, body, len(media)) != uid:
            self.store.kv_set("uid_mismatch_count", str(int(self.store.kv_get("uid_mismatch_count", "0") or 0) + 1))
        dec = decide(pol, address_raw, body2, bool(media), bool(m.get("contact_saved")), list(m.get("contact_labels") or []))
        if dec.decision == DROP:
            self.store.see_uid(uid, now, "server_gate_drop")
            self.store.add_audit(now, e164 or address_raw, direction, "dropped", "server:" + dec.reason, RULE_VERSION)
            raise Reject("server_gate_drop")
        address = e164 or address_raw
        role = self._role(e164)
        num = self.store.get_number(address) or {}
        name = str(m.get("contact_name") or "") or self.reg.person_for_phone(e164) or str(num.get("name") or "")
        row = {
            "uid": uid, "device_id": device_id, "direction": direction, "transport": str(m.get("transport") or ""),
            "address": address, "address_kind": kind, "contact_name": name, "ts_ms": ts_ms, "body": body2,
            "media_json": media, "gate_json": m.get("gate") or {}, "state": "received", "received_ms": now,
            "role": role, "redactions": ",".join(tags),
        }
        return "new" if self.store.insert_message(row) else "dup"

    def handle_ingest(self, device_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self.now_ms()
        pol = self.policy()
        accepted: List[str] = []
        dups: List[str] = []
        rejected: List[Dict[str, str]] = []
        new_uids: List[str] = []
        raw = payload.get("messages")
        for m in (raw if isinstance(raw, list) else [])[:20]:
            if not isinstance(m, dict):
                rejected.append({"uid": "", "reason": "bad_schema"})
                continue
            uid = str(m.get("uid") or "")
            try:
                out = self._accept(device_id, m, pol, now)
            except Reject as r:
                rejected.append({"uid": uid, "reason": r.reason})
                continue
            if out == "dup":
                dups.append(uid)
            else:
                accepted.append(uid)
                new_uids.append(uid)
        deadline = time.monotonic() + self.s.ingest_budget_seconds
        for uid in new_uids:
            if time.monotonic() > deadline:
                break  # remaining stay 'received'; the tick loop finishes them
            self.process_message(uid)
        return {
            "ok": True, "accepted": accepted, "duplicates": dups, "rejected": rejected,
            "media_wanted": self._media_wanted(accepted + dups), "policy_version": self.policy().version,
            "thread_verdicts": self._verdicts_since(device_id), "server_time_ms": now,
        }

    # ================================================================== screening / routing
    def process_message(self, uid: str) -> None:
        with self._busy_lock:  # ingest threads and the tick loop must not screen the same text twice
            if uid in self._busy:
                return
            self._busy.add(uid)
        try:
            self._process_message(uid)
        finally:
            with self._busy_lock:
                self._busy.discard(uid)

    def _process_message(self, uid: str) -> None:
        m = self.store.get_message(uid)
        if not m or m["state"] not in ("received", "pending_ai"):
            return
        now = self.now_ms()
        e164 = m["address"] if m["address_kind"] == KIND_PHONE else None
        role = m["role"] or "unknown"
        rows = [r for r in self.store.thread(m["address"], 6) if r["uid"] != uid]
        thread = [{"dir": r["direction"], "age_hours": round((now - r["ts_ms"]) / 3_600_000, 1),
                   "text": "[hidden]" if r["sensitive"] else (r["body"] or "")[:400]} for r in rows]
        cand = self.reg.candidates_for_screening(e164, m["body"] or "")
        media = json.loads(m["media_json"] or "[]")
        inp = ScreenInput(
            direction=m["direction"], body=m["body"] or "", role=role, thread=thread,
            jobs=[{"job_no": j.job_no, "site": j.site, "client": j.client, "stage": j.stage} for j in cand],
            now_local=self.clock.to_dt(now).strftime("%A %Y-%m-%d %H:%M"), has_media=bool(media))
        res = self.screener.screen(inp)
        if res.verdict is None:
            if role in KNOWN_FLOW_ROLES:
                verdict = heuristic_verdict(inp, self.policy(), res.error)
            else:
                self.store.update_message(uid, state="pending_ai", engine="none:" + str(res.error))
                return
        else:
            verdict = res.verdict
        self._apply_verdict(self.store.get_message(uid) or m, verdict, role)

    def _apply_verdict(self, m: Dict[str, Any], v: Verdict, role: str) -> None:
        uid, address, now = m["uid"], m["address"], self.now_ms()
        self.store.update_message(
            uid, category=v.category, confidence=v.confidence, engine=v.engine, sensitive=int(v.sensitive_content),
            needs_reply=int(v.needs_reply), urgency=v.reply_urgency, topics_json=v.topics, verdict_json=v.to_dict())
        business = v.category in BUSINESS_CATEGORIES or (v.category == "unclear" and role in KNOWN_FLOW_ROLES)
        if v.category in DROP_CATEGORIES or (business and v.sensitive_content and self.s.sensitive_business_policy == "drop"):
            self._drop(m, v, role)
            return
        if not business:  # unclear on an unknown/crew number: held unseen; a later business message promotes it
            self.store.update_message(uid, state="held", hold_until_ms=now + self.s.hold_hours_unclear * 3_600_000)
            return

        e164 = address if m["address_kind"] == KIND_PHONE else None
        if role in ("unknown", "crew") and e164:
            cur = self.store.get_number(address) or {}
            if cur.get("status") != "business":
                self.store.set_number(address, "business", now, source="ai")
            self._promote_held(address, uid)
        name = m.get("contact_name") or ""
        last = self.store.last_association(address)
        assoc = associate(self.reg, e164, m["body"] or "", self.s, now, v.job_numbers, v.addresses, last)
        media = json.loads(m["media_json"] or "[]")
        self.store.update_message(uid, media_wanted=1 if media else 0)
        if m["direction"] == "out":
            self.sla.on_outbound(address, m["ts_ms"], now)
        elif v.needs_reply:
            self.sla.open_item(m, v.to_dict(), assoc.job_no if assoc.auto else None, name)
        if assoc.auto and assoc.job_no:
            self._file(uid, assoc.job_no, f"automatic — {assoc.method} (score {assoc.confidence})", assoc.method, assoc.confidence, assoc.candidates)
        else:
            self.store.update_message(uid, state="queued", assoc_method=assoc.method, assoc_conf=assoc.confidence, assoc_json=assoc.candidates)

    def _drop(self, m: Dict[str, Any], v: Verdict, role: str) -> None:
        uid, address, now = m["uid"], m["address"], self.now_ms()
        self.store.add_audit(now, address, m["direction"], "dropped", "ai:" + v.category, RULE_VERSION)
        self.store.see_uid(uid, now, "dropped")
        self._delete_media(m.get("media_json"))
        self.store.x("DELETE FROM messages WHERE uid=?", [uid])
        if role == "unknown" and v.category in ("personal", "sensitive", "automated") and v.confidence >= 0.75:
            self.store.set_number(address, "excluded", now, source="ai")
            for r in self.store.purge_address(address, now, "ai_private_thread"):
                self._delete_media(r.get("media_json"))

    def _promote_held(self, address: str, exclude_uid: str) -> None:
        for r in self.store.q("SELECT uid FROM messages WHERE address=? AND state='held' AND uid<>?", [address, exclude_uid]):
            self.store.update_message(r["uid"], state="received", hold_until_ms=None)
            self.process_message(r["uid"])

    def _file(self, uid: str, job_no: str, routing: str, method: str, conf: float, cands: List[Dict[str, Any]]) -> bool:
        self.store.update_message(uid, job_no=job_no, assoc_method=method, assoc_conf=conf, assoc_json=cands)
        row = self.store.get_message(uid)
        if not row:
            return False
        try:
            res = self.filer.file_message(row, job_no, row.get("contact_name") or "", routing)
        except OSError:
            self.store.update_message(uid, state="file_failed")
            return False
        self.store.update_message(uid, state="filed", filed_path=str(res.path), filed_ms=self.now_ms())
        self._attach_media(uid)
        return True

    # ================================================================== media
    def _media_wanted(self, uids: List[str]) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        for uid in uids:
            r = self.store.get_message(uid)
            if r and r["media_wanted"] and r["state"] in ("filed", "queued"):
                for it in json.loads(r["media_json"] or "[]"):
                    if not it.get("incoming_path") and not it.get("filed_path"):
                        out.append({"uid": uid, "sha256": it["sha256"]})
        return out

    def all_media_wanted(self) -> List[Dict[str, str]]:
        rows = self.store.q("SELECT uid FROM messages WHERE media_wanted=1 AND state IN ('filed','queued')")
        return self._media_wanted([r["uid"] for r in rows])

    def accept_media(self, uid: str, sha: str, data: bytes) -> None:
        row = self.store.get_message(uid)
        if not row or not row["media_wanted"]:
            raise ValueError("not_wanted")
        if sha256_hex(data) != sha:
            raise ValueError("hash_mismatch")
        media = json.loads(row["media_json"] or "[]")
        item = next((x for x in media if x["sha256"] == sha), None)
        if item is None:
            raise ValueError("unknown_attachment")
        p = self.s.media_dir / uid[:16]
        p.mkdir(parents=True, exist_ok=True)
        (p / sha).write_bytes(data)
        item["incoming_path"] = str(p / sha)
        self.store.update_message(uid, media_json=media)
        if row["state"] == "filed":
            self._attach_media(uid)

    def _attach_media(self, uid: str) -> None:
        row = self.store.get_message(uid)
        if not row or row["state"] != "filed" or not row["job_no"]:
            return
        media = json.loads(row["media_json"] or "[]")
        changed = False
        for i, it in enumerate(media):
            if it.get("incoming_path") and not it.get("filed_path") and Path(it["incoming_path"]).exists():
                dest = self.filer.file_media(row, row["job_no"], i, it["sha256"], Path(it["incoming_path"]), it.get("mime", ""))
                it["filed_path"] = str(dest)
                Path(it["incoming_path"]).unlink(missing_ok=True)
                it.pop("incoming_path", None)
                changed = True
        if changed:
            self.store.update_message(uid, media_json=media)

    def _delete_media(self, media_json: Any) -> None:
        try:
            for it in (json.loads(media_json) if isinstance(media_json, str) else (media_json or [])):
                for k in ("incoming_path", "filed_path"):
                    if it.get(k):
                        Path(it[k]).unlink(missing_ok=True)
        except (ValueError, OSError):
            pass

    # ================================================================== phone-facing: heartbeat / reconcile / marks
    def _verdicts_since(self, device_id: str) -> List[Dict[str, str]]:
        key = f"verdict_sync:{device_id}"
        since = int(self.store.kv_get(key, "0") or 0)
        out: List[Dict[str, str]] = []
        mx = since
        for n in self.store.all_numbers():
            if n["status"] in ("business", "excluded") and (n["updated_ms"] or 0) > since and n.get("source") in ("ai", "ryan", "michael"):
                out.append({"address": n["address"], "verdict": "business" if n["status"] == "business" else "private"})
                mx = max(mx, n["updated_ms"])
        if mx > since:
            self.store.kv_set(key, str(mx))
        return out

    def handle_heartbeat(self, device_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self.now_ms()
        self.store.record_heartbeat(device_id, {**payload, "_server_ms": now}, now)
        self.store.ack_nudges([str(i) for i in (payload.get("nudge_acks") or [])], now)
        pending = self.store.pending_nudges(device_id)
        self.store.mark_nudges_delivered([n["id"] for n in pending], now)
        return {
            "ok": True, "server_time_ms": now, "policy_version": self.policy().version,
            "nudges": [{"id": n["id"], "level": n["level"], "title": n["title"], "text": n["text"],
                        "address": n["address"], "deadline_ms": n["deadline_ms"]} for n in pending],
            "media_wanted": self.all_media_wanted(), "thread_verdicts": self._verdicts_since(device_id),
        }

    def handle_reconcile(self, device_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        expected = [str(u) for u in (payload.get("expected_uids") or [])][:5000]
        known = self.store.known_uids(expected)
        missing = [u for u in expected if u not in known]
        self.store.record_reconcile(device_id, self.now_ms(), len(missing))
        return {"ok": True, "missing": missing, "known": len(known)}

    def apply_mark(self, address: str, verdict: str, uid: Optional[str] = None, by: str = "michael") -> Dict[str, Any]:
        kind, e164 = classify_address(address)
        addr = e164 or address
        now = self.now_ms()
        if verdict == "private":
            if e164 and self.reg.jobs_for_phone(e164):  # a register client is never excluded wholesale
                if uid:
                    row = self.store.get_message(uid)
                    if row:
                        self._delete_media(row.get("media_json"))
                        self.store.see_uid(uid, now, "purged")
                        self.store.x("DELETE FROM sla WHERE uid=?", [uid])
                        self.store.x("DELETE FROM messages WHERE uid=?", [uid])
                        self.store.add_audit(now, addr, row["direction"], "purged", f"marked_private_by_{by}", RULE_VERSION)
                    return {"ok": True, "note": "client_number_kept"}
                return {"ok": False, "reason": "client_in_register"}
            self.store.set_number(addr, "excluded", now, source=by)
            for r in self.store.purge_address(addr, now, f"marked_private_by_{by}"):
                self._delete_media(r.get("media_json"))
            return {"ok": True}
        if verdict == "business":
            self.store.set_number(addr, "business", now, source=by)
            for r in self.store.q("SELECT uid FROM messages WHERE address=? AND state='held'", [addr]):
                self.store.update_message(r["uid"], state="received", hold_until_ms=None)
                self.process_message(r["uid"])
            return {"ok": True}
        return {"ok": False, "reason": "bad_verdict"}

    def set_role(self, address: str, role: str, name: str = "") -> None:
        kind, e164 = classify_address(address)
        if role not in ROLES:
            raise ValueError("bad_role")
        self.store.set_number(e164 or address, "business", self.now_ms(), role=role, name=name or None, source="ryan")

    # ================================================================== review queue (office)
    def resolve_queue(self, address: str, action: str, job_no: Optional[str] = None, by: str = "ryan") -> Dict[str, Any]:
        if action == "assign":
            if not job_no:
                raise ValueError("job_no_required")
            uids = [r["uid"] for r in self.store.q("SELECT uid FROM messages WHERE address=? AND state='queued' ORDER BY ts_ms", [address])]
            n = 0
            for u in uids:
                n += 1 if self._file(u, job_no, f"assigned by {by}", "ryan", 1.0, []) else 0
            self.sla.set_job(address, job_no)
            return {"ok": True, "filed": n}
        if action in ("discard", "private"):
            return self.apply_mark(address, "private", by=by)
        raise ValueError("bad_action")

    def refile(self, uid: str, new_job_no: str, by: str = "ryan") -> Dict[str, Any]:
        """Correct a wrong filing: note the correction in the old job's transcript, file under the new job."""
        row = self.store.get_message(uid)
        if not row or row["state"] != "filed":
            raise ValueError("not_filed")
        old = row["job_no"]
        if old == new_job_no:
            return {"ok": True, "unchanged": True}
        if old:
            self.filer.append_note(row, old, f"filed here in error; re-filed to {new_job_no} by {by}. Disregard in this job.")
        ok = self._file(uid, new_job_no, f"re-filed from {old} by {by}", "ryan", 1.0, [])
        self.sla.set_job(row["address"], new_job_no)
        return {"ok": ok}

    def sla_handled(self, uid: str) -> None:
        self.sla.handled(uid, self.now_ms(), "office")

    def queue_view(self) -> List[Dict[str, Any]]:
        rows = self.store.q("SELECT * FROM messages WHERE state='queued' ORDER BY ts_ms")
        threads: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            t = threads.setdefault(r["address"], {
                "address": r["address"], "masked": mask(r["address"]), "name": r["contact_name"] or "",
                "role": r["role"], "messages": [], "candidates": [], "needs_reply": False, "oldest_ms": r["ts_ms"]})
            t["messages"].append({"uid": r["uid"], "dir": r["direction"], "ts_ms": r["ts_ms"],
                                  "text": "[hidden: sensitive content — see job file after filing]" if r["sensitive"] else (r["body"] or ""),
                                  "media": len(json.loads(r["media_json"] or "[]"))})
            t["needs_reply"] = t["needs_reply"] or bool(r["needs_reply"])
            if r["assoc_json"]:
                t["candidates"] = json.loads(r["assoc_json"])
        return sorted(threads.values(), key=lambda t: t["oldest_ms"])

    def sla_view(self) -> List[Dict[str, Any]]:
        now = self.now_ms()
        return [{"uid": s["uid"], "address": s["address"], "masked": mask(s["address"]), "name": s["contact_name"] or "",
                 "job_no": s["job_no"], "topic": s["topic"], "urgency": s["urgency"], "waiting_ms": now - s["started_ms"],
                 "level": s["level_sent"]} for s in self.store.sla_open()]

    def filed_view(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self.store.q("SELECT * FROM messages WHERE state='filed' ORDER BY filed_ms DESC LIMIT ?", [limit])
        return [{"uid": r["uid"], "name": r["contact_name"] or mask(r["address"]), "job_no": r["job_no"], "method": r["assoc_method"],
                 "conf": r["assoc_conf"], "ts_ms": r["ts_ms"], "dir": r["direction"], "address": r["address"]} for r in rows]

    def jobs_view(self) -> List[Dict[str, Any]]:
        return [{"job_no": j.job_no, "site": j.site, "client": j.client, "stage": j.stage, "open": j.is_open} for j in self.reg.jobs]

    def health_view(self) -> Dict[str, Any]:
        now = self.now_ms()
        return {
            "devices": [{"device_id": d["device_id"], "last_hb_ms": d["last_hb_ms"], "age_ms": (now - d["last_hb_ms"]) if d["last_hb_ms"] else None,
                         "queue_depth": (d.get("payload") or {}).get("queue_depth"), "permissions": (d.get("payload") or {}).get("permissions")}
                        for d in self.store.devices()],
            # capture-health only; reply-due alerts are shown in their own section
            "alerts": [{"key": a["key"], "level": a["level"], "subject": a["subject"], "body": a["body"]}
                       for a in self.store.active_alerts("health:")],
            "counts": {r["state"]: r["n"] for r in self.store.q("SELECT state, COUNT(*) AS n FROM messages GROUP BY state")},
        }

    # ================================================================== periodic work
    def tick(self) -> None:
        now = self.now_ms()
        self.reload_register_if_changed()
        for m in self.store.messages_in_state("received", 50) + self.store.messages_in_state("pending_ai", 50):
            self.process_message(m["uid"])
        for m in self.store.messages_in_state("file_failed", 50):
            if m.get("job_no"):
                self._file(m["uid"], m["job_no"], "retry after filing failure", m.get("assoc_method") or "retry", m.get("assoc_conf") or 0.0, [])
        for r in self.store.q("SELECT uid, address, media_json FROM messages WHERE state='held' AND hold_until_ms IS NOT NULL AND hold_until_ms<?", [now]):
            self.store.add_audit(now, r["address"], "n/a", "dropped", "held_expired", RULE_VERSION)
            self.store.see_uid(r["uid"], now, "held_expired")
            self._delete_media(r["media_json"])
            self.store.x("DELETE FROM messages WHERE uid=?", [r["uid"]])
        self.sla.tick(now, list(self.s.device_secrets.keys()) or None)
        self.health.check_all(now)
        self.health.digest(now)
        self.notifier.flush()
        if self.s.deadman_url:
            try:
                urllib.request.urlopen(self.s.deadman_url, timeout=10).read()
            except Exception:  # noqa: BLE001 - an unreachable monitor must not break the loop
                pass
