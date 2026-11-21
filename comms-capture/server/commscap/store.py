"""SQLite store (WAL). One process, one connection, guarded by a lock.

Privacy shape: the `messages` table holds only messages that passed screening (or are waiting for
it). A dropped message keeps NOTHING but a row in `audit` - hashed address, outcome, reason - so the
daily digest can say "14 private texts were discarded" without any ability to reconstruct them.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
  uid TEXT PRIMARY KEY, device_id TEXT NOT NULL, direction TEXT NOT NULL, transport TEXT,
  address TEXT, address_kind TEXT, contact_name TEXT, ts_ms INTEGER NOT NULL, body TEXT,
  media_json TEXT, gate_json TEXT, state TEXT NOT NULL,
  category TEXT, confidence REAL, engine TEXT, sensitive INTEGER DEFAULT 0,
  needs_reply INTEGER DEFAULT 0, urgency TEXT, topics_json TEXT, verdict_json TEXT,
  job_no TEXT, assoc_method TEXT, assoc_conf REAL, assoc_json TEXT,
  filed_path TEXT, filed_ms INTEGER, received_ms INTEGER NOT NULL,
  hold_until_ms INTEGER, media_wanted INTEGER DEFAULT 0, role TEXT, redactions TEXT
);
CREATE INDEX IF NOT EXISTS idx_msg_state ON messages(state);
CREATE INDEX IF NOT EXISTS idx_msg_addr ON messages(address, ts_ms);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts_ms INTEGER, addr_hash TEXT, direction TEXT,
  outcome TEXT, reason TEXT, rule_version TEXT
);
CREATE TABLE IF NOT EXISTS numbers (
  address TEXT PRIMARY KEY, status TEXT, role TEXT, name TEXT, source TEXT, updated_ms INTEGER
);
CREATE TABLE IF NOT EXISTS sla (
  uid TEXT PRIMARY KEY, address TEXT, job_no TEXT, contact_name TEXT, topic TEXT, urgency TEXT,
  started_ms INTEGER, due1 INTEGER, due2 INTEGER, due3 INTEGER, level_sent INTEGER DEFAULT 0,
  last_alert_ms INTEGER, resolved_ms INTEGER, resolved_by TEXT
);
CREATE TABLE IF NOT EXISTS nudges (
  id TEXT PRIMARY KEY, device_id TEXT, level INTEGER, title TEXT, text TEXT, address TEXT,
  deadline_ms INTEGER, created_ms INTEGER, delivered_ms INTEGER, acked_ms INTEGER, sla_uid TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
  key TEXT PRIMARY KEY, level TEXT, subject TEXT, body TEXT, created_ms INTEGER, sent_ms INTEGER,
  resolved_ms INTEGER, count INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS devices (
  device_id TEXT PRIMARY KEY, last_hb_ms INTEGER, last_payload TEXT, last_reconcile_ms INTEGER,
  last_reconcile_missing INTEGER, first_seen_ms INTEGER
);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS seen_uids (uid TEXT PRIMARY KEY, ts_ms INTEGER, outcome TEXT);
"""


def addr_hash(address: Optional[str]) -> str:
    return hashlib.sha256((address or "").encode("utf-8")).hexdigest()[:16]


def _enc(v: Any) -> Any:
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v


