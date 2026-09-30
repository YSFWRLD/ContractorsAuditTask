# Drilling Phase 2 — data ingestion and structural validation

Tool: Claude Code (Claude Opus 5.5). Date: 2026-09-29. Given verbatim below.

---

Implement Drilling Phase 2 only.

DO NOT start Phase 3.
DO NOT map report terms to service codes.
DO NOT price anything.
DO NOT generate audit findings.
DO NOT resolve Phase 1 contract ambiguities.
DO NOT modify Civil Works behavior.

We are continuing the phased Drilling implementation inside the existing clean multi-domain architecture.

Current state:

- Civil Works is complete and frozen.
- Drilling Phase 0 is complete.
- Drilling Phase 1 is complete.
- Phase 1 created the reviewed contract model and ambiguity register.
- Full suite currently passes 396 tests.
- Civil Works artifacts/outputs must remain byte-identical.

==================================================
PHASE 2 GOAL
==================================================

Build a robust, typed ingestion layer for ALL Drilling operational data.

The output of this phase should be a clean internal representation that Phase 3 can consume.

This phase is about:

RAW DATA
→ PARSED TYPED OBJECTS
→ STRUCTURAL VALIDATION
→ INDEXES / TIMELINES

NOT:

RAW DATA
→ SERVICE IDENTIFICATION
→ PRICING
→ AUDIT FINDINGS

Those come later.

==================================================
1. FIRST: INVENTORY ALL DRILLING INPUT DATA
==================================================

Before writing parsing logic, inspect every Drilling input file.

Identify:

- invoice files
- invoice line files
- daily drilling reports
- report formats / variants
- supporting operational files
- filenames
- extensions
- row / record counts
- encoding
- schemas
- identifiers
- date formats
- monetary formats
- nullable fields
- repeated structures

Create:

docs/drilling/phase2_data_inventory.md

It should document the actual discovered structure.

Do not infer fields that are not present.

==================================================
2. CLEAN ARCHITECTURE
==================================================

Keep all Drilling ingestion code inside:

src/contractor_audit/domains/drilling/

Suggested structure:

src/contractor_audit/domains/drilling/
    contract/
        ...
    ingestion/
        __init__.py
        models.py
        invoices.py
        reports.py
        loaders.py
        indexes.py
        validation.py
    reporting/
        ...

You may adjust this if the repository's existing conventions suggest something cleaner.

Important:

Do NOT put Drilling-specific parsing rules in shared/core modules unless they are genuinely domain-neutral.

Civil Works must remain isolated.

==================================================
3. TYPED INVOICE MODEL
==================================================

Create typed invoice/header models containing all fields actually present.

At minimum, where supported by source data, preserve:

- invoice identifier
- contractor / contract reference
- invoice date
- well identifier
- well class AS STATED BY CONTRACTOR
- invoice amount
- currency
- period / date range
- other header metadata

Money:

- represent money in integer cents where possible
- do not use binary float

Preserve raw source values where useful for traceability.

Do not infer well class from the contract.

If contractor-stated well class exists, store exactly what was stated.

==================================================
4. TYPED LINE MODEL
==================================================

Create typed invoice-line models.

Preserve all source fields.

Where present, support:

- line id / number
- invoice id
- service / description text
- nullable service date
- hole section
- depth / depth interval
- quantity
- stated unit
- stated unit rate
- amount
- report reference
- other source metadata

Use Decimal for non-money numeric quantities/rates where appropriate.

Do not map descriptions to contract service codes.

Do not decide whether a rate is correct.

==================================================
5. DAILY REPORT PARSING
==================================================

Parse each drilling daily report into a typed object.

Each parsed report should be keyed by the report's own:

Report:

field.

Capture, where actually present:

PART A

- report id
- well
- date
- operational status
- hole section
- start/end depths
- drilling/circulating/reaming/etc. hours as printed
- BHA run
- tools
- crew
- daily counts
- any other structured operational values

Keep tool/crew names as the VERBATIM rig wording.

Do NOT map them to Appendix G service codes yet.

PART B

Parse the run block.

Preserve all fields.

PART C / D / E

Parse their structures without trying to interpret them contractually.

SIGNATURES

Capture:

- printed signatory roles
- actual names/signatures where present
- blanks explicitly

Do not decide in Phase 2 whether a missing signature invalidates billing.

==================================================
6. REPORT VARIANTS
==================================================

Do not assume all reports share one perfect template.

Detect and document:

- format variants
- missing sections
- malformed rows
- duplicated labels
- unexpected values
- blank fields

Parsing must fail safely.

Do not silently fabricate defaults.

Store parse anomalies explicitly.

==================================================
7. INDEXES
==================================================

Build deterministic indexes useful to Phase 3.

At minimum:

reports_by_id

reports_by_well_and_date

invoice_lines_by_report_reference

invoices_by_well

