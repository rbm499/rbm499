# Gate 1 — document provenance enforcement

A renderer that **refuses to build** a document containing a Class 2 value with no source of record.

This is the absolute gate. Gate 2 (`../provenance_gate/`) is a harness hook that can be uninstalled;
Gate 1 is a `raise` inside the build path. No hook, no model cooperation, no way to opt out: an
unsourced number becomes a build error instead of a document.

## It does not touch the canonical renderers

`_invoice_render.py`, `_bid_render_letter.py` and `_loc_render.py` are the design constitution and
stay untouched (S-03). Gate 1 sits one step earlier, on the data a per-job builder hands in — which
STANDING_INSTRUCTIONS already defines as data-only. It validates, strips the provenance back off, and
returns plain values, so the renderer receives exactly what it received before.

That stripping is load-bearing: it is what keeps rule 6 / S-07 true. The audit goes to the job file.
The deliverable carries bare facts and no citations.

## Using it

```python
from doc_provenance import sourced, boilerplate, prepare, write_audit

data = {
    "client": "Tarun Phaugat",                                    # not a Class 2 value
    "total": sourced(7961.64, "PSCAA ledger 202603096, pulled 2026-09-24"),
    "completion_date": sourced("September 8, 2026", "LOC 26-4509, signed"),
    "scope": boilerplate("Removal performed under WAC 296-62-07712."),
}

payload, audit = prepare(data)              # raises ProvenanceError if anything is unsourced
render_invoice(payload)                     # canonical renderer, unchanged
write_audit(audit, job_dir / "PROVENANCE.md", job="26-1834",
            rendered="AAA-D_Invoice_26-1834.pdf")
```

### The four wrappers

| | Meaning |
|---|---|
| `sourced(value, source)` | A looked-up fact and its record. Wrapping a dict or list covers everything inside it with that one source. |
| `boilerplate(text)` | Fixed canon text from the design constitution. **Required** — regulatory boilerplate cites WAC and CFR by design, so without this every AHERA report would fail. Recorded in the audit as claimed-boilerplate, so the exemption is visible rather than silent. |
| `NOT_IN_RECORD` | Looked for, genuinely absent. Distinct from a field nobody filled in. Refuses in final mode; renders as a loud marker in draft. |
| bare value | Passes only if it carries no Class 2 token. Any bare number refuses. |

### Modes

- **`final`** (default) — any unsourced value, empty source, or `NOT_IN_RECORD` raises. Use for
  anything a client or a regulator will see.
- **`draft`** — renders anyway, stamps `NOT IN RECORD` on the page, and the audit says in plain words
  that the document must not be sent. For internal review, never for outbound.

## What a refusal looks like

Every violation is reported in one pass, so a single fix round clears them all:

```
Refusing to render: 4 value(s) have no source of record.

  total
    value:   7961.64
    problem: Bare number with no source.
    remedy:  Wrap it: sourced(7961.64, '<source of record>'). If it is arithmetic on
             values already sourced in this payload, wrap it with that derivation as
             the source.

  scope
    value:   Removal performed under WAC 296-62-07712.
    problem: Unsourced Class 2 value(s): WAC 296-62-07712 (wac_rcw)
    remedy:  Wrap with sourced(...), or boilerplate(...) if it is fixed canon text
             from the design constitution rather than a looked-up fact.
  ...
```

> The figures and sources in the examples above and in the tests are **synthetic fixtures**. They are
> not provenance records for any real job, and must not be read as ones.

## The two gates cannot drift

Gate 1 loads its Class 2 patterns from `../provenance_gate/gate_config.json` — the same file Gate 2
uses. One source of truth, and a test asserts they match, so tuning one tunes both. Override with the
`DOC_PROVENANCE_CONFIG` environment variable or the `config_path` argument.

A missing config **refuses** rather than passing everything. A gate that cannot load its rules must
not wave documents through.

## Tests

```
python3 test_doc_provenance.py
```

25 tests, no third-party packages, Python 3.9+. Verified 2026-09-24 on Python 3.11.15: 25/25 pass.

Among them, the three that matter most:

- **`no source string can reach the renderer`** — proves rule 6 holds structurally, not by discipline.
- **`all violations reported in one pass`** — four unsourced values produce four violations, not one.
- **`missing config refuses (not fails open)`** — the failure direction is correct.

## Integrating against the real builders

The canonical code at `Desktop\aaadnwinc.templates claude start here\` was **not readable from the
container this module was written in**, so the integration was deliberately not written blind. Wiring
it in requires reading the actual builders first. See `INTEGRATION_PROMPT.md` in this directory for
the handoff: a Cowork session with Desktop Commander at the G: path can do it against the real code.

Expected shape of the change, per builder, with no renderer edits:

1. `from doc_provenance import sourced, boilerplate, prepare, write_audit`
2. Wrap each Class 2 value in the builder's data dict with its source of record.
3. Wrap fixed regulatory text with `boilerplate(...)`.
4. Replace `render_x(data)` with `payload, audit = prepare(data)` then `render_x(payload)`.
5. `write_audit(audit, <job folder>/PROVENANCE.md, job=..., rendered=...)`.
6. Re-render a known-good past document and diff the PDF against the original — **byte-identical
   output is the acceptance test.** Gate 1 changes what is allowed to render, never what rendering
   produces.

## What this does not do

- It does not verify a source is *true*. A wrong ledger figure with a correct-looking citation passes.
  Gate 1 enforces traceability, not accuracy.
- It does not check effective dates. Correctly-sourced but superseded is still wrong.
- It cannot see a Class 2 value expressed in words ("about eight thousand").
- It only guards builders that call `prepare()`. A builder that skips it is unguarded — which is why
  step 6's diff test should be run against every builder, not a sample.
