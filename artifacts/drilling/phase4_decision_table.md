# Drilling Phase 4 — decision record

Readings approved by the user on 2026-09-30 (`approved_readings.json`), with the effect of each alternative against the canonical selection (`phase4_pricing_sensitivity.md`). Recommendations were formed from the contract text only.

| ambiguity | switch | approved reading | recommendation | effect of each alternative |
|---|---|---|---|---|
| AMB-06 | `dd120_hours` | **CIRCULATING_ONLY** (A) | CIRCULATING_ONLY (MEDIUM) | → CIRCULATING_PLUS_BACK_REAMING (canonical): $0.00 over 9,580 quantities; → CIRCULATING_PLUS_BACK_REAMING (with claimed classes (hypothetical)): $1,011,212.30 over 9,580 quantities |
| AMB-13 | `calloff_evidence` | **UNKNOWN / UNVERIFIED** (B) | INVOICE_STATEMENT_UNVERIFIED (LOW) | → INVOICE_STATEMENT_UNVERIFIED (canonical): $120,978,415.19 over 31,316 quantities |
| AMB-01 | `unranked_precedence` | **NO_RANK_CASE_BY_CASE** (A) | NO_RANK_CASE_BY_CASE (MEDIUM) | Meta-decision: no direct effect; each concrete conflict has its own switch. |
| AMB-02 | `pd210_class_factor` | **DO_NOT_APPLY** (B) | DO_NOT_APPLY (MEDIUM) | → APPLY (canonical): $0.00 over 0 quantities; → APPLY (with claimed classes (hypothetical)): $3,975,398.58 over 1,936 quantities |
| AMB-03 | `standby_section_factor` | **OMIT** (B) | OMIT (MEDIUM) | → APPLY (canonical): $9,129.66 over 140 quantities; → APPLY (with claimed classes (hypothetical)): $16,321.93 over 406 quantities |
| AMB-04 | `rig_services_index` | **APPLY_FROM_FIRST_MONTH** (A) | APPLY_FROM_FIRST_MONTH (MEDIUM) | → NOT_APPLIED (canonical): -$331,856.42 over 7,821 quantities; → NOT_APPLIED (with claimed classes (hypothetical)): -$1,879,193.35 over 15,642 quantities |
| AMB-05 | `rig_up_hour` | **PER_BHA_RUN** (B) | PER_BHA_RUN (LOW) | → PER_DAY_THEN_MINIMUM (canonical): $0.00 over 0 quantities; → NO_DEDUCTION (canonical): $249,470.65 over 943 quantities; → MINIMUM_THEN_PER_DAY (canonical): $0.00 over 0 quantities; → PER_DAY_THEN_MINIMUM (with claimed classes (hypothetical)): -$1,638,193.55 over 3,903 quantities; → NO_DEDUCTION (with claimed classes (hypothetical)): $544,660.65 over 1,646 quantities; → MINIMUM_THEN_PER_DAY (with claimed classes (hypothetical)): -$1,638,193.55 over 3,903 quantities |
| AMB-07 | `dd120_rate_from_feb_2026` | **LATER_ISSUED_GOVERNS** (A) | LATER_ISSUED_GOVERNS (MEDIUM) | → LATER_EFFECTIVE_GOVERNS (canonical): $0.00 over 0 quantities; → MONTHLY_TABLE_SEPARATE (canonical): $0.00 over 0 quantities; → LATER_EFFECTIVE_GOVERNS (with claimed classes (hypothetical)): $176,970.55 over 1,578 quantities; → MONTHLY_TABLE_SEPARATE (with claimed classes (hypothetical)): $176,970.55 over 1,578 quantities |
| AMB-08 | `monthly_rate_basis` | **BASE_RATE_THEN_BUILD_UP** (A) | BASE_RATE_THEN_BUILD_UP (MEDIUM) | → FINAL_RATE (canonical): $19,347.45 over 53 quantities; → FINAL_RATE (with claimed classes (hypothetical)): $19,347.45 over 53 quantities |
| AMB-10 | `volume_tier_scope` | **PER_WELL** (A) | PER_WELL (LOW) | → CONTRACT_WIDE (canonical): $0.00 over 0 quantities; → CONTRACT_WIDE (with claimed classes (hypothetical)): -$2,784,778.89 over 4,271 quantities |
| AMB-11 | `contract_year_2` | **STARTS_2026_01_01** (A) | STARTS_2026_01_01 (MEDIUM) | → YEAR_1_EXTENDED (canonical): $0.00 over 0 quantities; → YEAR_1_EXTENDED (with claimed classes (hypothetical)): $0.00 over 0 quantities |
| AMB-21 | `lih_replacement_value` | **SCHEDULE_2D_CONVERTED** (A) | SCHEDULE_2D_CONVERTED (MEDIUM) | → SCHEDULE_6_USD (canonical): $55,391.01 over 47 quantities; → SCHEDULE_6_USD (with claimed classes (hypothetical)): $55,391.01 over 47 quantities |
| AMB-26 | `ds900_threshold_basis` | **SERVICES_ONLY** (A) | SERVICES_ONLY (MEDIUM) | None in this data (DS-900 is invoice-level; no invoice carries a non-service charge besides DS-900). |

