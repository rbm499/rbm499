import json

import pytest

from commscap.screen import ScreenResult

from conftest import FELICIA, LUIS, PERSON, STRANGER, TONY, mk, outbox_text, transcript


def ingest(env, *msgs, device="dev-1"):
    return env.pipeline.handle_ingest(device, {"messages": list(msgs)})


def test_known_single_job_client_is_filed_automatically(env):
    env.screener.when("invoice", category="job_business", confidence=0.95, needs_reply=True, reply_urgency="normal",
                      topics=["invoice_payment"], summary="invoice request")
    m = mk("dev-1", "in", TONY, env.clock.ms(), "Can you resend the invoice for 4708?")
    r = ingest(env, m)
    assert r["accepted"] == [m["uid"]] and r["rejected"] == []
    row = env.store.get_message(m["uid"])
    assert (row["state"], row["job_no"], row["assoc_method"]) == ("filed", "26-4708", "only_job_for_contact")
    t = transcript(env, "26-4708 1021")
    assert "Can you resend the invoice" in t and "INFERRED screening (fake)" in t and "RECEIVED" in t
    assert (env.jobs_root / "26-4708 1021" / "Communications" / ".comms_ledger.jsonl").exists()
    assert len(env.store.sla_open()) == 1


def test_multi_job_client_queued_then_assigned_then_continuity(env):
    env.screener.when("start", category="job_business", confidence=0.9, needs_reply=True, reply_urgency="normal", topics=["schedule"])
    env.screener.when("ok sounds", category="job_business", confidence=0.9)
    m1 = mk("dev-1", "in", LUIS, env.clock.ms(), "Can we move the start date?")
    ingest(env, m1)
    assert env.store.get_message(m1["uid"])["state"] == "queued"
    view = env.pipeline.queue_view()
    assert len(view) == 1 and {c["job_no"] for c in view[0]["candidates"]} == {"26-6527", "26-8607", "26-2134"}
    assert env.pipeline.resolve_queue(LUIS, "assign", "26-6527")["filed"] == 1
    assert env.store.get_message(m1["uid"])["state"] == "filed"
    assert env.store.sla_open()[0]["job_no"] == "26-6527"
    env.clock.advance(minutes=30)
    m2 = mk("dev-1", "in", LUIS, env.clock.ms(), "ok sounds good")
    ingest(env, m2)
    assert env.store.get_message(m2["uid"])["job_no"] == "26-6527"  # same conversation, a human chose the job
    assert env.store.get_message(m2["uid"])["assoc_method"] == "thread_continuity"
    assert env.pipeline.queue_view() == []


def test_job_without_folder_goes_to_unfiled_and_alerts(env):
    env.screener.when("26-2134", category="job_business", confidence=0.9)
    m = mk("dev-1", "in", LUIS, env.clock.ms(), "thanks, the 26-2134 report looks right")
    ingest(env, m)
    row = env.store.get_message(m["uid"])
    assert row["state"] == "filed" and "_COMMS_UNFILED" in row["filed_path"]
    assert not any(p.name.startswith("26-2134") for p in env.jobs_root.iterdir() if p.name != "_COMMS_UNFILED")  # no invented folder
    env.pipeline.tick()
    assert "filed in _COMMS_UNFILED" in outbox_text(env)


def test_unknown_lead_queued_and_thread_becomes_business(env):
    env.screener.when("asbestos", category="new_lead", confidence=0.9, needs_reply=True, reply_urgency="normal", topics=["new_inquiry"])
    m = mk("dev-1", "in", STRANGER, env.clock.ms(), "Hi, I need an asbestos survey before we remodel, how much?")
    r = ingest(env, m)
    assert env.store.get_message(m["uid"])["state"] == "queued"
    assert {"address": STRANGER, "verdict": "business"} in r["thread_verdicts"]
    assert STRANGER in env.pipeline.policy().provisional_business
    # the rest of the thread now passes the gate on the phone AND on the server
    from commscap.gate import decide
    d = decide(env.pipeline.policy(), STRANGER, "ok sounds good")
    assert (d.decision, d.reason) == ("send", "thread_business")  # not merely "unsaved": the thread is now known business
    assert env.pipeline.queue_view()[0]["role"] == "unknown"


