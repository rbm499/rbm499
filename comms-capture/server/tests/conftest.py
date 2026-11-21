"""Shared fixtures. All data is synthetic; numbers are the reserved fictional 206-555-01xx range."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import pytest

from commscap.config import Settings
from commscap.filer import LocalFolderFiler
from commscap.notify import Notifier
from commscap.pipeline import Pipeline
from commscap.register import Register
from commscap.screen import ScreenInput, ScreenResult, Verdict
from commscap.store import Store
from commscap.wire import msg_uid

PT = ZoneInfo("America/Los_Angeles")
TONY, FELICIA, LUIS, ALEX = "+12065550101", "+12065550102", "+12065550103", "+12065550104"
STRANGER, PERSON = "+12065550177", "+12065550188"

REGISTER = {
    "schemaVersion": "pipeline-1", "generated": "2026-11-21T00:00:00Z",
    "jobs": [
        {"job_no": "26-4708", "site": "4708 8th Ave NE, Seattle, WA 98105", "client": "8th Ave NE, LLC", "stage": "awaiting_payment",
         "contact": {"name": "Tony Park", "email": "tony@example.com", "phone": "(206) 555-0101"}, "last_activity": {"date": "2026-10-21"}},
        {"job_no": "26-3310 1026", "site": "3310 Beacon Ave S, Seattle, WA", "client": "Skyway LLC", "stage": "abatement",
         "contact": {"name": "Felicia Hart", "email": "f@example.com", "phone": "cell (206) 555-0102; office (206) 555-0110"}},
        {"job_no": "26-6527", "site": "6527 32nd Ave NW, Seattle, WA", "client": "Green Dev", "stage": "abatement",
         "contact": {"name": "Luis Ortega", "email": "l@example.com", "phone": "(206) 555-0103"}, "last_activity": {"date": "2026-11-10"}},
        {"job_no": "26-8607", "site": "8607 Phinney Ave N, Seattle, WA", "client": "Green Dev", "stage": "invoice_pending",
         "contact": {"name": "Luis Ortega", "email": "l@example.com", "phone": "(206) 555-0103"}, "last_activity": {"date": "2026-11-02"}},
        {"job_no": "26-2134", "site": "2134 14th Ave W, Seattle, WA", "client": "Green Dev", "stage": "paid",
         "contact": {"name": "Luis Ortega", "email": "l@example.com", "phone": "(206) 555-0103"}},
        {"job_no": "26-1036 0508", "site": "1036 N 105th St, Seattle, WA", "client": "Unknown LLC", "stage": "needs_ryan", "contact": None},
        {"job_no": "(no job no.) 9999 East 12th St, Tacoma — Restoration Done LLC bid", "site": "9999 East 12th St, Tacoma, WA",
         "client": "Restoration Done LLC", "stage": "bid_sent",
         "contact": {"name": "Alex K", "email": "a@example.com", "phone": "Alex (206) 555-0104; main (206) 555-0105"}},
    ],
}


class Clock:
    def __init__(self, dt: datetime):
        self.t = dt.timestamp()

    def __call__(self) -> float:
        return self.t

    def advance(self, minutes: float = 0, hours: float = 0, days: float = 0) -> None:
        self.t += minutes * 60 + hours * 3600 + days * 86400

    def ms(self) -> int:
        return int(self.t * 1000)


class ScriptedScreener:
    """Stands in for the AI: verdicts are scripted by substring so tests state their own expectations."""

    def __init__(self) -> None:
        self.rules: List[Any] = []
        self.calls: List[ScreenInput] = []
        self.down: Optional[str] = None

    def when(self, needle: str, **kw: Any) -> "ScriptedScreener":
        self.rules.append((needle.lower(), kw))
        return self

    def screen(self, inp: ScreenInput) -> ScreenResult:
        self.calls.append(inp)
        if self.down:
            return ScreenResult(None, self.down)
        for needle, kw in self.rules:
            if needle in inp.body.lower():
                return ScreenResult(Verdict(engine="fake", **kw))
        return ScreenResult(Verdict(category="unclear", confidence=0.3, engine="fake"))


def mk(device: str, direction: str, address: str, ts_ms: int, body: str, media: Optional[List[Dict[str, Any]]] = None,
       **extra: Any) -> Dict[str, Any]:
    media = media or []
    m: Dict[str, Any] = {
        "uid": msg_uid(device, direction, address, ts_ms, body, len(media)), "direction": direction, "transport": "sms",
        "address": address, "contact_name": None, "contact_saved": False, "contact_labels": [], "ts_ms": ts_ms,
        "body": body, "redactions": [], "media": media, "thread_key": None,
        "gate": {"decision": "send", "reason": "test", "rule_version": "gate-1"},
    }
    m.update(extra)
    return m


@pytest.fixture
def env(tmp_path: Path) -> SimpleNamespace:
    start = datetime(2026, 11, 23, 10, 0, tzinfo=PT)  # a Monday, 10:00 PT
    assert start.weekday() == 0
    clock = Clock(start)
    jobs_root = tmp_path / "Job sites"
    for name in ("26-4708 1021", "26-3310 1026", "26-6527 1006", "26-8607 0924"):  # 26-2134 deliberately has no folder
        (jobs_root / name).mkdir(parents=True)
    settings = Settings(data_dir=tmp_path / "data", jobs_root=jobs_root, device_secrets={"dev-1": "secret-1"},
                        ui_token="ui-token", ai_enabled=True)
    store = Store(":memory:")
    reg = Register.from_dict(REGISTER)
    screener = ScriptedScreener()
    notifier = Notifier(settings, store, now_fn=clock)
    pipeline = Pipeline(settings, store, reg, screener, LocalFolderFiler(jobs_root, settings.unfiled_dir, settings.tz), notifier, now_fn=clock)
    outbox = settings.data_dir / "outbox"
    return SimpleNamespace(pipeline=pipeline, store=store, settings=settings, clock=clock, jobs_root=jobs_root,
                           screener=screener, notifier=notifier, reg=reg, outbox=outbox, tmp=tmp_path)


def outbox_text(env: SimpleNamespace) -> str:
    if not env.outbox.exists():
        return ""
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(env.outbox.glob("*.txt")))


def transcript(env: SimpleNamespace, job_dir: str) -> str:
    d = env.jobs_root / job_dir / "Communications"
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(d.glob("TEXTS_*.md"))) if d.exists() else ""
