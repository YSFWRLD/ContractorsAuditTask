# Drilling Phase 4: pricing engine

Phase 4 turns the Phase 3 quantities into priced amounts, under an explicit selection of readings.

A result is canonical only when every switch it uses was approved by you or resolved by the contract's own text. The engine refuses to start (`MissingSelectionError`) when any switch it needs has no reading.

**Phase 4b.** Every switch pricing needs is now approved, so a canonical result exists (`phase4_canonical_pricing.{json,md}`). Sensitivity runs replace one reading at a time with a HYPOTHETICAL one and are never canonical.

**AMB-13 is approved as UNKNOWN / UNVERIFIED** (`calloff_evidence = UNVERIFIABLE_QUERY`). This is a resolved audit decision about the evidence, not a missing selection. Any price that needs the missing call-off gets its own status, `EVIDENCE_NOT_PROVIDED`, with the reason recorded. That covers:
- the well class of the class-rated services (DD-120, LW-410 to LW-413, MW-310, MW-320);
- whether a 12-1/4" or 8-1/2" section was nominated for performance drilling (PD-210, cl. 23);
- the same eligibility for PD-201, the performance-drilling engineer (strict treatment, `prompts/drilling/06-pd201-strict-amb13.md`). Its rate can be calculated without the call-off, but whether it was chargeable at all cannot. The engine therefore calculates the full rate and keeps the build-up steps and the report evidence. It records the result as `EVIDENCE_NOT_PROVIDED`, with `amount_cents = 0` and the calculated figure in `conditional_amount_cents`. That field is conditional only and never enters a total. An invoice line for PD-201 is not evidence that it was authorised; pricing reads no invoice.

Every other service is priced canonically. The class stated on the invoice header is only the contractor's claimed class. It is never passed to the canonical run (a test checks that passing it changes nothing), and it is shown only in the labelled hypothetical scenarios.

Statuses:
- `PRICED`;
- `NOT_CHARGEABLE`: the contract says no charge arises, e.g. a DD-120 Standby day or a 17-1/2" PD-210 day;
- `EVIDENCE_NOT_PROVIDED`: resolved under AMB-13. Where a rate could be calculated (PD-201), it is kept as a conditional amount only;
- `UNPRICEABLE`: some other input is missing. The count is 0 in the canonical run.

Nothing is compared with invoices, no invoice is flagged, and the audit phase has not started.

## Decisions recorded

- **`artifacts/drilling/approved_readings.json`** is hand-maintained. It holds:
  - both approval rounds, verbatim in `history`;
  - the first round: AMB-17, 18, 19, 20, 22 and 24, all reading A;
  - the Phase 4b round:
    - AMB-01 no global rank;
    - AMB-02 no class factor on PD-210;
    - AMB-03 no section factor on Standby;
    - AMB-04 index from the first month;
    - AMB-05 rig-up hour once per BHA run (superseded in the audit review by PER_DAY_THEN_MINIMUM; see `approved_readings.json` `superseded` and `docs/drilling/phase5_audit.md`);
    - AMB-06 circulating hours only;
    - AMB-07 416.00 from its effective date;
    - AMB-08 base rate, then the build-up;
    - AMB-10 tiers per well;
    - AMB-11 Contract Year 2 from 2026-01-01;
    - AMB-21 Schedule 2D, converted;
    - AMB-26 services only;
    - AMB-13 UNKNOWN / UNVERIFIED;
  - the approved assumptions 1, 2, 4, 5 and 6;
  - the **rejected Assumption 3**, with its consequence: DD-121 reading B is no longer derived at all (`interpretation/switches.py: NOT_DERIVED`);
  - the ambiguities left for the audit phase: AMB-12, 14, 15, 23 and 25.
- **`artifacts/drilling/phase4_recommendations.json`** is also hand-maintained. It holds the recommendation made before approval, from the contract text only, with its remaining uncertainty.
- **`artifacts/drilling/phase4_decision_table.md`** is generated. It is now a decision record: for each ambiguity decided in Phase 4 it shows the approved reading, the recommendation and the measured effect of each alternative.

## Architecture

`src/contractor_audit/domains/drilling/pricing/`. It may import `sources`, `contract` and `interpretation`. It never imports `ingestion`, `reporting`, `audit` or findings, and it never names an invoice field; tests enforce this.

