"""Command line: serve the API, run one maintenance tick, inspect the register, mint a device secret."""
from __future__ import annotations

import argparse
import logging
import secrets
import sys
from typing import List, Optional

from .config import Settings
from .filer import LocalFolderFiler
from .notify import Notifier
from .pipeline import Pipeline
from .register import Register
from .screen import Screener
from .store import Store


def build_pipeline(settings: Settings) -> Pipeline:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(settings.db_path)
    reg = Register.from_file(settings.register_path) if settings.register_path and settings.register_path.exists() else Register([])
    return Pipeline(settings, store, reg, Screener(settings), LocalFolderFiler(settings.jobs_root, settings.unfiled_dir, settings.tz),
                    Notifier(settings, store))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="commscap")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sv = sub.add_parser("serve", help="run the API + review page + background loop")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8787)
    sub.add_parser("tick", help="run one maintenance pass (retries, reply clock, health, digest) and exit")
    sub.add_parser("register-stats", help="print aggregate stats of the loaded register (no personal data)")
    sec = sub.add_parser("new-secret", help="print a fresh device secret and phone setup string")
    sec.add_argument("--device", default="michael-phone-1")
    sec.add_argument("--url", default="https://YOUR-SERVER")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    settings = Settings.from_env()

    if args.cmd == "new-secret":
        s = secrets.token_urlsafe(32)
        print(f"COMMSCAP_DEVICE_SECRETS={args.device}:{s}")
        print(f"phone setup string: commscap://setup?url={args.url}&device={args.device}&secret={s}")
        return 0
    p = build_pipeline(settings)
    if args.cmd == "register-stats":
        r = p.reg
        print(f"jobs: {len(r.jobs)}; with at least one phone: {sum(1 for j in r.jobs if j.phones)}; "
              f"distinct client numbers: {len(r.by_phone)}; open jobs: {sum(1 for j in r.jobs if j.is_open)}")
        multi = sorted((len(v) for v in r.by_phone.values()), reverse=True)
        print("jobs per client number (descending):", multi)
        return 0
    if args.cmd == "tick":
        p.tick()
        print("tick done")
        return 0
    if args.cmd == "serve":
        import uvicorn

        from .api import create_app

        if not settings.device_secrets:
            print("refusing to start: set COMMSCAP_DEVICE_SECRETS (use `commscap new-secret`)", file=sys.stderr)
            return 2
        uvicorn.run(create_app(p, settings), host=args.host, port=args.port, log_level="info")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
