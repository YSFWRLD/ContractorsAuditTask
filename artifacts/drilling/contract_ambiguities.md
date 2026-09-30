# DDS-2025-118 — ambiguity register

Generated from `contract_ambiguities.json`. Readings were formed from the contract package only. Invoice, line and report data were not used to prefer any reading.

| id | title | status | preferred | confidence | affects totals | resolve in |
|---|---|---|---|---|---|---|
| AMB-01 | Rank of material not listed in Clause 2 | OPEN | — | — | yes | Phase 4 (pricing) as a documented switch per dependent conflict |
| AMB-02 | Well-class factor on PD-210 | OPEN | — | — | yes | Phase 4 (pricing) switch |
| AMB-03 | Hole-section factor on a Standby day | OPEN | — | — | yes | Phase 4 (pricing) switch |
| AMB-04 | Rig Services Index vs the Appendix B worked invoice | OPEN | A | MEDIUM | yes | Phase 4 (pricing) switch |
| AMB-05 | Rig-up hour (21A) and the 6-hour minimum | OPEN | — | — | yes | Phase 3 (quantities) and Phase 4 switch |
| AMB-06 | What DD-120 hours are | OPEN | — | — | yes | Phase 3 (quantities) |
| AMB-07 | DD-120 (and DD-101) rate from February 2026 | OPEN | — | — | yes | Phase 4 (pricing) switch |
| AMB-08 | Is a monthly re-published rate a base rate or the final rate? | OPEN | A | MEDIUM | yes | Phase 4 (pricing) switch |
| AMB-09 | 4 per cent (S2) and 7 per cent (A2) principal-services discounts | RESOLVED_BY_TEXT | A | HIGH | yes | Phase 4 (pricing) |
| AMB-10 | Scope of the Contract-Year metre tiers | OPEN | — | — | yes | Phase 4 (pricing) switch |
| AMB-11 | Contract Years after the extensions | OPEN | A | MEDIUM | yes | Phase 4 (pricing) switch |
| AMB-12 | Placement and scope of the Amendment No. 3 back-dated adjustment | OPEN | — | — | yes | Phase 4 (pricing) and Phase 5 (audit) switch |
| AMB-13 | Call-offs are not in the data | EVIDENCE_NOT_PROVIDED | — | — | yes | Phase 5 (audit policy) and Phase 6 (confidence) |
| AMB-14 | Separate field reports (cl. 16, Appendices E-F) vs parts of the one DDR (Schedule 5) | OPEN | A | MEDIUM | possibly | Phase 3 (records) and Phase 5 (audit) |
| AMB-15 | Service codes on the report (R5/R6, Appendix D) vs rig words (19A, Appendix G) | OPEN | A | MEDIUM | possibly | Phase 3 (report-to-service mapping) |
| AMB-16 | Report terms mapped to two codes | RESOLVED_BY_TEXT | A | HIGH | possibly | Phase 3 (report-to-service mapping) |
| AMB-17 | Pairings in Appendix G that look shifted or unexpected | OPEN | A | MEDIUM | yes | Phase 3 (report-to-service mapping) switch |
| AMB-18 | DD-102 charging basis | OPEN | A | LOW | possibly | Phase 3 (quantities) |
| AMB-19 | HC-630 charging basis | OPEN | A | MEDIUM | possibly | Phase 3 (quantities) |
| AMB-20 | DD-121 condition | OPEN | A | MEDIUM | possibly | Phase 3 (quantities) |
| AMB-21 | Which replacement values: Schedule 6 (USD) or Schedule 2D (SAR converted) | OPEN | A | MEDIUM | yes | Phase 4 (pricing) switch |
| AMB-22 | Hours for depreciation | OPEN | A | MEDIUM | yes | Phase 3 (quantities) |
| AMB-23 | Consequence of an unsigned or missing record | OPEN | — | — | yes | Phase 5 (audit policy) |
| AMB-24 | Metres for LW-410/411/412 and RM-510 | OPEN | A | MEDIUM | yes | Phase 3 (quantities) |
| AMB-25 | Submission date vs invoice date | EVIDENCE_NOT_PROVIDED | — | — | possibly | Phase 5 (audit policy) |
| AMB-26 | What the Clause 38 threshold counts | OPEN | A | MEDIUM | possibly | Phase 4 (pricing) |
| AMB-27 | Cross-references that do not resolve | NOTED | A | HIGH | no | none (noted) |

## AMB-01 — Rank of material not listed in Clause 2

