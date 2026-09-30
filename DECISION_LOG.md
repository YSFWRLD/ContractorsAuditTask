# Decision log

These are the decisions that shape `submission.csv`. Readings are grounded in the contract text. Where competing readings remained, invoice reconciliation was used only as the calibration check described in the task README; billed values were never used to derive contractual terms. Each alternative's effect is measured in the domains' `sensitivity.md`.

Full history:
- civil works: `docs/civil_works/decision_log.md`;
- drilling: `artifacts/drilling/approved_readings.json`, `artifacts/drilling/contract_ambiguities.md`, `docs/drilling/phase5_audit.md`.

## Both domains

| Decision | Basis | Status | Effect |
|---|---|---|---|
| Corrected total published only if fully determined (STRICT); else blank, never 0 | guideline 3: unpriceable is a query | policy | CW 40 blank; drilling all 1,906 blank |
| A breach with no contractual price flags the invoice but leaves its total | contract states no consequence | policy, MEDIUM cap | 3 CW timing flags |
| Contract governs over the guidelines | README; drilling PR-09 | stated | e.g. drilling 36A placement |

## Civil works (frozen)

| Decision | Basis | Status | Effect |
|---|---|---|---|
| Indexed rates follow Clause 29A, not Appendix B's example | Clause 2 includes Schedule 2A | MEDIUM | 22 totals blank; the alternative flags 215 more |
| A monthly rate is a base rate in the build-up | S1 1.2, S2 2.1 | MEDIUM | 4 totals blank |
| A later discount replaces an earlier; rebate bands restart each Contract Year | instruments' closing words; Sch 4 Pt 3 | accepted | settles discount and rebate findings |
| A missing record is not payable now; an unsigned record is invalid | Clauses 46, 47, P22 | MEDIUM | 8 totals blank |
| 31A adjustment on the first application on or after issue | 31A wording (A3 says "after") | LOW | PA-00006 |

## Drilling (frozen)

| Decision | Basis | Status | Effect |
|---|---|---|---|
| AMB-13: call-offs missing, so class and nominated sections are `EVIDENCE_NOT_PROVIDED` | P2, P3, cl. 23; no call-offs in the data | approved | 29,160 non-flagging queries; all totals blank |
| The invoice's `well_class` is descriptive, not evidence | cl. 34 and the Appendix B form have no class | approved | MDS-00215 and MDS-01445 are queries, not flags |
| AMB-05: rig-up hour deducted per day, then the 6-hour minimum | 21A: "the invoice charges one fewer" | approved (replaced per-run) | 0 lines below the record; +1 flag |
| AMB-25: submission date `EVIDENCE_NOT_PROVIDED` | only an invoice date in the data | approved | 6 timing flags removed (kept as observations) |
| AMB-12: one 36A adjustment, first invoice on or after issue | 36A wording | approved, LOW | MDS-01625 flagged |
| AMB-14 / AMB-15: DDR signatures cover Parts B-E; rig words valid | Schedule 5; 19A, Appendix G | approved, MEDIUM | alternatives would flag 1,508 / 1,792 |
| AMB-23: missing record, part or signature means not presently payable | cl. 37; civil works policy | approved, MEDIUM | 44 record findings not payable |
| Pricing and quantity readings (AMB-01–04, 06–08, 10, 11, 17–22, 24, 26) | contract text | approved | alternatives would flag up to 1,724 |
