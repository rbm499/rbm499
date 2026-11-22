import json

from fastapi.testclient import TestClient

from commscap.api import create_app

from conftest import LUIS, STRANGER, TONY, PERSON, mk, outbox_text


def ingest(env, *msgs):
    return env.pipeline.handle_ingest("dev-1", {"messages": list(msgs)})


def test_feed_is_a_dialogue_of_business_texts_in_and_out(env):
    env.screener.when("invoice", category="job_business", confidence=0.9, needs_reply=True, reply_urgency="normal", topics=["invoice_payment"])
    env.screener.when("sending", category="job_business", confidence=0.9)
    first = mk("dev-1", "in", TONY, env.clock.ms(), "Can you resend the invoice?")
    ingest(env, first)
    f = env.pipeline.feed_view()
    assert f["threads"][0]["waiting_ms"] is not None  # unanswered: the thread says so
    env.clock.advance(minutes=10)
    ingest(env, mk("dev-1", "out", TONY, env.clock.ms(), "Sending it now"))
    t = env.pipeline.feed_view()["threads"][0]
    assert [m["dir"] for m in t["messages"]] == ["in", "out"]  # reads oldest to newest, like a conversation
    assert t["job_no"] == "26-4708" and t["last_dir"] == "out" and t["waiting_ms"] is None  # answered
    assert t["name"] == "Tony Park" and t["role"] == "client"


def test_newest_conversation_first_and_per_thread_limit(env):
    env.screener.when("hello", category="job_business", confidence=0.9)
    ingest(env, mk("dev-1", "in", TONY, env.clock.ms(), "hello one"))
    env.clock.advance(minutes=5)
    for i in range(15):
        env.clock.advance(minutes=1)
        ingest(env, mk("dev-1", "in", LUIS, env.clock.ms(), f"hello {i}"))
    f = env.pipeline.feed_view(per_thread=12)
    assert [t["address"] for t in f["threads"]] == [LUIS, TONY]
    assert len(f["threads"][0]["messages"]) == 12 and f["threads"][0]["messages"][-1]["text"] == "hello 14"


def test_feed_never_shows_unscreened_dropped_or_held_texts_and_masks_sensitive(env):
    env.screener.when("dinner", category="personal", confidence=0.95)
    env.screener.when("hmm", category="unclear", confidence=0.3)
    env.screener.when("passed away", category="job_business", confidence=0.9, sensitive_content=True)
    env.screener.down = "api_error:X"
    ingest(env, mk("dev-1", "in", STRANGER, env.clock.ms(), "need a bid for my house"))  # AI down -> pending, unseen
    env.screener.down = None
    ingest(env, mk("dev-1", "in", PERSON, env.clock.ms() + 1, "bid you a dinner"))          # personal -> dropped
    ingest(env, mk("dev-1", "in", "+12065550166", env.clock.ms() + 2, "hmm"))               # unclear unknown -> held unseen
    ingest(env, mk("dev-1", "in", LUIS, env.clock.ms() + 3, "My mother passed away, can we move the survey?"))
    blob = json.dumps(env.pipeline.feed_view())
    for secret in ("need a bid for my house", "dinner", "hmm", "passed away"):
        assert secret not in blob
    assert "hidden: sensitive" in blob  # the business thread is there, its text is not


def test_new_count_since_last_look(env):
    env.screener.when("hello", category="job_business", confidence=0.9)
    ingest(env, mk("dev-1", "in", TONY, env.clock.ms(), "hello a"))
    looked = env.clock.ms() + 1
    env.clock.advance(minutes=3)
    ingest(env, mk("dev-1", "in", TONY, env.clock.ms(), "hello b"))
    assert env.pipeline.feed_view(since_ms=0)["new_count"] == 2
    assert env.pipeline.feed_view(since_ms=looked)["new_count"] == 1


def test_each_message_alert_is_opt_in_and_never_contains_the_text(env):
    env.screener.when("canarytext", category="job_business", confidence=0.9, topics=["schedule"])
    ingest(env, mk("dev-1", "in", TONY, env.clock.ms(), "canarytext one"))
    assert "Client text" not in outbox_text(env)  # off by default: no noise
    env.settings.alert_each_message = True
    env.clock.advance(minutes=1)
    ingest(env, mk("dev-1", "in", TONY, env.clock.ms(), "canarytext two"))
    env.clock.advance(minutes=1)
    ingest(env, mk("dev-1", "out", TONY, env.clock.ms(), "canarytext three"))
    text = outbox_text(env)
    assert "Client text from Tony Park" in text and "Client text to Tony Park" in text
    assert "filed to job 26-4708" in text and "canarytext" not in text


def test_feed_export_for_another_viewer_is_written_without_hidden_text(env):
    env.settings.feed_export_path = env.tmp / "drive" / "feed.json"
    env.screener.when("passed away", category="job_business", confidence=0.9, sensitive_content=True)
    env.screener.when("hello", category="job_business", confidence=0.9)
    ingest(env, mk("dev-1", "in", TONY, env.clock.ms(), "hello there"))
    ingest(env, mk("dev-1", "in", LUIS, env.clock.ms() + 1, "my mother passed away, can we move the survey"))
    data = json.loads(env.settings.feed_export_path.read_text(encoding="utf-8"))
    assert {t["name"] for t in data["threads"]} == {"Tony Park", "Luis Ortega"} and data["generated_ms"]
    assert "passed away" not in json.dumps(data) and "hello there" in json.dumps(data)
    assert not list(env.settings.feed_export_path.parent.glob("*.tmp"))  # written atomically


def test_feed_export_failure_never_breaks_capture(env):
    (env.tmp / "blocker").write_text("a file, not a folder")
    env.settings.feed_export_path = env.tmp / "blocker" / "feed.json"
    env.screener.when("hello", category="job_business", confidence=0.9)
    m = mk("dev-1", "in", TONY, env.clock.ms(), "hello")
    assert ingest(env, m)["accepted"] == [m["uid"]]


def test_page_is_installable_and_state_carries_the_feed(env):
    c = TestClient(create_app(env.pipeline, env.settings, tick_seconds=None))
    man = c.get("/ui/manifest.webmanifest")
    assert man.status_code == 200 and man.json()["start_url"] == "/ui" and man.json()["display"] == "standalone"
    icon = c.get("/ui/icon-192.png")
    assert icon.status_code == 200 and icon.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert c.get("/ui/icon-300.png").status_code == 404
    assert "Live conversations" in c.get("/ui").text
    env.screener.when("hello", category="job_business", confidence=0.9)
    ingest(env, mk("dev-1", "in", TONY, env.clock.ms(), "hello"))
    st = c.get("/ui/api/state?since=0", headers={"X-UI-Token": "ui-token"}).json()
    assert len(st["feed"]["threads"]) == 1 and st["feed"]["new_count"] == 1
