# Phase 2 — Civil Works pricing engine

Tool: Claude Code (Claude Opus 5.5). Date: 2026-09-29. Given verbatim below.

---

Continue the Civil Works implementation with PHASE 2 ONLY.

Do not proceed to Phase 3.
Do not create audit findings, invoice flags, confidence scores, or submission predictions yet.

At the end, stop and report back to me so I can review the work before authorizing the next phase.

==================================================
CURRENT STATE
==================================================

Phase 1 is accepted.

Current architecture:

src/contractor_audit/
    shared/
    domains/
        civil_works/
        drilling/        # later

Civil Works Phase 1 already provides:

- reviewed contract extraction
- typed contract/data models
- loaders
- record parsing
- source profiling
- provenance
- deterministic artifacts
- architecture boundaries
- 96 passing tests

Civil Works currently has:

- 900 applications
- 7,746 lines
- 2,169 site records
- 60 contract items

There are currently:

- no audit rules
- no invoice/application flags
- no confidence scores
- no submission output
- no predictions

Keep it that way during Phase 2.

==================================================
PHASE 2 GOAL
==================================================

Build a deterministic, testable Civil Works pricing engine capable of answering:

"For this item, on this work date, under this contract state and these line attributes, what contractual pricing components could apply?"

The engine must support all material pricing mechanisms in the Civil Works contract while preserving genuinely unresolved interpretations as explicit alternatives.

Phase 2 should establish pricing mechanics.

It should NOT decide whether an application is erroneous.

==================================================
CRITICAL METHODOLOGY RULE
==================================================

DO NOT use billed rates, billed line amounts, application totals, or known anomalies to choose the meaning of an ambiguous contract clause.

Contract semantics must come from:

- contract text
- schedules
- supplements
- amendments
- precedence rules
- dates
- explicit contract definitions

You MAY later compare independently-derived interpretations against billed data as a descriptive consistency/sensitivity analysis.

But:

BILLED DATA MUST NOT BE THE EVIDENCE THAT DEFINES THE CONTRACT RULE.

For example, do not reason:

"Interpretation A matches more invoices, therefore A is correct."

Instead:

1. derive A and B independently from the contract;
2. preserve both if the wording remains genuinely ambiguous;
3. measure their downstream effects separately;
4. document the ambiguity for later confidence/decision handling.

==================================================
1. BUILD A RATE-IN-FORCE RESOLVER
==================================================

Implement a pure deterministic resolver for:

item + work_date
→ applicable contractual rate/rate regime

It must handle:

- base Bill of Quantities rates
- Schedule 2A indexed rates
- Schedule 2B USD rates
- Supplement 1
- Amendment 1
- Supplement 2
- Amendment 2
- Amendment 3
- any other extracted instrument affecting price

Respect:

- effective date
- issue date
- explicitly backdated effective dates
- item-specific effective dates
- instrument precedence

Do not simply choose the newest document.

Encode precedence explicitly.

The engine should make it possible to inspect something like:

RateResolution(
    item_code=...,
    work_date=...,
    source_instrument=...,
    effective_from=...,
    base_rate=...,
    rate_type=...,
    calculation_trace=[...]
)

Names may differ if the existing architecture suggests something cleaner.

==================================================
2. INSTRUMENT TIMELINE
==================================================

Tests must pin important boundaries including:

2025-01-05
2025-05-01
2025-09-28
2025-10-01
2025-11-01
2025-12-01
2026-01-05
2026-04-01

Especially test:

day before
effective day
day after

for amendments/supplements that change rates.

Important:

Amendment issue date and pricing effective date are not always the same.

Amendment 3 is explicitly backdated.

Do not collapse issue_date and effective_date into one field.

==================================================
3. MONEY / DECIMAL RULES
==================================================

Never use binary float for contractual pricing.

Use Decimal or the project's exact-money abstraction.

The Phase 1 source data already preserves exact decimals and whole-halalah money.