class Store:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        with self.lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.executescript(SCHEMA)

    # ------------------------------------------------------------ generic
    def q(self, sql: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, tuple(params)).fetchall()]

    def x(self, sql: str, params: Iterable[Any] = ()) -> int:
        with self.lock:
            return self.db.execute(sql, tuple(params)).rowcount

    # ------------------------------------------------------------ messages
    def insert_message(self, m: Dict[str, Any]) -> bool:
        cols = list(m.keys())
        sql = f"INSERT OR IGNORE INTO messages ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
        return self.x(sql, [_enc(m[c]) for c in cols]) == 1

    def get_message(self, uid: str) -> Optional[Dict[str, Any]]:
        r = self.q("SELECT * FROM messages WHERE uid=?", [uid])
        return r[0] if r else None

    def update_message(self, uid: str, **fields: Any) -> None:
        if not fields:
            return
        sets = ",".join(f"{k}=?" for k in fields)
        self.x(f"UPDATE messages SET {sets} WHERE uid=?", [_enc(v) for v in fields.values()] + [uid])

    def messages_in_state(self, state: str, limit: int = 500) -> List[Dict[str, Any]]:
        return self.q("SELECT * FROM messages WHERE state=? ORDER BY ts_ms LIMIT ?", [state, limit])

    def thread(self, address: str, limit: int = 8, states: Iterable[str] = ("filed", "queued", "received", "pending_ai", "held")) -> List[Dict[str, Any]]:
        st = tuple(states)
        rows = self.q(
            f"SELECT * FROM messages WHERE address=? AND state IN ({','.join('?' * len(st))}) ORDER BY ts_ms DESC LIMIT ?",
            [address, *st, limit],
        )
        return list(reversed(rows))

    def last_association(self, address: str) -> Optional[Dict[str, Any]]:
        r = self.q(
            "SELECT job_no, assoc_method, assoc_conf, ts_ms FROM messages WHERE address=? AND job_no IS NOT NULL "
            "AND state IN ('filed') ORDER BY ts_ms DESC LIMIT 1", [address])
        return r[0] if r else None

    # ------------------------------------------------------------ audit / purge
    def add_audit(self, ts_ms: int, address: Optional[str], direction: str, outcome: str, reason: str, rule_version: str = "") -> None:
        self.x("INSERT INTO audit(ts_ms,addr_hash,direction,outcome,reason,rule_version) VALUES (?,?,?,?,?,?)",
               [ts_ms, addr_hash(address), direction, outcome, reason, rule_version])

    def audit_counts(self, since_ms: int) -> Dict[str, int]:
        rows = self.q("SELECT outcome, COUNT(*) AS n FROM audit WHERE ts_ms>=? GROUP BY outcome", [since_ms])
        return {r["outcome"]: r["n"] for r in rows}

    def purge_address(self, address: str, now_ms: int, reason: str = "private") -> List[Dict[str, Any]]:
        """Delete every stored message from this address. Returns the deleted rows (for media cleanup)."""
        with self.lock:
            rows = self.q("SELECT uid, media_json FROM messages WHERE address=?", [address])
            uids = [r["uid"] for r in rows]
            for u in uids:
                self.see_uid(u, now_ms, "purged")  # so a reconcile can never resurrect it
                self.x("DELETE FROM sla WHERE uid=?", [u])
            self.x("DELETE FROM messages WHERE address=?", [address])
            self.x("DELETE FROM nudges WHERE address=?", [address])
            self.add_audit(now_ms, address, "n/a", "purged", reason)
            return rows

    # ------------------------------------------------------------ seen uids (rejected / purged)
    def see_uid(self, uid: str, ts_ms: int, outcome: str) -> None:
        self.x("INSERT OR IGNORE INTO seen_uids(uid,ts_ms,outcome) VALUES (?,?,?)", [uid, ts_ms, outcome])

    def known_uids(self, uids: Iterable[str]) -> set:
        known: set = set()
        ids = list(uids)
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            ph = ",".join("?" * len(chunk))
            known.update(r["uid"] for r in self.q(f"SELECT uid FROM messages WHERE uid IN ({ph})", chunk))
            known.update(r["uid"] for r in self.q(f"SELECT uid FROM seen_uids WHERE uid IN ({ph})", chunk))
        return known

    # ------------------------------------------------------------ numbers
    def get_number(self, address: str) -> Optional[Dict[str, Any]]:
        r = self.q("SELECT * FROM numbers WHERE address=?", [address])
        return r[0] if r else None

    def set_number(self, address: str, status: str, now_ms: int, role: Optional[str] = None,
                   name: Optional[str] = None, source: str = "") -> None:
        cur = self.get_number(address) or {}
        self.x(
            "INSERT INTO numbers(address,status,role,name,source,updated_ms) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(address) DO UPDATE SET status=excluded.status, role=COALESCE(excluded.role, numbers.role), "
            "name=COALESCE(excluded.name, numbers.name), source=excluded.source, updated_ms=excluded.updated_ms",
            [address, status, role or cur.get("role"), name or cur.get("name"), source, now_ms])

    def numbers_with_status(self, status: str) -> List[Dict[str, Any]]:
        return self.q("SELECT * FROM numbers WHERE status=?", [status])

    def all_numbers(self) -> List[Dict[str, Any]]:
        return self.q("SELECT * FROM numbers")

    # ------------------------------------------------------------ SLA
    def sla_add(self, row: Dict[str, Any]) -> None:
        cols = list(row.keys())
        self.x(f"INSERT OR IGNORE INTO sla ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [row[c] for c in cols])

    def sla_open(self) -> List[Dict[str, Any]]:
        return self.q("SELECT * FROM sla WHERE resolved_ms IS NULL ORDER BY started_ms")

    def sla_update(self, uid: str, **f: Any) -> None:
        sets = ",".join(f"{k}=?" for k in f)
        self.x(f"UPDATE sla SET {sets} WHERE uid=?", list(f.values()) + [uid])

    def sla_resolve_address(self, address: str, upto_ms: int, now_ms: int, by: str) -> int:
        return self.x("UPDATE sla SET resolved_ms=?, resolved_by=? WHERE address=? AND resolved_ms IS NULL AND started_ms<=?",
                      [now_ms, by, address, upto_ms])

    def sla_resolve(self, uid: str, now_ms: int, by: str) -> int:
        return self.x("UPDATE sla SET resolved_ms=?, resolved_by=? WHERE uid=? AND resolved_ms IS NULL", [now_ms, by, uid])

    # ------------------------------------------------------------ nudges
    def add_nudge(self, device_id: str, level: int, title: str, text: str, address: str, deadline_ms: Optional[int],
                  now_ms: int, sla_uid: str) -> str:
        nid = "n_" + uuid.uuid4().hex[:10]
        self.x("INSERT INTO nudges(id,device_id,level,title,text,address,deadline_ms,created_ms,sla_uid) VALUES (?,?,?,?,?,?,?,?,?)",
               [nid, device_id, level, title, text, address, deadline_ms, now_ms, sla_uid])
        return nid

    def pending_nudges(self, device_id: str) -> List[Dict[str, Any]]:
        return self.q("SELECT * FROM nudges WHERE device_id=? AND acked_ms IS NULL ORDER BY created_ms", [device_id])

    def mark_nudges_delivered(self, ids: Iterable[str], now_ms: int) -> None:
        for i in ids:
            self.x("UPDATE nudges SET delivered_ms=COALESCE(delivered_ms,?) WHERE id=?", [now_ms, i])

    def ack_nudges(self, ids: Iterable[str], now_ms: int) -> None:
        for i in ids:
            self.x("UPDATE nudges SET acked_ms=? WHERE id=? AND acked_ms IS NULL", [now_ms, i])

    def cancel_nudges_for_address(self, address: str, now_ms: int) -> int:
        """Withdraw reminders that are still pending (the client has been answered)."""
        return self.x("UPDATE nudges SET acked_ms=? WHERE address=? AND acked_ms IS NULL", [now_ms, address])

    def unacked_nudges_older_than(self, cutoff_ms: int) -> List[Dict[str, Any]]:
        return self.q("SELECT * FROM nudges WHERE acked_ms IS NULL AND created_ms<=?", [cutoff_ms])

    # ------------------------------------------------------------ alerts
    def raise_alert(self, key: str, level: str, subject: str, body: str, now_ms: int) -> bool:
        """True when this is a new (or re-opened) alert that should be delivered."""
        with self.lock:
            r = self.q("SELECT * FROM alerts WHERE key=?", [key])
            if not r:
                self.x("INSERT INTO alerts(key,level,subject,body,created_ms) VALUES (?,?,?,?,?)", [key, level, subject, body, now_ms])
                return True
            if r[0]["resolved_ms"] is not None:
                self.x("UPDATE alerts SET level=?,subject=?,body=?,created_ms=?,sent_ms=NULL,resolved_ms=NULL,count=count+1 WHERE key=?",
                       [level, subject, body, now_ms, key])
                return True
            self.x("UPDATE alerts SET body=? WHERE key=?", [body, key])
            return False

    def resolve_alert(self, key: str, now_ms: int) -> None:
        self.x("UPDATE alerts SET resolved_ms=? WHERE key=? AND resolved_ms IS NULL", [now_ms, key])

    def active_alerts(self, prefix: str = "") -> List[Dict[str, Any]]:
        return self.q("SELECT * FROM alerts WHERE resolved_ms IS NULL AND key LIKE ? ORDER BY created_ms", [prefix + "%"])

    def mark_alert_sent(self, key: str, now_ms: int) -> None:
        self.x("UPDATE alerts SET sent_ms=? WHERE key=?", [now_ms, key])

    def unsent_alerts(self) -> List[Dict[str, Any]]:
        return self.q("SELECT * FROM alerts WHERE sent_ms IS NULL AND resolved_ms IS NULL ORDER BY created_ms")

    # ------------------------------------------------------------ devices
    def record_heartbeat(self, device_id: str, payload: Dict[str, Any], now_ms: int) -> None:
        self.x(
            "INSERT INTO devices(device_id,last_hb_ms,last_payload,first_seen_ms) VALUES (?,?,?,?) "
            "ON CONFLICT(device_id) DO UPDATE SET last_hb_ms=excluded.last_hb_ms, last_payload=excluded.last_payload",
            [device_id, now_ms, json.dumps(payload), now_ms])

    def record_reconcile(self, device_id: str, now_ms: int, missing: int) -> None:
        self.x(
            "INSERT INTO devices(device_id,last_reconcile_ms,last_reconcile_missing,first_seen_ms) VALUES (?,?,?,?) "
            "ON CONFLICT(device_id) DO UPDATE SET last_reconcile_ms=excluded.last_reconcile_ms, "
            "last_reconcile_missing=excluded.last_reconcile_missing", [device_id, now_ms, missing, now_ms])

    def devices(self) -> List[Dict[str, Any]]:
        out = self.q("SELECT * FROM devices")
        for d in out:
            d["payload"] = json.loads(d["last_payload"]) if d.get("last_payload") else {}
        return out

    # ------------------------------------------------------------ kv
    def kv_get(self, k: str, default: Optional[str] = None) -> Optional[str]:
        r = self.q("SELECT v FROM kv WHERE k=?", [k])
        return r[0]["v"] if r else default

    def kv_set(self, k: str, v: str) -> None:
        self.x("INSERT INTO kv(k,v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", [k, v])
