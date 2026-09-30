# Drilling Phase 1 — contract extraction and reviewed contract model

Tool: Claude Code (Claude Opus 5.5). Date: 2026-09-29. Given verbatim below.

---

Implement DRILLING PHASE 1 ONLY: Contract Extraction and Reviewed Contract Model.

Stop when Phase 1 is complete and report back to me.

Do NOT continue to Phase 2.
Do NOT implement invoice ingestion.
Do NOT implement report parsing.
Do NOT implement chargeable quantities.
Do NOT implement pricing calculations.
Do NOT generate audit findings.
Do NOT generate Drilling outputs or submission.csv.
Do NOT modify Civil Works logic.
Do NOT commit or push anything.

We are intentionally working phase-by-phase.

==================================================
CURRENT PROJECT
==================================================

Local project folder:

ContractorsAuditTask

Current Drilling architecture already exists:

src/contractor_audit/domains/drilling/
    __init__.py
    sources.py
    pipeline.py

    contract/
    ingestion/
    audit/
    reporting/

tests/drilling/
prompts/drilling/
docs/drilling/

Phase 0 is complete.

Read first:

docs/drilling/phase0_inventory.md
prompts/drilling/00-drilling-architecture.md

Then independently inspect the actual Drilling source documents.

Do NOT blindly trust the Phase 0 notes.

The source documents are the source of truth.

==================================================
IMPORTANT SOURCE RULE
==================================================

The Drilling contract is approximately 42 scanned pages and may have no usable text layer.

Inspect the actual source pages.

Do not silently infer missing clauses from:

- Civil Works
- industry conventions
- another hospital/task/project
- internet sources
- other candidates
- other GitHub forks
- expected invoice behavior
- invoice prices

Everything in the Phase 1 contract model must be traceable to the supplied Drilling contract package.

No web research is needed or allowed for interpreting the contract.

If the documents do not answer something, record it as unresolved.

==================================================
PHASE 1 GOAL
==================================================

Build a reviewed, source-traceable representation of the Drilling contract.

This phase is about:

CONTRACT FACTS

not:

CONTRACT EXECUTION

At the end of Phase 1, later phases should be able to consume structured contract terms without reopening the scanned documents for every rule.

However, this phase must NOT yet calculate what any invoice should cost.

==================================================
1. INVENTORY THE CONTRACT DOCUMENTS
==================================================

Identify every Drilling contractual document provided.

Record for each:

- filename
- document type
- page count
- issue date if stated
- effective date if stated
- amendment/change number if applicable
- relationship to the base contract
- file hash/fingerprint

Verify the Phase 0 claim that there are:

- base contractual terms
- schedules
- appendices
- hidden/unlisted sections
- five contract changes/amendments

Do not assume five if the actual files say otherwise.

Produce a source manifest.

==================================================
2. TWO-PASS EXTRACTION
==================================================

Use a two-pass process.

PASS A — transcription/facts

Extract the actual contractual facts.

PASS B — review

Re-read the relevant source pages and verify every structured value against the source.

The final artifact must distinguish:

- directly stated fact
- reviewed interpretation
- unresolved ambiguity

Never mix them silently.

==================================================
3. CREATE A STRUCTURED CONTRACT ARTIFACT
==================================================

Create a machine-readable reviewed artifact under:

artifacts/drilling/

Choose a clear name such as:

artifacts/drilling/contract_terms.json

Use a versioned schema.

Design the schema cleanly because Phases 3 and 4 will rely on it.

At minimum include sections for:

A. CONTRACT IDENTITY

- contract number
- parties if relevant
- currency
- commencement date
- original expiry
- final expiry after extensions
- VAT
- rounding rule
- contractual year definition

B. DOCUMENT PRECEDENCE

Represent all stated precedence rules.

Include:

- base contract
- amendments/change orders
- schedules
- appendices
- variations
- any sections omitted from the table of contents

Do NOT invent precedence for documents where the contract does not define it.

If precedence is unclear, encode that as an ambiguity.

C. SERVICE CATALOG

For every contracted service:

- service code
- contractual description
- unit basis
- base rate/rates
- source page
- source section/table
- effective period if relevant
- whether amended
- whether indexed
- whether monthly-republished
- any service-specific conditions

Phase 0 observed approximately 39 service codes.

Verify the real number.