lines_by_invoice

Use explicit duplicate handling.

Do not silently overwrite duplicate keys.

==================================================
8. WELL TIMELINES
==================================================

Construct structural well timelines.

For each well, derive from observed source data:

- first observed date
- last observed date
- ordered report list
- report gaps if determinable
- invoice periods linked to well

This is structural reconstruction only.

Do not infer contract eligibility.

==================================================
9. BHA RUN RECONSTRUCTION
==================================================

Reconstruct observed BHA runs across reports.

For each stated run, preserve:

- run identifier
- recorded first date if source gives it
- recorded last date if source gives it
- observed first report date
- observed last report date
- participating reports
- discrepancies between recorded and observed boundaries

Do not translate the run into billable services.

==================================================
10. STRUCTURAL VALIDATION REPORT
==================================================

Generate a Phase 2 structural validation report.

It should detect things such as:

- invoice line references missing report
- duplicate report ids
- report referenced by multiple invoices where suspicious
- duplicate invoice ids
- broken well references
- inconsistent contract-reference strings
- malformed dates
- invoice dates outside expected data shape
- report dates outside invoice period
- mismatched well ids between invoice/report
- missing required source fields
- duplicate line ids
- impossible numeric parsing
- blank signatures
- parse anomalies

Important:

These are STRUCTURAL observations.

Do not label them contractual billing errors yet.

Create something like:

outputs/drilling/phase2_structural_validation.json
outputs/drilling/phase2_structural_validation.md

But do NOT create the final Drilling audit output.

==================================================
11. SOURCE PROVENANCE
==================================================

Every parsed object should be traceable to its source.

Preserve enough metadata to identify:

- source filename
- row / record / report
- original identifier
- raw source value where normalization occurred

Do not lose information during normalization.

==================================================
12. TESTS
==================================================

Add strong tests under:

tests/drilling/

Cover at minimum:

- every input file loads
- invoice counts
- line counts
- report counts
- typed money behavior
- Decimal quantities
- date parsing
- nullable fields
- report IDs
- duplicate handling
- report variants
- malformed fields
- indexes
- well timelines
- BHA run reconstruction
- source provenance
- structural validation
- signatures
- missing references

Add tests proving:

- no Phase 2 code maps rig words to service codes
- no Phase 2 code executes contract rates
- no audit finding is generated
- no Drilling submission is generated

==================================================
13. CIVIL WORKS REGRESSION
==================================================

Run the full suite.

Verify:

- all Civil Works tests still pass
- all Civil Works artifacts remain byte-identical
- all Civil Works outputs remain byte-identical
- no Civil Works code changed unless absolutely unavoidable

If a shared file must change, explain exactly why.

Prefer no shared changes.

==================================================
14. PHASE 2 DOCUMENTATION
==================================================

Create:

docs/drilling/phase2_ingestion.md

Document:

- source files
- schemas
- parser design
- report variants
- indexes
- structural validation
- known data-quality issues
- what Phase 2 intentionally does NOT do

Also save this prompt verbatim as:

prompts/drilling/02-data-ingestion.md

Update:

prompts/README.md

only as needed.

==================================================
15. DO NOT RESOLVE PHASE 1 AMBIGUITIES
==================================================

Phase 1 intentionally left contract ambiguities open.

Do not use invoice behavior to decide them.

In particular do NOT yet decide:

- PD-210 class-factor conflict
- standby section-factor conflict
- Appendix B index contradiction
- DD-120 rig-up treatment
- DD-120 circulating vs back-reaming
- Feb 2026 DD-120 precedence
- volume-tier basis
- Contract Year 2 interpretation
- backdated adjustment scope
- records/signature contractual effect
- lost-in-hole valuation precedence
- DS-900 threshold basis
- call-off-dependent well class / eligibility

Phase 2 may expose evidence relevant to these.

Record the evidence.

Do not choose the interpretation.

==================================================
16. END-OF-PHASE REPORT
==================================================

When Phase 2 is complete, STOP.

Do not begin Phase 3.

Report back with:

1. exact source files inspected
2. invoice count
3. invoice-line count
4. report count
5. number of report format variants
6. wells found
7. parsed BHA runs
8. broken/missing report references
9. duplicate identifiers
10. structural anomalies
11. any previously unknown fields discovered
12. exact files created/changed
13. Drilling tests passed
14. full-project tests passed
15. Civil Works regression status
16. anything Phase 3 needs to know

Then propose the Phase 3 interface, but DO NOT implement it.

==================================================
IMPORTANT
==================================================

Keep this phase boring and trustworthy.

Do not try to impress by auditing early.

Phase 2 succeeds if we can confidently say:

"We know exactly what data we have, we can parse it reproducibly, every value is traceable to source, and the next phase can reason about billing without needing to touch raw files."

Nothing should be committed or pushed unless I explicitly ask.
