"""Job/contact register, loaded from the house JOB_PIPELINE.json (schema pipeline-1).

The register is the ONLY source of truth for "which jobs exist": the AI may suggest a job number or
address, but a suggestion counts only if it resolves to a job here (a correlate is not a determinant).

Real-data shapes this loader tolerates (observed in the 2026-10-21 register):
  * contact.phone is free text holding several labelled numbers ("cell (..); office (..)")
  * some jobs have no contact, or an empty phone
  * job_no can be "26-1036 0508" (house number repeats), carry trailing notes, or be absent
  * stages outside the schema's list (e.g. "needs_ryan")
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .phone import extract_phones

CLOSED_STAGES = {"paid", "archived", "cancelled"}
_JOBNO = re.compile(r"^\s*(\d{2}-\d{3,5})(?:\s+(\d{4}))?(?!\d)")
_JOBNO_IN_TEXT = re.compile(r"(?<![\d-])(\d{2}-\d{3,5})(?![\d-])")
_STREET_SUFFIX = {
    "ave", "avenue", "st", "street", "rd", "road", "blvd", "boulevard", "way", "ln", "lane", "dr", "drive",
    "ct", "court", "pl", "place", "pkwy", "hwy", "n", "s", "e", "w", "ne", "nw", "se", "sw",
}
_LABEL_STOP = {"cell", "office", "main", "survey", "invoice", "notice", "l&i", "m", "o", "mobile", "work"}


@dataclass
class Job:
    job_no: str  # raw register value, trimmed
    prefix: Optional[str]  # "26-4708" (None when the register has no job number)
    site: str
    client: str
    stage: str
    contact_name: str = ""
    phones: List[str] = field(default_factory=list)
    phone_people: Dict[str, str] = field(default_factory=dict)  # e164 -> person label
    email: str = ""
    last_activity: Optional[str] = None
    opened: Optional[str] = None
    _house: Optional[str] = None
    _street_tokens: Tuple[str, ...] = ()

    @property
    def is_open(self) -> bool:
        return self.stage not in CLOSED_STAGES

    @property
    def key(self) -> str:
        return self.prefix or self.job_no


def _parse_site(site: str) -> Tuple[Optional[str], Tuple[str, ...]]:
    m = re.match(r"\s*(\d{2,6})\s+([^,;]+)", site or "")
    if not m:
        return None, ()
    toks = [t for t in re.findall(r"[a-z0-9]+", m.group(2).lower()) if t not in _STREET_SUFFIX]
    return m.group(1), tuple(toks)


def _phone_people(phone_text: str, default_name: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    last_end = 0
    for m in re.finditer(r"(?<!\d)(?:\+?1[\s.\-]*)?\(?([2-9]\d{2})\)?[\s.\-]*([2-9]\d{2})[\s.\-]*(\d{4})(?!\d)", phone_text or ""):
        e164 = "+1" + m.group(1) + m.group(2) + m.group(3)
        label = re.sub(r"[;,()]", " ", phone_text[last_end:m.start()]).strip()
        last_end = m.end()
        words = [w for w in label.split() if w.lower() not in _LABEL_STOP and w[:1].isupper()]
        person = " ".join(words[-3:]) if words else default_name
        out.setdefault(e164, person or default_name)
    return out


class Register:
    def __init__(self, jobs: List[Job], generated: Optional[str] = None):
        self.jobs = jobs
        self.generated = generated
        self.by_phone: Dict[str, List[Job]] = {}
        for j in jobs:
            for p in j.phones:
                self.by_phone.setdefault(p, []).append(j)

    # ------------------------------------------------------------ loading
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Register":
        jobs: List[Job] = []
        for raw in d.get("jobs", []):
            job_no = str(raw.get("job_no") or "").strip()
            m = _JOBNO.match(job_no)
            prefix = m.group(1) if m else None
            contact = raw.get("contact") or {}
            name = str(contact.get("name") or "").strip()
            phone_text = str(contact.get("phone") or "")
            people = _phone_people(phone_text, name)
            house, toks = _parse_site(str(raw.get("site") or ""))
            la = raw.get("last_activity") or {}
            jobs.append(Job(
                job_no=job_no, prefix=prefix, site=str(raw.get("site") or ""),
                client=str(raw.get("client") or ""), stage=str(raw.get("stage") or ""),
                contact_name=name, phones=list(people.keys()) or extract_phones(phone_text),
                phone_people=people, email=str(contact.get("email") or ""),
                last_activity=(la.get("date") if isinstance(la, dict) else None),
                opened=raw.get("opened"), _house=house, _street_tokens=toks,
            ))
        return cls(jobs, d.get("generated"))

    @classmethod
    def from_file(cls, path: Path) -> "Register":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    # ------------------------------------------------------------ lookups
    def phone_roles(self) -> Dict[str, str]:
        return {p: "client" for p in self.by_phone}

    def jobs_for_phone(self, e164: Optional[str]) -> List[Job]:
        return list(self.by_phone.get(e164 or "", []))

    def person_for_phone(self, e164: Optional[str]) -> str:
        for j in self.jobs_for_phone(e164):
            if e164 in j.phone_people:
                return j.phone_people[e164]
        return ""

    def by_job_no(self, text: str) -> List[Job]:
        """Jobs whose register job number matches a job number written in `text`."""
        found = set(_JOBNO_IN_TEXT.findall(text or ""))
        return [j for j in self.jobs if j.prefix in found]

    def by_address(self, text: str) -> List[Tuple[Job, float]]:
        """(job, score): 0.9 house number + every street token present; 0.4 house number alone."""
        t = (text or "").lower()
        words = set(re.findall(r"[a-z0-9]+", t))
        out: List[Tuple[Job, float]] = []
        for j in self.jobs:
            if not j._house or j._house not in words:
                continue
            if j._street_tokens and all(tok in words for tok in j._street_tokens):
                out.append((j, 0.9))
            else:
                out.append((j, 0.4))
        return out

    def candidates_for_screening(self, e164: Optional[str], text: str, limit: int = 8) -> List[Job]:
        """The few jobs worth showing the AI: this contact's jobs plus anything the text names."""
        seen: Dict[str, Job] = {}
        for j in self.jobs_for_phone(e164):
            seen.setdefault(j.job_no, j)
        for j in self.by_job_no(text):
            seen.setdefault(j.job_no, j)
        for j, _s in self.by_address(text):
            seen.setdefault(j.job_no, j)
        ordered = sorted(seen.values(), key=lambda j: (not j.is_open, j.last_activity or ""), reverse=False)
        return ordered[:limit]
