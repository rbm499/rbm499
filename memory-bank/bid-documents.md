# Bid Documents — Protocol & Exact Structure

_Last updated: 2026-08-07. Source: all bid/proposal/invoice emails sent from
aaadnwinc@gmail.com (Jun–Aug 2026) + prior memory bank. This is the reference
for producing any future AAA & D NW bid, survey proposal, or invoice._

## Company identity block (use verbatim)

- **AAA & D NW Environmental Services, Inc.**
- 3632 49th Ave SW, Seattle, WA 98116
- Phone: 253-217-2537 · Email: aaadnwinc@gmail.com
- Signer: **Michael Neureiter, Principal** — title line under name is either
  "AHERA Certified Surveyor" or "AHERA Certified Asbestos Inspector"
  (both in active use; surveyor on survey-related mail, inspector on bids).
- AHERA cert #NES-BIR-20260313-31, exp 03/13/2027 (from 26-6808 corrections).
- Checks payable to: AAA & D NW Environmental Services, Inc., mailed to the
  3632 49th Ave SW address above.
- CAUTION: the Ford Fusion bill of sale used "3632 49th Ave **NW**" — the
  correct company address everywhere else is 49th Ave **SW**.

## Job / project numbering

- Job No. = `26-<street number of the property>` (26 = year 2026).
  Examples: 26-5917 (5917 41st Ave SW), 26-24108 (24108 56th Ave W),
  26-1404 (1404 169th Pl NE), 26-8045, 26-4827, 26-6808.
- Long-form "Project No." sometimes appends survey month/year MMYY:
  `26-1404-0524`.
- Combined two-property bids keep both street numbers: `26-6711-6719`.

## Document types & exact file naming

| Document | Filename pattern | Example |
|---|---|---|
| Abatement bid proposal (PDF) | `AAA-D_Bid_Proposal_<job>_<ClientShortName>.pdf` | `AAA-D_Bid_Proposal_26-24108_NetTree.pdf`, `AAA-D_Bid_Proposal_26-6711-6719_Jabooda.pdf`, `AAA-D_Bid_Proposal_26-1404_Matt_Homes.pdf`, `AAA-D_Bid_Proposal_26-5917_Westcost.pdf` |
| Survey (testing) proposal (PDF) | `AAA-D_Survey_Proposal_<ProjectName>_<Client>.pdf` | `AAA-D_Survey_Proposal_PikeHouse_Baldwin.pdf` |
| AHERA survey report (PDF) | `AHERA_<job>_<address-hyphenated>_<MMYY>_COLOR_Bates_R6 Signed and Final.pdf` (or informally `Signed Ahera survey <job>.pdf`) | `AHERA_26-1404_1404-169th-Pl-NE_Bellevue_0524_COLOR_Bates_R6 Signed and Final.pdf` |

ClientShortName = client company nickname (NetTree, Jabooda, Matt_Homes,
Westcost, Baldwin), not the contact's personal name.

## The bid proposal document (abatement)

Structure of the PDF (as consistently referenced in the cover emails; the
PDF internals could not be opened this session — see Gaps):

1. Multi-page proposal on company identity.
2. **Scope of work** — per room/area: the material system being removed
   (e.g. "ceiling and wall Sheetrock/Joint Compound Composite"), approximate
   quantities in sq ft per surface, associated items (insulation, nails,
   debris), plus encapsulation of remaining surfaces, and the regulatory
   citation: "as regulated by Washington State L&I under WISHA Regional
   Directive 23.30".
3. **Firm bid price** — a single fixed dollar amount "plus applicable
   Washington State sales tax". When a total is quoted it is price × local
   sales-tax rate (observed: 26-24108 Mountlake Terrace $3,180.00 → $3,513.90
   = 10.5%; 26-5917 Seattle $1,380.00 → $1,525.59 = 10.55%).
4. **Last page = acceptance/signature page.** The client signs and returns
   the last page (or the whole proposal) to accept. This is the trigger for
   scheduling.

One proposal can cover multiple properties (6711 & 6719 42nd Ave S were
"both houses covered on one proposal").

### Firm-bid pricing rules (IMPORTANT — set after the Jabooda incident)

- The firm bid **includes everything needed to access and remove the ACM**,
  including demo/removal of non-ACM material (e.g. an installed or dropped
  ceiling) that hides it. No extra charge for access.
