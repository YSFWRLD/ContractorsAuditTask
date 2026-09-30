# Contractor invoice audit

Solution to `invoice-auditing-level-2`: audit every civil works payment application
(`PA-*`) and drilling invoice (`MDS-*`) against its contract and produce one
`submission.csv`. Status: **complete: both domains audited and frozen; the combined `submission.csv` is at the repository root.**

Deliverables:
- `submission.csv`: 2,806 rows in the template's order;
- `REPORT.md`: approach, results and error analysis;
- `DECISION_LOG.md`: the decisions that shape the submission;
- `prompts/`: every prompt used, versioned.

The civil works contract is extracted and reviewed, priced through explicit interpretation switches,
audited, and its draft outputs are in `outputs/civil_works/`. The drilling contract is transcribed
into a reviewed, typed model with an ambiguity register. Its invoices, lines and daily reports are
parsed into typed, traceable objects with a structural validation report. Report words are mapped to
contract service candidates and evidence-backed quantities under every open reading. A switch-driven
pricing engine prices them canonically under the approved readings, and the drilling audit compares every
invoice with that evidence and writes its draft outputs to `outputs/drilling/`. `submission` joins both
domains' frozen results onto the upstream template.

## Running

Requires Python 3.11+ (developed and tested on 3.13).
- The package has no runtime dependencies; it uses the standard library only.
- `requirements.txt` pins the exact versions of pytest and its dependencies, used for the tests.
- `pyproject.toml` pins the build backend (`setuptools==84.0.0`).

End-to-end reproduction, from a fresh virtual environment:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # on Linux/macOS: .venv/bin/python
.venv/Scripts/python -m contractor_audit check-sources
.venv/Scripts/python -m contractor_audit build-artifacts --domain civil_works
.venv/Scripts/python -m contractor_audit build-artifacts --domain drilling
.venv/Scripts/python -m contractor_audit run --domain civil_works
.venv/Scripts/python -m contractor_audit run --domain drilling
.venv/Scripts/python -m contractor_audit submission
.venv/Scripts/python -m pytest -W error
```

What each step does:
- **`build-artifacts --domain civil_works`** and **`build-artifacts --domain drilling`** regenerate each domain's derived artifacts: contract, structural, interpretation and pricing (~10 s and ~40 s).
- **`run --domain civil_works`** audits the civil works applications and writes `outputs/civil_works/` (~35 s).
- **`run --domain drilling`** audits the drilling invoices and writes `outputs/drilling/` (~2.5 min, mostly the dependency re-runs).
- **`submission`** writes the root `submission.csv`. It reads each domain's frozen `outputs/<domain>/draft_predictions.csv` and fills the upstream `submission_template.csv` in its order. It stops with an error, and writes nothing, on any missing, duplicated or extra invoice id, bad column, non-integer amount, confidence outside [0, 1], or missing domain result.
- **`pytest -W error`** runs the whole suite (~5.5 min).

Every step is deterministic: running it again reproduces the committed artifacts, outputs and `submission.csv` byte for byte.

Without installing, prefix commands with `PYTHONPATH=src`. The task data is expected at
`./invoice-auditing-level-2/`; point elsewhere with `CONTRACTOR_AUDIT_DATA=/path/to/it`.
The upstream task data is never modified. `tests/civil_works/test_task_data_untouched.py`
checks every input byte-for-byte against `artifacts/civil_works/source_inventory.json`.

## Architecture

```
raw task files (read-only)
  -> domain sources / parsing      domains/<domain>/
  -> canonical domain models
  -> domain audit rules (the 12 checks)
  -> InvoiceResult + Finding       shared/findings.py
  -> per-domain outputs            outputs/<domain>/
  -> combined submission.csv
