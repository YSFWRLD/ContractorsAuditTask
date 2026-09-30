# Phase 3 — Civil Works audit engine

Tool: Claude Code (Claude Opus 5.5). Date: 2026-09-29. Given verbatim below.

---

We are now starting Phase 3 of the Civil Works implementation.

IMPORTANT:
This is still Civil Works only.

Do NOT start Drilling.
Do NOT redesign Phase 1 or Phase 2.
Do NOT create the final combined submission yet.
Do NOT commit or push anything.

Phase 2 is complete and accepted.

Current Phase 2 state:

- 252 tests pass
- all 2,169 Civil Works records resolve
- 7,746 lines can be valued
- pricing is deterministic and contract-driven
- all contested interpretations are represented as named switches
- pricing traces include rule/clause/page/calculation/result
- exact Decimal / halala arithmetic only
- task source files remain untouched
- outputs/ remains empty
- no predictions or flags exist yet

The architecture must remain clean enough that Drilling can later be added as a sibling domain without copying Civil Works-specific logic into shared code.

==================================================
PHASE 3 GOAL
==================================================

Build the Civil Works AUDIT LAYER.

Phase 3 should take:

- parsed task data
- reviewed Civil Works contract model
- Phase 2 pricing/valuation engine
- record-quantity resolution
- interpretation switches

and produce:

1. invoice/application-level audit findings
2. line-level evidence for those findings
3. corrected payable totals where they can be defended
4. blank/uncertain corrected totals where they cannot
5. Civil Works-only draft predictions
6. audit artifacts and coverage reports
7. tests

DO NOT create the final cross-domain submission yet.

==================================================
1. ARCHITECTURE FIRST
==================================================

Before implementing rules, inspect the existing architecture.

Keep Civil Works-specific code under:

src/contractor_audit/domains/civil_works/

The audit layer should be clearly separated from:

- contract parsing
- pricing
- quantity interpretation
- valuation
- sensitivity analysis

A suggested shape is:

src/contractor_audit/domains/civil_works/
    audit/
        __init__.py
        models.py
        context.py
        findings.py
        confidence.py
        categories.py
        rules/
            __init__.py
            contract_reference.py
            period.py
            records.py
            quantity.py
            item_identity.py
            rates.py
            limits.py
            exclusions.py
            duplicates.py
            arithmetic.py
            completion.py
        engine.py
        reports.py

Do not follow this blindly if the existing repository has a cleaner convention.

The important architectural rule is:

PRICING tells us what should be paid.

AUDIT compares that against what was billed/provided and explains the discrepancy.

Do not put audit-condition branches inside pricing.py.

Also keep anything that could later be reused by Drilling in a genuinely shared package, but DO NOT prematurely generalize Civil Works rules.

==================================================
2. AUDIT MODELS
==================================================

Create explicit structured models for findings.

A finding should be able to carry at least:

- application/invoice id
- line id if applicable
- category
- short explanation
- observed value
- expected value if known
- monetary impact if determinable
- contract clause/reference
- source page
- confidence
- interpretation dependencies
- whether it affects corrected application total
- whether it makes the application total non-reconstructable

Do not use free-form dictionaries throughout the engine.

There should be one canonical finding representation.

==================================================
3. ERROR CATEGORIES
==================================================

Create a small controlled category vocabulary.

Do not invent dozens of hyper-specific labels.

Implement categories for the actual Civil Works checks, for example:

- contract_reference_mismatch
- work_outside_contract_period
- work_after_final_completion

- missing_record
- unsigned_record
- record_application_mismatch

- quantity_mismatch
- item_record_mismatch

- unit_rate_mismatch
- adjustment_missing
- adjustment_incorrectly_applied

- rebate_incorrectly_applied
- discount_incorrectly_applied

- daily_limit_exceeded
- exclusion_window_violation

- duplicate_line
- duplicate_record

- line_total_arithmetic
- application_total_mismatch

Names may be adjusted to fit the actual task schema and contract terminology.

Keep them deterministic and documented.

==================================================
4. IMPLEMENT THE 12 AUDIT CHECK FAMILIES
==================================================

Implement the Civil Works checks recommended after Phase 2.

--------------------------------------------------
A. CONTRACT REFERENCE
--------------------------------------------------

Validate the contract reference against the applicable Civil Works contract/instruments.

Detect clearly incorrect references.

Do not infer a mismatch merely because an amendment applies.

--------------------------------------------------
B. CONTRACT PERIOD / DATE WINDOW
--------------------------------------------------

Validate:

- work dates
- application dates where contractually relevant
- commencement / expiry / extension windows
- amendment effective periods

Use WORK DATE for rate applicability unless a clause explicitly says otherwise.

--------------------------------------------------
C. SUPPORTING RECORDS
--------------------------------------------------

Audit the supporting work records.

Check:

- record exists
- required signature/status exists where represented in the dataset
- record belongs to the correct application
- known missing record files are detected

Phase 2 identified three missing record files.

Pin them in tests.

Do not treat absence of a field that does not exist in the dataset as misconduct.