- Additional charges are only allowed for a **completely separate hidden
  asbestos system not mentioned in the AHERA survey**.
- Never write a bid that reads as if hidden-but-expected material above
  ceilings/finishes would be an additional charge — that wording went out
  once (26-6711/6719, Jul 2026) and required a written correction/apology.
- Missed line items get an amended bid, not a change order: for 3011 70th
  Ave SE, 16 ACM windows were missed; corrected bid went from $5,110 to
  $6,150 plus tax (+$62.50/window) with a transparent apology.

## The survey (testing) proposal document

Priced and structured differently from an abatement bid (Pike House model):

- **Survey Fee**: flat, scaled to approximate square footage
  ($4,050.00 flat for ~20,000 sq ft).
- **Laboratory analysis**: $7.00 per sample, first two layers included;
  each additional layer analyzed $7.00 per layer; **only samples actually
  collected and analyzed are billed**.
- **Timeline commitments**: on-site inspection within 3–5 business days of
  authorization + confirmed access; written report 3–5 business days after
  lab results.
- Acceptance: sign and return the attached, **or a simple reply approval is
  acceptable** (looser than abatement bids, which want the signed page).
- Always note that demolition (vs remodel) extends sampling scope, and ask
  for floor plans/drawings.
- Standard close: once survey results are in, a firm abatement bid is
  offered as a follow-on.

## Cover email protocol (every bid goes out as a PDF attached to an email)

Subject line formats in use:
- `AAA & D NW Environmental Services — Asbestos Abatement Bid Proposal, <address> (Job <job>)`
- `Bid Proposal — <address> (Job <job>)`
- `AHERA Asbestos Survey & Abatement Bid - <address> (<job>)` (when survey
  report + bid are sent together)
- Short form for repeat clients: `Bid <job>`

Body structure (in order):
1. Greeting by first name ("Hello Steven," / "Hi Kaitlyn," / "Oleg,").
2. "Please find attached our … bid proposal for <scope area> at <full
   address incl. city, state, ZIP> (Job <job>)."
3. When sent with a survey: a **"Bottom line" plain-English summary** of the
   survey findings (what tested positive, at what %, what that legally
   requires, what came back clean), plus "keep a copy of the report on site
   throughout the work" and the color-print disclaimer ("This report is
   formatted to be understood in color only…").
4. Scope summary and/or firm price: "Firm bid: $X plus tax — total $Y."
5. Call to action: "sign and return the last page / the proposal and we
   will file the required **L&I / PSCAA notifications** and get you on the
   schedule." Scheduling-queue urgency is fair to mention ("window fills up
   as signed bids come in").
6. Offer to answer questions, then full signature block (identity block
   above).

## Lifecycle protocol (bid → invoice)

1. Inquiry arrives (often with someone else's survey attached, or asking
   for testing + removal).
2. If no survey exists → send **survey proposal**; do the AHERA survey.
3. Before bidding removal, confirm scope with the client (all materials in
   the survey vs. bare-minimum for demo; ask demo vs. remodel; ask timeline).
4. Send **bid proposal PDF** (with the signed AHERA report PDF if new).
5. Client signs & returns → file **L&I and PSCAA notifications** (copies of
   filed notices are sometimes emailed to the client with start date/hours,
   e.g. 5016 242nd St SW), schedule the work. Notification window example:
   "submit notifications for 27th–30th".
6. Complete work → **invoice** email: subject `Invoice — Job No. <job>
   (<address>)`, body states invoice total and "Payment is due upon
   completion of work." Totals include tax (e.g. 26-5917 $2,690.59;
   26-1404 $18,129.14). Attach invoice PDF.
7. **Clearance letter** provided to client after abatement for their records.

## Gaps / TODO

- The internal page-by-page layout of the bid PDF (header art, tables,
  terms & conditions text, acceptance-page wording) could not be pulled
  this session: Gmail attachment download isn't available in this toolset
  and the Google Drive connector is disabled ("operation not enabled" —
  same account-mismatch issue logged 2026-07-31). Next session with Drive
  access (or with a bid PDF/source file shared directly), extract the full
  template verbatim and append it here.
- Confirm whether current sales-tax totals should use each job's local
  rate (observed 10.5% vs 10.55%) or a fixed rate.
