# Drilling Phase 1: contract extraction

This phase records **contract facts** for DDS-2025-118. It does not execute them. No invoice was priced or audited, and invoice, line and report data were never used to choose or confirm a contract value or reading.

The detailed source of truth is `artifacts/drilling/contract_terms.json`, together with `contract_ambiguities.json`. This page is the readable summary.

## 1. Documents reviewed

| file | what it is | sha256 (prefix) |
|---|---|---|
| `drilling_services/contract/DDS-2025-118.pdf` | 42 scanned pages, no text layer: the whole contract package | `0f14d8a7e222d4c5` |
| `drilling_services/guidelines/INVOICE_AUDIT_GUIDELINES.md` | the 12 audit checks; not contractual ("the contract governs") | `621c507ed3a33003` |

There are no other contractual files. The five instruments (2 supplements, 3 amendments) are pages 38–42 of the same PDF, not separate files. The printed page number equals the PDF page number on all 42 pages.

**Method.** Two visual passes over page renders, with no OCR:
- **Pass A:** 150 dpi, full page.
- **Pass B:** 220 dpi, half-page crops.

Tables were transcribed in both passes and compared by script: 462 values, 0 discrepancies (`artifacts/drilling/review/`). Narrative text was read in pass A and transcribed verbatim from the pass B crops.

## 2. Contract structure

The PDF holds 34 documents; `contract_terms.json → documents` lists them with pages.

**Listed in Clause 2 and the Contents:**
- the Form of Agreement (p.1);
- Parts I–VII (pp.3–13);
- Schedules 1–6 (pp.15–25, with gaps);
- Appendices A–C (pp.29–31).

**Bound in, but listed in neither the Contents nor Clause 2:**
- Part VIII, Reporting and Data (p.14);
- Schedule 2C, Indexed Services (p.18);
- Schedule 2D, SAR replacement values and exchange rates (p.19);
- Schedule 7, Tool Specifications (p.26);
- Schedule 8, Scope of Services (pp.27–28);
- Appendices D–F, illustrative report forms (pp.32–34);
- Part IX, Particular Conditions (Second Series) (p.35);
- Appendix G, terms used in the field reports (p.36);
- the Schedule of Variations (p.37).

**Precedence as stated:**
- A Schedule prevails over a Part.
- Part VI prevails over Parts I–V.
- The instruments are read in the order issued, and each governs services performed from its effective date.
- Where two instruments state a rate or discount for the same service, the later governs.
- Clause 31A says Schedule 2D governs over Schedule 6.
- Appendix A definitions apply throughout.

Nothing ranks the unlisted material, or even Appendices A–C (**AMB-01**).

## 3. Service catalog summary

**Schedule 1 has 38 service codes, not 39.** DS-900 is the Clause 38 invoice discount code, not a Schedule 1 service; Phase 0 had counted it in.

| Series | Codes |
|---|---|
| 100 Directional Drilling | DD-101, 102, 110, 111, 120, 121, 130, 140 |
| 200 Performance Drilling | PD-201, 210, 220, 230 |
| 300 MWD | MW-301, 310, 320, 330 |
| 400 LWD | LW-401, 410, 411, 412, 413, 420, 430 |
| 500 Reaming | RM-510, 511, 520, 530 |
| 600 Hole Conditioning | HC-601, 610, 620, 630, 640 |
| 700 Mobilisation / Lost in Hole | MB-701, 702, LH-711..714 |

- **Units:** person-day, day, run, hour, survey, well, metre, point, trip, each.
- **Rates:** Schedule 1 prints a USD rate for 33 codes. PD-210 is rated by Schedule 2; LH-711..714 by Clause 31.

Each service record in the JSON carries:
- its section and class rating;
- its standby treatment and daily limit;
- whether it is once-per-well or subject to the 6-hour minimum;
- any required report part;
- whether it is indexed or monthly-republished;
- which instruments amend or discount it;
- its Appendix G terms;
- its Schedule 8 "charged for" text.

## 4. Amendment timeline

