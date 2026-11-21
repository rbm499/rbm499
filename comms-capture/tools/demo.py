#!/usr/bin/env python3
"""Run the office service with SYNTHETIC data so the review page can be seen working.

    python tools/demo.py [port]      # then open http://127.0.0.1:<port>/ui  (token: demo)

No AI call is made (a keyword stand-in screens the demo texts) and nothing leaves this machine.
"""
import pathlib
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "server" / "tests"))

import uvicorn  # noqa: E402

from commscap.api import create_app  # noqa: E402
from commscap.config import Settings  # noqa: E402
from commscap.filer import LocalFolderFiler  # noqa: E402
from commscap.notify import Notifier  # noqa: E402
from commscap.pipeline import Pipeline  # noqa: E402
from commscap.register import Register  # noqa: E402
from commscap.screen import ScreenResult, heuristic_verdict  # noqa: E402
from commscap.store import Store  # noqa: E402
from conftest import ALEX, FELICIA, LUIS, REGISTER, STRANGER, TONY, mk  # noqa: E402


class DemoScreener:
    def screen(self, inp):
        return ScreenResult(heuristic_verdict(inp))


def main(port: int) -> None:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="commscap-demo-"))
    jobs = tmp / "Job sites"
    for n in ("26-4708 1021", "26-3310 1026", "26-6527 1006", "26-8607 0924"):
        (jobs / n).mkdir(parents=True)
    s = Settings(data_dir=tmp / "data", jobs_root=jobs, device_secrets={"dev-1": "demo-secret"}, ui_token="demo")
    store = Store(":memory:")
    p = Pipeline(s, store, Register.from_dict(REGISTER), DemoScreener(), LocalFolderFiler(jobs, s.unfiled_dir, s.tz), Notifier(s, store))
    now = p.now_ms()
    mins = lambda m: now - m * 60_000  # noqa: E731
    seed = [
        ("in", TONY, 190, "Can you resend the invoice for 4708? Accountant is asking."),
        ("in", LUIS, 95, "Can we move the start date at the Phinney job? Neighbor complained about noise."),
        ("out", LUIS, 80, "Let me check with the crew, will call you."),
        ("in", LUIS, 40, "Also is the gate at 6527 32nd Ave NW still locked? Please advise."),
        ("in", STRANGER, 55, "Hi, I got your number from a friend. We need an asbestos survey before a remodel. How much?"),
        ("in", ALEX, 25, "Can you send the bid today? Inspector is coming tomorrow."),
        ("in", FELICIA, 12, "Water is flooding the containment please call right now"),
    ]
    for d, a, m, body in seed:
        p.handle_ingest("dev-1", {"messages": [mk("dev-1", d, a, mins(m), body, contact_name=None)]})
    p.handle_heartbeat("dev-1", {"ts_ms": now, "permissions": {"sms": True, "contacts": True, "notification_listener": False,
                                                              "battery_unrestricted": True, "post_notifications": True}, "queue_depth": 0})
    p.tick()
    print(f"demo up: http://127.0.0.1:{port}/ui  token=demo  (files under {jobs})", flush=True)
    uvicorn.run(create_app(p, s, tick_seconds=None), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8799)