## AMB-06 — What DD-120 hours are (`dd120_hours`)

1. **Relied on:** p.6, p.7, p.27, p.28
2. **Contract wording:** “Item DD-120 is charged per circulating hour recorded on the Daily Drilling Report for an Operating day” (p.6) / “DD-120 ... each circulating or back-reaming hour recorded on the report” (p.27)
3. **Reading A:** Circulating hours only (Clause 21).
4. **Reading B:** Circulating plus back-reaming hours (Schedule 8).
5. **Phase 1 preference:** none
6. **Measured effect of the alternatives:** → CIRCULATING_PLUS_BACK_REAMING (canonical): $0.00 over 9,580 quantities; → CIRCULATING_PLUS_BACK_REAMING (with claimed classes (hypothetical)): $1,011,212.30 over 9,580 quantities
7. **Recommendation:** CIRCULATING_ONLY (MEDIUM). Clause 21 is the pricing clause for DD-120 and charges 'per circulating hour'; Appendix A defines circulating hours as hours drilling fluid is pumped through the tool. Back-reaming hours are charged separately as RM-530 (cl. 30, Schedule 8), so reading B would charge the same hours under two items.
8. **Approved:** CIRCULATING_ONLY (reading A).
9. **Still uncertain:** Schedule 8 says 'circulating or back-reaming hour'; if Schedule 8 were ranked as a Schedule prevailing over Part III (cl. 2), B would govern. Schedule 8 is not listed in cl. 2.

## AMB-13 — Call-offs are not in the data (`calloff_evidence`)

1. **Relied on:** p.3, p.6, p.11, p.23, p.29
2. **Contract wording:** “Performance-drilled section: a 12-1/4 inch or 8-1/2 inch section of a well the call-off nominates for performance drilling.” (p.29) / “Each well is called off by a written notice stating the well name, the rig, the field and the well class. The well class stated in the call-off governs the whole well” (p.3)
3. **Reading A:** Take the well class stated on the invoice header as the Contractor's statement of the call-off, unverified; treat PD-210 as eligible only in 12-1/4 or 8-1/2 inch sections (the only sizes Appendix A allows).
4. **Reading B:** Treat both as unverifiable: charges that depend on them are queries, not verified passes.
5. **Phase 1 preference:** none
6. **Measured effect of the alternatives:** → INVOICE_STATEMENT_UNVERIFIED (canonical): $120,978,415.19 over 31,316 quantities
7. **Recommendation:** INVOICE_STATEMENT_UNVERIFIED (LOW). The contract fixes the well class by call-off (cl. 4, P2, P3), and no call-off is supplied. The invoice header is the contractor's statement of it, constant for every well. Reading B leaves every class-rated service unpriceable. PD-210/PD-201 eligibility (the nominated performance section) stays a flag for the audit phase either way.
8. **Approved:** UNKNOWN / UNVERIFIED (reading B). The missing call-offs mean well class and performance-section eligibility cannot be proven from the supplied contract evidence. The invoice is not evidence of its own entitlement. Any price that needs the class or the call-off stays unresolved (EVIDENCE_NOT_PROVIDED); unaffected services are priced canonically. The invoice-stated class is kept later only as the contractor's claimed class, marked unverified. The class sensitivity is preserved. PD-201 follows the same strict treatment: its rate is determinable without the call-off, but whether it was chargeable at all is not, so it is EVIDENCE_NOT_PROVIDED and its calculated amount is conditional only (never payable). The invoice's presence of PD-201 is not evidence that it was authorised.
9. **Still uncertain:** Whether any stated class is true; which 12-1/4" and 8-1/2" sections were nominated for performance drilling.

