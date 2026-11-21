# If Michael's phone is an iPhone

**Michael's phone type is NOT IN RECORD** (checked 2026-11-21: the Drive memory bank names an Android phone
running the field app, but its logs use "Mike" for both people, so whose phone that was is unclear).

The office service does not care what sends it a signed message (`docs/WIRE_CONTRACT.md`). What changes on an
iPhone is *how texts get to it*. Everything below is **INFERRED from general product knowledge and was not
verified this session** — confirm on the actual phone before relying on it.

1. **Why the Android agent cannot be ported:** iOS does not let a normal app read the Messages database or
   run in the background watching incoming texts. The agent's two key advantages (outgoing texts, a nightly
   completeness check) have no iPhone equivalent.
2. **Shortcuts automation (inbound only, partial):** a Shortcuts "Message" automation can run when a text
   arrives from chosen senders / containing chosen words and POST it to the service. It cannot see texts Michael
   *sends*, so the reply clock cannot detect his replies automatically (use the review page's "Handled"), and
   there is no on-device completeness check. Requests must be signed per the contract (HMAC-SHA256), which
   Shortcuts cannot do natively — a small relay endpoint would sign on its behalf.
3. **Mac relay:** if an always-on Mac is signed into the same Apple ID with Messages in iCloud, a script can
   read the local Messages store and forward gated messages — more complete (both directions) but fragile.
4. **The plan already in the record (8/10, 8/14 addenda):** a Google Voice or Twilio business number whose
   texts are forwarded/webhooked. Porting Michael's existing number is the only way to capture the number
   clients already use. Those options need no app on the phone and give both directions.

Recommendation if it is an iPhone: use option 4 (the record already prefers it), and point its webhook at
`/v1/ingest` through a small signing relay; the screening, filing, reply clock and review page work unchanged.
