"""Alert delivery. Alerts never contain message text - only counts, job numbers, masked numbers,
contact names and topics - so a forwarded alert cannot leak a private or sensitive message.

Channels (all optional; the file outbox is always on so an alert can never be silently lost):
  * outbox directory  - one .txt per alert (a scheduled Claude/Gmail sweep or a human can read it)
  * email (SMTP)      - to COMMSCAP_ALERT_EMAIL_TO
  * webhook           - JSON POST (Slack-style {"text": ...}; also works with ntfy-style endpoints)
A channel that fails is logged and the alert stays 'unsent' so the next tick retries it.
"""
from __future__ import annotations

import json
import logging
import smtplib
import time
import urllib.request
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .config import Settings
from .store import Store

log = logging.getLogger("commscap.notify")


class Notifier:
    def __init__(self, settings: Settings, store: Store, now_fn: Callable[[], float] = time.time,
                 http_post: Optional[Callable[[str, bytes], None]] = None,
                 smtp_factory: Optional[Callable[..., Any]] = None):
        self.s = settings
        self.store = store
        self.now = now_fn
        self._http_post = http_post or self._default_post
        self._smtp_factory = smtp_factory or smtplib.SMTP
        self.sent_log: List[Dict[str, Any]] = []  # in-memory record for tests/inspection

    @staticmethod
    def _default_post(url: str, data: bytes) -> None:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()

    def _outbox(self) -> Path:
        d = self.s.notify_dir or (self.s.data_dir / "outbox")
        d.mkdir(parents=True, exist_ok=True)
        return d

    def alert(self, key: str, level: str, subject: str, body: str) -> bool:
        """Raise (idempotently) and try to deliver. Returns True if this call raised a NEW alert."""
        now_ms = int(self.now() * 1000)
        new = self.store.raise_alert(key, level, subject, body, now_ms)
        self.flush()
        return new

    def flush(self) -> None:
        for a in self.store.unsent_alerts():
            if self._deliver(a):
                self.store.mark_alert_sent(a["key"], int(self.now() * 1000))

    def _deliver(self, a: Dict[str, Any]) -> bool:
        ok = True
        text = f"[{a['level'].upper()}] {a['subject']}\n\n{a['body']}\n\nalert key: {a['key']}\n"
        try:
            path = self._outbox() / (time.strftime("%Y%m%d-%H%M%S", time.gmtime(self.now())) + "_" + "".join(c if c.isalnum() else "-" for c in a["key"])[:60] + ".txt")
            path.write_text(text, encoding="utf-8")
        except OSError as e:  # noqa: PERF203
            log.error("outbox write failed: %s", e)
            ok = False
        if self.s.notify_webhook:
            try:
                self._http_post(self.s.notify_webhook, json.dumps({"text": f"[{a['level']}] {a['subject']}\n{a['body']}"}).encode())
            except Exception as e:  # noqa: BLE001
                log.error("webhook failed: %s", type(e).__name__)
                ok = False
        if self.s.alert_email_to and self.s.smtp.get("host"):
            try:
                m = EmailMessage()
                m["Subject"] = f"[comms-capture {a['level']}] {a['subject']}"
                m["From"] = self.s.smtp.get("from", "comms-capture@localhost")
                m["To"] = ", ".join(self.s.alert_email_to)
                m.set_content(text)
                with self._smtp_factory(self.s.smtp["host"], int(self.s.smtp.get("port", "587")), timeout=15) as smtp:
                    if self.s.smtp.get("user"):
                        smtp.starttls()
                        smtp.login(self.s.smtp["user"], self.s.smtp.get("password", ""))
                    smtp.send_message(m)
            except Exception as e:  # noqa: BLE001
                log.error("email failed: %s", type(e).__name__)
                ok = False
        self.sent_log.append({"key": a["key"], "level": a["level"], "subject": a["subject"], "ok": ok})
        return ok