## AMB-01 — Rank of material not listed in Clause 2 (`unranked_precedence`)

1. **Relied on:** p.2, p.3, p.11, p.14, p.18, p.19, p.26, p.27, p.32, p.35, p.36, p.37
2. **Contract wording:** “This Contract is to be read with the instruments below, in the order issued.” (p.37) / “A Schedule prevails over a Part, and Part VI prevails over Parts I to V.” (p.3) / “This Contract comprises this Agreement, Parts I to VII, Schedules 1 to 6 and Appendices A to C.” (p.3)
3. **Reading A:** The unlisted documents form part of the contract but have no stated rank; each conflict must be resolved on its own terms (specific over general, or kept as a sensitivity switch).
4. **Reading B:** Rank by name: Schedules 2C, 2D, 7 and 8 are Schedules and prevail over any Part (Clause 2); Part IX, being 'Particular Conditions (Second Series)', ranks with Part VI and prevails over Parts I-V. **Reading C:** Clause 2 is exhaustive: documents it does not list are not contract documents and carry no weight against listed ones.
5. **Phase 1 preference:** none
6. **Measured effect of the alternatives:** Meta-decision: no direct effect; each concrete conflict has its own switch.
7. **Recommendation:** NO_RANK_CASE_BY_CASE (MEDIUM). Clause 2 ranks only Schedules over Parts and Part VI over Parts I-V. Ranking by name (B) is not in the text; treating cl. 2 as exhaustive (C) would discard the Schedule of Variations and instruments the pricing depends on. Each conflict is settled through its own switch.
8. **Approved:** NO_RANK_CASE_BY_CASE (reading A). No global rank for documents omitted from Clause 2; each concrete conflict is resolved through its own switch.
9. **Still uncertain:** Every recommendation that relies on Part IX, Schedule 2C/2D/8 or Appendix G.

## AMB-02 — Well-class factor on PD-210 (`pd210_class_factor`)

1. **Relied on:** p.17, p.20, p.30, p.35
2. **Contract wording:** “The rate is class-rated under Schedule 3 Part 2 and is not section-rated.” (p.17) / “The well-class factor in Schedule 3 Part 2 is not applied to item PD-210, Schedule 2 having already priced the metre by depth.” (p.35)
3. **Reading A:** Apply the Schedule 3 Part 2 class factor to PD-210.
4. **Reading B:** Do not apply the class factor to PD-210.
5. **Phase 1 preference:** none
6. **Measured effect of the alternatives:** → APPLY (canonical): $0.00 over 0 quantities; → APPLY (with claimed classes (hypothetical)): $3,975,398.58 over 1,936 quantities
7. **Recommendation:** DO_NOT_APPLY (MEDIUM). Clause 17B speaks to PD-210 specifically and gives its reason ('Schedule 2 having already priced the metre by depth'). The contract's own worked invoice (Appendix B, an HPHT well) prices PD-210 at the unfactored band rates 58.15 and 76.45.
8. **Approved:** DO_NOT_APPLY (reading B).
9. **Still uncertain:** The Schedule 2 note and the Schedule 3 Part 2 list name PD-210 as class-rated, and cl. 2 ranks a Schedule over a Part if Part IX is a Part.

## AMB-03 — Hole-section factor on a Standby day (`standby_section_factor`)

