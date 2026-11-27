from commscap.associate import associate
from commscap.register import Register

from conftest import ALEX, FELICIA, LUIS, REGISTER, STRANGER, TONY


def test_register_parses_real_world_shapes():
    reg = Register.from_dict(REGISTER)
    by = {j.job_no: j for j in reg.jobs}
    assert by["26-3310 1026"].phones == [FELICIA, "+12065550110"]  # both labelled numbers extracted
    assert reg.person_for_phone(ALEX) == "Alex"  # label becomes the person
    assert by["26-1036 0508"].phones == []  # contact: null tolerated
    assert by["26-1036 0508"].prefix == "26-1036"
    nojob = [j for j in reg.jobs if j.prefix is None]
    assert len(nojob) == 1 and nojob[0].phones  # "(no job no.)" row kept, matchable by phone/address only
    assert len(reg.jobs_for_phone(LUIS)) == 3  # one client, three jobs
    assert reg.phone_roles()[TONY] == "client"


def test_job_number_and_address_lookup():
    reg = Register.from_dict(REGISTER)
    assert [j.job_no for j in reg.by_job_no("re 26-4708 invoice")] == ["26-4708"]
    assert reg.by_job_no("call 206-555-0101 on 2026-11-21") == []  # phone/date are not job numbers
    hits = {j.job_no: s for j, s in reg.by_address("gate at 6527 32nd Ave NW is stuck")}
    assert hits == {"26-6527": 0.9}
    weak = {j.job_no: s for j, s in reg.by_address("it was 6527 dollars")}
    assert weak == {"26-6527": 0.4}


def test_single_job_client_auto(env):
    a = associate(env.reg, TONY, "can you resend the invoice?", env.settings, env.clock.ms())
    assert a.job_no == "26-4708" and a.auto and a.method == "only_job_for_contact"


def test_multi_job_client_without_evidence_is_queued(env):
    a = associate(env.reg, LUIS, "can we move the start?", env.settings, env.clock.ms())
    assert not a.auto
    assert {c["job_no"] for c in a.candidates} == {"26-6527", "26-8607", "26-2134"}
    assert a.candidates[0]["job_no"] == "26-6527"  # equal evidence: the most recently active job is offered first


def test_explicit_job_number_beats_everything(env):
    a = associate(env.reg, LUIS, "re 26-8607 final invoice?", env.settings, env.clock.ms())
    assert a.job_no == "26-8607" and a.auto and a.method == "explicit_job_number"


def test_address_for_multi_job_client(env):
    a = associate(env.reg, LUIS, "is the gate at 6527 32nd Ave NW locked?", env.settings, env.clock.ms())
    assert a.job_no == "26-6527" and a.auto


def test_conflicting_evidence_goes_to_human(env):
    # Tony's only job is 26-4708, but he names another client's job number: do not guess.
    a = associate(env.reg, TONY, "any news on 26-8607?", env.settings, env.clock.ms())
    assert not a.auto
    assert {c["job_no"] for c in a.candidates[:2]} == {"26-8607", "26-4708"}


def test_continuity_only_trusted_when_a_human_or_explicit_set_it(env):
    now = env.clock.ms()
    weak = {"job_no": "26-6527", "assoc_method": "one_of_3_jobs_for_contact", "ts_ms": now - 3600_000}
    strong = {"job_no": "26-6527", "assoc_method": "ryan", "ts_ms": now - 3600_000}
    stale = {"job_no": "26-6527", "assoc_method": "ryan", "ts_ms": now - 72 * 3600_000}
    assert not associate(env.reg, LUIS, "ok sounds good", env.settings, now, last_assoc=weak).auto
    a = associate(env.reg, LUIS, "ok sounds good", env.settings, now, last_assoc=strong)
    assert a.auto and a.job_no == "26-6527"
    assert not associate(env.reg, LUIS, "ok sounds good", env.settings, now, last_assoc=stale).auto


def test_unknown_sender_address_only_is_capped_and_queued(env):
    a = associate(env.reg, STRANGER, "hi, about 4708 8th Ave NE", env.settings, env.clock.ms())
    assert a.job_no == "26-4708" and not a.auto and a.confidence <= 0.7
    b = associate(env.reg, STRANGER, "this is about 26-4708", env.settings, env.clock.ms())
    assert b.auto  # knowing the job number is strong evidence


def test_shared_prefix_is_ambiguous(env):
    reg = Register.from_dict({"jobs": [
        {"job_no": "26-1036 0508", "site": "1036 N 105th St", "stage": "opened", "contact": {"name": "A", "phone": "(206) 555-0111"}},
        {"job_no": "26-1036 0610", "site": "1036 N 106th St", "stage": "opened", "contact": {"name": "B", "phone": "(206) 555-0112"}},
    ]})
    a = associate(reg, STRANGER, "about 26-1036", env.settings, env.clock.ms())
    assert not a.auto and len(a.candidates) == 2