--------------------------------------------------
D. QUANTITY AGAINST RECORD
--------------------------------------------------

Compare billed quantity against the quantity established by the supporting record and quantity rules.

Use the existing quantity engine.

Do not re-parse text independently inside the audit rule.

Respect:

- first-hour rule
- surveyed quantity rule
- five-day-week rule
- daily limits
- exclusion rules

--------------------------------------------------
E. ITEM IDENTITY AGAINST RECORD
--------------------------------------------------

Check that the billed BOQ item is compatible with the supporting record.

Example noted in Phase 2:

B.23.020 line citing a PT record.

Build this as a principled record/item compatibility check.

Do not hard-code only that example.

--------------------------------------------------
F. RATE / PRICING
--------------------------------------------------

Use the Phase 2 pricing engine as the source of truth.

Detect:

- wrong base rate
- wrong amendment rate
- wrong monthly rate
- wrong indexed rate
- wrong USD conversion handling
- missing/incorrect zone factor
- missing/incorrect ground-class factor
- missing/incorrect night uplift
- missing/incorrect rest-day uplift
- rebate errors
- discount errors

DO NOT duplicate pricing formulas inside audit rules.

The audit layer should compare billed amounts against a PricingTrace from Phase 2.

--------------------------------------------------
G. LIMITS
--------------------------------------------------

Detect contractual quantity/daily-limit breaches.

Separate:

1. detecting a breach
2. knowing the exact payable correction

A breach can be confidently flagged even when the corrected total is not reconstructable.

--------------------------------------------------
H. EXCLUSION WINDOWS
--------------------------------------------------

Implement exclusion-window findings using the current working interpretation switch.

Current working reading:

same day counts as inside the window.

But this remains unresolved.

Any finding depending on this reading must record that dependency.

--------------------------------------------------
I. DUPLICATES
--------------------------------------------------

Detect true duplicate billing using stable evidence such as:

- same record
- same item
- same work event/date
- same quantity where appropriate

Do not flag two legitimate repeated services merely because descriptions match.

Distinguish:

duplicate line

from:

duplicate supporting record / duplicate work event

if the data supports that distinction.

--------------------------------------------------
J. LINE ARITHMETIC
--------------------------------------------------

Check billed line arithmetic independently from contract pricing.

For example:

quantity × billed unit rate

against billed line amount.

Use exact arithmetic.

A line can have BOTH:

- arithmetic error
- rate error

if both are independently true.

--------------------------------------------------
K. APPLICATION TOTAL
--------------------------------------------------

Verify the application/invoice header total against its billed lines.

Keep this separate from the corrected contractual total.

--------------------------------------------------
L. WORK AFTER COMPLETION
--------------------------------------------------

Phase 2 found two lines after final completion.

Audit them explicitly.

Determine from the contract whether they are:

- non-payable
- outside scope
- otherwise handled

Do not silently price them as normal work.

==================================================
5. TWO OPEN DECISIONS
==================================================

Phase 2 identified two issues that must NOT be hidden.

--------------------------------------------------
DECISION A:
OUTSIDE-MEASURED-TOTAL CORRECTIONS
--------------------------------------------------

Examples include:

- Amendment 3 backdated-rate adjustment
- retention
- retention release
- "deduct from next valuation" mechanisms

Do NOT automatically add these into the application's expected measured-work total.

Use this working principle:

`expected_total` should represent the corrected total of the amount that THIS application actually measures/bills.

Contractual adjustments that are explicitly settled outside that measured total should be:

- recorded as findings/adjustments
- quantified separately when possible
- NOT silently folded into expected_total

Examples:

- backdated rate adjustment payable through another valuation mechanism
- retention release
- correction expressly stated to be deducted from the next valuation

However, verify the task's required output schema before implementing this.

If the task definition clearly requires a different meaning of expected_total, stop and report the conflict.

Document this decision clearly.

--------------------------------------------------
DECISION B:
DO DISALLOWED QUANTITIES COUNT TOWARD REBATE BANDS?
--------------------------------------------------

Do NOT pretend the contract settles this if it does not.

Keep both interpretations available as a switch:

A:
all measured quantities count toward rebate progression

B:
only payable quantities count toward rebate progression

For the main audit:

use the interpretation that is most directly supported by the contract's wording.

If neither is clearly supported:

- keep the working interpretation already used in Phase 2
- record the dependency
- calculate sensitivity
- lower confidence / blank corrected total where this ambiguity materially changes the conclusion

Do NOT select the interpretation because it matches billed values better.

Report how many:

- lines
- applications
- findings
- corrected totals

change under this switch.

==================================================
6. EXPECTED TOTAL POLICY
==================================================

Build application-level reconstruction conservatively.

An application gets a corrected expected total only if all monetary components needed to reconstruct its measured payable total are sufficiently determined.

Return blank / unresolved expected total if, for example:

- an important line identity is unknown
- payable quantity cannot be resolved
- an unresolved interpretation materially changes the total
- exclusion/limit consequence is known but exact payable amount is not
- a required rate cannot be established

But:

a finding can still be emitted even when total reconstruction is blank.