```

**Shared** (`src/contractor_audit/shared/`) holds only what is contract-neutral:
- the 12 guideline checks and the pass/query/part-reject outcomes (the guidelines are identical for both contracts);
- the `InvoiceResult` row that mirrors the submission template;
- money to integer minor units;
- file fingerprints (`provenance.py`);
- path conventions;
- the `AuditDomain` protocol the CLI talks to (`required_sources`, `build_artifacts`, `run`);
- the combined submission (`submission.py`): the template joined with every domain's draft predictions, validated, never repaired.

It must not import any domain; `tests/test_architecture.py` enforces this.

**Civil works** (`src/contractor_audit/domains/civil_works/`) owns everything about CW-2025-0417-CIV:

| module | role |
|---|---|
| `sources.py` | layout of the raw `civilwork/` files |
| `contract.py` | typed, validated view of the reviewed contract extraction |
| `models.py`, `loaders.py` | strict loaders for applications and lines (Decimal rates, integer-halala money, parsed dates, raw strings kept) |
| `records.py` | parser for the nine site-record types (verbatim descriptions, signatures, DW day lists) |
| `profiling.py`, `reports.py`, `artifacts.py` | descriptive profiles and their JSON/Markdown artifacts |
| `interpretation.py` | `CivilWorksInterpretation`: one enum per contested reading, the working reading, and why |
| `rounding.py` | the only place money is rounded (Clause 28 half-up, 26A/29A half-even, 45 down) |
| `rates.py` | rate in force per item and work date across the BoQ and five instruments (issue vs effective dates) |
| `pricing.py`, `trace.py` | the Clause 27 build-up with a structured, clause-cited trace |
| `rebates.py` | stateful Schedule 4 Part 3 band ledger (per Contract Year or whole Works) |
| `contract_period.py` | contract in force, extensions, Contract Years |
| `valuation.py` | whole-dataset valuation; retention, 31A adjustment and 45A release kept outside the measured total |
| `record_quantities.py`, `quantity_rules.py` | rule-based record quantities; 6A, 33/33A, 47A, 31 and 32/P19/P21 evaluators |
| `sensitivity.py`, `pricing_reports.py` | effect of every alternative reading; Phase 2 artifacts |
| `pipeline.py` | domain entry point; `run()` audits every application and writes `outputs/civil_works/` |

**Data locations**

| what | where | mutable |
|---|---|---|
| raw task data | `invoice-auditing-level-2/` (upstream clone) | never |
| reviewed contract transcription | `artifacts/civil_works/contract_extraction.json` | only by deliberate re-review |
| reviewed drilling contract terms and ambiguity register | `artifacts/drilling/contract_terms.json`, `contract_ambiguities.json`, `review/` | only by deliberate re-review |
| generated derived artifacts | `artifacts/<domain>/*` (everything else) | regenerated by `build-artifacts` |
| final per-domain results | `outputs/<domain>/` | regenerated by `run` |
| combined submission | `submission.csv` (repository root) | regenerated by `submission` |
| prompts used with AI assistance | `prompts/` (civil works at top level, drilling in `prompts/drilling/`) | versioned |

**Drilling** (`src/contractor_audit/domains/drilling/`) owns everything about DDS-2025-118. Unlike civil
works, whose modules grew flat, it is split into layers from the start. `tests/drilling/test_layout.py`
enforces the dependency order:

| layer | role | may import |
|---|---|---|
| `sources.py` | layout of the raw `drilling_services/` files | shared |
| `ingestion/` | invoices, lines and Daily Drilling Reports (Parts A–E) as typed rows; rig words kept verbatim | shared, `sources` |
| `interpretation/` | report words → Appendix G service candidates → evidence-backed quantities, under every interpretation switch | shared, `sources`, `ingestion`, `contract` |
| `pricing/` | quantities → priced amounts under an explicit selection of readings (fails when a required reading is missing) | shared, `sources`, `contract`, `interpretation` |
| `contract/` | reviewed extraction → typed terms, instruments, Appendix G vocabulary, interpretation switches, pricing | shared, `sources` |
| `audit/` | the 12 checks: what was billed and recorded vs what the contract allows | + `ingestion`, `contract`, `interpretation`, `pricing` |
| `reporting/` | artifacts and draft outputs | + `audit` |
| `pipeline.py` | the `DOMAIN` entry point; the only module that wires layers together | everything |

For drilling, `build-artifacts` is contract-only:
- it validates `artifacts/drilling/contract_terms.json` and `contract_ambiguities.json` (the reviewed transcription, checked against the PDF's sha256);
- it writes `source_manifest.json`, `contract_terms.md` and `contract_ambiguities.md`.

It also ingests the operational data (`ingestion/`: typed invoices, lines and Daily Drilling Reports, indexes, well timelines, BHA runs) and writes `phase2_structural_validation.{json,md}`, which holds neutral observations, not findings. Then it interprets the reports (`interpretation.engine.interpret`, which accepts reports and the contract only) and writes `phase3_*` mapping, quantity, switch and descriptive billed-code coverage artifacts. Finally it prices the quantities under the approved readings and writes `phase4_canonical_pricing.{json,md}`. Prices that need the missing call-off are `EVIDENCE_NOT_PROVIDED` (AMB-13: UNKNOWN / UNVERIFIED). It also writes the hypothetical `phase4_pricing_sensitivity.*` and the `phase4_decision_table.md` decision record. Approved readings live in `artifacts/drilling/approved_readings.json`.

`run` audits every drilling invoice against that evidence (the twelve checks) and writes the draft outputs to `outputs/drilling/`; see "Drilling audit (Phase 5)" below.

`contract/models.py` keeps every rate statement with its issue and effective dates. `rate_statements_on(code, date)` lists the candidates for a service date and never chooses between them.

See `docs/drilling/phase5_audit.md` (Phase 5), `docs/drilling/phase4_pricing_engine.md` (Phase 4), `docs/drilling/phase3_service_mapping.md` (Phase 3), `docs/drilling/phase2_ingestion.md` and `phase2_data_inventory.md` (Phase 2), `phase1_contract_extraction.md` (Phase 1) and `phase0_inventory.md` (Phase 0).

**Dependency direction:** `cli` → `domains` registry → `domains/<domain>` → `shared`.

## Civil works contract extraction

The contract PDF is a 43-page scan with no text layer. It was transcribed **once, during
development**, by an AI assistant reading page renders (no OCR engine), into
`artifacts/civil_works/contract_extraction.json`. Every value carries:
- its page, section and a short source quotation;
- a review status (`VERIFIED`, `AMBIGUOUS`, `UNREADABLE` or `NOT_PROVIDED_IN_DATA`);
- the number of independent reads.

Every table was read twice and cross-checked. Invoice data was never used to confirm or
correct a contract value. Clauses that support more than one reading are recorded with every
reading preserved; none is resolved in the extraction.

The audit reads this JSON and never needs the PDF or OCR at runtime. `build-artifacts`
checks that the PDF's sha256 still matches the one recorded in the extraction.

Generated Phase 1 artifacts (`build-artifacts --domain civil_works`):

| file | content |
|---|---|
| `contract_extraction.md` | human-readable rendering of the JSON, with per-item instrument history and precedence timeline |
| `contract_verification.md` | review status counts, verification method, ambiguities, data not provided |
| `record_inventory.{json,md}` | the 2,169 site records by type, format variants, signatures, phrasing patterns |
| `source_profile.{json,md}` | applications, lines, record references, date relationships, raw arithmetic (descriptive only) |
| `source_inventory.json` | sha256 of every raw input |
| `rate_timeline.{json,md}` | rate in force per item at every instrument boundary (day before / on / after) |
| `interpretation_matrix.md` | every interpretation switch, its readings, status and working choice |
| `pricing_model.md` | the build-up order and worked, fully traced examples |
| `quantity_parsing.{json,md}` | record quantity rules and coverage |
| `sensitivity.{json,md}` | effect of each alternative reading; billing consistency shown descriptively only |

Decisions and open questions are recorded in `docs/civil_works/decision_log.md`.

## Civil works audit (Phase 3)

`domains/civil_works/audit/`: pricing says what should be paid; the audit compares it with what was billed.

| module | role |
|---|---|
| `categories.py` | the 24-value error-category vocabulary, each tied to a guideline check and clause |
| `options.py` | audit-level readings (rebate progression, missing-record consequence, unsigned records, measurement order) and the total policy |
| `rules/` | one module per check family; quantity rules cap payable quantity, valuation rules compare billed figures with Phase 2 prices |
| `engine.py`, `valuation.py` | one audit pass: rules → payable quantities → Phase 2 pricing → comparisons |
| `assessment.py`, `confidence.py` | re-runs the audit under every alternative reading to measure dependencies; confidence and blank-total policy |
| `reports.py` | the draft outputs below |

The finding model is the shared `contractor_audit.shared.findings.Finding`. Each finding carries citations from the reviewed extraction, evidence (billed line, record, Phase 2 pricing trace), its monetary impact and its measured dependencies.

Outputs (`outputs/civil_works/`, civil works draft only, not the combined submission):

| file | content |
|---|---|
| `draft_predictions.csv` | the 900 `PA-*` rows in the submission-template columns |
| `application_audit.csv` | per application: flag, categories, billed / corrected / working / GRADED totals, confidence, blank reasons, dependencies |
| `findings.jsonl` | every finding with full evidence, citations and dependencies |
| `audit_summary.md`, `coverage.md`, `uncertainty_report.md`, `sensitivity.md` | readable summaries |
| `review.md` | the Phase 4 freeze review: guideline checklist, category matrix, adversarial checks, duplicate / exclusion / split-line / total verification |

Confidence bands (evidence quality, not probability): HIGH 0.95, MEDIUM 0.75, LOW 0.55. A corrected total is published only when no unresolved reading changes it (STRICT policy); otherwise it is blank and `primary_blank_reason` says why. Civil works was completed through Phase 4 and later received a targeted final correctness patch resolving the indexed-rate interpretation; the current policy is documented at the top of `docs/civil_works/decision_log.md`.

## Drilling audit (Phase 5)

`domains/drilling/audit/`: the contract-side prices are established from the reports first (`bundle.py`); only then are the invoices compared with them.

| module | role |
|---|---|
| `categories.py` | the drilling error-category vocabulary, each tied to a guideline check and clause; `entitlement_unverified` is the one query that never flags |
| `policy.py` | the readings the audit uses: the approved ones, including the audit-phase decisions (AMB-12, 14, 15, 23 approved; AMB-25 evidence not provided), each with its grade |
| `bundle.py` | canonical prices, plus the conditional price of each call-off-dependent charge under each possible well class (AMB-13) |
| `lines.py`, `diagnosis.py` | checks 2-11 per line; a shared ledger of report evidence already charged (duplicates within and across invoices); rate differences diagnosed to one build-up component |
| `invoices.py`, `engine.py` | invoice-level checks (reference, timing, arithmetic, VAT, DS-900, the Clause 36A adjustment) and the valuation |
| `dependencies.py`, `results.py`, `runner.py` | re-runs the audit under every alternative reading; confidence and the STRICT corrected-total policy |

Outputs (`outputs/drilling/`, drilling draft only, not the combined submission): `draft_predictions.csv` (the 1,906 `MDS-*` rows in the template columns), `invoice_audit.csv`, `findings.jsonl`, `audit_summary.md`, `coverage.md`, `uncertainty_report.md`, `sensitivity.md`, `review.md`.

The call-offs are not in the data (AMB-13, approved as UNKNOWN / UNVERIFIED) and every invoice charges a class-rated service, so no drilling corrected total is published; the conditional total (claimed entitlement confirmed) is kept in `invoice_audit.csv` for analysis only. See `docs/drilling/phase5_audit.md`.
