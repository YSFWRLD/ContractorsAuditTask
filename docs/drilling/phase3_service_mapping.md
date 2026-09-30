# Drilling Phase 3: service mapping and evidence-backed quantities

This phase takes each Daily Drilling Report to contract service candidates, and from there to quantities backed by report evidence. It stops there:
- nothing is priced;
- nothing is compared with what was billed, beyond a separate descriptive coverage report;
- no invoice is flagged;
- no open reading is chosen.

## Architecture

`src/contractor_audit/domains/drilling/interpretation/`. It may import `sources`, `ingestion` and `contract`, and `tests/drilling/test_layout.py` enforces that.

| module | role |
|---|---|
| `models.py` | `MappingStatus`, `ServiceCandidate`, `MappingResult`, `Quantity`, `FieldRef`, `Condition`, `InterpretationResult` |
| `provenance.py` | `field_ref(report, section, label)`: the exact report line a value came from |
| `switches.py` | the registry of 26 interpretation switches, built from the Phase 1 ambiguity register |
| `ambiguity.py` | the Appendix G vocabulary under each reading (read from the contract model), and the later-phase dependencies of each quantity |
| `service_mapping.py` | report word to candidate codes, with a status for every occurrence |
| `common.py` | building a quantity with a deterministic id; conditions evaluated from reports |
| `quantities.py` | daily quantities from one day's report only |
| `run_quantities.py` | once per BHA run, from the Phase 2 run reconstruction |
| `well_quantities.py` | once per well (Clause 27), with timing read from the contract |
| `lost_in_hole.py` | Part E, with every depreciation-hours figure carried (AMB-22) |
| `engine.py` | `interpret(reports, terms, ambiguities)`, the whole pass |

`interpret` accepts reports and the contract, nothing else. It cannot see invoices, billed codes, rates or amounts.

On the reporting side:
- `reporting/phase3_mapping_report.py` writes the statistics.
- `reporting/phase3_billed_coverage.py` is the only Phase 3 code that reads invoice lines. It runs after interpretation, compares codes only, and never feeds back.

## Mapping pipeline

Three report fields carry rig words: Part A `In the hole` (tools), Part A `Crew on tour` (roles) and Part E `Lost in hole tool`. For each word in each report:

1. **Look up the contract candidates.** `ContractTerms.codes_for_report_term(word)` gives the Appendix G candidates, exactly as printed. Nothing is typed in by hand.
2. **Apply the field context (AMB-16).** Four words appear twice in Appendix G: mud motor, rotary steerable, MWD collar and gamma tool, each as a rental row and a lost-in-hole row. The Appendix G footnote says a lost tool is recorded by the same term and charged at its replacement value. So:
   - Part A (in the hole) selects the rental row;
   - Part E (lost) selects the lost-in-hole row;
   - status `IDENTIFIED_BY_CONTEXT`, with the other candidate named in the note.
3. **Apply the Appendix G reading (AMB-17).** Under `LWD_ROWS_SHIFTED` the three LWD "logged" rows, and LH-714, which follows LW-410, move up one row:
   - gamma tool → nothing;
   - resistivity tool → LW-410 / LH-714;
   - density-neutron → LW-411;
   - LW-412 then has no term.

   These three words are `UNRESOLVED_INTERPRETATION`, and their candidates are kept per reading. The other surprising pairings (night man, survey package, float sub, bit and reamer, hydraulics package) have no alternative in the contract. They stay literal and are marked with a note.

**Statuses:** `IDENTIFIED`, `IDENTIFIED_BY_CONTEXT`, `AMBIGUOUS`, `UNRESOLVED_INTERPRETATION`, `UNSUPPORTED` and `NOT_APPLICABLE`. The first two count as deterministic.

**On the real data:** 84,036 word mappings:

| status | count |
|---|---|
| deterministic | 76,915 |
| switch-dependent | 7,121 |
| ambiguous | 0 |
| unsupported | 0 under the literal reading |

## Quantity derivation

Every `Quantity` carries:
- the service code and the contract unit;
- a basis: person-day, rental day, hour, count, metre, run, well, lost in hole, or standby day;
- its scope (day, run or well), well, date, run and report ids;
- the derivation method and the clauses relied on;
- field-level evidence;
- the mapping status;
- conditions;
- the readings it exists under;
- the later-phase switches it depends on.

| basis | source | rule |
|---|---|---|
| person-day | Part A crew `<count> <role>` | the printed count per role (cl. 22, P7). DD-102 takes it from "night man" only under `dd102_basis = PER_COORDINATOR_RECORDED`. |
| rental day | Part A in the hole | 1 per day per recorded day-rated tool (cl. 28). No undocumented day is inferred. |
| hour | Part A circulating / back-reaming hours | DD-120 when the rotary steerable is in the hole, under both `dd120_hours` readings; RM-530 from back-reaming hours (cl. 30). |
| count | Part A gyro surveys, pressure points, wiper trips, clean-out runs | the field value (cl. 30). HC-630 only under `hc630_basis = DAILY_COUNT`. |
| metre | Part A depths | `metre_source = DAILY_DEPTH_ADVANCE`: the day's advance for each LWD tool, or for the underreamer (the RM-511 term) giving RM-510. PD-210 is split at the Schedule 2 boundaries, with a boundary depth in the shallower band. |
| run | Part B, via the reconstructed runs | DD-111 once per run carrying the PDM, on its recorded last day. LW-420 once per run carrying a source, on its first day. HC-630 under `PER_BHA_RUN`. Part B metres logged or reamed, once per run, under `PART_B_RUN_METRES`. |
| well | first and last report of the well | MB-701 and DD-140 on the first day; MB-702 and LW-430 on the last. LW-430 only where an LWD word was in the hole under the reading. |
| standby day | Part A status | DD-121 only on a Standby day whose own report records the rotary steerable in the hole (`dd121_condition` A, approved). Reading B is not derived: its only definition, Assumption 3, was rejected. |
| lost in hole | Part E | 1 unit on the day of loss, with the Part E hours, the tool's own accumulated hours, and the whole-well figure as context. |