Create one central rounding policy based on the actual contract wording.

Do not silently use Python default rounding.

If the contract is ambiguous about an intermediate rounding point:

- preserve that ambiguity
- add an interpretation switch
- test both

==================================================
4. PRICING BUILD-UP
==================================================

Implement the contract pricing build-up as composable components.

At minimum support:

- base/current item rate
- indexed-rate calculation
- USD conversion
- zone factor
- ground-class factor
- night uplift
- rest-day uplift
- rebate band
- contractual discounts
- monthly-rate substitutions
- any specifically extracted pricing modifiers

Produce a pricing trace.

For example conceptually:

base rate
→ amended/indexed/current rate
→ zone adjustment
→ ground adjustment
→ uplift
→ rebate tier
→ contractual discount
→ final contractual unit rate

Do NOT assume this exact order unless the contract establishes it.

Derive the order from the extracted clauses.

A reviewer should be able to inspect the trace and understand exactly why a rate was produced.

==================================================
5. ZONE FACTORS
==================================================

Support all four zone factors.

Remember Phase 1 established they apply only to series A–D.

Test:

- each zone
- an A–D item
- a Series E item

Ensure Series E cannot accidentally receive a zone factor unless another explicit clause overrides that.

==================================================
6. GROUND-CLASS FACTORS
==================================================

Support the five ground classes for the 15 applicable items.

Do not apply ground factors to unrelated items.

Explicitly implement the unresolved Clause 27A interpretation concerning work after 2025-09-27.

Create named alternatives, something like:

GROUND_AFTER_ORIGINAL_COMPLETION =
    "recorded_ground_class"

versus

GROUND_AFTER_ORIGINAL_COMPLETION =
    "datum_g2"

Use whatever names fit the project.

Do NOT silently pick one yet if the contract remains genuinely ambiguous.

Build sensitivity support for both.

==================================================
7. NIGHT / REST-DAY UPLIFTS
==================================================

Support:

- 13 night-uplift items
- 4 rest-day-uplift items

Also encode the Clause 27A issue that may prohibit night uplift where the zone factor exceeds 1.1.

Preserve this as an explicit interpretation if needed.

For combined night + rest-day uplift:

the data has no Engineer instruction capable of proving authorization.

Do not invent authorization.

The pricing engine can model the theoretical contractual branch, but later audit logic must distinguish:

"contract allows this if authorized"

from

"authorization is evidenced in the provided data."

==================================================
8. INDEXED RATES
==================================================

Implement Schedule 2A using the extracted monthly index table.

All required index months already exist locally.

No external data/network request is allowed.

Important unresolved issue:

The contract formula and its own Appendix B worked example disagree.

Do NOT hide this.

Implement both interpretations:

A. literal contractual formula
B. worked-example interpretation

Give each a named mode and deterministic tests.

For the known C.31.010 May 2025 example, explicitly demonstrate the difference.

Do not choose a winner based on which better matches billed invoices.

==================================================
9. USD RATES
==================================================

Implement Schedule 2B using the extracted monthly exchange-rate table.

No external FX lookup.

Preserve the ambiguity:

- Schedule 2B identifies three items as USD-priced
- other language/column headings may describe them in SAR

Model the viable readings explicitly.

Do not silently convert or not convert.

Write boundary/unit tests for the three affected items.

==================================================
10. MONTHLY RATE ITEMS
==================================================

Implement D.41.020 and E.54.010 monthly-rate behavior with their correct effective dates.

Keep explicit switches for unresolved questions such as whether:

- zone factor
- night uplift
- discounts

apply on top of the monthly rate.

Do not infer this from billed values.

Also investigate the D.41.020 unit/index inconsistency recorded in Phase 1.

If contract language does not resolve it, document it rather than guessing.

==================================================
11. DISCOUNTS
==================================================

Implement all time/item-specific discounts introduced by supplements/amendments.

Important:

Determine from the documents whether later discounts:

