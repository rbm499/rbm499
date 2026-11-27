"""Files messages into the job's electronic folder.

Layout (inside the existing job folder, e.g. "26-3310 1026"):
    Communications/TEXTS_<contact>_<number>.md      append-only transcript, one block per message
    Communications/media/<stamp>_<uid8>_<n>.<ext>   attachments
    Communications/.comms_ledger.jsonl              one line per filed uid (idempotency)

If the job folder cannot be found (or is ambiguous) the message is filed under
<jobs_root>/_COMMS_UNFILED/<job_no>/ and the caller raises an alert; nothing is ever dropped and no
new job folder is ever invented.

Provenance (house rule: every value carries its source; AI-derived values are labelled INFERRED):
the message text is the record as received from the phone (after redaction, tags shown); screening
fields are marked INFERRED with the engine that produced them.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from .phone import mask

HEADER = """# Text messages — {contact} ({number})

Archive of text messages with this contact for this job, captured from the company phone.
Append-only: each block below is one message. Message text is as received (after automatic
redaction of card, SSN, account and password numbers, shown as [REDACTED:…]). Lines marked INFERRED
come from automatic screening and are not verified.

"""


@dataclass
class FileResult:
    path: Path
    job_dir: Optional[Path]
    unfiled: bool
    already: bool = False


def slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", (s or "").strip()).strip("-")
    return s[:40] or "contact"


def transcript_name(contact_name: str, number: str) -> str:
    digits = re.sub(r"\D", "", number or "") or "unknown"
    return "TEXTS_" + slug(contact_name or number) + "_" + digits + ".md"


class LocalFolderFiler:
    def __init__(self, jobs_root: Optional[Path], unfiled_root: Path, tz: str = "America/Los_Angeles"):
        self.jobs_root = Path(jobs_root) if jobs_root else None
        self.unfiled_root = Path(unfiled_root)
        self.tz = ZoneInfo(tz)

    # ------------------------------------------------------------ job folder
    def resolve_job_dir(self, job_no: Optional[str]) -> Optional[Path]:
        """Existing folder named exactly <job_no> or starting with '<job_no> ' (e.g. '26-3310 1026').
        Exactly one match or None."""
        if not self.jobs_root or not job_no or not self.jobs_root.exists():
            return None
        jn = job_no.strip()
        matches = [p for p in self.jobs_root.iterdir()
                   if p.is_dir() and (p.name == jn or p.name.startswith(jn + " "))]
        return matches[0] if len(matches) == 1 else None

    def _comm_dir(self, job_no: str) -> "tuple[Path, bool]":
        jd = self.resolve_job_dir(job_no)
        if jd is not None:
            return jd / "Communications", False
        # job_no can come from a person typing in the review page: never let it choose a path
        safe = re.sub(r"[^A-Za-z0-9 ._-]", "_", job_no or "").strip(" .") or "no-job"
        return self.unfiled_root / safe[:60], True

    # ------------------------------------------------------------ writing
    @staticmethod
    def _ledger_has(ledger: Path, uid: str) -> bool:
        if not ledger.exists():
            return False
        with ledger.open("r", encoding="utf-8") as f:
            return any(('"uid": "%s"' % uid) in line for line in f)

    def file_message(self, msg: Dict[str, Any], job_no: str, contact_name: str, routing: str) -> FileResult:
        cdir, unfiled = self._comm_dir(job_no)
        cdir.mkdir(parents=True, exist_ok=True)
        ledger = cdir / ".comms_ledger.jsonl"
        number = msg.get("address") or ""
        tpath = cdir / transcript_name(contact_name, number)
        if self._ledger_has(ledger, msg["uid"]):
            return FileResult(tpath, None if unfiled else cdir.parent, unfiled, already=True)

        ts = datetime.fromtimestamp(msg["ts_ms"] / 1000.0, tz=timezone.utc)
        local = ts.astimezone(self.tz)
        who = f"{contact_name or 'Unknown'} ({mask(number)})" if msg["direction"] == "in" else f"Michael → {contact_name or mask(number)}"
        body = (msg.get("body") or "").rstrip()
        quoted = "\n".join("> " + ln for ln in body.splitlines()) if body else "> (no text)"
        media = json.loads(msg["media_json"]) if isinstance(msg.get("media_json"), str) and msg.get("media_json") else (msg.get("media_json") or [])
        v = json.loads(msg["verdict_json"]) if isinstance(msg.get("verdict_json"), str) and msg.get("verdict_json") else {}
        lines = [
            f"### {local.strftime('%Y-%m-%d %H:%M')} PT · {'RECEIVED' if msg['direction'] == 'in' else 'SENT'} · {who}",
            quoted,
            f"- source: phone message {msg['uid'][:12]} via {msg.get('device_id')} ({msg.get('transport')}); utc {ts.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        ]
        if msg.get("redactions"):
            lines.append(f"- redacted before storage: {msg['redactions']}")
        if media:
            lines.append("- attachments: " + ", ".join(f"{m.get('mime', '?')} {m.get('size', '?')} bytes (file follows)" for m in media))
        if v:
            lines.append(
                f"- INFERRED screening ({v.get('engine', '?')}): {v.get('category')} "
                f"conf {v.get('confidence', 0):.2f}; needs reply: {'yes' if v.get('needs_reply') else 'no'}"
                f"{' (' + ', '.join(v.get('topics') or []) + ')' if v.get('topics') else ''}"
                + ("; ⚠ contains sensitive content" if v.get('sensitive_content') else ""))
        lines.append(f"- filed to {job_no}: {routing}" + (" — JOB FOLDER NOT FOUND, held in _COMMS_UNFILED" if unfiled else ""))
        block = "\n".join(lines) + "\n\n"

        new = not tpath.exists()
        with tpath.open("a", encoding="utf-8") as f:
            if new:
                f.write(HEADER.format(contact=contact_name or "Unknown", number=mask(number)))
            f.write(block)
            f.flush()
            os.fsync(f.fileno())
        with ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"uid": msg["uid"], "ts_ms": msg["ts_ms"], "file": tpath.name, "job_no": job_no}) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return FileResult(tpath, None if unfiled else cdir.parent, unfiled)

    def append_note(self, msg: Dict[str, Any], job_no: str, note: str) -> bool:
        """Append a correction note to this contact's transcript in `job_no` (history is never rewritten)."""
        cdir, _unfiled = self._comm_dir(job_no)
        tpath = cdir / transcript_name(msg.get("contact_name") or "", msg.get("address") or "")
        if not tpath.exists():
            return False
        with tpath.open("a", encoding="utf-8") as f:
            f.write(f"- CORRECTION for message {msg['uid'][:12]}: {note}\n\n")
            f.flush()
            os.fsync(f.fileno())
        return True

    def file_media(self, msg: Dict[str, Any], job_no: str, index: int, sha: str, src: Path, mime: str) -> Path:
        cdir, _unfiled = self._comm_dir(job_no)
        mdir = cdir / "media"
        mdir.mkdir(parents=True, exist_ok=True)
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "application/pdf": ".pdf",
               "video/mp4": ".mp4", "image/heic": ".heic"}.get(mime, ".bin")
        stamp = datetime.fromtimestamp(msg["ts_ms"] / 1000.0, tz=timezone.utc).astimezone(self.tz).strftime("%Y%m%d-%H%M%S")
        dest = mdir / f"{stamp}_{msg['uid'][:8]}_{index}{ext}"
        if not dest.exists():
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(Path(src).read_bytes())
            os.replace(tmp, dest)
        # note the file in the transcript (append-only)
        number = msg.get("address") or ""
        tpath = cdir / transcript_name(msg.get("contact_name") or "", number)
        if tpath.exists():
            with tpath.open("a", encoding="utf-8") as f:
                f.write(f"- attachment for message {msg['uid'][:12]} saved: media/{dest.name}\n\n")
        return dest