def test_private_text_from_unknown_number_leaves_nothing_behind(env):
    env.screener.when("dinner", category="personal", confidence=0.93)
    env.screener.when("also", category="personal", confidence=0.9)
    first = mk("dev-1", "in", PERSON, env.clock.ms() - 5000, "I'd bid you a dinner at 7?")  # passed the phone gate on 'bid'
    r = ingest(env, first)
    assert r["accepted"] == [first["uid"]]
    assert env.store.get_message(first["uid"]) is None  # row deleted
    assert env.store.get_number(PERSON)["status"] == "excluded"
    assert PERSON in env.pipeline.policy().exclude_numbers
    # no body is retained anywhere in the database
    dump = json.dumps(env.store.q("SELECT * FROM audit") + env.store.q("SELECT * FROM numbers") + env.store.q("SELECT * FROM seen_uids"))
    assert "dinner" not in dump
    assert env.store.audit_counts(0).get("dropped") == 1
    # re-sent copy is acknowledged (so the phone deletes it) but never stored
    again = ingest(env, first)
    assert again["duplicates"] == [first["uid"]]
    # any later message from that number is rejected by the server gate
    later = mk("dev-1", "in", PERSON, env.clock.ms(), "also a bid on the cat?")
    assert ingest(env, later)["rejected"] == [{"uid": later["uid"], "reason": "server_gate_drop"}]
    # nightly reconcile must not resurrect it
    rec = env.pipeline.handle_reconcile("dev-1", {"expected_uids": [first["uid"], later["uid"]]})
    assert rec["missing"] == []


def test_ai_outage_known_clients_flow_unknown_numbers_wait(env):
    env.screener.down = "api_error:APIConnectionError"
    client = mk("dev-1", "in", TONY, env.clock.ms(), "Can you call me about the invoice? thanks")
    stranger = mk("dev-1", "in", STRANGER, env.clock.ms() + 1, "need a bid for my house")
    ingest(env, client, stranger)
    c = env.store.get_message(client["uid"])
    assert c["state"] == "filed" and c["engine"] == "heuristic" and c["job_no"] == "26-4708"
    assert env.store.get_message(stranger["uid"])["state"] == "pending_ai"
    assert env.pipeline.queue_view() == []  # unscreened text is never shown
    env.clock.advance(minutes=35)
    env.pipeline.tick()
    assert "Messages waiting for screening" in outbox_text(env)
    # AI returns: the held text is screened on the next tick
    env.screener.down = None
    env.screener.when("bid", category="new_lead", confidence=0.9, needs_reply=True, reply_urgency="normal", topics=["bid_request"])
    env.pipeline.tick()
    assert env.store.get_message(stranger["uid"])["state"] == "queued"
    assert not any("ai-backlog" in a["key"] for a in env.store.active_alerts("health:"))


def test_sensitive_aside_in_business_text_is_filed_but_hidden(env):
    env.screener.when("passed away", category="job_business", confidence=0.9, sensitive_content=True, sensitive_kinds=["family"],
                      needs_reply=True, reply_urgency="normal", topics=["schedule"])
    m = mk("dev-1", "in", LUIS, env.clock.ms(), "My mother passed away, can we move the survey a week?")
    ingest(env, m)
    view = env.pipeline.queue_view()
    assert "passed away" not in json.dumps(view) and "hidden" in view[0]["messages"][0]["text"]
    env.pipeline.tick()
    env.clock.advance(hours=10)
    env.pipeline.tick()
    assert "passed away" not in outbox_text(env)  # alerts carry topic only, never text


def test_sensitive_policy_drop_mode(env):
    env.settings.sensitive_business_policy = "drop"
    env.screener.when("passed away", category="job_business", confidence=0.9, sensitive_content=True)
    m = mk("dev-1", "in", LUIS, env.clock.ms(), "My mother passed away, can we move the survey?")
    ingest(env, m)
    assert env.store.get_message(m["uid"]) is None