Do not allow:

"we know something is wrong"

to become:

"therefore we know the corrected total."

==================================================
7. CONFIDENCE
==================================================

Do not invent fake statistical probabilities.

Confidence should reflect evidence quality.

Create a deterministic confidence policy based on finding dependencies.

Example bands:

HIGH:
direct deterministic contract/data violation

MEDIUM:
depends on a defensible but unresolved interpretation

LOW:
finding materially depends on one of the least certain readings

For machine output, map these to numeric values consistently.

Document the mapping.

An application with multiple findings should not automatically inherit the highest confidence.

The prediction confidence should reflect the weakest material dependency behind the conclusion.

==================================================
8. FINDING TRACEABILITY
==================================================

Every finding must answer:

WHY WAS THIS FLAGGED?

A reviewer should be able to follow:

billed line
→ supporting record
→ applicable contract provision
→ expected rule/value
→ comparison
→ finding

Include clause/page references wherever Phase 1/2 already captured them.

Reuse existing PricingTrace data.

Do not create a second parallel citation system.

==================================================
9. CIVIL WORKS DRAFT OUTPUT
==================================================

Generate a Civil Works-only draft output.

For example:

outputs/civil_works/
    findings.jsonl
    application_audit.csv
    audit_summary.md
    coverage.md
    uncertainty_report.md
    sensitivity.md

Use the repository's existing conventions if they differ.

DO NOT yet create the final multi-domain submission.

The Civil Works draft should make it easy to inspect:

- application id
- flagged/not flagged
- categories
- billed total
- expected total if reconstructable
- confidence
- reason expected total is blank
- interpretation dependencies

==================================================
10. COVERAGE REPORT
==================================================

Produce a report containing:

- number of applications
- number of lines
- flagged applications
- unflagged applications
- reconstructable corrected totals
- blank corrected totals

Break blank totals down by reason.

Break findings down by category.

Also report:

- how many findings depend on each unresolved interpretation
- how many applications change under each sensitivity switch

Do not hide unresolved cases.

==================================================
11. TESTS
==================================================

Add thorough tests.

At minimum test:

- every finding category
- no false finding on a clean synthetic case
- contract period boundaries
- amendment boundaries
- missing records
- unsigned records where represented
- record/application mismatch
- quantity mismatch
- record/item mismatch
- wrong rate
- zone factor
- ground factor
- night/rest-day uplift
- rebate
- discount
- daily limit
- exclusion boundary
- duplicates
- arithmetic
- application total
- work after completion

Also test:

- one line can have multiple independent findings
- finding order is deterministic
- output is deterministic
- no floats
- no network dependency
- source task files unchanged
- Phase 1/2 artifacts unchanged unless audit artifacts intentionally reference them

And crucially:

pricing tests must continue passing unchanged.

==================================================
12. REGRESSION
==================================================

Run the complete test suite.

Verify:

- Phase 1 still passes
- Phase 2 still passes
- pricing outputs/artifacts are unchanged
- reviewed contract JSON unchanged
- task source files unchanged
- sensitivity results unchanged unless a genuine bug is found

If you discover a genuine Phase 2 bug:

STOP.

Report it before changing Phase 2 behavior.

Do not quietly repair earlier phases during the audit phase.

==================================================
13. DO NOT OPTIMIZE AGAINST BILLED RESULTS
==================================================

Very important:

The billed data may be used to DETECT discrepancies.

It must not be used to CHOOSE the contract interpretation that minimizes discrepancies.

Examples:

BAD:
"Interpretation A matches 99% of billed values, so choose A."

GOOD:
"The contract supports A more directly. After choosing A, observed billing matches X/Y lines."

Sensitivity may report consistency descriptively, as Phase 2 already does.

==================================================
14. DOCUMENTATION
==================================================

Update:

- docs/civil_works/decision_log.md
- README.md
- prompts/README.md

Create:

prompts/03-phase3-audit-engine.md

Document:

- audit categories
- expected-total policy
- confidence policy
- the two unresolved decisions
- finding traceability
- coverage limitations
- any newly discovered ambiguities

==================================================
15. STOP BEFORE FINAL SUBMISSION
==================================================

At the end of Phase 3:

DO NOT:

- implement Drilling
- produce the final cross-domain submission
- commit
- push
- create a GitHub repository
- optimize findings to improve apparent accuracy

Stop and report back.

==================================================
FINAL REPORT
==================================================

When Phase 3 is complete, report:

1. Files created
2. Files modified
3. Final architecture
4. Audit checks implemented
5. Finding categories
6. Total applications/lines reviewed
7. Flagged applications
8. Finding counts by category
9. Corrected totals reconstructable
10. Blank totals and reason breakdown
11. Findings/totals affected by each unresolved interpretation
12. Results of the two open-decision sensitivity runs
13. Any new ambiguities found
14. Tests added
15. Total tests passing
16. Confirmation Phase 1/2 remained unchanged
17. Confirmation task source files remained untouched
18. Git status
19. Recommended Phase 4 scope

Do not continue into Phase 4.

Wait for my review.