D. COST BUILD-UP TERMS

Capture, but DO NOT execute:

- hole-section factors
- well-class factors
- standby percentages
- order in which the contract says they apply
- exclusions from those factors
- any interaction rules

Store formula semantics structurally where possible.

Do not calculate invoice prices.

E. DEPTH-BAND TERMS

Capture PD-210 or the actual relevant service exactly.

Include:

- depth bands
- per-metre rates
- band boundaries
- split rules where a day crosses a boundary
- volume-tier definitions
- Contract Year rules
- source references

Do NOT decide unsupported questions such as whether volume is per-well or contract-wide.

Record both plausible readings if the contract is ambiguous.

F. PRICE INDEX TERMS

Capture:

- affected services
- index name/reference as written
- base period
- adjustment timing
- calculation language
- rounding
- effective dates

Do not calculate indexed rates yet.

G. MONTHLY REPUBLISHED RATES

Capture all contract tables governing services such as:

- HC-601
- DD-120

Verify the service codes from source.

Store:

- month/effective period
- rate
- currency
- source page
- interaction with amendments where explicitly stated

H. LOST-IN-HOLE TERMS

Capture:

- affected tools/services
- SAR values/rates
- monthly FX mechanism
- depreciation rule
- circulating-hour bands/rates
- any maximum/minimum
- effective dates
- source references

Do not perform currency conversion.

I. INVOICE-LEVEL DISCOUNT

Capture the DS-900 / invoice discount rule.

Verify from source:

- threshold
- percentage
- basis
- timing/order
- inclusions/exclusions
- whether threshold wording is >, >=, etc.

Do not apply it.

J. APPENDIX G / SERVICE WORD MAPPING

Transcribe the contract-provided translation/mapping table faithfully.

Do NOT "correct" strange entries.

If Appendix G says something surprising, preserve the contract wording exactly.

Phase 0 identified possible examples such as:

- mud motor mapping to multiple codes
- rotary steerable mapping to multiple codes
- MWD collar mapping to multiple codes
- gamma tool mapping to multiple codes
- potentially shifted logging-tool mappings
- unusual crew role mappings

Verify each from source.

Store:

- raw phrase
- mapped code
- mapped description if stated
- source page
- notes only where necessary

A strange mapping is NOT automatically an error.

The contract governs.

K. REPORT / CHARGEABILITY TERMS

Capture contractual language governing the daily report Parts A–E and clauses governing what may become chargeable.

Do NOT convert actual reports into services yet.

We only need the rules available for Phase 3.

L. AMENDMENTS / CONTRACT CHANGES

Represent every change separately.

For each:

- change/amendment number
- issued date
- effective date
- affected clauses/services
- previous value
- replacement value
- prospective vs retroactive language
- source page/document
- precedence statement if any

Phase 0 observed:

- two extensions
- rate substitutions
- 4% then 7% discounts on five main services
- one amendment issued 2026-08-17 but effective 2026-02-01
- a required single adjustment line for the backdated change

VERIFY ALL OF THIS.

Do not use Phase 0 as proof.

M. CONTRACT VALIDITY / BILLING RULES

Capture contractual rules concerning:

- service dates
- invoice dates
- billing periods
- invoice timing
- contract references
- VAT
- signatures if contractually required
- duplicates/repeats
- adjustment lines
- service eligibility dates

Again, do not create findings yet.

==================================================
4. SOURCE TRACEABILITY
==================================================

Every material contract term must have provenance.

At minimum:

{
  "source_file": "...",
  "page": ...,
  "section": "...",
  "source_text": "..."
}

The source_text should be only the minimum passage necessary to support the extracted fact.

Do not copy huge pages into JSON.

If page numbering differs between:

- PDF physical page
- printed page number

record both where useful.

We must be able to answer later:

"Why did the code use this term?"

and point directly back to the contract.

==================================================
5. AMBIGUITY REGISTER
==================================================

Create:

artifacts/drilling/contract_ambiguities.json

or an equivalently clear reviewed artifact.

Each ambiguity should include:

- id
- topic
- source location
- exact issue
- reading A
- reading B
- additional readings if necessary
- evidence supporting each
- whether one reading is currently preferred
- why
- confidence
- whether the ambiguity can affect invoice totals
- phase where it must be resolved
- status

Do NOT force a decision if the source does not support one.