- replace earlier discounts
or
- stack with them.

If genuinely unresolved, implement both alternatives.

Specifically preserve the 5% / 8% interaction as a named interpretation switch if the contract does not settle it.

==================================================
12. REBATE BANDS
==================================================

Implement the 8 rebate-band items.

This must be stateful where required.

Support the two plausible interpretations already identified:

A. rebate volume resets each contract year
B. rebate volume is cumulative over the entire job

Do NOT choose between them using invoice correctness.

Implement both.

The state engine must make clear:

- volume before current line
- quantity on current line
- threshold crossings
- quantity allocated to each band
- resulting effective amount/rate

If a single line crosses a threshold, split quantity correctly if the contract requires band-level splitting.

Use exact arithmetic.

==================================================
13. FIRST-HOUR RULE
==================================================

Implement the "first hour not chargeable" provision for applicable hourly items.

If its scope/meaning is genuinely ambiguous, represent alternatives.

Add explicit tests around:

0.5 hour
1 hour
1.5 hours
multiple hours

Do not silently assume whether this applies per:

- line
- record
- day
- application

unless the contract makes that clear.

==================================================
14. SITE-RECORD QUANTITY EXTRACTION
==================================================

Implement deterministic quantity extraction from site records.

Phase 1 found only 1–5 standard phrasings per record type.

Use rule-based parsing first.

Do NOT use an LLM for simple structured phrases.

For each parsed quantity, preserve:

- source record id
- raw text
- parsed quantity
- unit
- parser/rule used
- provenance

If a record cannot be parsed confidently:

return unresolved.

Do not guess.

==================================================
15. SURVEYED QUANTITY RULE
==================================================

Model the conflict between:

Clause 33:
exact surveyed quantity

and

Clause 33A:
2% tolerance

as explicit alternatives if the extracted contract cannot resolve precedence.

Do not create audit findings yet.

The pricing/quantity layer only needs to expose:

- contractual expected quantity or range
- interpretation used
- provenance

==================================================
16. EXCLUSION WINDOW
==================================================

Implement the contract's exclusion-window mechanics as a reusable evaluator.

Do not flag applications yet.

Preserve the unresolved boundary question:

does the two-day window include the same day?

If necessary expose:

same_day_included
same_day_excluded

as alternative interpretations.

==================================================
17. CONTRACT PERIOD / EXTENSIONS
==================================================

Implement a deterministic contract-in-force resolver.

It must understand:

- original completion date
- Amendment 1 extension
- Amendment 2 extension
- final completion date

The two lines after the final extended completion date should become visible to later audit logic, but DO NOT flag them in Phase 2.

==================================================
18. BACKDATED AMENDMENT 3
==================================================

Separate two concepts:

A. rate effective date
B. later adjustment/reconciliation event

Implement enough state to compute the pricing effect of the backdated rate.

Do not yet decide the final invoice/application error.

Preserve the ambiguity between:

"on or after issue date"

and

"after issue date"

for deciding which later application receives the adjustment.

The three applications dated exactly 2026-05-12 should be boundary cases in tests.

==================================================
19. RETENTION
==================================================

Model the contractual retention calculation.

Phase 1 found all 900 applications currently use exactly 5% rounded down.

Build the contract-side calculation independently.

Also model the Clause 45A release event after 2026-09-30.

Do not create findings yet.

Because the release may sit outside the measured total, expose it separately from measured-work pricing.

For example conceptually:

PricingResult(
    measured_work_total=...,
    retention=...,
    outside_measured_adjustments=[...]
)

Do not force it into expected_total until Phase 3 decides the task semantics.

==================================================
20. PRICING TRACE / PROVENANCE
==================================================

Every reconstructed price must be auditable.

Produce structured trace entries such as:

- rule
- clause/source
- input
- calculation
- result
- interpretation mode

Do not store only the final number.

We need to be able to explain every later finding.

==================================================
21. INTERPRETATION CONFIGURATION
==================================================

