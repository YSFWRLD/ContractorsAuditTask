# Drilling: Phase 0 inventory

> Superseded for contract facts by Phase 1 (`docs/drilling/phase1_contract_extraction.md`). Phase 1 corrections: Schedule 1 has 38 service codes, not 39 (DS-900 is the Clause 38 discount code, not a Schedule 1 service); Appendix B also prices PD-210 without the class factor (supporting 17B); ten further ambiguities were found. Phase 2 correction: Part C appears on 479 reports, not 486 (see `phase2_data_inventory.md`).

This is a first pass over contract DDS-2025-118 and its data. Nothing here is a decision. Ambiguities are **identified, not resolved**, and every value below still has to be transcribed and reviewed in Phase 1 before any code relies on it.

Sources:
- the 42 page renders of `drilling_services/contract/DDS-2025-118.pdf`, read by eye;
- a descriptive pass over the CSVs and the 8,151 reports.

## Contract map (42 scanned pages, no text layer)

| pages | part | content |
|---|---|---|
| 1 | Agreement | Northgate Petroleum (Company) and Meridian Downhole Services Ltd (Contractor). Term 01-Jan-2025 to 31-Dec-2025. USD. VAT 15%. Rounding "to the cent, half to even, at each step". Invoicing "per well, within 30 days of period end". |
| 2 | Contents | lists Parts I–VII, Schedules 1–6 and Appendices A–C only |
| 3–4 | Part I, cl. 1–14 | precedence (cl. 2: a Schedule prevails over a Part; Part VI over Parts I–V); call-off fixes the well class (cl. 4); suspension is Standby (cl. 13) |
| 5 | Part II, cl. 15–16 | Daily Drilling Report content; separate BHA run, gyro survey, source handling and lost-in-hole reports |
| 6–7 | Part III, cl. 17–31 | cl. 17 half-even rounding per step; cl. 18 build-up order (section factor → class factor → standby %); cl. 19–31 status, standby, circulating hours (min 6 h), personnel limits, PD-210 depth bands and splitting, metres logged and reamed, per-run and per-well items, tools in the hole, no double charging, counts, lost in hole |
| 8 | Part IV, cl. 32–42 | per-well invoices; submission window (not before period end, within 30 days); charge content; units; net amount; documents as a condition of payment; cl. 38 discount of 4% of services above 250,000; VAT; total |
| 9–10 | Part V, T1–T16 | technical requirements, not pricing |
| 11–12 | Part VI, P1–P14 | prevails over Parts I–V: HPHT / ER from the call-off, rig moves not chargeable, weather is Standby, crew change counted once, no night or holiday uplift, minimum hours per day, discount per invoice, lost-in-hole hours include the day of loss, standby personnel |
| 13 | Part VII, H1–H12 | HSE (H6: Source Handling Certificate for every run) |
| 14 | **Part VIII, R1–R12** | reporting: whole metres, whole hours (≥30 min rounds up), tools and personnel listed by service code (R5, R6), status is final (R7), corrections (R8), BHA run report (R9) |
| 15–16 | Schedule 1 | 39 service rates across Series 100–700; PD-210 → Schedule 2; LH-711..714 → cl. 31 |
| 17 | Schedule 2 (+ Part 2) | PD-210 depth bands (1,500 / 3,000 / 4,500 m; boundary is shallower); **Part 2** Contract-Year metre tiers 100 / 96 / 92% |
| 18 | **Schedule 2C** | indexed services MW-310, HC-620; Rig Services Index 2025-01 … 2026-12 |
| 19 | **Schedule 2D** | lost-in-hole replacement values in SAR; halalas per USD 2025-01 … 2026-12 |
| 20–22 | Schedule 3, Parts 1–7 | section factors (6 section-rated items); class factors (8 class-rated items); standby % / not chargeable; DD-121 standby only; daily limits; once per well; DD-120 minimum hours |
| 23 | Schedule 4 | personnel "normally on the rig"; the charge follows the DDR count |
| 24 | Schedule 5 | **all records are parts A–E of the one DDR** ("no separate run, survey, source or loss documents"); condition-of-payment table |
| 25 | Schedule 6 | lost-in-hole replacement values in USD |
| 26 | **Schedule 7** | tool specifications |
| 27–28 | **Schedule 8** | scope: what each service is "charged for" |
| 29 | Appendix A | definitions (BHA run, Day, Operating/Standby day, performance-drilled section = a nominated 12-1/4" or 8-1/2" section) |
| 30 | Appendix B | worked invoice: HPHT, Standby, band split; cl. 38 example (312,400.00 → −2,496.00) |
| 31 | Appendix C | insurances, notices, execution |
| 32–34 | **Appendices D–F** | illustrative DDR, BHA run, gyro and lost-in-hole forms (Appendix F: 412 h → 16%) |
| 35 | **Part IX, second series** | 3A Contract Years; 17A indexed rates; 17B factors that do not apply; 19A DDR number and rig words; 21A chargeable hour; 25A 1% metre tolerance; 31A SAR replacement values govern; 36A backdated amendments |
| 36 | **Appendix G** | rig words used in the report, mapped to service codes |
| 37 | **Schedule of Variations** | 5 instruments, read in order of issue |
| 38–42 | Instruments | Supplement 1, Amendment 1, Supplement 2, Amendment 2, Amendment 3 |