| document | issued | effective | effect |
|---|---|---|---|
| Supplement 1 (p.38) | 2025-05-19 | 2025-07-01 | DD-120 384.15 → 398.50; DD-121 2,893.65 → 2,984.00; HC-601 monthly rates Jul–Dec 2025, the last carries forward |
| Amendment 1 (p.39) | 2025-11-07 | 2026-01-01 | Expiry → 2026-06-30 (+181 days); DD-101 → 1,916.50; MW-301 → 1,708.00; LW-401 → 1,969.00 |
| Supplement 2 (p.40) | 2026-02-24 | 2026-04-01 | DD-120 monthly rates Apr–Dec 2026 (406.00 … 447.50); 4% rate discount on DD-101, MW-301, LW-401, DD-120, MB-701 |
| Amendment 2 (p.41) | 2026-05-21 | 2026-07-01 | Expiry → 2026-12-31 (+184 days); MW-301 → 1,763.00; MB-701 → 19,237.00; 7% discount on the same five |
| Amendment 3 (p.42) | 2026-08-17 | **2026-02-01** | Back-dated: DD-120 → 416.00, DD-101 → 1,954.00; services already invoiced are re-priced as a single adjustment (Clause 36A) |

**Term:** commencement 2025-01-01, original expiry 2025-12-31, final expiry 2026-12-31. No instrument adds or removes a service. The model keeps every rate statement with its issue and effective dates; `rate_statements_on(code, date)` returns all candidates for a date and never chooses between them.

## 5. Pricing-component inventory (captured, not executed)

- **Build-up (cl. 18):**
  1. hole-section factor (6 section-rated services);
  2. well-class factor (8 class-rated services as printed);
  3. standby percentage.

  Each step is rounded half to even to the cent (cl. 17). Before step 1 comes the Rig Services Index for MW-310 and HC-620 (17A). After step 3 comes the S2/A2 rate discount, applied as the last factor before rounding.
- **Section factors:** 26" 1.315, 17-1/2" 1.145, 12-1/4" 1.00, 8-1/2" 0.945, 6" 0.885.
- **Class factors:** Standard 1.00, Extended Reach 1.175, HPHT 1.325.
- **Standby:**
  - 17 services charge a percentage (50/80/100%);
  - 12 are not chargeable on a Standby day;
  - DD-121 is charged only on a Standby day;
  - per-well and lost-in-hole items are charged in full whatever the day's status.
- **PD-210 depth bands:** 42.35 / 58.15 / 76.45 / 98.70 per metre, with bands ending at 1,500, 3,000 and 4,500 m. A boundary depth belongs to the shallower band; a day that crosses a boundary is split into one charge per band.
- **Contract-Year tiers for PD-210:** 100% up to 40,000 m, 96% from 40,001 to 120,000 m, 92% above.
- **Rig Services Index:** base 100.00, monthly for 2025-01 to 2026-12. Nothing is published after that.
- **Monthly rates:** HC-601 (S1) and DD-120 (S2).
- **Lost in hole:**
  - Schedule 2D SAR values, converted at the month's halalas-per-USD rate (half-even), then depreciated;
  - depreciation is 1% per complete 25 circulating hours, capped at 50%;
  - Schedule 6 gives the same values in USD at the rate when the contract was let (they match exactly at 375.00).
- **Invoice discount DS-900:** 4% of the excess where the services total *exceeds* 250,000.00 USD. It is calculated per invoice alone, rounded under cl. 17, and taken after the rate discounts. VAT is 15% of the net amount, which includes DS-900.
- **Limits:**
  - daily limits on 22 services;
  - once per well: DD-140, LW-430, MB-701, MB-702;
  - DD-120 minimum of 6 hours per Operating day, not averaged over a run;
  - 21A rig-up hour;
  - 25A 1% tolerance on metres.

## 6. Appendix G observations

There are 24 rows, transcribed literally.

**Four terms map to two codes each:**
- mud motor → DD-110 and LH-711;
- rotary steerable → DD-120 and LH-712;
- MWD collar → MW-310 and LH-713;
- gamma tool → LW-410 and LH-714.

The Appendix G footnote explains the pairing: a lost tool is recorded by the same term and charged at its replacement value (AMB-16).

**Pairings that look shifted or odd are preserved, not corrected (AMB-17):**
- gamma tool → LW-410 resistivity;
- resistivity tool → LW-411 density-neutron;
- density-neutron → LW-412 sonic;
- survey package → MW-320 PWD;
- float sub → HC-640 cuttings bed monitoring;
- bit and reamer → PD-220 vibration tool;
- hydraulics package → PD-230 memory sub;
- night man → DD-102 office-based coordinator.

The mapping exists only in the contract artifact. A test fails if any other layer hard-codes an Appendix G term.