def test_ingest_is_idempotent_and_validates(env):
    env.screener.when("hello", category="job_business", confidence=0.9)
    m = mk("dev-1", "in", TONY, env.clock.ms(), "hello about the job")
    assert ingest(env, m)["accepted"] == [m["uid"]]
    assert ingest(env, m)["duplicates"] == [m["uid"]]
    bad = ingest(env, {"uid": "nothex", "direction": "in", "ts_ms": 1, "address": TONY})
    assert bad["rejected"] == [{"uid": "nothex", "reason": "bad_schema"}]


def test_server_regate_rejects_what_the_phone_should_not_have_sent(env):
    otp = mk("dev-1", "in", STRANGER, env.clock.ms(), "Your verification code is 483920")
    chase = mk("dev-1", "in", "CHASE", env.clock.ms(), "Your invoice is ready")
    r = ingest(env, otp, chase)
    assert {x["reason"] for x in r["rejected"]} == {"server_gate_drop"} and len(r["rejected"]) == 2
    assert env.store.q("SELECT COUNT(*) AS n FROM messages")[0]["n"] == 0


def test_server_redacts_again_before_storing(env):
    env.screener.when("card", category="job_business", confidence=0.9)
    m = mk("dev-1", "in", TONY, env.clock.ms(), "paying the invoice, card 4111 1111 1111 1111")
    ingest(env, m)
    row = env.store.get_message(m["uid"])
    assert "4111" not in row["body"] and "[REDACTED:card]" in row["body"]
    assert "4111" not in transcript(env, "26-4708 1021")


def test_uid_mismatch_is_counted_not_dropped(env):
    env.screener.when("hello", category="job_business", confidence=0.9)
    m = mk("dev-1", "in", TONY, env.clock.ms(), "hello again")
    m["uid"] = "a" * 64
    assert ingest(env, m)["accepted"] == ["a" * 64]
    env.pipeline.tick()
    assert "did not match between phone and office" in outbox_text(env)


def test_reconcile_reports_only_what_is_missing(env):
    env.screener.when("hello", category="job_business", confidence=0.9)
    m = mk("dev-1", "in", TONY, env.clock.ms(), "hello")
    ingest(env, m)
    r = env.pipeline.handle_reconcile("dev-1", {"expected_uids": [m["uid"], "b" * 64]})
    assert r["missing"] == ["b" * 64] and r["known"] == 1


def test_filing_failure_is_retried(env, monkeypatch):
    env.screener.when("hello", category="job_business", confidence=0.9)
    real = env.pipeline.filer.file_message
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("drive offline")
        return real(*a, **k)

    monkeypatch.setattr(env.pipeline.filer, "file_message", flaky)
    m = mk("dev-1", "in", TONY, env.clock.ms(), "hello")
    ingest(env, m)
    assert env.store.get_message(m["uid"])["state"] == "file_failed"
    env.clock.advance(minutes=61)
    env.pipeline.tick()
    assert "could not be filed" in outbox_text(env) or env.store.get_message(m["uid"])["state"] == "filed"
    assert env.store.get_message(m["uid"])["state"] == "filed"


def test_media_is_requested_only_after_screening_and_filed_into_job(env):
    env.screener.when("photo", category="job_business", confidence=0.9)
    sha = "c" * 64
    data = b"fake-jpeg-bytes"
    import hashlib
    sha = hashlib.sha256(data).hexdigest()
    m = mk("dev-1", "in", TONY, env.clock.ms(), "photo of the ceiling", media=[{"mime": "image/jpeg", "size": len(data), "sha256": sha}])
    r = ingest(env, m)
    assert r["media_wanted"] == [{"uid": m["uid"], "sha256": sha}]
    with pytest.raises(ValueError):
        env.pipeline.accept_media(m["uid"], sha, b"tampered")
    env.pipeline.accept_media(m["uid"], sha, data)
    files = list((env.jobs_root / "26-4708 1021" / "Communications" / "media").glob("*.jpg"))
    assert len(files) == 1 and files[0].read_bytes() == data
    assert "attachment for message" in transcript(env, "26-4708 1021")
    assert env.pipeline.all_media_wanted() == []


