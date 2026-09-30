# Drilling Phase 3 — service mapping and evidence-backed quantities

Tool: Claude Code (Claude Opus 5.5). Date: 2026-09-30. Given verbatim below.

---

Implement Drilling Phase 3 only.

Do NOT move into pricing, invoice findings, final audit decisions, or submission generation yet.

The purpose of this phase is:

REPORT DATA
→ CONTRACT SERVICE CANDIDATES
→ EVIDENCE-BACKED CHARGEABLE QUANTITIES

Nothing more.

At the end, stop and report back to me. Do not begin Phase 4 until I explicitly approve it.

==================================================
CURRENT FROZEN STATE
==================================================

Civil Works is already complete and frozen.

Do not modify Civil Works code, tests, outputs, artifacts, docs, or behavior.

Phase 2 Drilling is complete.

Current validated Drilling dataset:

- 1,906 invoices
- 91,244 invoice lines
- 8,151 daily drilling reports
- 214 wells
- 1,369 BHA runs
- 84 Drilling tests currently passing
- 432 full-project tests currently passing with `-W error`

Phase 2 artifacts:

artifacts/drilling/phase2_structural_validation.json
artifacts/drilling/phase2_structural_validation.md

Existing Drilling architecture:

src/contractor_audit/domains/drilling/

with:

ingestion/
reporting/
pipeline.py

Phase 1 also produced the Drilling contract model and contract ambiguities.

Use those existing structures instead of rebuilding them.

==================================================
PHASE 3 GOAL
==================================================

Build a deterministic interpretation layer that converts the parsed drilling reports into candidate contractual service quantities.

The output of Phase 3 should answer questions like:

- Which contract service code(s) could this report evidence?
- What quantity is supported?
- What source field produced that quantity?
- Is the mapping deterministic or ambiguous?
- Which interpretation switch affects it?
- What evidence supports the mapping?

It must NOT answer:

- What should the invoice price be?
- Is the invoice wrong?
- What is the corrected total?
- Should an invoice be flagged?

Those belong to later phases.

==================================================
1. PRESERVE CLEAN ARCHITECTURE
==================================================

Keep Drilling domain code modular and easy to reason about.

Prefer something like:

src/contractor_audit/domains/drilling/
    ingestion/
        ...existing Phase 2 code...

    contract/
        ...existing Phase 1 code...

    interpretation/
        __init__.py
        models.py
        service_mapping.py
        quantities.py
        run_quantities.py
        well_quantities.py
        ambiguity.py
        switches.py
        provenance.py

    reporting/
        ...existing reports...
        phase3_mapping_report.py

    pipeline.py

You may adapt the exact names if the current repository structure suggests something cleaner.

Important:

Do NOT create giant files.

Separate:

- service identity
- quantity derivation
- ambiguity handling
- interpretation switches
- provenance

The design should also leave room for later:

Phase 4:
pricing and contract rule application

Phase 5:
invoice comparison / findings

Phase 6:
final outputs

==================================================
2. USE PHASE 1 CONTRACT MODEL
==================================================

Do not manually duplicate contract vocabulary.

Use the existing Phase 1 contract structures.

Especially use:

ContractTerms.codes_for_report_term

or the repository's equivalent if the actual API differs.

Phase 2 established:

- drilling reports contain 15 tool words
- 5 crew roles
- no service codes

Therefore mapping must be:

report wording
→ contract vocabulary
→ candidate service code(s)

Do NOT map based on billed invoice rates.

Do NOT use invoice amount to choose identity.

==================================================
3. SERVICE MAPPING MODEL
==================================================

Create an explicit mapping result type.

For example conceptually:

ServiceCandidate:
    service_code
    source_term
    report_id
    source_field
    confidence/status
    ambiguity_id
    provenance

MappingResult:
    deterministic
    candidates[]
    unresolved_reason

Use typed models.

Every result must preserve provenance back to the exact report field.

Possible statuses should clearly distinguish things like:

- IDENTIFIED
- AMBIGUOUS
- NOT_APPLICABLE
- UNSUPPORTED
- UNRESOLVED_INTERPRETATION

Do not silently collapse ambiguity.

==================================================
4. APPENDIX G MAPPING
==================================================

Implement report-term → service-code mapping from the contract.

Where a report term maps to exactly one contractual service:

record the deterministic service code.

Where a term maps to multiple codes:

retain all valid candidates unless report context legitimately disambiguates them.

Phase 2 specifically noted:

AMB-16:
some report terms map to two Appendix G codes and Part E context may distinguish them.

