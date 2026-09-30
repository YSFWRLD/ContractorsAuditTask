# Phase 1 — Civil Works source understanding and canonical data models

Tool: Claude Code (Claude Opus 5.5). Date: 2026-09-29. Given verbatim below.

---

We are now starting PHASE 1 of the Civil Works implementation.

Work ONLY inside:

ContractorsAuditTask/

The upstream task clone is:

ContractorsAuditTask/invoice-auditing-level-2/

Keep that upstream clone completely untouched.

Do NOT commit.
Do NOT push.
Do NOT create the GitHub repository yet.
Do NOT work on Drilling.
Do NOT inspect other candidates' repositories, forks, submissions, or solutions.

When Phase 1 is complete, STOP and report back to me.
Do not continue into Phase 2 until I explicitly tell you to.

==================================================
CURRENT STATE
==================================================

Phase 0 is complete.

The architecture already exists:

ContractorsAuditTask/
├── README.md
├── pyproject.toml
├── .gitignore
├── invoice-auditing-level-2/          # untouched upstream clone
├── src/contractor_audit/
│   ├── __main__.py
│   ├── cli.py
│   ├── shared/
│   └── domains/
│       └── civil_works/
├── tests/
├── artifacts/civil_works/
├── outputs/civil_works/
└── prompts/

Current Phase 0 tests:

20 passed

The architecture boundary is intentional:

SHARED:
- submission/result primitives
- money/minor-unit handling
- common 12-check enum
- paths
- domain protocol
- registry

CIVIL WORKS:
- contract extraction
- contract models
- schedules/rates
- supplements/amendments
- record parsing
- item interpretation
- pricing
- Civil Works-specific audit rules

Future Drilling must remain independently pluggable.

Do not weaken this separation.

==================================================
PHASE 1 GOAL
==================================================

Phase 1 is:

CIVIL WORKS SOURCE UNDERSTANDING AND CANONICAL DATA MODELS

The objective is to turn the raw Civil Works sources into trustworthy,
structured, source-cited artifacts and typed loaders.

DO NOT implement audit findings yet.

DO NOT decide which invoices are wrong yet.

DO NOT generate submission predictions yet.

This phase should answer:

"What exactly does the contract say, and what exactly is in the source data?"

==================================================
IMPORTANT DECISIONS FOR THIS PHASE
==================================================

1. UPSTREAM DATA

Keep:

invoice-auditing-level-2/

untouched.

Do not copy or rewrite the task data.

Do not decide the final vendoring/submodule strategy yet.

The existing path abstraction / CONTRACTOR_AUDIT_DATA override should continue
to work.

We will decide repository packaging later.

--------------------------------------------------
2. CONTRACT EXTRACTION
--------------------------------------------------

The Civil Works contract is:

invoice-auditing-level-2/civilwork/contract/CW-2025-0417-CIV.pdf

It is a 43-page image-only scanned PDF.

Do NOT introduce OCR as a runtime requirement for the final audit.

Instead, Phase 1 should create a VERSIONED, REVIEWED CONTRACT EXTRACTION under:

artifacts/civil_works/

You may use your visual/PDF reading capability during development.

The resulting audit should later be able to run from the reviewed extracted
artifact without re-OCRing the PDF.

IMPORTANT:

Never guess unreadable text or numbers.

If something cannot be read confidently:

- mark it unresolved
- preserve the source page
- explain the uncertainty

Do not silently infer it from invoice behavior.

==================================================
1. CONTRACT EXTRACTION
==================================================

Read the complete 43-page Civil Works contract.

Do not rely only on the Phase 0 page map.

Inspect the actual pages again.

Create a structured extraction with page-level provenance.

At minimum extract:

A. BASIC CONTRACT INFORMATION

- contract number
- currency
- commencement date
- original completion date
- working week
- retention percentage
- contract parties if relevant
- any relevant definitions

--------------------------------------------------
B. BILL OF QUANTITIES

For every contracted item needed for invoice pricing:

- item code
- exact contract description
- series
- unit
- base rate
- source page
- any notes or restrictions

Schedules appear around pages 17–19, but verify against the PDF.

--------------------------------------------------
C. ZONE FACTORS

Extract:

- applicable series
- zones
- factors
- exceptions
- source page

Do not assume Series E follows A–D if the contract does not say so.

--------------------------------------------------
D. INDEXED RATES

Extract Schedule 2A completely.

Identify:

- which items it applies to
- index definition
- base/reference index
- formula
- effective period mechanics
- rounding rules if stated
- required external/internal source data

If a required index value is not supplied in the task dataset,
record that fact explicitly.

Do not look it up externally.

--------------------------------------------------
E. USD RATES

Extract Schedule 2B.

Identify:

- applicable items
- USD rates
- conversion mechanism
- which month's exchange rate applies
- where the exchange rate comes from
- rounding requirements
- whether required FX values exist in the provided task data

No external lookup.

--------------------------------------------------
F. GROUND CLASS FACTORS

Extract:

- ground classes
- factors
- applicable item groups
- exceptions
- source page

--------------------------------------------------
G. NIGHT / REST-DAY RULES

Extract all relevant provisions including:

- night definition
- rest-day definition
- uplift percentage/factor
- eligibility
- any record/evidence requirement
- interaction with other adjustments
- source clauses/pages

Do not simplify wording prematurely.

--------------------------------------------------
H. VOLUME REBATES

Extract the complete schedule:

- thresholds
- bands
- percentage/factor
- whether cumulative
- measurement period
- unit/item scope
- threshold boundary wording
- application order
- source page

Record ambiguous threshold wording exactly.

Do not choose a pricing interpretation yet unless the contract is explicit.

--------------------------------------------------
I. QUANTITY LIMITS

Extract:

- item
- limit
- period
- consequence of exceeding the limit
- source page

Distinguish carefully between:

- "not payable above limit"
- "requires approval"
- "query"
- "part reject"

Do not assume a cap automatically means price only up to the cap.

--------------------------------------------------
J. REQUIRED RECORDS

Extract Schedule 5 completely.

For each relevant item/item family identify:

- required record type
- whether the record is a condition of payment
- signature requirements
- date/reference requirements
- consequence when missing
- source clause/page

This will later be critical.

--------------------------------------------------
K. DAYWORK

Extract Schedule 6:

- labour/equipment/material categories
- units
- rates
- required supporting records
- any markups
- source pages

--------------------------------------------------
L. PROVISIONAL / PRIME COST SUMS

Extract Schedule 7 and relevant governing clauses.

Do not assume they behave like normal BoQ quantities.

--------------------------------------------------
M. PRELIMINARIES

Extract Schedule 8 and relevant payment mechanics.

--------------------------------------------------
N. CONTRACT-YEAR / WEEK DEFINITIONS

Extract any provisions such as:

- contract year
- week
- minimum days worked
- date boundaries

Pay special attention to clause 47 / 47A and definitions affecting calculation.

--------------------------------------------------
O. VARIATIONS

Extract the Schedule of Variations.

Record:

- variation identifiers
- affected items/rates/rules
- effective dates
- approval/status if stated

--------------------------------------------------
P. SUPPLEMENTS AND AMENDMENTS

This is especially important.

Extract EVERY supplement and amendment on pages approximately 39–43.

For each instrument record:

- instrument name
- issue date
- effective date
- retroactive date if any
- affected clauses
- affected rates/items
- additions
- deletions
- replacement wording
- precedence
- source page

Known instruments appear to include:

- Supplement 1
- Amendment 1
- Supplement 2
- Amendment 2
- Amendment 3

But derive exact facts from the PDF itself.

Build an explicit precedence timeline.

Do not assume issue date == effective date.

==================================================
2. CONTRACT ARTIFACT DESIGN
==================================================

Create clean artifacts under:

artifacts/civil_works/

Suggested structure:

artifacts/civil_works/
├── contract_extraction.json
├── contract_extraction.md
├── contract_verification.md
└── source_inventory.json

Use the architecture that best fits the repo, but keep it simple.

`contract_extraction.json` should be machine-readable.

`contract_extraction.md` should be human-readable.

Every important extracted value must retain provenance such as:

{
  "value": ...,
  "source_page": 17,
  "source_section": "Schedule 1",
  "source_text": "...",
  "review_status": "verified"
}

Do not store huge unnecessary quotations.

Use short identifying source text only.

==================================================
3. CONTRACT VERIFICATION
==================================================

Create:

artifacts/civil_works/contract_verification.md

This must distinguish:

VERIFIED
AMBIGUOUS
UNREADABLE
NOT PROVIDED IN DATA

For high-impact values, independently inspect them twice.

High impact includes:

- BoQ rates
- units
- zone factors
- ground factors
- uplifts
- rebates
- quantity limits
- record requirements
- amendment effective dates
- changed rates

Do not mark something VERIFIED merely because invoice values seem to agree.

Invoice behavior is not proof of contract wording.

==================================================
4. APPLICATION MODELS / LOADERS
==================================================

Now create the actual Civil Works source models.

Likely files:

src/contractor_audit/domains/civil_works/models.py
src/contractor_audit/domains/civil_works/loaders.py

Use names that fit the architecture cleanly.

Load:

civilwork/invoices/applications.csv

and:

civilwork/invoices/application_lines.csv

Create typed canonical objects.

Application should preserve at least:

- invoice/application id
- contract reference
- period
- application date
- application total
- retention
- net payable
- adjustment
- retention released

Line should preserve at least:

- line id
- application id
- line number if present
- work date
- item code
- unit
- zone
- ground class
- quantity
- billed rate
- billed amount
- night flag
- record_ref

Use:

- Decimal for decimal quantities/rates where necessary
- integer minor units for money where appropriate
- explicit parsed dates

Never use binary float for money.

Keep raw source strings when normalization could lose evidence.

==================================================
5. SITE RECORD PARSER
==================================================

Create a parser for:

