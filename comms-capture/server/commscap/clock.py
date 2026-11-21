"""Business-hours arithmetic. Normal-urgency reply clocks only run while the office is open;
urgent ones run on the wall clock."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple
from zoneinfo import ZoneInfo

from .config import Settings


class BusinessClock:
    def __init__(self, settings: Settings):
        self.tz = ZoneInfo(settings.tz)
        self.days = set(settings.business_days)
        self.start = settings.business_start
        self.end = settings.business_end

    def to_dt(self, ms: int) -> datetime:
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).astimezone(self.tz)

    def to_ms(self, dt: datetime) -> int:
        return int(dt.timestamp() * 1000)

    def _window(self, day: datetime) -> Tuple[datetime, datetime]:
        s = day.replace(hour=self.start[0], minute=self.start[1], second=0, microsecond=0)
        e = day.replace(hour=self.end[0], minute=self.end[1], second=0, microsecond=0)
        return s, e

    def is_open(self, ms: int) -> bool:
        dt = self.to_dt(ms)
        if dt.weekday() not in self.days:
            return False
        s, e = self._window(dt)
        return s <= dt < e

    def next_open(self, ms: int) -> int:
        """ms itself if the office is open then, else the next opening."""
        dt = self.to_dt(ms)
        for i in range(0, 15):
            day = (dt + timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            if day.weekday() not in self.days:
                continue
            s, e = self._window(day)
            if i == 0:
                if dt < s:
                    return self.to_ms(s)
                if dt < e:
                    return ms
                continue
            return self.to_ms(s)
        return ms

    def add_business_minutes(self, ms: int, minutes: int) -> int:
        """Instant after `minutes` of open-office time, starting from ms (clock starts at next opening)."""
        cur = self.next_open(ms)
        remaining = int(minutes)
        if remaining <= 0:
            return cur
        for _ in range(400):
            dt = self.to_dt(cur)
            _s, e = self._window(dt)
            avail = int((e - dt).total_seconds() // 60)
            if remaining <= avail:
                return self.to_ms(dt + timedelta(minutes=remaining))
            remaining -= avail
            cur = self.next_open(self.to_ms(e))
        return cur

    def local_date(self, ms: int) -> str:
        return self.to_dt(ms).strftime("%Y-%m-%d")