Implement this as explicit logic with provenance.

Do not choose a code because the billed invoice happens to contain one.

==================================================
5. RECORDED QUANTITIES
==================================================

Convert report evidence into typed quantities.

Each quantity must include:

- service candidate/code
- quantity
- unit/basis
- report id
- well
- date
- source field
- raw source value
- derivation method
- interpretation switch if relevant

Support at minimum the categories discovered in Phase 2:

### Crew / person-day quantities

Use crew counts from reports.

Preserve:

- role
- count
- date
- report

Do not assume two different crew roles map to the same service unless the contract says so.

### Rental day quantities

Use tools/equipment present in the hole.

Derive daily rental quantities only from evidence in the reports.

Do not infer undocumented days.

### Hour-based quantities

Support:

- circulating hours
- back-reaming hours
- any other contract-defined drilling hours

Important:

Phase 2 established that run totals in Part B are repeated on every daily report.

DO NOT sum repeated run totals across days.

Use daily values where the contract requires daily hours.

If a run-level value is required, derive it exactly once using the run timeline.

### Count-based services

Support quantities such as:

- gyro surveys
- pressure points
- wiper trips
- clean-out runs

Use the actual source field.

### Metres / depth-based quantities

Implement daily metres with provenance.

Phase 2 found:

- metres logged and reamed equal the BHA run's depth advance wherever non-zero.

Do not silently decide AMB-24 yet.

Represent competing interpretations explicitly if needed.

For PD-210:

support depth-band splitting if required by the contract model.

Do not price the bands.

Only produce quantities assigned to the relevant band/service candidate.

### Once-per-run items

Use the validated BHA run indexes.

Generate a quantity once per run where supported.

Do not accidentally emit the same run-level quantity once per report/day.

### Once-per-well items

Use well timelines.

Generate only once per well where the contract supports that structure.

### Lost-in-hole

Produce the evidence-backed quantity but preserve AMB-22.

Phase 2 evidence:

- Part E hours equal the lost tool's accumulated hours in 54/54 relevant reports
- whole-well total matches in only 27

Do not silently resolve the contract interpretation.

==================================================
6. INTERPRETATION SWITCHES
==================================================

Every material unresolved contract reading must become an explicit switch.

Do NOT bury these assumptions inside mapping logic.

Include at minimum the ambiguities already identified:

- rig-up hour
- DD-120 hours
- DD-102
- HC-630
- DD-121
- metre source
- Appendix G literal vs shifted reading
- AMB-22 lost-in-hole hours
- AMB-24 metres
- standby interpretations AMB-05 / AMB-06
- AMB-12 backdated adjustment where relevant to interpretation

If some of these belong to pricing rather than quantity interpretation, do NOT implement their pricing behavior yet.

Instead define the switch/interface now and document:

"used later in pricing phase"

Each switch should have:

- stable name
- possible values/readings
- default if Phase 1 already selected one
- source ambiguity id
- explanation

Do not invent a preferred reading just for coverage.

==================================================
7. STANDBY EVIDENCE
==================================================

Phase 2 found:

290 of 381 standby days still contain circulating hours.

Do not assume:

standby => zero other activity

unless the contract explicitly says so.

Preserve both facts.

If standby changes which service is chargeable and the contract reading is unresolved, mark it as an interpretation dependency.

==================================================
8. REPORT REFERENCES
==================================================

Use the report's own `Report:` field as the canonical report identity.

Do NOT join by filename.

Phase 2 verified:

- every report reference resolves
- every report is cited
- 63 lines with no report reference are all DS-900 discount lines
- one report is cited by two invoices:
  DDR-063-20260427
  referenced by MDS-01340 and MDS-01352

Phase 3 must not treat multiple invoice references as duplicated report evidence automatically.

Keep report evidence independent of invoice association.

==================================================
9. DUPLICATE REPORT/CODE PAIRS
==================================================

Phase 2 found:

189 report-and-code pairs appear on multiple invoice lines.

184:
PD-210 with different depth intervals

5:
no distinct intervals:
- MW-301 ×2
- LW-401 ×2
- LW-411 ×1

Do NOT classify these as billing duplicates in Phase 3.

Phase 3 only needs to expose the relationship so later phases can evaluate it.

Create indexes/reporting that allow Phase 4/5 to see:

report
service code
invoice lines referencing it
intervals if any

==================================================
10. NO BILLED-DATA LEAKAGE
==================================================

Invoice billed data may be used only for descriptive coverage comparison.

It must NOT decide:

- service identity
- quantity
- ambiguity resolution
- contract interpretation

Specifically do NOT use:

- unit price
- line amount
- invoice total
- billed service code

as proof of what a report means.

If billed service codes are compared, keep that in a separate reporting-only module.

==================================================
11. PHASE 3 ARTIFACTS
==================================================

Create deterministic artifacts such as:

artifacts/drilling/phase3_service_mapping.json
artifacts/drilling/phase3_quantities.json
artifacts/drilling/phase3_ambiguities.json

and readable reports such as:

artifacts/drilling/phase3_service_mapping.md
artifacts/drilling/phase3_quantity_summary.md

Do NOT create final invoice audit outputs yet.

Respect the existing frozen Civil Works rule about `outputs/drilling`.

If the current project intentionally reserves `outputs/` for final audit outputs, keep Phase 3 artifacts under `artifacts/drilling/`.

==================================================
12. REQUIRED PHASE 3 METRICS
==================================================

At the end compute:

- total reports interpreted
- reports with at least one mapped service
- deterministic service mappings
- ambiguous service mappings
- unsupported/unmapped report terms
- quantities generated by unit type:
  - person-days
  - rental days
  - hours
  - counts
  - metres
  - run-level units
  - well-level units
  - lost-in-hole units
- mappings depending on interpretation switches
- reports affected by each ambiguity
- service-code coverage
- contract services never evidenced by reports
- report terms mapping to more than one code
- report/code relationships with multiple billed lines

Do not call these invoice findings.

They are mapping/coverage statistics.

==================================================
13. TESTS
==================================================

Add strong tests.

At minimum test:

### Provenance

Every generated quantity points to a valid report and source field.

### Mapping

Known report vocabulary maps only to allowed contract candidates.

### Ambiguity

Multi-code contract terms remain ambiguous unless valid report context resolves them.

### Repeated run totals

Part B run totals are not summed once per day.

### Run-level services

Generated exactly once per run.

### Well-level services

Generated exactly once per well.

### Daily quantities

Generated only from that day's report evidence.

### PD-210

Depth intervals/bands are handled without double counting.

### Lost-in-hole

AMB-22 remains an explicit interpretation dependency.

### Metres

AMB-24 remains an explicit interpretation dependency unless Phase 1 already conclusively resolved it.

### Standby

A standby report may still contain circulating hours.

### No leakage

Construct tests proving mapping results do not change when billed price, line amount or invoice total changes.

### Civil Works regression

All frozen Civil Works artifacts and outputs remain byte-identical.

### Phase 2 regression

Phase 2 Drilling structural artifacts remain byte-identical unless a genuine Phase 2 bug is found.

Do NOT "clean up" old artifacts gratuitously.

==================================================
14. DOCUMENTATION
==================================================

Create:

docs/drilling/phase3_service_mapping.md

Document:

- architecture
- mapping pipeline
- quantity derivation
- provenance model
- ambiguity handling
- interpretation switches
- things intentionally deferred

Update:

README.md
prompts/README.md

only where necessary.

Save this prompt verbatim as:

prompts/drilling/03-service-mapping-and-quantities.md

==================================================
15. DO NOT DO THESE THINGS
==================================================

Do NOT:

- price services
- calculate expected invoice totals
- compare expected vs billed values
- create findings
- flag invoices
- resolve every ambiguity for convenience
- use invoice prices to identify service
- modify Civil Works behavior
- alter frozen Civil Works outputs
- generate final Drilling submission rows
- begin Phase 4
- commit
- push

==================================================
16. FINAL VALIDATION
==================================================

Run:

- all Drilling tests
- full project tests with warnings as errors
- byte comparison of frozen Civil Works files
- deterministic regeneration of Phase 3 artifacts
- whitespace/diff checks

If a Windows access-violation notice occurs but tests exit successfully, report it exactly rather than hiding it.

==================================================
17. REPORT BACK
==================================================

Stop after Phase 3 and report:

1. files created/changed
2. final test counts
3. confirmation Civil Works is byte-identical
4. number of reports successfully interpreted
5. deterministic vs ambiguous mappings
6. service-code coverage
7. quantities generated by type
8. interpretation switches implemented
9. unresolved Phase 1 ambiguities still blocking later logic
10. any surprising data discovered
11. any assumptions you had to make
12. exact artifacts created
13. proposed Phase 4 interface

Most importantly:

Tell me which decisions need MY approval before Phase 4.

Do not make those decisions yourself just to increase coverage.

Then wait for my response.