Clause 2 lists the Agreement, Parts I-VII, Schedules 1-6 and Appendices A-C, and ranks only Schedules over Parts and Part VI over Parts I-V. Part VIII, Part IX, Schedules 2C, 2D, 7 and 8, Appendices D-G and the Schedule of Variations are bound into the package but are absent from both the Contents and Clause 2 (verified on p.2 and p.3). No clause ranks them, and Clause 2 gives no rank to Appendices A-C either. Conflicts that depend on this: AMB-02, AMB-03, AMB-04, AMB-05, AMB-06, AMB-14, AMB-15, AMB-21.

Sources: p.2 Contents, p.3 Clause 2, p.11 P1, p.14 Part VIII, p.35 Part IX, p.18 Schedule 2C, p.19 Schedule 2D, p.26 Schedule 7, p.27 Schedule 8, p.32 Appendices D-F, p.36 Appendix G, p.37 Schedule of Variations

- **Reading A.** The unlisted documents form part of the contract but have no stated rank; each conflict must be resolved on its own terms (specific over general, or kept as a sensitivity switch).
  - p.37 Schedule of Variations: “This Contract is to be read with the instruments below, in the order issued.”
  - p.35 Clause 31A: “Schedule 6 states the same values ... and Schedule 2D governs.”
- **Reading B.** Rank by name: Schedules 2C, 2D, 7 and 8 are Schedules and prevail over any Part (Clause 2); Part IX, being 'Particular Conditions (Second Series)', ranks with Part VI and prevails over Parts I-V.
  - p.3 Clause 2: “A Schedule prevails over a Part, and Part VI prevails over Parts I to V.”
  - p.35 Part IX heading: “PART IX — PARTICULAR CONDITIONS (SECOND SERIES)”
- **Reading C.** Clause 2 is exhaustive: documents it does not list are not contract documents and carry no weight against listed ones.
  - p.3 Clause 2: “This Contract comprises this Agreement, Parts I to VII, Schedules 1 to 6 and Appendices A to C.”

Preferred: none (no preference). The contract does not rank these documents. Reading C would discard the Schedule of Variations the instruments depend on, which the package plainly intends to operate; A and B both remain open.
Status: OPEN. Phase 0 check: confirmed; also found that Appendices A-C have no stated rank.

## AMB-02 — Well-class factor on PD-210

Clause 17B says the well-class factor is not applied to PD-210. The Schedule 2 note says PD-210 is class-rated, and the Schedule 3 Part 2 list includes PD-210. The Appendix B worked invoice (an HPHT well) prices PD-210 at the unfactored band rates 58.15 and 76.45 (with the 1.325 HPHT factor Band 2 would be 77.05).

Sources: p.35 Clause 17B, p.17 Schedule 2 note, p.20 Schedule 3 Part 2, p.30 Appendix B

- **Reading A.** Apply the Schedule 3 Part 2 class factor to PD-210.
  - p.17 Schedule 2 note: “The rate is class-rated under Schedule 3 Part 2 and is not section-rated.”
  - p.20 Schedule 3 Part 2: “Class-rated services: DD-120, PD-210, MW-310, MW-320, LW-410, LW-411, LW-412, LW-413.”
  - p.3 Clause 2: “A Schedule prevails over a Part”
- **Reading B.** Do not apply the class factor to PD-210.
  - p.35 Clause 17B: “The well-class factor in Schedule 3 Part 2 is not applied to item PD-210, Schedule 2 having already priced the metre by depth.”
  - p.30 Appendix B: “04-Jun-2025 PD-210 12-1/4" Operating 2,930-3,000 70 58.15 4,070.50 (on an HPHT well)”

Preferred: none (no preference). Two provisions on each side; Part IX's rank against Schedules is unstated (AMB-01). The contract's own worked example agrees with B.
Status: OPEN. Phase 0 check: confirmed; Phase 1 adds that Appendix B follows 17B.

## AMB-03 — Hole-section factor on a Standby day

Clause 18 applies the section factor, then the class factor, then the standby percentage where the day is a Standby day. Clause 17B says the section factor is not applied on a day the rig is on Standby.

Sources: p.6 Clause 18, p.35 Clause 17B

- **Reading A.** On a Standby day apply section factor, class factor, then standby percentage (Clause 18 order, no exception).
  - p.6 Clause 18: “first the hole section factor ... then the well class factor ... then the standby percentage in Schedule 3 Part 3, where the day is a Standby day.”
- **Reading B.** On a Standby day omit the section factor; apply class factor and standby percentage.
  - p.35 Clause 17B: “The hole-section factor in Schedule 3 Part 1 is not applied on a day the rig is on Standby, the section not being drilled.”

Preferred: none (no preference). Direct conflict; Part IX vs Part III rank unstated (AMB-01).
Status: OPEN. Phase 0 check: new in Phase 1.