civilwork/records/*.txt

There are 9 known types:

CT
CV
DW
DX
JS
MO
PR
PS
PT

Do NOT match them to invoice lines yet beyond direct record reference lookup.

Parse at minimum:

- record type
- ticket/reference
- area
- date
- free-text description
- foreman signature/name/presence
- Engineer's representative signature/name/presence
- raw text
- source filename

Do not over-normalize the descriptions.

Preserve raw wording.

If formats differ by record type, allow Civil Works-specific parsers internally.

Do not force everything through brittle regex if the records differ structurally.

==================================================
6. RECORD INVENTORY
==================================================

Create a descriptive artifact containing:

- total records
- count by type
- malformed records
- duplicate ticket ids
- missing dates
- missing foreman signature
- missing Engineer's-rep signature
- description vocabulary / common phrase patterns

This is descriptive only.

Do not call anything an invoice error yet.

==================================================
7. SOURCE PROFILE
==================================================

Create:

artifacts/civil_works/source_profile.md

and/or a machine-readable equivalent.

Profile:

APPLICATIONS

- count
- unique IDs
- duplicate IDs
- contract references
- application date range
- period range
- totals distributions
- retention distributions
- adjustments
- retention releases

LINES

- count
- lines/application
- work-date range
- item codes
- units
- zones
- ground classes
- quantities
- night flags
- record_ref coverage

RECORD REFERENCES

- lines with a reference
- lines without one
- references that exist
- references that do not exist
- references reused across multiple lines
- records never referenced

DATE RELATIONSHIPS

Profile counts around:

- commencement date
- original completion date
- supplements
- amendment effective dates
- retroactive amendment dates

Do not flag anything merely for being outside the original completion date;
later amendments may matter.

==================================================
8. RAW ARITHMETIC PROFILE
==================================================

Without deciding whether rates are contractually correct, measure:

billed line amount
vs
quantity × billed rate

Use the contract's relevant monetary precision only if already explicitly known.

Report:

- exact reconciliations
- mismatches
- mismatch magnitude distribution

This is descriptive only.

Do NOT label mismatches as findings yet.

==================================================
9. CONTRACT REFERENCE PROFILE
==================================================

Profile application contract references.

For example Phase 0 observed some applications with:

CW-2024-0417-CIV

instead of:

CW-2025-0417-CIV

Do not automatically flag them yet.

Just record:

- reference
- count
- affected applications

We will interpret it during audit-rule phases.

==================================================
10. NO AUDIT LOGIC YET
==================================================

Phase 1 MUST NOT yet implement:

- invoice flags
- submission rows
- wrong-rate findings
- missing-record deductions
- night-uplift findings
- rebate findings
- cap findings
- amendment findings
- contract-reference findings
- confidence scores

You may build helpers needed for source understanding,
but no final audit judgments.

`pipeline.run()` may remain unimplemented or may stop after validated loading,
but it must NOT emit predictions yet.

==================================================
11. TESTS
==================================================

Add comprehensive tests for:

- contract artifact schema
- page provenance presence
- Decimal/minor-unit parsing
- applications loader
- lines loader
- date parsing
- record parser
- each record type
- malformed record handling
- duplicate/reference inventory
- source profiling
- task data remains untouched
- shared/domain architecture boundary remains intact

Use actual source fixtures sparingly plus small synthetic unit fixtures.

Do not rewrite source data during tests.

Run the entire suite, not only new tests.

==================================================
12. PROMPT PROVENANCE
==================================================

Save this prompt verbatim as:

prompts/01-phase1-contract-and-data-understanding.md

Update:

prompts/README.md

if that index now exists/needs updating.

This task requires versioned prompt disclosure.

==================================================
13. README
==================================================

Update the root README only as necessary to document:

- current architecture
- how Phase 1 artifacts are produced/used
- that the contract extraction is a reviewed development artifact
- that runtime audit reproduction will not require OCR
- upstream task data remains untouched

Do not write future audit results.

==================================================
14. QUALITY RULES
==================================================

Be conservative.

If the scan is unclear:

DO NOT GUESS.

If two readings exist:

PRESERVE BOTH.

If a value cannot be verified:

MARK IT UNVERIFIED.

Do not use invoice billed values to "correct" an uncertain contract extraction.

Do not search online.

Do not inspect GitHub forks or other participants' solutions.

Everything needed must come from:

- the provided Civil Works contract
- the provided invoice files
- the provided site records
- the task README/guidelines

==================================================
15. WHEN FINISHED
==================================================

STOP.

Do not start Phase 2.

Report back with:

1. CONTRACT EXTRACTION
   - sections extracted
   - number of BoQ items
   - number of factors/rate tables
   - supplements/amendments found
   - effective-date timeline
   - unreadable/ambiguous clauses

2. DATA LOADERS
   - applications loaded
   - lines loaded
   - record files parsed
   - malformed/unparsed records

3. RECORD PROFILE
   - counts by type
   - missing references
   - reused references
   - signature anomalies
   - any format variants

4. SOURCE PROFILE
   - application count
   - line count
   - item-code count
   - zones
   - ground classes
   - work-date range
   - contract-reference variants

5. HIGH-RISK CONTRACT INTERPRETATIONS
   List each unresolved interpretation that could materially change future
   invoice results.

6. FILES CREATED/MODIFIED

7. TEST RESULTS
   - total tests
   - passed/failed
   - any warnings

8. ARCHITECTURE CHECK
   Confirm Drilling can still be added without changing Civil Works internals.

9. GIT STATUS
   Confirm:
   - upstream task clone untouched
   - nothing committed
   - nothing pushed

10. RECOMMENDED PHASE 2
    Give a proposed Phase 2 plan, but DO NOT implement it.

Stop after reporting.
