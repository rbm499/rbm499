import json
import time

from fastapi.testclient import TestClient

from commscap.api import create_app
from commscap.cli import build_pipeline, main
from commscap.config import Settings

from conftest import REGISTER


def test_background_loop_runs_the_tick(env):
    with TestClient(create_app(env.pipeline, env.settings, tick_seconds=0.05)) as c:
        time.sleep(0.4)
        assert c.get("/healthz").json()["last_tick_age_s"] is not None  # the loop ran and recorded itself


def test_background_loop_survives_a_failing_tick(env, monkeypatch):
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        raise RuntimeError("disk full")

    monkeypatch.setattr(env.pipeline, "tick", boom)
    with TestClient(create_app(env.pipeline, env.settings, tick_seconds=0.05)):
        time.sleep(0.4)
    assert calls["n"] >= 2  # kept trying after the first exception


def test_settings_from_env():
    s = Settings.from_env({"COMMSCAP_DEVICE_SECRETS": "a:b,c:d", "COMMSCAP_UI_TOKEN": "t", "ANTHROPIC_API_KEY": "k",
                           "COMMSCAP_MODEL": "claude-haiku-5-5", "COMMSCAP_ALERT_EMAIL_TO": "x@example.com, y@example.com"})
    assert s.device_secrets == {"a": "b", "c": "d"} and s.ai_enabled and s.model == "claude-haiku-5-5"
    assert s.alert_email_to == ["x@example.com", "y@example.com"]
    assert not Settings.from_env({}).ai_enabled  # no key -> heuristic only
    assert not Settings.from_env({"ANTHROPIC_API_KEY": "k", "COMMSCAP_AI": "off"}).ai_enabled
    assert Settings.from_env({}).model == "claude-opus-5-5"


def test_cli_register_stats_and_new_secret(tmp_path, monkeypatch, capsys):
    reg = tmp_path / "reg.json"
    reg.write_text(json.dumps(REGISTER))
    monkeypatch.setenv("COMMSCAP_REGISTER", str(reg))
    monkeypatch.setenv("COMMSCAP_DATA_DIR", str(tmp_path / "d"))
    assert main(["register-stats"]) == 0
    out = capsys.readouterr().out
    assert "jobs: 7" in out and "distinct client numbers" in out
    assert "206" not in out  # aggregate output must never print a phone number
    assert main(["new-secret", "--device", "dev-x", "--url", "https://h.example"]) == 0
    out = capsys.readouterr().out
    assert "COMMSCAP_DEVICE_SECRETS=dev-x:" in out and "commscap://setup?url=https://h.example&device=dev-x&secret=" in out


def test_serve_refuses_to_start_without_a_device_secret(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("COMMSCAP_DEVICE_SECRETS", raising=False)
    monkeypatch.setenv("COMMSCAP_DATA_DIR", str(tmp_path / "d"))
    assert main(["serve"]) == 2
    assert "refusing to start" in capsys.readouterr().err
