"""Settings, read from environment variables. Every default flagged (INFERRED) is a starting value
chosen by the builder, not a recorded decision - the owner sets the real numbers."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class SlaConfig:
    # Minutes of BUSINESS time after a client message that needs a reply (INFERRED defaults).
    normal_levels_min: Tuple[int, int, int] = (120, 240, 480)  # nudge Michael / alert Ryan / overdue
    # Urgent messages (safety, "emergency", inspector on site...) use WALL-CLOCK minutes.
    urgent_levels_min: Tuple[int, int, int] = (0, 60, 180)
    repeat_overdue_hours: int = 12  # re-alert while still overdue
    nudge_unacked_min: int = 30  # phone online but never displayed the nudge -> escalate to Ryan


@dataclass
class HealthConfig:
    heartbeat_gap_business_min: int = 45  # INFERRED
    heartbeat_gap_off_hours_min: int = 180  # INFERRED
    phone_queue_stale_min: int = 60
    paused_alert_hours: int = 4
    reconcile_overdue_hours: int = 36
    review_queue_alert_min: int = 240
    ai_backlog_min: int = 30
    filing_backlog_min: int = 60
    clock_skew_seconds: int = 240
    digest_hour_local: int = 19
    register_stale_days: int = 7  # INFERRED: clients on newer jobs look like strangers once the register ages


@dataclass
class Settings:
    data_dir: Path = Path("./data")
    jobs_root: Optional[Path] = None  # e.g. C:\Users\<user>\Desktop\Job sites (or its Drive mirror)
    register_path: Optional[Path] = None  # JOB_PIPELINE.json
    device_secrets: Dict[str, str] = field(default_factory=dict)
    ui_token: Optional[str] = None
    model: str = "claude-opus-5-5"
    ai_enabled: bool = True
    tz: str = "America/Los_Angeles"
    business_days: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)  # Mon-Sat (INFERRED)
    business_start: Tuple[int, int] = (7, 0)  # INFERRED
    business_end: Tuple[int, int] = (19, 0)  # INFERRED
    hold_hours_unclear: int = 72
    defer_hours: int = 24
    sensitive_business_policy: str = "file_hidden"  # or "drop"
    unknown_policy: str = "ai_all"  # or "keyword" (stricter, misses new customers)
    alert_each_message: bool = False  # one info alert (no text) per business text, in or out
    feed_export_path: Optional[Path] = None  # write the live feed here (e.g. a Drive-synced folder) as JSON
    auto_assoc_min: float = 0.80  # INFERRED
    auto_assoc_margin: float = 0.25  # INFERRED
    ingest_budget_seconds: float = 20.0
    notify_dir: Optional[Path] = None
    notify_webhook: Optional[str] = None
    smtp: Dict[str, str] = field(default_factory=dict)
    alert_email_to: List[str] = field(default_factory=list)
    deadman_url: Optional[str] = None
    sla: SlaConfig = field(default_factory=SlaConfig)
    health: HealthConfig = field(default_factory=HealthConfig)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "commscap.sqlite"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media_incoming"

    @property
    def unfiled_dir(self) -> Path:
        return (self.jobs_root / "_COMMS_UNFILED") if self.jobs_root else (self.data_dir / "unfiled")

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "Settings":
        e = env if env is not None else os.environ
        s = cls()
        s.data_dir = Path(e.get("COMMSCAP_DATA_DIR", "./data"))
        if e.get("COMMSCAP_JOBS_ROOT"):
            s.jobs_root = Path(e["COMMSCAP_JOBS_ROOT"])
        if e.get("COMMSCAP_REGISTER"):
            s.register_path = Path(e["COMMSCAP_REGISTER"])
        secrets = e.get("COMMSCAP_DEVICE_SECRETS", "")  # "michael-phone-1:secret,other:secret2"
        for pair in [p for p in secrets.split(",") if ":" in p]:
            dev, sec = pair.split(":", 1)
            s.device_secrets[dev.strip()] = sec.strip()
        s.ui_token = e.get("COMMSCAP_UI_TOKEN") or None
        s.model = e.get("COMMSCAP_MODEL", s.model)
        s.ai_enabled = e.get("COMMSCAP_AI", "on").lower() != "off" and bool(e.get("ANTHROPIC_API_KEY"))
        s.tz = e.get("COMMSCAP_TZ", s.tz)
        s.sensitive_business_policy = e.get("COMMSCAP_SENSITIVE_BUSINESS", s.sensitive_business_policy)
        s.unknown_policy = e.get("COMMSCAP_UNKNOWN_POLICY", s.unknown_policy)
        s.alert_each_message = e.get("COMMSCAP_ALERT_EACH_MESSAGE", "off").lower() in ("on", "1", "true", "yes")
        if e.get("COMMSCAP_FEED_EXPORT"):
            s.feed_export_path = Path(e["COMMSCAP_FEED_EXPORT"])
        if e.get("COMMSCAP_NOTIFY_DIR"):
            s.notify_dir = Path(e["COMMSCAP_NOTIFY_DIR"])
        s.notify_webhook = e.get("COMMSCAP_NOTIFY_WEBHOOK") or None
        s.alert_email_to = [x.strip() for x in e.get("COMMSCAP_ALERT_EMAIL_TO", "").split(",") if x.strip()]
        for k in ("host", "port", "user", "password", "from"):
            v = e.get("COMMSCAP_SMTP_" + k.upper())
            if v:
                s.smtp[k] = v
        s.deadman_url = e.get("COMMSCAP_DEADMAN_URL") or None
        return s