1. **Relied on:** p.6, p.35
2. **Contract wording:** “first the hole section factor ... then the well class factor ... then the standby percentage in Schedule 3 Part 3, where the day is a Standby day.” (p.6) / “The hole-section factor in Schedule 3 Part 1 is not applied on a day the rig is on Standby, the section not being drilled.” (p.35)
3. **Reading A:** On a Standby day apply section factor, class factor, then standby percentage (Clause 18 order, no exception).
4. **Reading B:** On a Standby day omit the section factor; apply class factor and standby percentage.
5. **Phase 1 preference:** none
6. **Measured effect of the alternatives:** → APPLY (canonical): $9,129.66 over 140 quantities; → APPLY (with claimed classes (hypothetical)): $16,321.93 over 406 quantities
7. **Recommendation:** OMIT (MEDIUM). Clause 17B says the hole-section factor is not applied on a Standby day and gives the reason ('the section not being drilled'); Clause 18 only states the general order. No example contradicts it (the Appendix B Standby line is not section-rated).
8. **Approved:** OMIT (reading B).
9. **Still uncertain:** Rank of Part IX against Part III (AMB-01).

## AMB-04 — Rig Services Index vs the Appendix B worked invoice (`rig_services_index`)

1. **Relied on:** p.18, p.30, p.35
2. **Contract wording:** “The rate for a service listed in Schedule 2C is the base rate stated in Schedule 1 multiplied by the Rig Services Index published for the calendar month in which the service was performed and divided by the base index” (p.35) / “04-Jun-2025 MW-310 12-1/4" Operating 1 2,975.75 2,975.75” (p.30)
3. **Reading A:** Apply the index from the first month (17A, Schedule 2C); Appendix B illustrates the build-up only.
4. **Reading B:** Appendix B, a Clause 2 contract document, shows MW-310 charged without the index; the index does not apply (or not in 2025).
5. **Phase 1 preference:** A (MEDIUM)
6. **Measured effect of the alternatives:** → NOT_APPLIED (canonical): -$331,856.42 over 7,821 quantities; → NOT_APPLIED (with claimed classes (hypothetical)): -$1,879,193.35 over 15,642 quantities
7. **Recommendation:** APPLY_FROM_FIRST_MONTH (MEDIUM). Clause 17A is an operative pricing clause and Schedule 2C restates it, calling the Schedule 1 rates of MW-310 and HC-620 'base rates'. Appendix B is a form of invoice; it also ignores 21A, so it does not reflect Part IX at all.
8. **Approved:** APPLY_FROM_FIRST_MONTH (reading A).
9. **Still uncertain:** Appendix B is listed in cl. 2 while Part IX and Schedule 2C are not; the index does not affect January 2025 (index 100.00).

## AMB-05 — Rig-up hour (21A) and the 6-hour minimum (`rig_up_hour`)

1. **Relied on:** p.6, p.11, p.21, p.30, p.32, p.35
2. **Contract wording:** “The report states the hours run; the invoice charges one fewer.” (p.35) / “BHA run: the period from the running of a bottom hole assembly into the hole to its recovery.” (p.29) / “04-Jun-2025 DD-120 12-1/4" Operating 18 509.00 9,162.00” (p.30) / “subject to a minimum of 6 hours on any Operating day on which the tool is in the hole” (p.6)
3. **Reading A:** Deduct one hour per report day for each hourly service, then apply the 6-hour minimum.
4. **Reading B:** Deduct one hour per BHA run (first day of the run only). **Reading C:** No deduction: charge the circulating hours recorded, as Appendix B does. **Reading D:** Apply the 6-hour minimum first, then deduct the rig-up hour.
5. **Phase 1 preference:** none
6. **Measured effect of the alternatives:** → PER_DAY_THEN_MINIMUM (canonical): $0.00 over 0 quantities; → NO_DEDUCTION (canonical): $249,470.65 over 943 quantities; → MINIMUM_THEN_PER_DAY (canonical): $0.00 over 0 quantities; → PER_DAY_THEN_MINIMUM (with claimed classes (hypothetical)): -$1,638,193.55 over 3,903 quantities; → NO_DEDUCTION (with claimed classes (hypothetical)): $544,660.65 over 1,646 quantities; → MINIMUM_THEN_PER_DAY (with claimed classes (hypothetical)): -$1,638,193.55 over 3,903 quantities
7. **Recommendation:** PER_BHA_RUN (LOW). 21A deducts 'the first hour of each period in the hole'; Appendix A defines a BHA run as 'the period from the running of a bottom hole assembly into the hole to its recovery' - the same period. The deduction is taken before the 6-hour minimum, because 21A defines the Chargeable Hour the minimum counts.
8. **Approved:** PER_BHA_RUN (reading B).
9. **Still uncertain:** 21A's second sentence ('the report states the hours run; the invoice charges one fewer') also fits a per-day deduction (A); Appendix B makes no deduction at all (C).

