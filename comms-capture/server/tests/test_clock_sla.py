from datetime import datetime

from commscap.clock import BusinessClock
from commscap.config import Settings

from conftest import LUIS, PT, TONY, mk, outbox_text


def ms(dt):
    return int(dt.timestamp() * 1000)


def test_business_clock_skips_nights_and_sunday():
    c = BusinessClock(Settings())
    mon_10 = ms(datetime(2026, 11, 23, 10, 0, tzinfo=PT))
    assert c.add_business_minutes(mon_10, 120) == ms(datetime(2026, 11, 23, 12, 0, tzinfo=PT))
    # 9 PM Monday: clock starts Tuesday 07:00
    assert c.add_business_minutes(ms(datetime(2026, 11, 23, 21, 0, tzinfo=PT)), 120) == ms(datetime(2026, 11, 24, 9, 0, tzinfo=PT))
    # Saturday 6 PM + 120 min spills over Sunday (closed) to Monday morning
    sat = ms(datetime(2026, 11, 21, 18, 0, tzinfo=PT))
    got = c.to_dt(c.add_business_minutes(sat, 120))
    assert (got.weekday(), got.hour, got.minute) == (0, 8, 0)  # 60 min Sat evening + 60 min Monday from 07:00
    assert not c.is_open(ms(datetime(2026, 11, 22, 12, 0, tzinfo=PT)))  # Sunday


def question(env, uid_body="can you send the bid today?", address=TONY):
    env.screener.when("can you", category="job_business", confidence=0.95, needs_reply=True, reply_urgency="normal", topics=["bid_request"])
    env.screener.when("flooding", category="job_business", confidence=0.95, needs_reply=True, reply_urgency="high", topics=["safety_urgent"])
    m = mk("dev-1", "in", address, env.clock.ms(), uid_body)
    env.pipeline.handle_ingest("dev-1", {"messages": [m]})
    return m


def test_reply_ladder_and_resolution_by_outbound(env):
    question(env)
    p = env.pipeline
    assert len(env.store.sla_open()) == 1
    env.clock.advance(minutes=121)
    p.tick()
    nudges = env.store.pending_nudges("dev-1")
    assert len(nudges) == 1 and nudges[0]["level"] == 1 and "Tony Park" in nudges[0]["title"]
    env.clock.advance(minutes=120)  # 4h
    p.tick()
    assert "Client waiting: Tony Park" in outbox_text(env)
    # Michael replies by text: everything resolves and alerts stop
    reply = mk("dev-1", "out", TONY, env.clock.ms(), "Sending it now, give me 20 min")
    env.screener.when("sending it now", category="job_business", confidence=0.9)
    p.handle_ingest("dev-1", {"messages": [reply]})
    assert env.store.sla_open() == []
    env.clock.advance(hours=9)
    p.tick()
    text = outbox_text(env)
    assert "OVERDUE" not in text and "STILL" not in text  # replying stopped the ladder (the daily digest may still send)
    assert env.store.pending_nudges("dev-1") == []  # reminders already queued for the phone were withdrawn on reply


def test_overdue_alert_repeats_until_handled(env):
    question(env)
    env.clock.advance(minutes=9 * 60)
    env.pipeline.tick()
    assert "OVERDUE reply: Tony Park" in outbox_text(env)
    env.clock.advance(hours=13)
    env.pipeline.tick()
    assert "STILL OVERDUE" in outbox_text(env)
    uid = env.store.sla_open()[0]["uid"]
    env.pipeline.sla_handled(uid)
    assert env.store.sla_open() == []


def test_urgent_message_alerts_immediately_on_wall_clock(env):
    env.clock.advance(hours=11)  # 9 PM Monday, office closed
    question(env, "Water is flooding the containment, please come now", address=LUIS)
    env.pipeline.tick()
    assert "URGENT client message" in outbox_text(env)
    assert env.store.pending_nudges("dev-1")[0]["title"].startswith("URGENT")
    assert all(not a["key"].startswith("sla") for a in env.pipeline.health_view()["alerts"])  # health panel = capture health only


def test_after_hours_message_is_not_late_at_night(env):
    env.clock.advance(hours=11)  # 9 PM
    question(env)
    env.clock.advance(minutes=30)
    env.pipeline.tick()
    assert env.store.pending_nudges("dev-1") == []  # clock starts at 07:00 tomorrow


def test_unmatched_job_still_starts_the_reply_clock(env):
    question(env, address=LUIS)  # Luis has 3 jobs -> queued, no job number yet
    assert env.store.sla_open()[0]["job_no"] is None
    env.clock.advance(minutes=130)
    env.pipeline.tick()
    assert "no job number yet" in env.store.pending_nudges("dev-1")[0]["text"]


def test_unacked_nudge_escalates_when_phone_is_online(env):
    question(env)
    p = env.pipeline
    env.clock.advance(minutes=121)
    p.tick()
    p.handle_heartbeat("dev-1", {"ts_ms": env.clock.ms(), "permissions": {}, "queue_depth": 0})  # delivers, no ack yet
    env.clock.advance(minutes=31)
    p.handle_heartbeat("dev-1", {"ts_ms": env.clock.ms(), "permissions": {}, "queue_depth": 0})  # still online, still no ack
    p.tick()
    assert "Reminder not shown on Michael's phone" in outbox_text(env)