**Repeated Part B values.** They are read once, from one report of the run, and never summed. The tests check that each run-level item exists exactly once per run, and that the daily metre reading summed over a run equals the Part B figure.

**Conditions** are evaluated from the reports, never assumed:
- `OPERATING_DAY` (cl. 21/24/25/30);
- `STANDBY_DAY`;
- `RECORD_PART_B/C/D/E` (Schedule 5);
- `REPORT_SIGNED` (cl. 15);
- `PERFORMANCE_SECTION_NOMINATED`: unknown in 12-1/4" and 8-1/2" sections because the call-offs are missing, and false in any other section.

Standby days keep their recorded activity. 290 of 381 have circulating hours, and a DD-120 hour quantity is kept on those with `OPERATING_DAY = false`.

**On the real data:** 114,745 quantities: 76,034 reading-independent and 38,711 existing only under particular readings. By basis: rental day 49,729, person-day 30,444, metre 19,151, hour 10,523, count 2,296, run 1,451, well 856, standby day 241, lost in hole 54. (Before the review this was 115,126: the 381 DD-121 quantities of rejected reading B are no longer derived.)

## Provenance

Every quantity and every mapping holds `FieldRef`s: report id, source file, section, label, raw value and physical line. The tests check each one against the parsed report. The report's own `Report:` field is the identity; file names are never used for joining. Invoice associations are not part of the evidence, so a report cited by two invoices is still one report.

## Interpretation switches

`artifacts/drilling/phase3_ambiguities.json` lists all 26 switches. Each has its readings, taken from the register's own wording; its default, which is only the Phase 1 preferred reading and otherwise none; whether it needs approval; and the counts affected.

**Evaluated in Phase 3,** with quantities under every reading:

| switch | ambiguity |
|---|---|
| `appendix_g_reading` | AMB-17 |
| `dd102_basis` | AMB-18 |
| `hc630_basis` | AMB-19 |
| `dd121_condition` | AMB-20 |
| `dd120_hours` | AMB-06 |
| `metre_source` | AMB-24 |
| `lih_hours` | AMB-22; both figures carried on one quantity |
| `appendix_g_duplicates` | AMB-16; resolved by the text |

**Defined now, used later:**

- **Phase 4, pricing:**

  | switch | ambiguity |
  |---|---|
  | `rig_up_hour` | AMB-05 |
  | `pd210_class_factor` | AMB-02 |
  | `standby_section_factor` | AMB-03 |
  | `rig_services_index` | AMB-04 |
  | `dd120_rate_from_feb_2026` | AMB-07 |
  | `monthly_rate_basis` | AMB-08 |
  | `principal_discount_combination` | AMB-09; resolved by the text |
  | `volume_tier_scope` | AMB-10 |
  | `contract_year_2` | AMB-11 |
  | `lih_replacement_value` | AMB-21 |
  | `ds900_threshold_basis` | AMB-26 |
  | `unranked_precedence` | AMB-01 |

- **Phase 5, audit:**

  | switch | ambiguity |
  |---|---|
  | `backdated_adjustment` | AMB-12 |
  | `calloff_evidence` | AMB-13 |
  | `record_signatories` | AMB-14 |
  | `report_vocabulary` | AMB-15 |
  | `missing_record_consequence` | AMB-23 |
  | `submission_date` | AMB-25 |

Each quantity's `depends_on` lists the later switches that will affect how it is used.

## Evidence recorded, not used to decide

From the reports alone, in `phase3_ambiguities.json → evidence_facts`:
- Part B metres logged are non-zero on exactly the 500 runs whose tools include "gamma tool".
- A radioactive source is carried on exactly the 369 runs whose tools include "resistivity tool". Appendix G literally maps that word to density-neutron, which T9 says needs a source.
- "hole opener" coincides with metres reamed in 121 of 121 runs.
- "logging engineers" are on tour exactly on the 3,430 days with a literal LWD word.
- "performance engineer" appears only in 12-1/4" and 8-1/2" sections.
- 2 source runs have no Part D on their first day: DDR-029-20260515 and DDR-201-20251115.
- 1 gyro count has no Part C: DDR-009-20251211.

## Deferred on purpose

- Pricing, factors, the index, discounts, the 21A rig-up hour, the 6-hour minimum, daily limits and the 25A tolerance: Phase 4.
- Comparing quantities with billed lines, duplicates, findings and confidence: Phase 5.
- Outputs and the submission: Phase 6.

The billed-code coverage report (`phase3_billed_coverage.{json,md}`) is descriptive only. It includes the 189 report/code pairs cited by several billed lines, with their intervals. It does not classify any of them.

## Changes after the Phase 3 review (2026-09-30)

- `dd121_condition` reading B is no longer derived (rejected Assumption 3; `switches.NOT_DERIVED`).
- Daily quantities now carry their BHA run number, which the per-run rig-up reading needs. This changes the qids of daily quantities, not their values.
- Approved readings are recorded in `artifacts/drilling/approved_readings.json`.