## 7. Important contradictions (all kept as ambiguities)

| id | conflict |
|---|---|
| AMB-02 | 17B says there is no class factor on PD-210; the Schedule 2 note and the Schedule 3 Part 2 list say PD-210 is class-rated. Appendix B (an HPHT well) prices PD-210 without the factor. |
| AMB-03 | 17B drops the section factor on Standby days; cl. 18 applies it before the standby percentage. |
| AMB-04 | Appendix B prices MW-310 in June 2025 without the index: 2,975.75 against 3,082.88 with index 103.60. This is a real contradiction, not a Phase 0 misread. |
| AMB-05 | 21A deducts a rig-up hour; Appendix B charges the full 18 report hours. The unit of "period in the hole" and the order against the 6-hour minimum are undefined. |
| AMB-06 | Cl. 21 counts circulating hours; Schedule 8 counts circulating or back-reaming hours for DD-120. |
| AMB-07 | DD-120 from Feb 2026: A3's 416.00 (issued last, back-dated) against S2's monthly table from April. |
| AMB-12 | 36A says "on or after the date of issue"; A3 says "after". It is unclear whether the adjustment is one for the contract or one per well. The Schedule of Variations says nothing reopens a service already charged. |
| AMB-14 | Cl. 16 and Appendices E–F require separate reports with other signatories; Schedule 5 says there are none. |
| AMB-15 | R5/R6 and Appendix D require service codes on the report; 19A and Appendix G say rig words. |
| AMB-21 | Cl. 31, the Agreement and the Appendix G footnote point to Schedule 6; 31A says Schedule 2D governs. |

The full register has 27 entries, each with readings, verbatim evidence, preference (if any), confidence, the phase that resolves it, and status:
- 22 open (9 with no preferred reading; 13 with a recorded, non-binding preference);
- 2 resolved by the text (AMB-09 discount replacement, AMB-16 duplicate terms);
- 2 evidence not provided;
- 1 noted with no effect.

## 8. Evidence not provided

- **NP-01, call-offs.** Without them the well class and the nominated performance-drilled sections can't be verified (PD-210, PD-201, all class-rated services).
- **NP-02, clauses 19.1, 19.3 and 16.4.** The instruments cite them, but they don't exist.
- **NP-03, the Circulating Equipment and Steerable Tool indices.** Not needed: the resulting rates are published.
- **NP-04, index and exchange rates after 2026-12.**
- **NP-05, separate run, survey, source and loss documents.**
- **NP-06, invoice submission dates.** Only an invoice date is available.
- **NP-07, report revisions and issue times.**
- **NP-08, rig-move days.**
- **NP-09, execution signatures.**

## 9. Questions deliberately deferred

**Phase 3 (report → chargeable quantities):**
- AMB-05, AMB-06 (hours);
- AMB-14, AMB-15, AMB-16, AMB-17 (records and vocabulary);
- AMB-18, AMB-19, AMB-20 (DD-102, HC-630, DD-121 basis);
- AMB-22, AMB-24 (hours and metres).

**Phase 4 (rates and pricing switches):**
- AMB-01, AMB-02, AMB-03, AMB-04 (precedence and factors);
- AMB-07, AMB-08, AMB-09 (rates and discounts);
- AMB-10, AMB-11 (tiers and Contract Years);
- AMB-21, AMB-26 (lost-in-hole value, discount threshold).

**Phase 5/6 (audit policy and confidence):** AMB-12, AMB-13, AMB-23, AMB-25.

## 10. Artifacts produced

| file | kind |
|---|---|
| `artifacts/drilling/contract_terms.json` | reviewed, versioned (`drilling-contract-terms` 1.0): the contract facts with provenance |
| `artifacts/drilling/contract_ambiguities.json` | reviewed, versioned (`drilling-contract-ambiguities` 1.0): the ambiguity register |
| `artifacts/drilling/review/transcription_pass_{a,b}.json` | the two independent table transcriptions |
| `artifacts/drilling/source_manifest.json` | generated: sha256 of every drilling input, including the 8,151 reports as a tree hash |
| `artifacts/drilling/contract_terms.md`, `contract_ambiguities.md` | generated readable renderings |

`python -m contractor_audit build-artifacts --domain drilling` does contract-only work:
1. validates both reviewed files;
2. checks the PDF sha256;
3. regenerates the three derived files.

`run --domain drilling` is still not implemented.