## AMB-07 — DD-120 (and DD-101) rate from February 2026 (`dd120_rate_from_feb_2026`)

1. **Relied on:** p.37, p.38, p.40, p.42
2. **Contract wording:** “This Contract is to be read with the instruments below, in the order issued.” (p.37) / “The rate chargeable is the rate published for the calendar month in which the service was performed.” (p.40) / “The rates below are substituted for the rates in Schedule 1 for services performed on or after the effective date” (p.42)
3. **Reading A:** Later issued governs: A3's 416.00 applies to all DD-120 services from 2026-02-01, displacing the S2 monthly table.
4. **Reading B:** Later effective governs: 416.00 for February and March 2026; the S2 monthly rates from April 2026. **Reading C:** A3 substitutes the Schedule 1 rate only; the monthly re-publication is a separate mechanism and governs from April 2026 regardless.
5. **Phase 1 preference:** none
6. **Measured effect of the alternatives:** → LATER_EFFECTIVE_GOVERNS (canonical): $0.00 over 0 quantities; → MONTHLY_TABLE_SEPARATE (canonical): $0.00 over 0 quantities; → LATER_EFFECTIVE_GOVERNS (with claimed classes (hypothetical)): $176,970.55 over 1,578 quantities; → MONTHLY_TABLE_SEPARATE (with claimed classes (hypothetical)): $176,970.55 over 1,578 quantities
7. **Recommendation:** LATER_ISSUED_GOVERNS (MEDIUM). Each instrument says: 'Where this instrument and an earlier instrument both state a rate ... the later governs services performed on or after its effective date'. 'Earlier instrument' is ordered by issue (the Schedule of Variations reads them 'in the order issued'), so Amendment No. 3 (issued last) governs DD-120 from 1 February 2026, including the months Supplement No. 2 re-published.
8. **Approved:** LATER_ISSUED_GOVERNS (reading A). Amendment No. 3's 416.00 governs DD-120 from its stated effective date (2026-02-01).
9. **Still uncertain:** Whether A3, which substitutes 'the rates in Schedule 1', reaches a monthly re-publication at all (C), or 'later' means later-effective (B).

## AMB-08 — Is a monthly re-published rate a base rate or the final rate? (`monthly_rate_basis`)

1. **Relied on:** p.6, p.38, p.40
2. **Contract wording:** “The rates below are substituted for the rates in Schedule 1” (p.38) / “The rate chargeable is the rate published for the calendar month in which the service was performed.” (p.40)
3. **Reading A:** The monthly rate replaces the Schedule 1 base rate; the Clause 18 build-up and discounts still apply.
4. **Reading B:** The monthly 'rate chargeable' is the final rate; no factors are applied to it.
5. **Phase 1 preference:** A (MEDIUM)
6. **Measured effect of the alternatives:** → FINAL_RATE (canonical): $19,347.45 over 53 quantities; → FINAL_RATE (with claimed classes (hypothetical)): $19,347.45 over 53 quantities
7. **Recommendation:** BASE_RATE_THEN_BUILD_UP (MEDIUM). Clause 18 builds every charge from the Schedule 1 rate; the instruments substitute for Schedule 1 rates; the standby percentage is stated as a percentage of the operating rate. Nothing says a monthly rate is all-in.
8. **Approved:** BASE_RATE_THEN_BUILD_UP (reading A).
9. **Still uncertain:** The instruments call it 'the rate chargeable'. If AMB-07 is approved as recommended, this affects only HC-601 on Standby days.

## AMB-10 — Scope of the Contract-Year metre tiers (`volume_tier_scope`)