def test_media_not_requested_for_dropped_message(env):
    env.screener.when("selfie", category="personal", confidence=0.95)
    sha = "d" * 64
    m = mk("dev-1", "in", PERSON, env.clock.ms(), "bid on my selfie", media=[{"mime": "image/jpeg", "size": 10, "sha256": sha}])
    r = ingest(env, m)
    assert r["media_wanted"] == []


def test_mark_private_purges_and_excludes_but_never_a_register_client(env):
    env.screener.when("asbestos", category="new_lead", confidence=0.9)
    m = mk("dev-1", "in", STRANGER, env.clock.ms(), "asbestos survey please")
    ingest(env, m)
    assert env.pipeline.apply_mark(STRANGER, "private")["ok"]
    assert env.store.get_message(m["uid"]) is None and STRANGER in env.pipeline.policy().exclude_numbers
    # a register client: refuse wholesale exclusion; purge only the named message
    env.screener.when("hello", category="job_business", confidence=0.9)
    c = mk("dev-1", "in", TONY, env.clock.ms(), "hello")
    ingest(env, c)
    assert env.pipeline.apply_mark(TONY, "private")["ok"] is False
    assert env.pipeline.apply_mark(TONY, "private", uid=c["uid"])["note"] == "client_number_kept"
    assert env.store.get_message(c["uid"]) is None and TONY not in env.pipeline.policy().exclude_numbers


def test_unclear_unknown_is_held_then_promoted_when_thread_turns_business(env):
    env.screener.when("hmm", category="unclear", confidence=0.3)
    env.screener.when("bid", category="new_lead", confidence=0.9, needs_reply=True, reply_urgency="normal", topics=["bid_request"])
    first = mk("dev-1", "in", STRANGER, env.clock.ms(), "hmm")
    ingest(env, first)
    assert env.store.get_message(first["uid"])["state"] == "held" and env.pipeline.queue_view() == []
    env.clock.advance(minutes=5)
    second = mk("dev-1", "in", STRANGER, env.clock.ms(), "can you bid my roof tear-off?")
    ingest(env, second)
    states = {r["uid"]: r["state"] for r in env.store.q("SELECT uid,state FROM messages")}
    assert states[second["uid"]] == "queued"
    assert states[first["uid"]] in ("queued", "held")  # re-screened with the thread; scripted AI still calls it unclear


def test_held_text_expires_without_trace(env):
    env.screener.when("hmm", category="unclear", confidence=0.3)
    m = mk("dev-1", "in", STRANGER, env.clock.ms(), "hmm secretcanary")
    ingest(env, m)
    env.clock.advance(hours=73)
    env.pipeline.tick()
    assert env.store.get_message(m["uid"]) is None
    assert "secretcanary" not in json.dumps(env.store.q("SELECT * FROM audit"))


def test_refile_corrects_wrong_job_without_rewriting_history(env):
    env.screener.when("hello", category="job_business", confidence=0.9)
    m = mk("dev-1", "in", LUIS, env.clock.ms(), "hello re 26-6527")
    ingest(env, m)
    assert env.store.get_message(m["uid"])["job_no"] == "26-6527"
    env.pipeline.refile(m["uid"], "26-8607")
    assert env.store.get_message(m["uid"])["job_no"] == "26-8607"
    old = transcript(env, "26-6527 1006")
    assert "hello re 26-6527" in old and "CORRECTION" in old  # history kept, correction appended
    assert "hello re 26-6527" in transcript(env, "26-8607 0924")


def test_policy_version_changes_when_verdicts_change(env):
    v1 = env.pipeline.policy().version
    env.pipeline.set_role("+12065550166", "crew", "Donnie")
    assert env.pipeline.policy().numbers["+12065550166"] == "crew"
    assert env.pipeline.policy().version != v1


def test_crew_texts_are_screened_not_trusted(env):
    env.pipeline.set_role("+12065550166", "crew", "Donnie")
    env.screener.when("lunch", category="personal", confidence=0.9)
    m = mk("dev-1", "in", "+12065550166", env.clock.ms(), "lunch?")
    ingest(env, m)
    assert env.store.get_message(m["uid"]) is None  # crew number: personal chatter is still dropped
    assert env.store.get_number("+12065550166")["status"] == "business"  # but the crew number itself is not excluded
