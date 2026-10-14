# CANONICAL DOCUMENT SYSTEM — read before producing ANY client document

_Recorded 2026-08-25 after Claude built an invoice from scratch instead of
using this system. Do not repeat that._

## Where it lives

Google Drive, scripts folder **`1p3bFvMZ8ah4rQ8m5XrwxZoD5sOv9nxU7`**.
CLAUDE.md inside it names the canonical lock folder as
**`1zflF4Q5wlOmzph4NvzIyIkTbn6FWlDwe`** (inside "START HERE"
`1IKEuQnA5TzvQc7zkSR8taSpJuWdSBaCt`).

| File | Drive ID | Role |
|---|---|---|
| `CLAUDE.md` | 1mR7GfpdI_sB8bX-cUeBywfCP4CAZBbRU | **The directives. Read first.** |
| `_invoice_render.py` | 16EXTwSFUFN059kv3SouVS9PE8UOoBSzn | THE invoice body renderer |
| `letterhead.py` | 1R3m8cg0YIzTdAkw7h3fKHDOLR0KYIJxw | LOCKED header/footer |
| `invoice_body_style.py` | 1TnefXokZp0Emb5dTP5wkpVy_wbSYbqMa | typography/spacing constants |
| `_bid_render.py` | 15uG50PiEx8Mc26NDJt4o0-pwQb_4DSEL | THE bid body renderer |
| `_loc_render.py` | 1sJnV-NsoiPMmOm9GbfZJKy4ziHvV_Ve9 | Letter of Completion renderer |
| `INVOICE_REQUEST_TEMPLATE.md` | 1cUo49vm6gtLXrOSNs0XhAr4FXTHMuB0O | production protocol |
| `LETTERHEAD_LOCK.md` | 1-JlMVcS35nSIBnGAPphyx2V-DEqMB9u4 | letterhead constitution |
| `MANIFEST.sha256` | 15TNnwCOIza_8LDKcxP9FNwtiJ6Xk1_V8 | integrity gate |
| `letterhead_golden.json` | 1tF8szmv8JpRUuETwJjL1eLEB0Tk-MJoV | golden: 193 glyphs / 22 words |

Principal: **Ryan**. Letterhead locked 2026-07-01, invoice body 2026-07-03.

## Mandatory first actions, in order

1. `sha256sum -c MANIFEST.sha256` — ANY failure → STOP, tell the principal.
2. `python3 test_letterhead.py` — build gate. BLOCK all generation on failure.

## Absolute rules (verbatim intent)

- **NEVER redraw, restyle, or re-derive the letterhead or invoice body from a
  PDF, image, screenshot, or memory. The code in this folder IS the design.**
  If asked to match a visual, the visual must match the code, not the reverse.
- Letterhead renders ONLY via `letterhead.draw_letterhead()`.
  Invoice bodies render ONLY via `_invoice_render.render()`.
- Per-invoice builder files are **DATA ONLY**. New invoice = copy a builder,
  change the data dict. Never re-implement layout.
- Override contract is CLOSED: only `show_footer, footer_words, header_mode,
  address_block, body_min_gap`.
- Asbestos cert is DERIVED via `asbestos_cert_display()` → `#ABCN00001541`.
  Never hardcode. Contractor reg `#AAADNDN883KB`.
- No horizontal rules in header/footer, no decorative dividers. The only
  sanctioned lines are the accounting underlines under tax and Grand Total.
- Client-facing documents must NEVER carry L&I/PSCAA regulatory notification
  language, filing prompts, or regulatory action items.
- Descriptions: plain, direct company voice. No reg codes, no accounting
  labels. Abatement line mirrors the bid wording verbatim. One paragraph
  string per description — the renderer wraps and justifies. Never pre-wrap.
- Design changes need explicit principal approval → edit style module → re-run
  gate → regenerate MANIFEST.sha256 → note revision + date in CLAUDE.md.
- Never import from `_quarantine/`. 14 POISON Drive file IDs listed in
  CLAUDE.md must never be imported.

## Settled conventions

- **No invoice numbers** — retired 2026-07-14. A job is identified by Job ID +
  the invoice date printed on the page. Do not add `invoice_no`.
- Job ID: `YY-housenum MMDD` (YY, house number, space, job OPENING date).
  Short form `YY-housenum` is what documents normally carry.
- **Card surcharge is 3.5%**, credit only, on the tax-inclusive total, using
  exact-decimal half-cent-rounds-UP. Check/ACH/Zelle pay the base Grand Total.
  ⚠️ On 2026-08-21 Claude was told "3% is fine" in chat — the locked system and
  the shipped document both use **3.5%**. The locked value governs.
- Sales tax: **verify live against WA DOR per jobsite before rendering.**
  Never from memory. Abatement is retail-taxable; AHERA survey is a
  non-taxable professional service at $850; agency fees are non-taxable
  pass-through.
- Payment options (rev 2026-08-18/23): `payment` dict is optional.
  `card_request` / `ach_request` render clickable mailto request rows;
  `zelle` + `zelle_note` + `zelle_link` for Zelle. Zelle handle
  **aaadnwinc@gmail.com** (confirmed by Michael 2026-08-21).
  `ach_account` deliberately EMPTY — printing a full account number on every
  invoice is a lasting exposure; "details on request" is the safer default.

## Practical note for Claude sessions

Drive's `read_file_content` returns these `.py` files as markdown-ESCAPED text
(`\_`, `\[`, `\#`). That is a lossy copy — reconstructing and running it would
itself be re-deriving the design, which the rules forbid. Use
`download_file_content` (base64) if the actual bytes are needed, and only
after the manifest check.

**Anything Claude generates outside this system is not a company document.**
The HTML invoice built in the 2026-08-21 session
(`scratchpad/inv/invoice-26-3011.html`) is NON-CANONICAL and must not be sent
or used as a reference. It carried a retired invoice number and a 3% surcharge.