1. **Relied on:** p.17
2. **Contract wording:** “according to the metres already drilled on the well in the Contract Year (Clause 3A)” (p.17) / “Part 2 — Metres drilled in the Contract Year” (p.17)
3. **Reading A:** Per well: cumulative metres already drilled on that well within the Contract Year.
4. **Reading B:** Contract-wide: cumulative metres across all wells within the Contract Year.
5. **Phase 1 preference:** none
6. **Measured effect of the alternatives:** → CONTRACT_WIDE (canonical): $0.00 over 0 quantities; → CONTRACT_WIDE (with claimed classes (hypothetical)): -$2,784,778.89 over 4,271 quantities
7. **Recommendation:** PER_WELL (LOW). The only operative sentence says 'metres already drilled on the well in the Contract Year'.
8. **Approved:** PER_WELL (reading A).
9. **Still uncertain:** The heading and the column say 'in the Contract Year' without 'well'. Under PER_WELL no well reaches 40,000 m in this data, so the tiers never engage; that is context, not evidence, but it is why this needs your judgment.

## AMB-11 — Contract Years after the extensions (`contract_year_2`)

1. **Relied on:** p.35, p.37
2. **Contract wording:** “each following Contract Year from that anniversary. The final Contract Year ends on the Expiry Date as extended by any Amendment” (p.35) / “an extension does not begin a new Contract Year.” (p.35)
3. **Reading A:** Contract Year 2 runs 2026-01-01 to 2026-12-31 (starts at the anniversary; ends on the extended Expiry Date).
4. **Reading B:** The extensions do not begin a new Contract Year, so Contract Year 1 continues to 2026-12-31.
5. **Phase 1 preference:** A (MEDIUM)
6. **Measured effect of the alternatives:** → YEAR_1_EXTENDED (canonical): $0.00 over 0 quantities; → YEAR_1_EXTENDED (with claimed classes (hypothetical)): $0.00 over 0 quantities
7. **Recommendation:** STARTS_2026_01_01 (MEDIUM). 3A: 'each following Contract Year from that anniversary'; the extension sentence stops an extension's effective date from starting a year.
8. **Approved:** STARTS_2026_01_01 (reading A).
9. **Still uncertain:** Only matters where the tiers engage (the contract-wide reading of AMB-10).

## AMB-21 — Which replacement values: Schedule 6 (USD) or Schedule 2D (SAR converted) (`lih_replacement_value`)

1. **Relied on:** p.1, p.7, p.19, p.25, p.35, p.36
2. **Contract wording:** “Schedule 6 states the same values in the currency of the Contract as they stood when it was let, and Schedule 2D governs.” (p.35) / “the charge is its replacement value in Schedule 6 less depreciation” (p.7)
3. **Reading A:** Schedule 2D converted at the month of loss (31A).
4. **Reading B:** Schedule 6 USD values (Clause 31).
5. **Phase 1 preference:** A (MEDIUM)
6. **Measured effect of the alternatives:** → SCHEDULE_6_USD (canonical): $55,391.01 over 47 quantities; → SCHEDULE_6_USD (with claimed classes (hypothetical)): $55,391.01 over 47 quantities
7. **Recommendation:** SCHEDULE_2D_CONVERTED (MEDIUM). 31A addresses the conflict expressly: 'Schedule 6 states the same values ... as they stood when it was let, and Schedule 2D governs'.
8. **Approved:** SCHEDULE_2D_CONVERTED (reading A).
9. **Still uncertain:** Clause 31, the Form of Agreement and the Appendix G footnote cite Schedule 6; rank of Part IX (AMB-01).

## AMB-26 — What the Clause 38 threshold counts (`ds900_threshold_basis`)

1. **Relied on:** p.8, p.35
2. **Contract wording:** “Where the sum of the amounts of the services charged on an invoice exceeds 250,000.00 USD” (p.8) / “The net amount of an invoice is the sum of the amounts of its charges” (p.8)
3. **Reading A:** Services only (Schedule 1 items including LH items); the 36A adjustment is excluded.
4. **Reading B:** Every charge on the invoice other than DS-900 itself.
5. **Phase 1 preference:** A (MEDIUM)
6. **Measured effect of the alternatives:** None in this data (DS-900 is invoice-level; no invoice carries a non-service charge besides DS-900).
7. **Recommendation:** SERVICES_ONLY (MEDIUM). Clause 38 measures 'the sum of the amounts of the services charged on an invoice'.
8. **Approved:** SERVICES_ONLY (reading A).
9. **Still uncertain:** It only matters if an invoice carries a charge other than services and DS-900 (a 36A adjustment line, AMB-12). DS-900 is invoice-level and is priced when invoices are assembled, not in this phase.

