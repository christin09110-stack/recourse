# Recourse

**An autonomous agent that appeals health-insurance denials, and never misses the clock.**

Built on the [Strands Agents SDK](https://strandsagents.com) against Amazon Bedrock.
Track: **Everyday Agents**, AWS Agents for Humans.

Recourse is what you have left when you have been refused. It reads a denial, works
out from the denial's own code whether the problem is paperwork or medicine,
assembles the appeal from documents you already hold, and counts down every
statutory deadline. It drafts on its own. It never files on its own, and it never
lets a deadline pass in silence.

---

## 1. Why

| | |
|---|---|
| Insurers received about **496 million claims** in 2024; **85 million in-network claims were denied** | [KFF, 2024](https://www.kff.org/patient-consumer-protections/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/) |
| **Fewer than 1%** of denied claims were appealed | KFF |
| Of appeals filed, insurers **upheld 66%** — so roughly **a third are overturned** | KFF |
| **25%** of denials were administrative. Only **5%** were medical necessity | KFF |

A quarter of denials are paperwork. One in twenty is a clinical judgement. Almost
nobody challenges any of them, and a third of the people who do, win.

They do not fail to appeal because they accept the decision. They fail because the
appeal is unpaid administrative work, done while ill or caring for someone ill,
against a deadline nobody told them about, using documents held by three different
organisations.

**And it is a clock problem.** You have **180 days** to file an internal appeal. The
plan owes you an answer in **30 or 60 days**. After a final internal denial you have
**four months** to request external review. Every one of those runs whether or not
anybody is watching, and missing the 180 is the only failure here where the merits
stop mattering.

## 2. What makes it tractable

A denial is not free text. It arrives carrying standardised
[X12 codes](https://x12.org/codes/claim-adjustment-reason-codes).

| Code | X12 text | What it means |
|---|---|---|
| **16** | Claim/service lacks information or has submission/billing error(s) | Paperwork — often the provider's, not a coverage decision at all |
| **197** | Precertification/authorization/notification/pre-treatment absent | Sometimes never obtained; sometimes obtained and never attached |
| **50** | Not deemed a "medical necessity" by the payer | **Clinical.** The treating clinician's argument and nobody else's |

That line — 16 against 50 — is the whole product. It is a lookup, not an
interpretation.

**Failing closed.** A CARC 16 arriving beside a code we do not recognise classifies
`unassessable`, not `clerical`: the unreadable code might be the clinical half of
the denial. Since **36%** of real denials are coded "Other" with no reason listed,
that is the common case rather than the edge.

## 3. Where its authority ends

The dial moves ordinary things — how early it warns, whether it may ask a provider
for records in your name, whether it drafts unprompted.

**Three rules ignore it at every level**, and the third is the odd one out.

1. **It never asserts a clinical fact the record does not support.** Every clinical
   sentence must cite a document in the case file. `CitationGuard` returns `Deny`,
   not `Confirm` — there is nothing for a human to approve about a sentence nothing
   supports, and offering it would invite somebody to wave through a false statement
   on an insurance document made in a patient's name.
2. **It never files.** No tool in this system submits an appeal to anyone; a test
   fails if one appears. Filing is a legal act in the claimant's name. It prepares,
   and a person sends.
3. **It never lets a deadline pass in silence.** A *duty*, not a prohibition. Every
   other rule waits to be provoked by a tool call; this one fires because the agent
   is about to do nothing. A background agent that only spoke when provoked would go
   quiet through six months of a 180-day window and be right about everything except
   the thing that mattered.

## 4. Two bodies of rules

Both shipped, both read from primary sources, every figure carrying its citation.

| | ACA marketplace | ERISA group health |
|---|---|---|
| To appeal | 180 days | at least 180 days — [§(h)(3)(i)](https://www.govinfo.gov/content/pkg/CFR-2023-title29-vol9/xml/CFR-2023-title29-vol9-sec2560-503-1.xml) |
| Decision on appeal, one level | 72 hrs / 30 / 60 days | same — §(i)(2) |
| Decision on appeal, **two mandatory levels** | n/a | **15 + 15** or **30 + 30** — §(i)(2) |
| After the final internal denial | external review, 4 months to request | external review if non-grandfathered, else a civil action under ERISA §502(a) |

The last two rows are what an agent is for. An ERISA plan may require **two**
mandatory internal appeals, which splits the clock: "you have 60 days" becomes "you
have 30, then 30 more, and the second only starts when the first is answered." A
person tracking that by hand is tracking a clock that pauses and restarts.

**A plan type with no clock table is refused, never defaulted.** ERISA *non-health*
plans allow 60 days to appeal, not 180 ([§(h)(2)(i)](https://www.govinfo.gov/content/pkg/CFR-2023-title29-vol9/xml/CFR-2023-title29-vol9-sec2560-503-1.xml)).
Falling back to the health figure would tell somebody they had four months they do
not have, so the loader raises and says why.

## 5. Architecture

The model reasons. It never does the arithmetic, and it never computes a date.

- **Clocks are pure functions** over a notice date, a plan's rules and a stage.
- **The rulebook and the code table are data**, versioned, each figure carrying the
  `.gov` or X12 URL it came from.
- **Two Strands loops.** WATCH triages a denial; PRESS runs the clock on a schedule.
- **Two interventions, in order.** `CitationGuard` first, because its `Deny`
  short-circuits and an unsupported clinical claim must never reach a policy that
  would weigh it on urgency and find nothing wrong.
- **An MCP server** over the same engine, read-only. It can classify a denial and
  price a deadline; it cannot change anyone's case.

## 6. Quick start

```bash
pip install -e ".[dev]"
pytest -m "not integration"          # no AWS credentials needed

cd frontend && npm install && npm run build && cd ..
uvicorn recourse.api.app:create_app --factory --reload --port 8080
```

## 7. What this build does not do

Said plainly, because the gap between a demo and a product is where the honesty
goes.

- **The EOB is an uploaded PDF against a seeded world.** There is no live payer
  connection. Real interoperability exists — the CMS Interoperability and Patient
  Access rules put claims behind a patient-authorised FHIR API — and that is where
  this goes next. It is not what was built here.
- **Scanned EOBs have no text layer**, so the parser returns nothing and says so. A
  meaningful share of what people are actually mailed is a scan. OCR is the answer,
  and it is not here.
- **Many payers print a footnote marker per row** and put the code in a legend
  below, rather than inline. The samples are the friendly case.
- **Real notices batch several claims** under one notice number. This takes the
  first.
- **Nothing is durable.** The stores are in memory. Restart the process and every
  pending decision goes with it.

## Licence

MIT.