Explicitly investigate Phase 0's open questions:

### A. Well-class factor and PD-210

Phase 0 says:

- Part IX says the well-class factor does NOT apply to PD-210
- Schedules 2 and 3 appear to say it DOES

Verify both.

Do not resolve by intuition.

### B. Appendix B worked example

Phase 0 says the example may:

- ignore the price index
- ignore/differ on the first rig-up hour deduction

Verify.

Determine whether this is:

- actual contradiction
- different scope
- example simplification
- misread in Phase 0

### C. DD-120 February 2026 overlap

Inspect interaction between:

- backdated amendment
- monthly republished rates
- service discount changes

Do not choose a final mathematical interpretation unless the contract clearly establishes one.

### D. Contract-Year volume tiers

Question:

Is cumulative volume counted:

- per well
or
- contract-wide?

Extract every relevant sentence.

Do not use feasibility ("40,000 m cannot be reached per well") as contractual proof.

It may be useful context but not source evidence.

### E. Backdated adjustment

Investigate:

- when adjustment must appear
- which invoice contains it
- whether "after" means strictly after issue date
- whether issue-date invoice counts
- whether reconciliation is per well or contract-wide

Keep unresolved readings if necessary.

### F. Missing call-offs

Record exactly which terms depend on unavailable call-offs.

Phase 0 believes call-offs establish:

- well class
- performance-drilling sections

Verify from the contract.

If required evidence is not in the supplied dataset, encode that explicitly.

Do NOT invent the values.

### G. Unlisted documents / precedence

Investigate:

- Part VIII
- Part IX
- Schedule 2C
- Schedule 2D
- Schedule 7
- Schedule 8
- Appendices D–G
- Schedule of Variations

Verify whether they are actually absent from the Contents.

More importantly:

determine whether the contract states how they rank.

If not, keep it unresolved.

==================================================
6. CONTRACT MODEL CODE
==================================================

Implement clean typed code in:

src/contractor_audit/domains/drilling/contract/

The code should LOAD and VALIDATE the reviewed contract artifact.

It should not contain dozens of duplicated hardcoded values if the artifact is the source of truth.

Use typed models/dataclasses/enums as appropriate.

For example, conceptually:

ContractTerms
ServiceDefinition
RatePeriod
ContractChange
FactorRule
DepthBand
VolumeTier
MonthlyRate
IndexRule
LostInHoleRule
ContractMapping
Ambiguity

Choose names that fit the existing project.

Keep the architecture simple.

Do not overengineer.

==================================================
7. EFFECTIVE-DATE MODEL
==================================================

Build the structural ability to represent temporal contract terms.

We will need later to ask things like:

"Which contractual rule/rate was in force on service date X?"

But Phase 1 should NOT calculate an invoice.

Make sure the contract model can represent:

- original terms
- amendments
- prospective changes
- retroactive changes
- extensions
- service additions/removals
- monthly rates

Do not prematurely flatten all amendments into one final rate table because later we need historical pricing.

==================================================
8. PRESERVE CONTRADICTIONS
==================================================

Very important:

Do not "clean up" contradictory contractual material.

Example:

if one schedule says:

well-class factor applies

and another clause says:

it does not

store both source facts plus the ambiguity.

Later phases will choose/read sensitivity switches.

The reviewed contract artifact must preserve the evidence rather than hiding the conflict.

==================================================
9. TESTS
==================================================

Add Phase 1 tests under:

tests/drilling/

Test at least:

### Source fidelity

- expected contractual documents are represented
- hashes/fingerprints match
- no source file silently omitted

### Contract model

- artifact loads
- schema/version valid
- required top-level fields present
- duplicate service codes rejected unless deliberately versioned by effective date
- money values are integer minor units where representable
- no float used for monetary amounts

### Dates

- commencement captured
- extension chain captured
- final expiry captured
- amendment issue/effective dates captured separately
- retroactive amendment remains distinguishable

### Service catalog

- expected verified number of service codes
- different unit bases represented
- amended services preserve historical rates
- added services have effective dates

### Appendix G

- strange/duplicate mappings are preserved rather than "corrected"
- mappings are contract data, not ingestion aliases

### Ambiguities

Tests should ensure important contradictory readings are represented, not silently collapsed.

At minimum pin:

- PD-210 well-class-factor conflict
- Contract-Year volume scope uncertainty
- backdated adjustment placement uncertainty
- missing call-off dependency
- unclear precedence of unranked material

### Architecture

Existing import-boundary tests must continue passing.

==================================================
10. NO INVOICE-DERIVED CONTRACT EXTRACTION
==================================================

This is critical.

Do NOT look at billed prices or invoice results and then choose the contract interpretation that matches them.

Contract extraction must be independent.

Invoice/report data may only be used at this phase where needed to understand data shape — never to decide which contract reading is correct.

Do not report things such as:

"this reading is correct because invoices use it."

That belongs, if anywhere, in a later consistency/sensitivity discussion and cannot serve as contractual proof.

==================================================
11. DOCUMENTATION
==================================================

Create:

docs/drilling/phase1_contract_extraction.md

Keep it useful and readable.

Include:

1. Documents reviewed
2. Contract structure
3. Service catalog summary
4. Amendment timeline
5. Pricing-component inventory
6. Appendix G observations
7. Important contradictions
8. Evidence not provided
9. Questions deliberately deferred
10. Exact artifacts produced

Do not turn this into a giant dump of the contract.

The JSON artifact is the detailed source of truth.

==================================================
12. PROMPT PROVENANCE
==================================================

Save this exact prompt as:

prompts/drilling/01-contract-extraction.md

Update:

prompts/README.md

if the project convention requires it.

==================================================
13. CIVIL WORKS FREEZE
==================================================

Civil Works is frozen.

Do not modify Civil Works files.

At the end verify Civil Works artifacts/outputs against the existing frozen snapshot mechanism.

Expected principle:

all Civil Works artifacts and outputs remain byte-identical.

Shared files may only be touched if absolutely necessary for the contract-model architecture.

Prefer not to touch shared files in Phase 1.

If you believe a shared change is necessary:

STOP and report why before making it.

==================================================
14. NO PHASE 2 WORK
==================================================

Phase 1 must NOT implement:

- invoice loaders beyond anything already shared
- daily report parser
- Report: join
- BHA run reconstruction
- well timeline
- report-to-service matching
- Appendix G execution against reports
- quantity derivation
- pricing
- depth calculation
- discount calculation
- lost-in-hole calculation
- VAT calculation
- audit findings
- confidence
- outputs/drilling predictions
- submission merge

Those belong to later phases.

==================================================
15. RUN VALIDATION
==================================================

Run:

- all Drilling tests
- full project tests
- architecture/import-boundary tests
- Civil Works frozen hash checks
- whitespace checks if applicable

`build-artifacts --domain drilling` should still NOT perform the complete Drilling pipeline unless Phase 1 architecture explicitly has a safe contract-only command.

Do not accidentally make the unfinished audit runnable as though complete.

==================================================
16. STOP AND REPORT
==================================================

When Phase 1 is complete, STOP.

Do not start Phase 2.

Report back with:

### 1. Sources reviewed

List every contractual document and page count.

### 2. Extracted contract facts

Summarize:

- contract dates
- currency/VAT/rounding
- number of service codes
- units
- factors
- depth bands
- volume tiers
- indices
- monthly rates
- lost-in-hole rules
- discounts
- amendment/change timeline

### 3. Amendment timeline

Give a compact chronological table:

document | issue date | effective date | effect

### 4. Ambiguities

For every unresolved material ambiguity:

- source clauses
- competing readings
- which later phase it affects

Do NOT hide awkward contradictions.

### 5. Missing evidence

Especially call-offs or any other contractual evidence referenced but not provided.

### 6. Appendix G

Report:

- number of mapping rows
- duplicate phrase mappings
- suspicious-looking entries
- confirmation they were preserved literally

### 7. Artifacts created

Exact filenames.

### 8. Code created/changed

Exact files.

### 9. Tests

- Drilling test count
- total project test count
- failures
- Civil Works byte-identity status

### 10. Scope check

Explicitly confirm:

- no invoice audit performed
- no report-to-service mapping performed
- no pricing performed
- no findings generated
- no Drilling submission generated
- no Civil Works logic changed
- nothing committed
- nothing pushed

### 11. Proposed Phase 2 interface

Based on what Phase 1 learned, briefly tell me what the ingestion layer will need to expose to Phase 3.

DO NOT IMPLEMENT IT YET.

Wait for my Phase 2 prompt.
