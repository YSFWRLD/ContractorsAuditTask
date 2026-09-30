# Prompts

The task requires AI assistance to be disclosed and prompts kept as versioned files.

- Session prompts driving each build phase are saved verbatim, in order: civil works as
  `NN-<phase>.md` at this level, drilling as `drilling/NN-<phase>.md` (numbered from its own Phase 0).
- The pipeline itself calls no language model, so there are no runtime prompts.

| file | phase |
|---|---|
| `00-phase0-inspection-architecture.md` | repository inspection and project scaffold |
| `01-phase1-contract-and-data-understanding.md` | civil works contract extraction, typed loaders, record parser, source profiles |
| `02-phase2-pricing-engine.md` | civil works pricing engine, interpretation switches, quantity rules, sensitivity |
| `03-phase3-audit-engine.md` | civil works audit layer, findings, confidence, draft outputs |
| `04-civil-works-freeze.md` | civil works review and freeze: checklist, adversarial review, policies |
| `drilling/00-drilling-architecture.md` | drilling inspection, domain layout and scaffold (no contract logic) |
| `drilling/01-contract-extraction.md` | drilling contract extraction: reviewed terms, ambiguity register, typed contract model (no pricing) |
| `drilling/02-data-ingestion.md` | drilling ingestion: typed invoices, lines and reports, indexes, timelines, structural validation (no mapping, pricing or findings) |
| `drilling/03-service-mapping-and-quantities.md` | drilling interpretation: Appendix G service candidates, evidence-backed quantities, interpretation switches (no pricing or findings) |
| `drilling/04-pricing-engine.md` | approvals after the Phase 3 review, decision table, switch-driven pricing engine (no canonical price, no invoice comparison) |
| `drilling/05-approved-pricing-readings.md` | Phase 4 approvals; AMB-13 approved as UNKNOWN / UNVERIFIED; canonical pricing coverage and sensitivity (no invoice comparison) |
| `drilling/06-pd201-strict-amb13.md` | strict AMB-13 treatment for PD-201: eligibility not established, conditional amount only (no invoice comparison) |

## How AI was used in Phase 1

The civil works contract is a 43-page scan with no text layer. Its terms were transcribed by
the AI assistant (Claude Code) looking at page renders, not by an OCR engine, into
`artifacts/civil_works/contract_extraction.json`. Every table was read twice, and the two
transcriptions were compared programmatically (0 discrepancies). Invoice data was not
used to confirm or correct any contract value. The audit runs from that reviewed JSON and
never needs the PDF or OCR at runtime. See `artifacts/civil_works/contract_verification.md`.

## How AI was used in Phase 2

The pricing engine, quantity parsers and tests were written by the AI assistant. Every working
interpretation was chosen from contract text before the engine was run against billed data. Billed
data appears only in `sensitivity.md` under the label "consistency with observed billing". It is
descriptive, and no reading was changed because of it (`docs/civil_works/decision_log.md`). Record
quantities are extracted by anchored regular expressions, not a language model.

## How AI was used in Drilling Phase 0

The AI assistant read the 42 drilling contract page renders by eye to inventory its structure
(`docs/drilling/phase0_inventory.md`). Nothing was transcribed into a machine-read artifact yet;
that is Phase 1, with two-pass review. The scaffold, layer tests and source tests were written by
the assistant.

## How AI was used in Drilling Phase 1

The AI assistant transcribed the 42-page drilling contract from page renders (no OCR) into
`artifacts/drilling/contract_terms.json`. Pass A read each page at 150 dpi, and pass B read
220 dpi half-page crops. Both transcriptions of every table are kept in `artifacts/drilling/review/`
and were compared by script (462 values, 0 discrepancies). Contradictions were recorded, not
resolved, in `contract_ambiguities.json`. The only arithmetic done was on the contract's own
worked examples, to classify them. Invoice, line and report data were not consulted for any contract
value or reading. The authoring script that assembled the JSON from the transcriptions was a
development aid and is not part of the pipeline; the reviewed JSON is the source of truth.

## How AI was used in Drilling Phase 2

The AI assistant profiled every drilling input file and wrote the ingestion layer and its tests
(`docs/drilling/phase2_data_inventory.md`, `phase2_ingestion.md`). Parsing is deterministic Python
with no language model. Rig words are kept verbatim and nothing is mapped to service codes. The
structural validation records observations only; data facts that bear on the open contract
ambiguities are recorded but were not used to choose a reading.

## How AI was used in Drilling Phase 3

The AI assistant wrote the interpretation layer, which maps report words to Appendix G candidates and
derives quantities with field-level provenance. It also wrote the switch registry, the reports and the
tests. The mapping is deterministic code that reads the contract model; no language model is called at
runtime. Every open reading is evaluated, none is chosen, and billed data is read only by a separate
descriptive coverage report.

## How AI was used in Drilling Phase 4

The AI assistant recorded the user's approvals verbatim in `artifacts/drilling/approved_readings.json`. It
wrote the recommendations for the unresolved readings from the contract text only, and wrote the pricing
engine, the sensitivity report and the tests. The engine reproduces the contract's own Appendix B worked
invoice under the readings that example implies. No reading was chosen to reconcile billed invoices, and
no invoice was compared.

## How AI was used in Drilling Phase 4b

The AI assistant recorded the user's second round of approvals verbatim, including AMB-13 as UNKNOWN / UNVERIFIED. It
added the `EVIDENCE_NOT_PROVIDED` status for prices that need the missing call-off, the canonical pricing report, the
two-background sensitivity and the well-class scenarios, and the tests. The invoice-claimed class is never used canonically,
and no reading was chosen because it reconciles billed amounts. No invoice was compared.

Following the user's instruction (`06-pd201-strict-amb13.md`), the assistant extended the same treatment to PD-201.
Its calculated rate is kept as a conditional, not-payable amount. Tests show that no invoice claim can make it canonically payable.