## AMB-04 — Rig Services Index vs the Appendix B worked invoice

17A and Schedule 2C price MW-310 and HC-620 at base rate x index / 100. Appendix B prices MW-310 on 04-Jun-2025 (12-1/4", HPHT) at 2,975.75, which is 2,245.85 x 1.00 x 1.325 with no index; with the June 2025 index (103.60) the build-up gives 2,326.70 x 1.325 = 3,082.88. This is an actual contradiction between the illustrative form and the operative clause, not a misread.

Sources: p.35 Clause 17A, p.18 Schedule 2C, p.30 Appendix B

- **Reading A.** Apply the index from the first month (17A, Schedule 2C); Appendix B illustrates the build-up only.
  - p.35 Clause 17A: “The rate for a service listed in Schedule 2C is the base rate stated in Schedule 1 multiplied by the Rig Services Index published for the calendar month in which the service was performed and divided by the base index”
  - p.18 Schedule 2C: “The rate stated in Schedule 1 for them is a base rate.”
- **Reading B.** Appendix B, a Clause 2 contract document, shows MW-310 charged without the index; the index does not apply (or not in 2025).
  - p.30 Appendix B: “04-Jun-2025 MW-310 12-1/4" Operating 1 2,975.75 2,975.75”

Preferred: A (MEDIUM). 17A is an operative pricing clause restated by Schedule 2C; Appendix B is a form of invoice. Held open because the rank of Part IX and Schedule 2C is unstated (AMB-01).
Status: OPEN. Phase 0 check: confirmed as a real contradiction (Phase 0 was not a misread).

## AMB-05 — Rig-up hour (21A) and the 6-hour minimum

21A: for a service charged by the hour the first hour of each period in the hole is not chargeable; 'the report states the hours run; the invoice charges one fewer'. Open points: (1) which services (DD-120 and RM-530 are the hourly items); (2) what a 'period in the hole' is (each day, each BHA run, each continuous spell); (3) whether the deduction comes before or after the 6-hour minimum; (4) Appendix B charges DD-120 at 18 hours, the circulating hours on the Appendix D report for the same day, with no deduction.

Sources: p.35 Clause 21A, p.6 Clause 21, p.11 P10, p.21 Schedule 3 Part 7, p.30 Appendix B, p.32 Appendix D

- **Reading A.** Deduct one hour per report day for each hourly service, then apply the 6-hour minimum.
  - p.35 Clause 21A: “The report states the hours run; the invoice charges one fewer.”
- **Reading B.** Deduct one hour per BHA run (first day of the run only).
  - p.29 Appendix A: “BHA run: the period from the running of a bottom hole assembly into the hole to its recovery.”
- **Reading C.** No deduction: charge the circulating hours recorded, as Appendix B does.
  - p.30 Appendix B: “04-Jun-2025 DD-120 12-1/4" Operating 18 509.00 9,162.00”
  - p.32 Appendix D: “Circulating hours 18”
- **Reading D.** Apply the 6-hour minimum first, then deduct the rig-up hour.
  - p.6 Clause 21: “subject to a minimum of 6 hours on any Operating day on which the tool is in the hole”

Preferred: none (no preference). 21A is explicit but its unit is undefined and the contract's own example does not apply it.
Status: OPEN. Phase 0 check: confirmed; Appendix B/D quantity 18 = report hours.

## AMB-06 — What DD-120 hours are

Clause 21 charges DD-120 per circulating hour; Schedule 8 says 'each circulating or back-reaming hour'. RM-530 (back-reaming while tripping) is also charged per back-reaming hour (cl. 30, Schedule 8).

Sources: p.6 Clause 21, p.27 Schedule 8 DD-120, p.28 Schedule 8 RM-530, p.7 Clause 30

- **Reading A.** Circulating hours only (Clause 21).
  - p.6 Clause 21: “Item DD-120 is charged per circulating hour recorded on the Daily Drilling Report for an Operating day”
- **Reading B.** Circulating plus back-reaming hours (Schedule 8).
  - p.27 Schedule 8: “DD-120 ... each circulating or back-reaming hour recorded on the report”

Preferred: none (no preference). Schedule 8 is unranked (AMB-01); reading B would charge back-reaming hours under both DD-120 and RM-530.
Status: OPEN. Phase 0 check: confirmed.

## AMB-07 — DD-120 (and DD-101) rate from February 2026

A3 (issued last, 2026-08-17) substitutes 416.00 for DD-120 from 2026-02-01. S2 (issued 2026-02-24) re-publishes DD-120 monthly from April 2026 (406.00 ... 447.50). The closing rule says 'the later governs services performed on or after its effective date', without saying whether 'later' means later issued or later effective. S2 and A2 discounts apply to DD-120 separately (AMB-09). DD-101 is simpler: A1 1,916.50 from 2026-01-01, A3 1,954.00 from 2026-02-01 (A3's 'rate previously chargeable' is A1's).

Sources: p.42 Amendment No. 3, p.40 Supplement No. 2, 2.1, p.38 instrument closing rule, p.37 Schedule of Variations

- **Reading A.** Later issued governs: A3's 416.00 applies to all DD-120 services from 2026-02-01, displacing the S2 monthly table.
  - p.37 Schedule of Variations: “This Contract is to be read with the instruments below, in the order issued.”
  - p.42 Amendment No. 3 closing: “the later governs services performed on or after its effective date”
- **Reading B.** Later effective governs: 416.00 for February and March 2026; the S2 monthly rates from April 2026.
  - p.40 Supplement No. 2, 2.1: “The rate chargeable is the rate published for the calendar month in which the service was performed.”
- **Reading C.** A3 substitutes the Schedule 1 rate only; the monthly re-publication is a separate mechanism and governs from April 2026 regardless.
  - p.42 Amendment No. 3, 3.1: “The rates below are substituted for the rates in Schedule 1 for services performed on or after the effective date”

Preferred: none (no preference). The instruments' ordering language supports A; the monthly mechanism's own wording supports B/C.
Status: OPEN. Phase 0 check: confirmed.

## AMB-08 — Is a monthly re-published rate a base rate or the final rate?

S1/S2 publish 'the rate chargeable' per month. DD-120 is section- and class-rated (Schedule 3) and discounted (S2/A2); HC-601 has a standby percentage (50%). The instruments do not say whether the Clause 18 build-up is applied on top of the monthly rate.

Sources: p.38 Supplement No. 1, 1.2, p.40 Supplement No. 2, 2.1, p.6 Clause 18

- **Reading A.** The monthly rate replaces the Schedule 1 base rate; the Clause 18 build-up and discounts still apply.
  - p.38 Supplement No. 1, 1.1: “The rates below are substituted for the rates in Schedule 1”
  - p.6 Clause 18: “The rate for a charge is the Schedule 1 rate ... to which is applied”
- **Reading B.** The monthly 'rate chargeable' is the final rate; no factors are applied to it.
  - p.40 Supplement No. 2, 2.1: “The rate chargeable is the rate published for the calendar month in which the service was performed.”

Preferred: A (MEDIUM). Schedule 1 rates are always the start of the Clause 18 build-up and the instruments describe their rates as substitutes for Schedule 1 rates.
Status: OPEN. Phase 0 check: new in Phase 1.

## AMB-09 — 4 per cent (S2) and 7 per cent (A2) principal-services discounts

Both instruments list the same five services. From 2026-07-01 are they cumulative, or does 7% replace 4%? Also, both refer to 'the build-up required by Clause 17' although the build-up is Clause 18 (Clause 17 is rounding).

Sources: p.40 Supplement No. 2, 2.2, p.41 Amendment No. 2, 2.3

- **Reading A.** 7% replaces 4% from 2026-07-01.
  - p.41 Amendment No. 2 closing: “Where this instrument and an earlier instrument both state a rate or a discount for the same service, the later governs services performed on or after its effective date”
  - p.41 Amendment No. 2 purpose: “the deepening of the Supplement No. 2 discount”
- **Reading B.** Both apply from 2026-07-01 (cumulative).
  - p.40 Supplement No. 2, 2.2: “A discount of 4 per cent is allowed on the services listed below for services performed on or after 1 April 2026.”

Preferred: A (HIGH). The closing rule covers 'a rate or a discount for the same service', and A2 describes itself as deepening the S2 discount.
Status: RESOLVED_BY_TEXT. Phase 0 check: new in Phase 1.

## AMB-10 — Scope of the Contract-Year metre tiers

Schedule 2 Part 2 sets PD-210 at 100/96/92 per cent by 'metres already drilled on the well in the Contract Year'. The heading and column say 'in the Contract Year' without 'well'. Also open: which metres count (PD-210 metres only, or every metre drilled on the well) and, for a per-well count, whether metres before the call-off's performance section count. That a single well could hardly reach 40,000 m is context only and is not treated as evidence.

Sources: p.17 Schedule 2 Part 2

- **Reading A.** Per well: cumulative metres already drilled on that well within the Contract Year.
  - p.17 Schedule 2 Part 2: “according to the metres already drilled on the well in the Contract Year (Clause 3A)”
- **Reading B.** Contract-wide: cumulative metres across all wells within the Contract Year.
  - p.17 Schedule 2 Part 2 heading: “Part 2 — Metres drilled in the Contract Year”
  - p.17 Schedule 2 Part 2 table: “Metres in the Contract Year”

Preferred: none (no preference). The only operative sentence says 'on the well'; the heading and column do not. Not decided in Phase 1.
Status: OPEN. Phase 0 check: confirmed; sentences extracted, no feasibility argument used.

## AMB-11 — Contract Years after the extensions

3A: first Contract Year to the day before the first anniversary; each following year from that anniversary; the final year ends on the extended Expiry Date; 'an extension does not begin a new Contract Year'. The Term as let was one year.

Sources: p.35 Clause 3A, p.37 Schedule of Variations

- **Reading A.** Contract Year 2 runs 2026-01-01 to 2026-12-31 (starts at the anniversary; ends on the extended Expiry Date).
  - p.35 Clause 3A: “each following Contract Year from that anniversary. The final Contract Year ends on the Expiry Date as extended by any Amendment”
- **Reading B.** The extensions do not begin a new Contract Year, so Contract Year 1 continues to 2026-12-31.
  - p.35 Clause 3A: “an extension does not begin a new Contract Year.”

Preferred: A (MEDIUM). The anniversary rule starts a new year independently of any extension; the extension sentence is read as preventing an extension's effective date from starting a year.
Status: OPEN. Phase 0 check: new in Phase 1.

## AMB-12 — Placement and scope of the Amendment No. 3 back-dated adjustment

36A: the difference on services already invoiced is shown 'as a single adjustment on the first invoice submitted on or after the date of issue, and on no other'. A3: 'on the first invoice submitted after the date of issue'. Open points: (1) 'on or after' vs 'after' 2026-08-17; (2) invoices are per well (cl. 32), so is there one adjustment for the whole contract or one per well; (3) submission date vs invoice date (NP-06); (4) the Schedule of Variations says nothing in an instrument reopens a service already charged at the rate then chargeable.

Sources: p.42 Amendment No. 3, p.35 Clause 36A, p.37 Schedule of Variations, p.8 Clause 32

- **Reading A.** One adjustment for the whole contract, on the first invoice (any well) submitted on or after 2026-08-17 (36A wording).
  - p.35 Clause 36A: “shown as a single adjustment on the first invoice submitted on or after the date of issue, and on no other”
- **Reading B.** As A but strictly after 2026-08-17 (A3 wording).
  - p.42 Amendment No. 3: “the difference shown as a single adjustment on the first invoice submitted after the date of issue (Clause 36A)”
- **Reading C.** One adjustment per well, on that well's first invoice submitted on or after the date of issue.
  - p.8 Clause 32: “The Contractor shall invoice each well separately”
- **Reading D.** No re-pricing of services already charged (Schedule of Variations).
  - p.37 Schedule of Variations: “nothing in an instrument reopens a service already charged at the rate then chargeable.”

Preferred: none (no preference). A3 and 36A are specific to back-dated amendments and both require an adjustment; D conflicts with them. A vs B vs C is not settled by the text.
Status: OPEN. Phase 0 check: confirmed; 'on or after' (36A) vs 'after' (A3) verified.

## AMB-13 — Call-offs are not in the data

The well class (factor for class-rated services, whole well) and the performance-drilled sections (the only sections on which PD-210 is chargeable; PD-201 staffing) are fixed by the call-off. No call-off is supplied.

Sources: p.3 Clause 4, p.11 P2/P3, p.29 Appendix A, p.6 Clause 23, p.23 Schedule 4

- **Reading A.** Take the well class stated on the invoice header as the Contractor's statement of the call-off, unverified; treat PD-210 as eligible only in 12-1/4 or 8-1/2 inch sections (the only sizes Appendix A allows).
  - p.29 Appendix A: “Performance-drilled section: a 12-1/4 inch or 8-1/2 inch section of a well the call-off nominates for performance drilling.”
- **Reading B.** Treat both as unverifiable: charges that depend on them are queries, not verified passes.
  - p.3 Clause 4: “Each well is called off by a written notice stating the well name, the rig, the field and the well class. The well class stated in the call-off governs the whole well”

Preferred: none (no preference). Evidence not provided; the choice is an audit policy, not a contract reading.
Status: EVIDENCE_NOT_PROVIDED. Phase 0 check: confirmed from cl. 4, P2, P3, cl. 23 and Appendix A.

## AMB-14 — Separate field reports (cl. 16, Appendices E-F) vs parts of the one DDR (Schedule 5)

Clause 16 (and H6) require separate BHA Run Reports, Gyro Survey Reports, Source Handling Certificates and Lost in Hole Reports; Appendices E and F show them as separate forms with different signatories (lead DD + MWD engineer; survey engineer + Company Representative; Company Representative + field manager). Schedule 5 says these records are Parts B-E of the DDR and there are no separate documents. Which signatures a Part B-E record needs is therefore open.

Sources: p.5 Clause 16, p.24 Schedule 5, p.33 Appendix E, p.34 Appendix F, p.13 H6

- **Reading A.** Schedule 5 governs: Parts B-E of the signed DDR are the records; the DDR's two signatures (cl. 15) cover them.
  - p.24 Schedule 5: “There are no separate run, survey, source or loss documents.”
  - p.3 Clause 2: “A Schedule prevails over a Part”
- **Reading B.** Each record needs the signatories of its illustrative form (Appendices E-F).
  - p.33 Appendix E: “Signed Lead directional driller; MWD engineer”
  - p.34 Appendix F: “Signed Survey engineer; Company Representative”

Preferred: A (MEDIUM). Clause 2 ranks Schedule 5 above Part II; Appendices D-F are marked 'Illustrative only' and unranked.
Status: OPEN. Phase 0 check: new in Phase 1.

## AMB-15 — Service codes on the report (R5/R6, Appendix D) vs rig words (19A, Appendix G)

R5 and R6 require tools and personnel to be listed by service code, and the Appendix D form does so. 19A says the report is written in the ordinary words of the rig and does not carry service codes; Appendix G gives the vocabulary.

Sources: p.14 R5/R6, p.32 Appendix D, p.35 Clause 19A, p.36 Appendix G

- **Reading A.** Rig words are the contractual form; Appendix G maps them to codes.
  - p.35 Clause 19A: “does not repeat the descriptions in Schedule 1 or carry the service codes.”
  - p.36 Appendix G: “The terms below are the ones it uses for the items Schedule 1 prices.”
- **Reading B.** The report must list codes (R5/R6); a report in rig words is non-compliant.
  - p.14 R5: “The report lists by service code every rental tool in the hole at any time during the day.”

Preferred: A (MEDIUM). Appendix G exists only to serve reading A, and 19A addresses the vocabulary specifically. Parts VIII and IX are both unranked (AMB-01).
Status: OPEN. Phase 0 check: confirmed.

## AMB-16 — Report terms mapped to two codes

'mud motor' -> DD-110 and LH-711; 'rotary steerable' -> DD-120 and LH-712; 'MWD collar' -> MW-310 and LH-713; 'gamma tool' -> LW-410 and LH-714.

Sources: p.36 Appendix G and footnote

- **Reading A.** The rental/logging code applies while the tool is in the hole; the LH code applies to a tool recorded as lost (Part E).
  - p.36 Appendix G footnote: “A tool lost in the hole is recorded by the term above; the item charged is the replacement value Schedule 6 states against it.”
- **Reading B.** The term alone cannot identify the item; such charges are unresolved identification (guideline check 6).

Preferred: A (HIGH). The footnote states how the duplicate terms are used.
Status: RESOLVED_BY_TEXT. Phase 0 check: confirmed all four duplicates.

## AMB-17 — Pairings in Appendix G that look shifted or unexpected

Printed pairings: 'gamma tool' -> LW-410 LWD resistivity (and LH-714 LWD resistivity tool); 'resistivity tool' -> LW-411 density and neutron; 'density-neutron' -> LW-412 sonic; MW-310 'MWD directional and gamma tool' -> 'MWD collar'; 'survey package' -> MW-320 pressure while drilling; 'float sub' -> HC-640 cuttings bed monitoring; 'bit and reamer' -> PD-220 vibration mitigation tool; 'hydraulics package' -> PD-230 memory sub; 'night man' -> DD-102 office-based coordinator. No term is given for a sonic tool, a pressure tester or a source.

Sources: p.36 Appendix G

- **Reading A.** Literal: the table is the contract's vocabulary and governs as printed.
  - p.36 Appendix G: “The terms below are the ones it uses for the items Schedule 1 prices.”
- **Reading B.** The LWD rows are shifted by one line and the words carry their ordinary meaning.

Preferred: A (MEDIUM). The contract governs; a surprising mapping is not treated as an error. Kept as a sensitivity question.
Status: OPEN. Phase 0 check: confirmed; preserved literally.

## AMB-18 — DD-102 charging basis

Schedule 8's intro: DD-102 is 'charged per day for each coordinator the Daily Drilling Report records'. Its row: 'each day the Daily Drilling Report records the tool in the hole'. Schedule 4: 1, office based, whole well. Appendix G maps DD-102 to 'night man' (a crew entry). Unit: day; daily limit 1.

Sources: p.27 Schedule 8 intro and DD-102 row, p.23 Schedule 4, p.36 Appendix G, p.21 Schedule 3 Part 5

- **Reading A.** Per coordinator the report records (the 'night man' crew count), limit 1 a day.
  - p.27 Schedule 8 intro: “Item DD-102 is office based and is charged per day for each coordinator the Daily Drilling Report records.”
- **Reading B.** Each day the report records a tool in the hole.
  - p.27 Schedule 8 DD-102: “each day the Daily Drilling Report records the tool in the hole”

Preferred: A (LOW). The intro singles DD-102 out specifically; the row repeats the generic rental wording.
Status: OPEN. Phase 0 check: confirmed.

## AMB-19 — HC-630 charging basis

Schedule 8: HC-630 'each BHA run, as Clause 26 describes', but Clause 26 names only DD-111 and LW-420. Clause 30 charges clean-out runs in the numbers recorded on the DDR for an Operating day.

Sources: p.28 Schedule 8 HC-630, p.7 Clauses 26 and 30

- **Reading A.** Count clean-out runs from the report for an Operating day (Clause 30).
  - p.7 Clause 30: “Gyro surveys, formation pressure points, wiper trips, back-reaming hours and clean-out runs are charged in the numbers recorded on the Daily Drilling Report for an Operating day.”
- **Reading B.** Once per BHA run.
  - p.28 Schedule 8 HC-630: “each BHA run, as Clause 26 describes”

Preferred: A (MEDIUM). Clause 30 names clean-out runs expressly; the Schedule 8 cross-reference points to a clause that does not mention HC-630.
Status: OPEN. Phase 0 check: confirmed.

## AMB-20 — DD-121 condition

DD-121 is charged on a Standby day in place of DD-120. Schedule 8 and Clause 28 add 'each day the DDR records the tool in the hole'.

Sources: p.6 Clause 21, p.21 Schedule 3 Part 4, p.27 Schedule 8 DD-121, p.7 Clause 28

- **Reading A.** Only on a Standby day on which the report records the rotary steerable in the hole.
  - p.27 Schedule 8 DD-121: “each day the Daily Drilling Report records the tool in the hole”
  - p.7 Clause 28: “A rental charged by the day is charged for a day only where the Daily Drilling Report records the tool in the hole on that day.”
- **Reading B.** On every Standby day of a well using the rotary steerable, in place of DD-120.
  - p.21 Schedule 3 Part 4: “DD-121 is charged only on a Standby day, in place of item DD-120 (Clause 21).”

Preferred: A (MEDIUM). Clause 28 applies to every day rental; B is not excluded by the text.
Status: OPEN. Phase 0 check: confirmed.

## AMB-21 — Which replacement values: Schedule 6 (USD) or Schedule 2D (SAR converted)

Clause 31, the Form of Agreement and the Appendix G footnote point to Schedule 6 (USD). 31A says Schedule 2D (SAR, converted at the month of loss) governs. At the 2025-01 rate (375.00) the two agree exactly.

Sources: p.7 Clause 31, p.1 Form of Agreement, p.36 Appendix G footnote, p.35 Clause 31A, p.19 Schedule 2D, p.25 Schedule 6

- **Reading A.** Schedule 2D converted at the month of loss (31A).
  - p.35 Clause 31A: “Schedule 6 states the same values in the currency of the Contract as they stood when it was let, and Schedule 2D governs.”
- **Reading B.** Schedule 6 USD values (Clause 31).
  - p.7 Clause 31: “the charge is its replacement value in Schedule 6 less depreciation”
  - p.36 Appendix G footnote: “the item charged is the replacement value Schedule 6 states against it.”

Preferred: A (MEDIUM). 31A addresses the conflict expressly and names the governing schedule; Part IX's general rank is still unstated (AMB-01).
Status: OPEN. Phase 0 check: confirmed.

## AMB-22 — Hours for depreciation

Clause 31 and P12: circulating hours 'the tool accumulated on the well', including the day of loss. Part E records 'the circulating hours accumulated on the well at the time of the loss' (well, not tool).

Sources: p.7 Clause 31, p.11 P12, p.24 Schedule 5 Part E

- **Reading A.** Use the Part E figure as stated.
  - p.24 Schedule 5 Part E: “the circulating hours accumulated on the well at the time of the loss”
- **Reading B.** Use the tool's own hours on the well (sum of report hours while that tool was in the hole, including the day of loss).
  - p.11 P12: “Circulating hours for Clause 31 are those the tool accumulated on the well on which it was lost, including the day of the loss.”

Preferred: A (MEDIUM). Clause 31 says the hours are 'as stated on the Lost in Hole Report'.
Status: OPEN. Phase 0 check: new in Phase 1.

## AMB-23 — Consequence of an unsigned or missing record

Clause 15 requires two signatures on the DDR. Clause 37 and Schedule 5 make listed services 'not payable until' the part is delivered; a part that applies and is absent is 'a record not delivered'. Nothing states the consequence of an unsigned report, or whether 'not payable until' means part-reject or query.

Sources: p.5 Clause 15, p.8 Clause 37, p.24 Schedule 5, p.14 R8

- **Reading A.** Not payable: part-reject the charge.
  - p.8 Clause 37: “is not payable until the document Schedule 5 names has been delivered”
- **Reading B.** Payable later once delivered: a query, not a rejection.
  - p.8 Clause 37: “not payable until”

Preferred: none (no preference). Audit-policy question the contract does not answer.
Status: OPEN. Phase 0 check: confirmed.

## AMB-24 — Metres for LW-410/411/412 and RM-510

Clauses 24/25 charge 'the metres drilled on an Operating day while the tool is in the hole' (day depths). Part B records metres logged and reamed for the run. Schedule 8 describes PD-210, LW-410/411/412 and RM-510 alike as 'each metre drilled, logged or reamed as Clauses 23 to 25 describe'. 25A allows 1% over the metres 'the report supports'.

Sources: p.6 Clauses 24-25, p.24 Schedule 5 Part B, p.27 Schedule 8, p.35 Clause 25A

- **Reading A.** Day metres: depth end minus depth start on an Operating day with the tool in the hole.
  - p.6 Clause 24: “charged for the metres drilled on an Operating day while the tool is in the hole, which are the metres logged.”
- **Reading B.** Part B metres logged/reamed.
  - p.24 Schedule 5 Part B: “metres logged and reamed”

Preferred: A (MEDIUM). The clauses define the metres logged as the metres drilled that day; Part B is a run record.
Status: OPEN. Phase 0 check: new in Phase 1.

## AMB-25 — Submission date vs invoice date

Clause 33 and 36A turn on when an invoice is submitted; the Form of Agreement says 'within 30 days of period end'. The data supplies an invoice date only (NP-06).

Sources: p.8 Clause 33, p.1 Form of Agreement

- **Reading A.** Treat the invoice date as the submission date.
- **Reading B.** Submission date unknown: window findings are queries.

Preferred: none (no preference). Evidence not provided; a Phase 5 policy.
Status: EVIDENCE_NOT_PROVIDED. Phase 0 check: new in Phase 1.

## AMB-26 — What the Clause 38 threshold counts

'the sum of the amounts of the services charged on an invoice' - does it include a 36A adjustment line (not a service) and lost-in-hole charges? 'Exceeds' is read as strictly greater than.

Sources: p.8 Clause 38, p.35 Clause 36A

- **Reading A.** Services only (Schedule 1 items including LH items); the 36A adjustment is excluded.
  - p.8 Clause 38: “Where the sum of the amounts of the services charged on an invoice exceeds 250,000.00 USD”
- **Reading B.** Every charge on the invoice other than DS-900 itself.
  - p.8 Clause 36: “The net amount of an invoice is the sum of the amounts of its charges”

Preferred: A (MEDIUM). Clause 38 says 'services'.
Status: OPEN. Phase 0 check: new in Phase 1.

## AMB-27 — Cross-references that do not resolve

S1 cites Clause 19.3, A1 Clause 19.1 and A3 Clause 16.4 - none exists (Clauses 16 and 19 have no sub-clauses). S2/A2 refer to 'the build-up required by Clause 17' (the build-up is Clause 18). Schedule 5 cites Clause 19 for one DDR per well and day (issued under Clause 15). The Contents title of Schedule 5 differs from its page heading.

Sources: p.38 Supplement No. 1, p.39 Amendment No. 1, p.42 Amendment No. 3, p.40 Supplement No. 2, 2.2, p.41 Amendment No. 2, 2.3, p.24 Schedule 5

- **Reading A.** Clerical: the references do not change the instruments' operative text.
  - p.40 Supplement No. 2, 2.2: “as the last factor in the build-up required by Clause 17 and before the rounding it requires”
- **Reading B.** The instruments rest on clauses not provided, so their basis cannot be verified.

Preferred: A (HIGH). Each instrument states its changes in full; nothing turns on the cited clause.
Status: NOTED. Phase 0 check: new in Phase 1.
