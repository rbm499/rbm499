"""HTTP API: signed phone endpoints (/v1/*) and a token-protected review page (/ui)."""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse

from .config import Settings
from .pipeline import Pipeline
from .wire import verify

log = logging.getLogger("commscap.api")
UI_FILE = Path(__file__).parent / "ui" / "index.html"


def create_app(pipeline: Pipeline, settings: Settings, tick_seconds: Optional[float] = 60.0) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = None
        if tick_seconds:
            async def loop() -> None:
                while True:
                    try:
                        await run_in_threadpool(pipeline.tick)
                        pipeline.store.kv_set("last_tick_ms", str(pipeline.now_ms()))
                    except Exception:  # noqa: BLE001 - the loop must survive anything
                        log.exception("tick failed")
                    await asyncio.sleep(tick_seconds)
            task = asyncio.create_task(loop())
        yield
        if task:
            task.cancel()

    app = FastAPI(title="comms-capture", lifespan=lifespan)

    MAX_JSON = 2 * 1024 * 1024
    MAX_MEDIA = 30 * 1024 * 1024

    async def authed(request: Request, max_bytes: int = MAX_JSON) -> Tuple[str, bytes]:
        device = request.headers.get("x-device-id", "")
        secret = settings.device_secrets.get(device)
        try:
            declared = int(request.headers.get("content-length", "0"))
        except ValueError:
            declared = 0
        if declared > max_bytes:
            raise HTTPException(status_code=413, detail="too_large")
        body = await request.body()
        if len(body) > max_bytes:
            raise HTTPException(status_code=413, detail="too_large")
        try:
            ts = int(request.headers.get("x-timestamp", "0"))
        except ValueError:
            ts = 0
        if not secret or not verify(secret, ts, device, body, request.headers.get("x-signature", ""), int(pipeline.now())):
            raise HTTPException(status_code=401, detail="bad_signature")
        return device, body

    def jsonbody(body: bytes) -> Dict[str, Any]:
        try:
            d = json.loads(body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(status_code=400, detail="bad_json")
        if not isinstance(d, dict):
            raise HTTPException(status_code=400, detail="bad_json")
        return d

    @app.get("/healthz")
    async def healthz() -> Dict[str, Any]:
        last = int(pipeline.store.kv_get("last_tick_ms", "0") or 0)
        return {"ok": True, "last_tick_age_s": (pipeline.now_ms() - last) // 1000 if last else None}

    @app.post("/v1/ingest")
    async def ingest(request: Request):
        device, body = await authed(request)
        return await run_in_threadpool(pipeline.handle_ingest, device, jsonbody(body))

    @app.post("/v1/heartbeat")
    async def heartbeat(request: Request):
        device, body = await authed(request)
        return await run_in_threadpool(pipeline.handle_heartbeat, device, jsonbody(body))

    @app.post("/v1/reconcile")
    async def reconcile(request: Request):
        device, body = await authed(request)
        return await run_in_threadpool(pipeline.handle_reconcile, device, jsonbody(body))

    @app.post("/v1/mark")
    async def mark(request: Request):
        device, body = await authed(request)
        d = jsonbody(body)
        return await run_in_threadpool(pipeline.apply_mark, str(d.get("address") or ""), str(d.get("verdict") or ""),
                                       d.get("uid"), "michael")

    @app.get("/v1/policy")
    async def policy(request: Request):
        await authed(request)
        return pipeline.policy().to_dict()

    @app.put("/v1/media/{uid}/{sha}")
    async def media(uid: str, sha: str, request: Request):
        _dev, data = await authed(request, MAX_MEDIA)
        try:
            await run_in_threadpool(pipeline.accept_media, uid, sha, data)
        except ValueError as e:
            return JSONResponse({"ok": False, "reason": str(e)}, status_code=409 if str(e) == "hash_mismatch" else 404)
        return {"ok": True}

    # ------------------------------------------------------------------ office UI
    def ui_auth(request: Request) -> None:
        tok = settings.ui_token
        if not tok:
            raise HTTPException(status_code=403, detail="ui_disabled")
        got = request.headers.get("x-ui-token") or request.headers.get("authorization", "").removeprefix("Bearer ")
        if not hmac.compare_digest(got.encode("utf-8"), tok.encode("utf-8")):
            raise HTTPException(status_code=401, detail="bad_token")

    @app.get("/ui")
    async def ui_page():
        return FileResponse(UI_FILE, media_type="text/html")

    @app.get("/ui/manifest.webmanifest")
    async def ui_manifest():
        return FileResponse(UI_FILE.parent / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/ui/icon-{size}.png")
    async def ui_icon(size: int):
        if size not in (192, 512):
            raise HTTPException(status_code=404)
        return FileResponse(UI_FILE.parent / f"icon-{size}.png", media_type="image/png")

    @app.get("/ui/api/state")
    async def ui_state(request: Request, since: int = 0):
        ui_auth(request)
        return {
            "now_ms": pipeline.now_ms(), "feed": pipeline.feed_view(since_ms=since),
            "queue": pipeline.queue_view(), "sla": pipeline.sla_view(),
            "filed": pipeline.filed_view(20), "health": pipeline.health_view(), "jobs": pipeline.jobs_view(),
        }

    @app.post("/ui/api/assign")
    async def ui_assign(request: Request):
        ui_auth(request)
        d = await request.json()
        try:
            return await run_in_threadpool(pipeline.resolve_queue, d["address"], "assign", d.get("job_no"), "ryan")
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/ui/api/private")
    async def ui_private(request: Request):
        ui_auth(request)
        d = await request.json()
        return await run_in_threadpool(pipeline.resolve_queue, d.get("address", ""), "private", None, "ryan")

    @app.post("/ui/api/handled")
    async def ui_handled(request: Request):
        ui_auth(request)
        d = await request.json()
        await run_in_threadpool(pipeline.sla_handled, d.get("uid", ""))
        return {"ok": True}

    @app.post("/ui/api/refile")
    async def ui_refile(request: Request):
        ui_auth(request)
        d = await request.json()
        try:
            return await run_in_threadpool(pipeline.refile, d["uid"], d["job_no"])
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/ui/api/role")
    async def ui_role(request: Request):
        ui_auth(request)
        d = await request.json()
        try:
            await run_in_threadpool(pipeline.set_role, d["address"], d["role"], d.get("name", ""))
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True}

    return app