| module | role |
|---|---|
| `selection.py` | `Selection` of (switch, value, source ∈ APPROVED / CONTRACT_TEXT / HYPOTHETICAL). `require()` fails on any missing reading. A hypothetical reading may not replace an approval. |
| `rates.py` | the rate statement in force on the service date, under `dd120_rate_from_feb_2026`. Every candidate statement is kept, and rates can be re-resolved without retroactive instruments. |
| `build_up.py` | 17A index → 18 section factor → 18 class factor → 18 standby percentage → S2/A2 principal discount. Each step is rounded half to even (cl. 17). |
| `quantity_rules.py` | chargeability (term, Operating-day clauses, Schedule 3 not-chargeable on Standby, Appendix A hole sizes); the 21A rig-up hour; the 6-hour minimum; Schedule 3 Part 5 daily limits. Audit-phase conditions become flags. |
| `tiers.py` | PD-210 Contract-Year tiers under `volume_tier_scope` and `contract_year_2` |
| `lost_in_hole.py` | Schedule 2D (SAR, converted at the month of loss) or Schedule 6, then depreciation of 1% per complete 25 hours, capped at 50% |
| `engine.py` | `price(result, terms, switches, selection, well_classes, services)` |

## Provenance chain

Each `PricedQuantity` holds the full chain:
1. the report evidence (`FieldRef`s);
2. the Phase 3 quantity id;
3. the recorded and chargeable quantity, with the quantity steps (rig-up, minimum, limit);
4. every reading used, with its source;
5. the `RateSource` relied on: statement, instrument, month, page, and every candidate statement;
6. the rate steps, each with input, factor, rounded output and clause;
7. the amount (quantity × rate, rounded).

For back-dated rates it also carries the amount at the rates known before Amendment No. 3, for the 36A question (AMB-12). Tests check that every step starts from the previous rounded output.

**Verification against the contract's own example.** From two synthetic reports, the engine reproduces the Appendix B worked invoice exactly (net 25,662.26) under the readings that example implies:
- no index;
- no rig-up deduction;
- no PD-210 class factor.

Under the other readings it shows each contradiction numerically:
- **Index:** MW-310 at 3,082.88 instead of 2,975.75.
- **Rig-up hour:** DD-120 at 17 hours instead of 18.
- **Class factor:** PD-210 at 77.05 / 101.30 instead of 58.15 / 76.45.

## Canonical pricing

`phase4_canonical_pricing.{json,md}` (`reporting/phase4_canonical_pricing.py`) summarises the canonical result:
- counts by status and service;
- the reason for every quantity not priced;
- the audit-phase flags;
- the Amendment No. 3 retroactive totals;
- the conditional, not-payable amounts (PD-201), listed separately;
- a sha256 digest of every priced quantity.

Canonical coverage:
- 61,995 priced, $147,426,868.78;
- 3,189 not chargeable;
- 31,316 evidence not provided;
- 0 unpriceable.

It refuses to write a result that is not canonical.

## Sensitivity (not canonical)

`phase4_pricing_sensitivity.{json,md}` starts from the canonical selection. It flips each approved reading alone to each alternative and reprices only the services that switch can affect. Every figure is a total of priced report evidence, never an invoice figure.

The flips run against two backgrounds:
- **canonical**: the class-rated services and PD-210 stay `EVIDENCE_NOT_PROVIDED`.
- **claimed_class** (HYPOTHETICAL): uses the contractor's claimed classes, and treats every allowed-size PD-210 day as nominated. Readings that act only on those services (AMB-02, 05, 06, 07, 10) would otherwise show no effect.

The well-class section prices the class-rated services four ways, without choosing between them: every well Standard, every well Extended Reach, every well HPHT, and under the claimed class. It also gives the PD-210 upper bound "if every allowed-size day were nominated", and the PD-201 conditional amount "if eligibility were established".

## Not priced in this phase

These items are invoice-level and need invoice assembly, which starts with the audit phase:
- DS-900 (Clause 38);
- VAT (Clause 39);
- the 36A back-dated adjustment;
- the 25A metre tolerance, which compares billed metres.

Well classes are an input to `price`. The engine never looks them up, and under the approved AMB-13 it ignores them. Only the hypothetical `INVOICE_STATEMENT_UNVERIFIED` reading uses them, and every quantity priced that way carries a `WELL_CLASS_FROM_INVOICE_STATEMENT_UNVERIFIED (AMB-13)` flag.

**Phase 3 correction made in Phase 4b.** Pricing exposed two defects in run-level quantities:
- The Part B metres (logged and reamed) and the per-run HC-630 had no service date, so they could not be priced. They are now dated to the run's first report and to its first clean-out day, respectively.
- A run- or well-scope quantity drawn from a single report inherited that day's Operating/Standby status. The day status now belongs to day-scope quantities only.

The number of quantities is unchanged (114,745). The Phase 3 digest and the day-status counts in `phase3_quantity_summary.md` changed.