Create a clean Civil Works interpretation/config object.

Do not scatter booleans through the code.

For example:

CivilWorksInterpretation(
    rebate_reset=...,
    indexed_rate_method=...,
    usd_currency_reading=...,
    post_completion_ground_rule=...,
    monthly_rate_modifiers=...,
    discount_stacking=...,
    exclusion_same_day=...,
    surveyed_quantity_rule=...,
    ...
)

Use enums where appropriate.

Provide:

- clearly named default
- all meaningful alternatives

IMPORTANT:

At this phase, "default" does not mean proven correct.

It means the currently selected working interpretation.

==================================================
22. SENSITIVITY ANALYSIS
==================================================

After the engine is complete, run a descriptive sensitivity analysis.

For each unresolved interpretation report:

- number of lines affected
- number of applications affected
- financial magnitude if calculable
- whether alternate readings produce the same price
- whether the ambiguity matters downstream

You MAY additionally report how frequently each independently-derived interpretation happens to reconcile with billed data.

But label this ONLY as:

"consistency with observed billing"

Never:

"proof the interpretation is correct."

Do not change an interpretation merely because it produces higher reconciliation.

==================================================
23. NO AUDIT FINDINGS YET
==================================================

Phase 2 MUST NOT create categories like:

- wrong_rate
- wrong_quantity
- missing_uplift
- incorrect_discount
- duplicate
- etc.

Do not decide:

flagged = true/false

Do not calculate confidence.

Do not generate submission.csv.

That begins in Phase 3.

==================================================
24. TESTS
==================================================

Add substantial tests covering:

- all rate effective-date boundaries
- amendment precedence
- index formula alternatives
- USD conversion alternatives
- monthly-rate changes
- zone factors
- ground factors
- uplifts
- discounts
- rebate bands
- threshold crossing
- contract-year reset alternative
- full-job cumulative alternative
- first-hour rule
- quantity extraction
- surveyed-quantity alternatives
- exclusion-window alternatives
- retention
- backdated adjustment boundaries
- contract extensions
- pricing trace provenance
- no binary float money
- deterministic rebuilds
- task source files unchanged
- architectural isolation from future Drilling domain

Keep warnings-as-errors.

==================================================
25. ARCHITECTURE
==================================================

Keep the existing clean architecture.

Civil Works-specific pricing logic belongs under:

src/contractor_audit/domains/civil_works/

Shared code should only receive abstractions that are genuinely reusable by Drilling.

Do NOT move Civil Works concepts into shared simply because they might someday be useful.

Drilling must still be addable as:

src/contractor_audit/domains/drilling/

without importing Civil Works.

==================================================
26. ARTIFACTS / DOCUMENTATION
==================================================

Generate/update Civil Works artifacts describing:

- rate timeline
- interpretation matrix
- pricing model
- sensitivity results
- quantity parsing coverage

Update the Civil Works decision log with:

- resolved interpretations
- unresolved interpretations
- exact alternatives retained
- provenance

Do not rewrite Phase 1 history.

==================================================
27. FINAL PHASE 2 REPORT
==================================================

At the end, STOP.

Do not proceed to Phase 3.

Report:

1. Files created
2. Files modified
3. Pricing engine architecture
4. Rate timeline implementation
5. Number of pricing mechanisms implemented
6. Quantity extraction coverage
7. Interpretation switches and their meanings
8. Sensitivity results for every unresolved interpretation
9. Any new contract ambiguity discovered
10. Test count and result
11. Confirmation task source files remain untouched
12. Confirmation no flags/predictions/submission were created
13. Git status
14. Recommended Phase 3 scope

Also specifically report:

- whether you found any Phase 1 transcription mistake
- whether any contract interpretation became unambiguous after closer implementation work
- whether billed-data consistency was used ONLY descriptively, never to define the contract rule

Do NOT commit.
Do NOT push.
Do NOT create the GitHub repository yet.

Stop and wait for my review.