The parts in **bold** are missing from the Contents on page 2, and their place in the cl. 2 precedence order is not stated.

### Instruments (Schedule of Variations, p. 37)

| instrument | issued | effective | change |
|---|---|---|---|
| Supplement 1 | 2025-05-19 | 2025-07-01 | DD-120 384.15 → 398.50; DD-121 2,893.65 → 2,984.00; HC-601 monthly Jul–Dec 2025 (the last rate carries forward) |
| Amendment 1 | 2025-11-07 | 2026-01-01 | expiry → 2026-06-30; DD-101 1,916.50, MW-301 1,708.00, LW-401 1,969.00 |
| Supplement 2 | 2026-02-24 | 2026-04-01 | DD-120 monthly Apr–Dec 2026; 4% discount on DD-101, MW-301, LW-401, DD-120, MB-701, applied to the rate as the last factor |
| Amendment 2 | 2026-05-21 | 2026-07-01 | expiry → 2026-12-31; MW-301 1,763.00, MB-701 19,237.00; 7% discount on the same five items |
| Amendment 3 | 2026-08-17 | **2026-02-01** (backdated) | DD-120 416.00, DD-101 1,954.00; re-price already invoiced services as one adjustment (cl. 36A) |

## Data shape

| file | rows | notes |
|---|---|---|
| `invoices/invoices.csv` | 1,906 | One well per invoice. 214 wells, up to 13 invoices per well. 4 fields; well class Standard / Extended Reach / HPHT. `adjustment` is 0.00 on every row. 3 rows where net + VAT ≠ total. |
| `invoices/invoice_lines.csv` | 91,244 | `line_ref` is `MDS-nnnnn-lll`. 39 service codes. Depths only on PD-210 (2,390 lines). 63 DS-900 discount lines have no date, section, status or report. |
| `records/*.txt` | 8,151 | One Daily Drilling Report per well-day. Joined through the **`Report:` field** (`DDR-<well no>-<yyyymmdd>`), not the file name (`DDR_<well>_<yyyymmdd>.txt`). Every report is referenced and every reference resolves. |
| `submission_template.csv` | 2,806 | 1,906 MDS rows, each matching exactly one invoice |

**Reports.** Parts A (operations) and B (BHA run) are on every report.
- C (gyro): 486 reports.
- D (source handling): 367 reports.
- E (lost in hole): 54 reports.

In total, 6 part combinations occur. Parts A/B record tools and crew in rig words ("mud motor", "directional hands", …). These are exactly the 15 tool terms and 5 crew terms of Appendix G, with no service codes, even though R5/R6 say otherwise. Part B repeats the whole run's first/last day and totals on each day of the run. Status: Operating 7,770, Standby 381. Blank signature lines: 3 for the Company Representative and 3 for the lead directional driller.

**Observed descriptively (not yet findings):**
- Contract refs: `DSS-2025-118` on 2 invoices, `DDS-2025-181` on 1.
- 3 invoices were raised before period end and 3 more than 30 days after.
- 3 dated lines fall outside their invoice period.
- Services are billed up to 2027-01-23, past the extended expiry of 2026-12-31.
- Report `DDR-063-20260427` is referenced by two invoices, MDS-01340 and MDS-01352.
- MB-701 appears on 217 lines against 214 wells; MW-301 on 8,152 lines against 8,151 reports.

## Ambiguities identified (to become interpretation switches; none resolved)

1. **Precedence of the unlisted parts.** Cl. 2 ranks Schedules above Parts, and Part VI above Parts I–V. It says nothing about Part VIII, Part IX, Schedules 2C, 2D, 7 and 8, or Appendices D–G. The conflicts this leaves open:
   - 17B (Part IX) says no class factor on PD-210, but Schedule 2 and Schedule 3 Part 2 list PD-210 as class-rated.
   - R5/R6 (service codes on the report) conflict with 19A and Appendix G (rig words).
2. **Appendix G vocabulary.**
   - The same word maps to two codes: "mud motor" DD-110 / LH-711, "rotary steerable" DD-120 / LH-712, "MWD collar" MW-310 / LH-713, "gamma tool" LW-410 / LH-714.
   - The LWD rows look shifted: "gamma tool" → resistivity, "resistivity tool" → density-neutron, "density-neutron" → sonic.
   - Several pairings read oddly: "night man" → the office-based coordinator DD-102; "float sub" → cuttings bed monitoring; "survey package" → PWD; "bit and reamer" / "hydraulics package" / "hole opener" → PD-220 / PD-230 / RM-511.
   - The contract governs, but the literal wording and the Appendix G reading must both be kept.
