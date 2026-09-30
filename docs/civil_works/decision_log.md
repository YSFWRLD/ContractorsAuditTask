# Decision log — civil works (CW-2025-0417-CIV)

What was assumed, what the contract settles, and what stays open. Readings are chosen from the
contract text only. Billed data is used **descriptively** (sensitivity, "consistency with observed
billing") and never to pick a reading. Phase 1 records are not rewritten here; this log adds to them.

Evidence: `artifacts/civil_works/contract_extraction.json` (page-cited transcription),
`interpretation_matrix.md` (every switch), `sensitivity.md` (effect of each alternative).

## CURRENT POLICY (frozen in Phase 4, 2026-09-29)

This section is authoritative. The phase notes below are history. The figures are regenerated in
`outputs/civil_works/` (`coverage.md`, `sensitivity.md`, `review.md`).

**Result:**
- 900 applications and 7,746 lines were audited.
- 77 applications are flagged, with 95 findings.
- 37 corrected totals are published and 40 are blank.
- Flagged confidence: HIGH 66, MEDIUM 9, LOW 2. Unflagged confidence: HIGH 571, MEDIUM 250, LOW 2.

### Accepted readings (contract text settles them; the alternative is only measured)

| Reading | Basis |
|---|---|
| Rebate bands restart each Contract Year | Sch 4 Part 3 expressly substitutes Clause 30; Clause 2 says a Schedule prevails |
| Schedule 2B figures are USD, converted monthly | Clause 2 precedence over Clause 38 and the Schedule 1 heading |
| Converted and indexed figures are rounded half-even before the build-up | 26A / 29A |
| G2 ground class for all work after 2025-09-27 | 27A: "that is to say for work executed after 27 September 2025" |
| No night uplift above zone factor 1.1 | 27A |
| The later discount replaces the earlier (A2 8% replaces S2 5%) | closing words of every instrument |
| D.41.020 monthly rate is per m² | S1 1.2; S2 2.1; Clause 26 |
| A1 rates apply from 2025-10-01 | A1 1.2: "the effective date stated against each" |

### Unresolved readings (working value, grade, measured effect)

| Reading | Working | Grade | Alternative flags / unflags | Flagged totals changed |
|---|---|---|---|---|
| `indexed_rate_method` | 29A index | MEDIUM | flags 215 more | 22 |
| `monthly_rate_treatment` | base rate in build-up | MEDIUM | flags 33 more | 4 |
| `survey_quantity_rule` | 33A 2% tolerance | MEDIUM | flags 25 more | 0 |
| `measurement_order` (Clause 44 "later") | later submission | MEDIUM | 7 findings move between applications | 7 |
| `missing_record_consequence` | Clause 46: not payable now | MEDIUM | 0 (findings stay) | 8 |
| `unsigned_record` | not a valid record | MEDIUM | 0 | 1 |
| `retro_adjustment_trigger` | 31A "on or after" issue | LOW | the adjustment moves PA-00006 → PA-00443 | 1 |
| `exclusion_window` | same day included | LOW | unflags PA-00801 | 1 |
| `rebate_progression` | "measurable" quantities count | MEDIUM | 0 | 0 |
| `chargeable_hour_scope` | per record | MEDIUM | 0 | 0 |
| `concurrent_uplifts` | rest-day only without an instruction | MEDIUM (evidence absent) | 0 | 0 |

**Indexation:** reviewed in Phase 4.
- Clause 2 lists "Schedules 1 to 5 and Appendix A" as the whole agreement. Schedule 2A is inside that list; Appendix B's unindexed example is not.
- That favours 29A more strongly than Phase 2 recorded. The conflict is still inside the document, so the reading stays MEDIUM; it was not upgraded for the freeze.

**Daily cap:**
- The consequence is contract-defined. Clause 31 makes the payable quantity the limit.
- Clause 44 disallows any second measurement of the same item, work area and date, so the cap always binds one line.
- A defensive guard blanks the total if that ever fails.

### Corrected-total policy: STRICT (production)

A flagged application's `expected_total_cents` is published only if:
- every line is priced;
- every payable quantity is determined; and
- no unresolved or evidence-dependent reading changes the total.

Otherwise it is blank. Each blank application has one mutually exclusive `primary_blank_reason`: data gaps first, then the LOW readings, then fixed switch order. The full list is kept in `blank_reasons`.

The GRADED figure (75 totals) is kept in `application_audit.csv` for analysis only; it is never the output. Unflagged rows carry `expected_total_cents = billed_total_cents`.

### Timing-only policy

A breach of an explicit timing or documentation requirement flags the application (guideline check 3, Clauses 40–41). It does not change the total, and no financial consequence is invented. Contractual non-compliance is not the same as repricing.

- **Application-level fields:** `total_status = unchanged`, `outcome = query`.
- **Confidence:** these findings (`application_timing`, `application_period_misstated`) are capped at MEDIUM. The breach is certain, but the contract states no consequence for it.
- **Timing-only applications:** PA-00125, PA-00699 and PA-00708.

### Adjustment versus total

`application_total` is the measured total (Clause 43). Retention, the Clause 31A adjustment and the Clause 45A release are separate columns (Clause 45A). They are reported as findings with their amounts and never folded into `expected_total_cents`.

`total_status` distinguishes the two cases:
- "this application has a contractual error" (`flagged`);
- "`application_total` itself is the wrong number" (`corrected`, or `undetermined` when blank).

For example, PA-00006 (missing adjustment) and PA-00678 (missing release) are flagged for those sums; neither sum changes the application total.

### Primary-category precedence

The row's `error_category` is the finding with the lowest (tier, category precedence, line, rule). The monetary amount never decides it. Tiers:

1. HIGH-confidence finding that changes the total.
2. Any other finding that changes the total.
3. A determinable sum outside the total.
4. A structural issue.
5. A timing or documentation issue.

The category precedence within a tier is `CATEGORY_PRECEDENCE` in `audit/categories.py`, also printed in `review.md`. Every finding is kept in `findings.jsonl`.

### Categories

There are 25 categories. Five have no occurrence in this data but are implemented and tested: `work_outside_contract_period`, `record_line_mismatch`, `item_not_in_contract`, `adjustment_incorrectly_applied` and `retention_incorrect`.
- `record_line_mismatch` is zero now because the one case was the same defect as its `item_record_mismatch` and is reported once.
- `item_not_in_contract` was added in Phase 4 for guideline check 6. There is no `service_not_contracted_on_date`: no Schedule 1 item is date-limited.

## Phase 1 — extraction decisions (2026-09-29)

| # | Decision | Basis |
|---|---|---|
| 1 | Contract transcribed by AI visual reading, two passes, no OCR at runtime | Scan has no text layer; two transcriptions compared, 0 discrepancies |
| 2 | Nothing marked UNREADABLE | Every page legible at 170–240 dpi |
| 3 | 18 ambiguities recorded with all readings; none resolved in the extraction | Resolution deferred to pricing (Phase 2) |

## Phase 2 — pricing decisions (2026-09-29)

### Settled by the contract text (alternative kept only for sensitivity)

| Question | Working reading | Why | Phase 1 id |
|---|---|---|---|
| Rebate bands: per Contract Year or whole Works? | Per Contract Year | Sch 4 Part 3 says "Clause 30 is substituted" and counts "from zero at the start of each Contract Year"; Clause 2: a Schedule prevails over the General Conditions | AMB-BANDS |
| Schedule 2B items: USD or SAR? | USD, converted at the month's Sch 2B rate | Clause 2: a Schedule prevails over the GC (cl. 38) and a later-numbered Schedule (2B) over an earlier one (1) | AMB-USD-CURRENCY |
| Round the converted / indexed figure before the build-up? | Yes, half-even | 26A/29A state their own rounding and that the result "is then treated as the rate"; Clause 28's single rounding applies to the build-up from there | new |
| Ground class after 2025-09-27 | G2 for all work | 27A: "that is to say for work executed after 27 September 2025" — no work-area limit | AMB-G2-EOT |
| Night uplift above zone factor 1.1 | Not payable (Z3, Z4) | 27A, express | AMB-NIGHT-ZONE |
| 5% (S2) and 8% (A2) discounts | 8% replaces 5% from 2026-04-01 | Every instrument's closing words: where two instruments state a discount for the same item, the later governs; A2 recital "deepening" | AMB-DISCOUNT-STACK |
| D.41.020 monthly rate: per m2 or per tonne? | Per m2 | S1 1.2 publishes the "rate payable for a measured quantity"; D.41.020 is measured in m2 (cl. 26 forbids another unit); S2 2.1 lists 220.50 as the m2 rate "previously payable". "Per tonne" names the index, not the unit | AMB-D41020-UNIT (now resolved) |
| A1 effective 2025-09-28 vs its rates' 2025-10-01 | Rates from 2025-10-01 | A1 1.2: "for work executed on or after the effective date stated against each" | new |
| D.41.020 after September 2025 | 220.50 in October and November 2025, then S2 228.00 | S1 1.2: "the rate last published applies until it is superseded" | new |
| Build-up order and rounding | Clause 27 order; discount after rebate, before rounding; one half-up rounding | Clauses 27–28; S2 2.2 / A2 2.3 | — |
| Multipliers compound | `x(1+p)` / `x p%` / `x(1-p)` in sequence | Clause 27 "applying ... in the following order" | new |

### Genuinely unresolved (working reading chosen from the text; alternative priced alongside)

| Question | Working | Alternative(s) | Why working | Sensitivity (lines / applications / Σ\|Δ\| SAR) |
|---|---|---|---|---|
| Indexation of C.31.010, D.41.030 (29A vs the Appendix B example) | 29A | unindexed | 29A and Sch 2A are operative; Appendix B is an illustrative form outside the Clause 2 documents | 279 / 237 / 716,967 |
| Monthly rate: a base rate for the build-up, or final? | base rate | final | the instruments call BoQ substitutions "rate payable" too, and S2 applies its discount "within the build-up" to D.41.020 | 40 / 37 / 903,203 |
| Surveyed quantity: 33 exact vs 33A 2% tolerance | 33A | 33 | 33A is later and specific; Part VII has no stated precedence | 25 lines differ, ~20,335 |
| 6A first hour: per record / line / work-area-day | per record | per line, per area-day | 6A ties it to "the site record [that] states the hours attended" | 7 area-days differ; 1,550 vs 1,557 hours |
| Exclusion window includes the same day? | included | excluded | P19 "within two days of" | 1 line |
| Which application carries the A3 adjustment; is an application dated on the issue day post-issue? | 31A "on or after" (PA-00006) | A3 recital "after" (PA-00443) | A3 cites Clause 31A for the mechanism | adjustment moves PA-00006 → PA-00443; 2 lines repriced |

### Rule clear, evidence absent

| Question | Handling |
|---|---|
| Night + rest-day uplift together (P11) | Only on a Clause 9 instruction; none in the data, so rest-day alone. Theoretical branch `both_assumed_instructed` exists; no line in the data reaches it (0 lines). |
| Contract reference CW-2024-0417-CIV on PA-00560, PA-00711 | Not a pricing question; left for the audit rules. |

### New ambiguities found in Phase 2

1. **Tie among same-day first applications.** Three applications are dated 2026-05-12, the A3 issue date. Clause 31A names "the first", with no tie-break; application-number order is used, which gives PA-00006.
2. **Band ordering after substitution.** Sch 4 Part 3 replaces Clause 30 but restates no ordering. Clause 30's order (date of execution, then application number, then line number) is the only one in the contract and is used under both counting readings.
3. **What counts toward a band.** Every billed quantity currently counts, including measurements a later rule may disallow. To be decided with the audit rules.
4. **Base of the 45A release.** "Retention held on all earlier Applications" may mean the retention actually deducted, or retention as it should have been. The engine takes it as a parameter; the working valuation uses contract-side retention.
5. **Fractional quantities.** No rounding rule is stated for quantity × rate with a sub-halala result. This only arises for a fractional quantity (none in the data); half-up per Clause 28 is used.
6. **Work after the final completion date in band counting.** Two lines fall there (PA-00375-07, PA-00678-10). They are counted in the final Contract Year for illustration only; the lines are not measurable (A2 2.1).

### Outside the measured total

Clause 45A: amount payable = measured total + 31A adjustment − retention + released retention. The
engine therefore reports the A3 adjustment (60,508.18 on PA-00006 under the working reading) and the
45A release (on PA-00678, the first application after 2026-09-30) separately. How these relate to the
judged figure, `application_total`, is a Phase 3 decision.

### Transcription check

Implementing the engine found no Phase 1 transcription error. The Appendix B example lines A.12.020
and A.14.020 are reproduced exactly (50.72, 23.74).

## Phase 3 — audit decisions (2026-09-29)

Pricing says what should be paid; the audit (`src/.../civil_works/audit/`) compares that with the
application. Billed data is used to **detect** differences, never to choose a reading. Every audit
reading below was fixed from the contract wording before its effect on the data was measured.

### Decision A — sums settled outside the measured total

`expected_total_cents` is the corrected total of what this application measures: its `application_total`,
which Clause 43 defines as the sum of its items. This agrees with the task schema ("what the invoice
should have totalled"; the figure judged is `application_total`), and the CSV carries `adjustment` and
`retention_released` as separate columns. The Clause 31A adjustment and the Clause 45A release are
therefore findings (`adjustment_missing` / `adjustment_incorrectly_applied`), quantified but not folded
into `expected_total_cents`:
- PA-00006: 31A adjustment of 60,508.18 missing, graded LOW because of `retro_adjustment_trigger`.
- PA-00678: 45A release of 4,036,222.10 missing.

Retention errors are findings outside the total.

### Decision B — do disallowed quantities advance the rebate bands?

| Reading | Status | Basis |
|---|---|---|
| **`measurable_only` (working)** | unresolved, MEDIUM | Sch 4 Part 3 counts "the quantity measured"; the contract distinguishes "not measurable" (31, 32, 44, 26, 41, A2 2.1, quantity above the record, 6A, 33A) from "not payable" (46). |
| `all_billed` | alternative | what Phase 2 valued |
| `payable_only` | alternative | |

Measured effect: 0 lines, 0 findings and 0 totals change under either alternative. The only banded line with a disallowed quantity is PA-00609-01 (missing record, so "not payable" but still measured).

### New audit readings (all unresolved, MEDIUM)

| Switch | Working | Alternative | Measured effect |
|---|---|---|---|
| `missing_record_consequence` | Clause 46: not payable in this application | P23: deduct from the next valuation | 8 totals change; findings remain |
| `unsigned_record` | not a valid record (47, P22) | accepted with a defect | 1 total (PA-00613) |
| `measurement_order` (which is the "later measurement", Clause 44) | later submission date (guideline 10: "against an earlier one") | higher application number | 7 findings move between applications |

### Expected-total policy (STRICT)

A flagged application's corrected total is published only if:
- every line is priced and its payable quantity determined; and
- no unresolved or evidence-dependent reading changes the total.

Otherwise it is left blank, and `blank_reasons` says why. Result: 37 of 77 totals are published; 40 are blank, 22 of them because of `indexed_rate_method`. Under the GRADED alternative, which blanks only on LOW-grade readings, 75 would be published. A finding is emitted whether or not the total can be published.

### Confidence policy

Confidence reflects evidence quality, not probability. Each reading has a fixed grade:
- **HIGH:** text-resolved;
- **MEDIUM:** unresolved or evidence-absent;
- **LOW:** unresolved where the text gives near-equal support to both sides (`exclusion_window`, `retro_adjustment_trigger`).

The grades map to fixed scores: HIGH 0.95, MEDIUM 0.75, LOW 0.55.

- **Findings:** a finding's band is the weakest grade among the readings whose alternative makes it disappear. These dependencies are measured by re-running the whole audit with each reading flipped.
- **Flagged applications:** the band of the best-supported finding, since one finding suffices. When a total is published, it is capped by the weakest reading that total depends on.
- **Unflagged applications:** HIGH, unless an unresolved reading would flag the application.

### Audit choices recorded

1. **Band-split lines.** A line the contract divides at a band edge has no single rate (Clause 28), so only its amount is compared. The contractor prints the pre-rebate rate on such lines; that is not judged.
2. **One allowance per record.** A record evidences its quantity once. Every line quoting it draws on one allowance in measurement order. A later line refused for that reason is `duplicate_record`. This catches 19 weekly dewatering logs, each quoted by 2–3 A.16.010 lines for the same week and work area.
3. **Record defects follow the missing-record consequence.** A record of the wrong series or item, or for another area or date, does not evidence the line; it is treated as missing, subject to `missing_record_consequence`.
4. **Timing and reference findings do not change the total.** Late or early submission (Clause 41), a misstated period (Clause 40) and a wrong contract reference state no monetary consequence. They flag the application but leave its total unchanged. A line outside the stated period is not payable in that application, because Clause 41 says "no item shall be included".
5. **Retroactive A3 rates.** An application submitted before Amendment 3's issue is valued at the rate then in force (31A); it is not a rate error.

### New ambiguities found in Phase 3

1. **Which duplicate is disallowed.** "Later measurement" (Clause 44) could mean later submission, a higher application number or a later work date. This is the `measurement_order` switch.
2. **Whether timing breaches make an invoice "wrong".** Clause 41 states no monetary consequence for a late or early submission. These are flagged per guideline check 3, with no total change.
