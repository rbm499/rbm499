"""Which job does this message belong to?

Evidence per job is combined noisy-OR style, then the best job is filed automatically only if it is
strong AND clearly ahead of the runner-up. Anything else goes to the review queue with ranked
candidates and the reasons, so a human picks in one tap.

Every threshold lives in Settings (INFERRED defaults). The AI's job-number / address suggestions are
only evidence if they resolve to a job in the register.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .config import Settings
from .register import Job, Register

CONTINUITY_WINDOW_MS = 36 * 3600 * 1000
STRONG_METHODS = ("ryan", "explicit_job_number", "address", "ryan_assigned")


@dataclass
class Association:
    job_no: Optional[str]
    confidence: float
    method: str
    auto: bool
    candidates: List[Dict[str, Any]] = field(default_factory=list)


def _noisy_or(strengths: Sequence[float]) -> float:
    p = 1.0
    for s in strengths:
        p *= (1.0 - max(0.0, min(1.0, s)))
    return 1.0 - p


def associate(
    reg: Register,
    e164: Optional[str],
    text: str,
    settings: Settings,
    now_ms: int,
    hint_job_numbers: Sequence[str] = (),
    hint_addresses: Sequence[str] = (),
    last_assoc: Optional[Dict[str, Any]] = None,
) -> Association:
    contact_jobs = reg.jobs_for_phone(e164)
    known = bool(contact_jobs)
    contact_keys = {j.job_no for j in contact_jobs}
    ev: Dict[str, List[Tuple[float, str]]] = {}
    jobs: Dict[str, Job] = {}

    def add(job: Job, strength: float, why: str) -> None:
        if strength <= 0:
            return
        ev.setdefault(job.job_no, []).append((strength, why))
        jobs[job.job_no] = job

    full_text = " ".join([text or "", *hint_job_numbers, *hint_addresses])

    # 1. explicit job number
    by_no = reg.by_job_no(full_text)
    prefixes: Dict[str, List[Job]] = {}
    for j in by_no:
        prefixes.setdefault(j.prefix or j.job_no, []).append(j)
    for _p, js in prefixes.items():
        for j in js:
            add(j, 1.0 if len(js) == 1 else 0.6, "explicit_job_number" if len(js) == 1 else "job_number_shared_by_%d_jobs" % len(js))

    # 2. street address
    for j, score in reg.by_address(full_text):
        if known:
            if j.job_no in contact_keys:
                add(j, score, "address")
            elif score >= 0.9:
                add(j, score * 0.8, "address_of_other_contact_job")
        else:
            add(j, min(score, 0.7), "address_unknown_sender")

    # 3. the contact's own jobs
    if known:
        open_jobs = [j for j in contact_jobs if j.is_open]
        if len(contact_jobs) == 1:
            add(contact_jobs[0], 0.85, "only_job_for_contact")
        elif len(open_jobs) == 1:
            add(open_jobs[0], 0.85, "only_open_job_for_contact")
            for j in contact_jobs:
                if j is not open_jobs[0]:
                    add(j, 0.1, "closed_job_for_contact")
        else:
            for j in contact_jobs:
                add(j, 0.2 if j.is_open else 0.1, "one_of_%d_jobs_for_contact" % len(contact_jobs))

    # 4. conversation continuity
    if last_assoc and last_assoc.get("job_no") and now_ms - int(last_assoc.get("ts_ms") or 0) <= CONTINUITY_WINDOW_MS:
        prev = next((j for j in reg.jobs if j.job_no == last_assoc["job_no"]), None)
        if prev is not None:
            strong = (last_assoc.get("assoc_method") or "") in STRONG_METHODS
            add(prev, 0.8 if strong else 0.4, "thread_continuity")

    ranked = sorted(((jn, _noisy_or([s for s, _w in items])) for jn, items in ev.items()),
                    key=lambda t: jobs[t[0]].last_activity or "", reverse=True)  # most recently active first ...
    ranked = sorted(ranked, key=lambda t: -t[1])  # ... then by score (stable, so ties keep the recent job on top)
    cands = [{
        "job_no": jn, "site": jobs[jn].site, "client": jobs[jn].client, "stage": jobs[jn].stage,
        "score": round(sc, 3), "why": sorted({w for _s, w in ev[jn]}),
    } for jn, sc in ranked[:6]]

    if not ranked:
        return Association(None, 0.0, "none", False, [])
    top_jn, top = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    why_top = sorted(ev[top_jn], key=lambda t: -t[0])
    method = why_top[0][1] if why_top else "none"
    auto = top >= settings.auto_assoc_min and (top - second) >= settings.auto_assoc_margin
    return Association(top_jn, round(top, 3), method, auto, cands)