3. **DD-120 hours.**
   - Cl. 21 counts circulating hours only; Schedule 8 counts "circulating or back-reaming" hours.
   - 21A deducts a rig-up hour "of each period in the hole" (per day or per run?), and it is unclear whether that comes before or after the 6-hour minimum (P10).
   - Appendix B bills 18 h, the report's figure, with no deduction.
   - Does 21A also apply to RM-530?
4. **The Appendix B example against 17A.** The example prices MW-310 in June 2025 without the index (2,245.85 × 1.325), but 17A requires base × index / 100.
5. **Where the index sits in the cl. 18 build-up.** It is also unclear how 17B ("section factor not applied on Standby") interacts with the Schedule 3 Part 3 percentages.
6. **The DD-120 rate from February 2026.** Three instruments overlap:
   - Amendment 3 (issued last) sets 416.00 from 2026-02-01;
   - Supplement 2 re-publishes DD-120 monthly from April 2026;
   - the Supplement 2 / Amendment 2 discounts also apply.

   "Later instrument governs" does not settle whether 416.00 displaces the monthly table. There is a similar question for DD-101: A1 then A3.
7. **Cl. 36A adjustment.**
   - Which invoice is "the first submitted on or after" 2026-08-17: per well, or contract-wide?
   - Amendment 3 says "after", not "on or after".
   - `adjustment` is always 0.
   - The Schedule of Variations says an instrument never reopens a charged service, which conflicts with Amendment 3.
8. **Schedule 2 Part 2 tiers.** Metres are counted "on the well in the Contract Year". A per-well count never reaches 40,000 m; a contract-wide count does. It is also unclear whether PD-210 metres only are counted, or all metres drilled.
9. **Standalone items.**
   - HC-630: Schedule 8 says "per BHA run as cl. 26", but cl. 26 does not mention it, while cl. 30 counts clean-out runs.
   - DD-102: the Schedule 8 intro says "per coordinator recorded", but its row says "tool in the hole".
   - DD-121: does it also need the tool in the hole?
10. **Condition of payment.** Is a missing or unsigned part a "not payable" part-reject or a query? What about the 3 unsigned reports? And R8 corrections?
11. **Evidence not provided.**
   - The call-offs: well class, and the nominated performance-drilled sections that gate PD-210 and PD-201.
   - The clauses the instruments cite: 19.1, 19.3, 16.4.
   - Index, FX and monthly rates after 2026-12.
12. **Lost in hole.** 31A and Schedule 2D (SAR, converted at the month's rate, half-even) govern over Schedule 6 (USD). Depreciation is 1% per complete 25 h, capped at 50%, and includes the day of loss. The order of rounding is stated; confirm it in Phase 1.

## Proposed phases

1. **Contract extraction and review.** Build `artifacts/drilling/contract_extraction.json`:
   - two-pass transcription of all 42 pages, with page, clause and source text;
   - instruments with their issue and effective dates; index, FX and monthly tables; Appendix G;
   - a precedence map and an ambiguity register with every reading kept.

   Also: typed `contract/` terms and the verification report. No pricing.
2. **Ingestion and structure.**
   - Typed invoice and line loaders.
   - A DDR parser for Parts A–E that keeps rig words verbatim.
   - Structural validation: joins, references, signatures, format variants.
   - Reconstruction of BHA runs and well timelines across days.
   - Source profiles and the input fingerprint.
3. **Record entitlement.** Turn each report into chargeable quantities per well, day and service, through Appendix G and cl. 20–31. Every contested reading becomes an explicit switch. Coverage is descriptive only.
4. **Rates and pricing.** Rate in force by service date across the 5 instruments, plus monthly republications, the 17A index, the principal-service discounts and 36A. Also:
   - the cl. 18 / 17B build-up, half-even at each step;
   - PD-210 band splits and the Contract-Year tiers;
   - standby percentages and lost in hole;
   - the invoice-level DS-900 discount and VAT;
   - sensitivity per switch.
5. **Audit rules.** The 12 checks, with a Drilling-owned category vocabulary: identity, term, window, records, quantities, identification, rates, adjustments, limits, duplicates (within an invoice and across invoices), arithmetic, and the 36A adjustment.
6. **Assessment and outputs.** Re-run under alternative readings; confidence; the expected-total policy; draft outputs and coverage in `outputs/drilling/`.
7. **Adversarial review and freeze.**
8. **Combined submission.** The one genuinely shared step: merge each domain's `InvoiceResult`s into `outputs/submission.csv`.
