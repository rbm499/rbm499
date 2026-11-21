from datetime import datetime

from conftest import PT, TONY, mk, outbox_text

PERMS = {"sms": True, "contacts": True, "notification_listener": True, "battery_unrestricted": True, "post_notifications": True}


def hb(env, **kw):
    payload = {"ts_ms": env.clock.ms(), "permissions": dict(PERMS), "queue_depth": 0, "oldest_queued_ms": None,
               "capture_paused_until_ms": None}
    payload.update(kw)
    return env.pipeline.handle_heartbeat("dev-1", payload)


def keys(env):
    return {a["key"] for a in env.store.active_alerts("health:")}


def test_phone_never_seen(env):
    env.clock.advance(hours=3)
    env.pipeline.tick()
    assert "health:never-seen:dev-1" in keys(env)
    assert "never checked in" in outbox_text(env)


def test_heartbeat_gap_alerts_then_clears_when_phone_returns(env):
    hb(env)
    env.clock.advance(minutes=50)  # business hours: limit 45 min
    env.pipeline.tick()
    assert "health:hb-gap:dev-1" in keys(env)
    hb(env)
    env.pipeline.tick()
    assert "health:hb-gap:dev-1" not in keys(env)


def test_overnight_gap_is_tolerated_up_to_three_hours(env):
    env.clock.advance(hours=11)  # 9 PM, office closed
    hb(env)
    env.clock.advance(minutes=120)
    env.pipeline.tick()
    assert "health:hb-gap:dev-1" not in keys(env)
    env.clock.advance(minutes=70)
    env.pipeline.tick()
    assert "health:hb-gap:dev-1" in keys(env)


def test_revoked_sms_permission_is_critical(env):
    hb(env, permissions={**PERMS, "sms": False})
    env.pipeline.tick()
    assert "health:perm:dev-1:sms" in keys(env)
    assert "[CRITICAL]" in outbox_text(env)
    hb(env)
    env.pipeline.tick()
    assert "health:perm:dev-1:sms" not in keys(env)


def test_phone_online_but_upload_queue_stuck(env):
    hb(env, queue_depth=4, oldest_queued_ms=env.clock.ms() - 90 * 60_000)
    env.pipeline.tick()
    assert "health:queue-stuck:dev-1" in keys(env)


def test_long_pause_is_reported(env):
    hb(env, capture_paused_until_ms=env.clock.ms() + 10 * 3600_000)
    env.pipeline.tick()
    assert "health:paused:dev-1" in keys(env)


def test_clock_skew_flagged(env):
    hb(env, ts_ms=env.clock.ms() - 600_000)
    env.pipeline.tick()
    assert "health:skew:dev-1" in keys(env)


def test_reconcile_overdue_after_first_day(env):
    hb(env)
    for _ in range(14):  # keep the phone "alive" for two days without ever reconciling
        env.clock.advance(hours=4)
        hb(env)
    env.pipeline.tick()
    assert "health:reconcile-overdue:dev-1" in keys(env)
    env.pipeline.handle_reconcile("dev-1", {"expected_uids": []})
    env.pipeline.tick()
    assert "health:reconcile-overdue:dev-1" not in keys(env)


def test_review_queue_ageing_alert_only_in_business_hours(env):
    env.screener.when("hello", category="job_business", confidence=0.9)
    from conftest import LUIS
    env.pipeline.handle_ingest("dev-1", {"messages": [mk("dev-1", "in", LUIS, env.clock.ms(), "hello")]})
    hb(env)
    env.clock.advance(minutes=250)
    hb(env)
    env.pipeline.tick()
    assert "health:review-queue" in keys(env)


def test_daily_digest_once_a_day_and_never_contains_message_text(env):
    env.screener.when("canary", category="job_business", confidence=0.9, needs_reply=True, reply_urgency="normal", topics=["schedule"])
    env.pipeline.handle_ingest("dev-1", {"messages": [mk("dev-1", "in", TONY, env.clock.ms(), "canarybody123 can you call")]})
    hb(env)
    env.clock.advance(hours=9, minutes=5)  # 7:05 PM
    hb(env)
    env.pipeline.tick()
    text = outbox_text(env)
    assert "Daily text-capture summary 2026-11-23" in text and "Texts filed to job folders (24h): 1" in text
    assert "canarybody123" not in text
    n = text.count("Daily text-capture summary")
    hb(env)
    env.pipeline.tick()
    assert outbox_text(env).count("Daily text-capture summary") == n  # not repeated the same day
    env.clock.advance(days=1)
    hb(env)
    env.pipeline.tick()
    assert outbox_text(env).count("Daily text-capture summary") == n + 1


def test_stale_register_is_flagged_and_clears_after_refresh(env):
    env.clock.advance(days=10)  # register says generated 2026-11-21; clock is now 2026-12-03
    hb(env)
    env.pipeline.tick()
    assert "health:register-stale" in keys(env)
    import json
    fresh = {**__import__("conftest").REGISTER, "generated": "2026-12-03T00:00:00Z"}
    p = env.tmp / "register.json"
    p.write_text(json.dumps(fresh))
    env.settings.register_path = p
    hb(env)
    env.pipeline.tick()  # picks the file up without a restart
    assert "health:register-stale" not in keys(env)


def test_register_reload_adds_new_clients_and_survives_a_broken_file(env):
    import json
    from conftest import REGISTER, mk
    newcomer = {"job_no": "26-9999", "site": "9999 Alder St, Seattle", "client": "New Co", "stage": "opened",
                "contact": {"name": "Nora New", "phone": "(206) 555-0166"}}
    p = env.tmp / "register.json"
    p.write_text(json.dumps({**REGISTER, "jobs": REGISTER["jobs"] + [newcomer]}))
    env.settings.register_path = p
    assert "+12065550166" not in env.pipeline.policy().numbers
    assert env.pipeline.reload_register_if_changed() is True
    assert env.pipeline.policy().numbers["+12065550166"] == "client"
    n_before = len(env.pipeline.reg.jobs)
    import os, time
    p.write_text("{ not json")
    os.utime(p, (time.time() + 5, time.time() + 5))
    assert env.pipeline.reload_register_if_changed() is False
    assert len(env.pipeline.reg.jobs) == n_before  # kept the last good register
    hb(env)
    env.pipeline.tick()
    assert "health:register-load-failed" in keys(env)


def test_no_register_at_all_is_critical(env):
    from commscap.register import Register
    env.pipeline.reg = Register([])
    env.pipeline._record_register_state()
    hb(env)
    env.pipeline.tick()
    assert "health:register-empty" in keys(env)
