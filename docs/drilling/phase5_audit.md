# Drilling Phase 5: invoice audit

Phase 5 audits the 1,906 `MDS-*` invoices (91,244 lines) against DDS-2025-118 and the twelve guideline checks.

It writes draft outputs to `outputs/drilling/`. It does not write the combined `submission.csv`.

## The order of the evidence

```
report evidence -> interpreted quantity -> entitlement status -> contractual price    (built first: audit/bundle.py)
               -> invoice comparison -> finding -> invoice result                     (audit/lines.py, invoices.py, results.py)
```

Contract-side prices are built from the reports and the contract before any invoice is read. The invoice is a claim.

Its well class, service code, quantity, rate and amounts are read only to compare with a contract-side figure that is already established. The invoice's claimed class selects which conditional price to compare with; it never becomes evidence.

A billed service code selects which report quantity to compare with. A line whose code the report does not evidence is `unsupported_service`, and nothing is re-identified on price.

## The checks

| check | what | where | clauses |
|---|---|---|---|
| 1 | contract reference; issuer; every charge on the invoice's own well | `invoices.py`, `lines.py` | Form of Agreement, 32 |
| 2 | service date inside the term as extended | `lines.py` | 5, A1 1.1, A2 2.1 |
| 3 | invoice dated on or after its period end and within 30 days; every charge inside the period | `invoices.py`, `lines.py` | 32, 33 |
| 4 | the quoted report exists, is for the same well and day, is signed by both signatories, and has the Schedule 5 part the service needs | `lines.py` | 15, 19A, 37, Schedule 5 |
| 5 | billed quantity against the chargeable quantity (21A rig-up, 6-hour minimum, 25A 1% metre tolerance) | `lines.py` | 21, 21A, 22-25, 25A, 30 |
| 6 | code in Schedule 1; Schedule 1 unit and description; the report evidences the item | `lines.py` | 19A, 22, 28, 34, 35, Appendix G |
| 7 | the rate in force on the work date; Clause 36A decides which side of Amendment No. 3 applies | `lines.py`, `diagnosis.py` | Schedule of Variations, 36A |
| 8 | build-up factors, index, standby percentage, discount; lost-in-hole value; the 36A adjustment | `diagnosis.py`, `engine.py` | 17A, 18, 20, S2/A2, 31, 31A, 36A |
| 9 | Standby exclusions, PD-210 hole sizes, daily limits, once-per-well / once-per-run items | `lines.py` | 20, 21, 22, 23, 26, 27 |
| 10 | report evidence already charged on this or an earlier invoice (a ledger in invoice-date processing order, a proxy (AMB-25); PD-210 by depth interval) | `lines.py` | 29 |
| 11 | quantity x rate; net = sum of charges; VAT 15% half-even; total = net + VAT; DS-900 | `invoices.py`, `lines.py` | 17, 36, 38, 39, 40 |
| 12 | outcome, clause, payable figure, what is undetermined | `results.py`, `reporting/audit_outputs.py` | guideline 12 |

A billed rate that differs from the contract rate is diagnosed (`diagnosis.py`). The diagnosis looks for the one build-up component that, changed, reproduces the billed rate: another rate statement, a factor dropped or added, another index month, another depth band. Pairs of changes are tried after single ones.

The diagnosis only names the category. The contract rate never changes.

## AMB-13: the call-offs are not in the data

The strict treatment approved in Phase 4b is kept. Three kinds of charge need the call-off:
- the class-rated services (DD-120, MW-310, MW-320, LW-410 to LW-413);
- PD-210;
- PD-201.

For these charges:

- The line is `CONDITIONAL`. Its quantity, record, duplicates and arithmetic are checked in full. Those checks do not need the class.
- Its rate is compared with the price each possible class would give (`bundle.by_class`). The comparison then goes one of three ways:
  - **Matches the claimed class:** an `entitlement_unverified` query. It never flags; it blocks a canonical total.
  - **Matches only another class:** also only an `entitlement_unverified` query (rule `entitlement.descriptive_class_differs`). The invoice's well class is descriptive, so it proves nothing either way (see below).
- Across a whole well, the classes each class-rated line's billed rate admits must have one class in common, because the call-off fixes one class for the whole well (cl. 4, P2, P3). If they do not, the invoice is flagged `well_class_inconsistent` (see below).
  - **Matches no class:** a rate finding. The billed figure is wrong whatever the call-off says.
- The conditional amount (claimed class, nomination assumed) is kept in `invoice_audit.csv` for analysis. It is never presented as payable.

Every invoice charges MW-310, which is on every report. So every invoice has at least one conditional charge, and no drilling total is fully determined.

For every unflagged invoice, the conditional total equals the billed total exactly: 1,785 of 1,785. This is a strong internal consistency check.

## Readings

- **Pricing and quantity readings:** as approved (`artifacts/drilling/approved_readings.json`), or resolved by the contract text.
- **The five audit-phase switches:** run first at working readings chosen from the contract text (`audit/policy.py`), then decided by the user (`prompts/drilling/08-audit-review-decisions.md`). The grade is kept after approval: an approval records the decision, it does not remove the uncertainty the text leaves.

| switch | ambiguity | reading | status | grade |
|---|---|---|---|---|
| `backdated_adjustment` | AMB-12 | one adjustment, on the first invoice submitted on or after 2026-08-17 (36A wording) | approved | LOW |
| `record_signatories` | AMB-14 | the DDR's two signatures cover Parts B-E (Schedule 5) | approved | MEDIUM |
| `missing_record_consequence` | AMB-23 | where the contract makes a record or signature a condition of payment and it is missing, the charge is not presently payable (cl. 37; the frozen civil works policy) | approved | MEDIUM |
| `submission_date` | AMB-25 | the submission date is not in the data; the invoice date does not prove it | decided: EVIDENCE_NOT_PROVIDED | MEDIUM |
| `report_vocabulary` | AMB-15 | rig words are the contractual form (19A, Appendix G) | approved | MEDIUM |

**AMB-25 in practice.** No Clause 33 timing finding is raised from the invoice date. The six invoices dated before their period ended, or more than 30 days after it, are recorded as observations: `invoice_audit.csv` column `observations`, and `uncertainty_report.md`. Line dates outside an invoice's own stated period (cl. 32) are not submission facts, and they are still findings.

**The submission-date proxy** (`policy.SUBMISSION_PROXY`, targeted correctness patch). The invoice date is used for one thing only: a deterministic processing order, with ties broken by invoice number. It is never presented as the submission date. Three conclusions depend on the actual submission order, and each carries an explicit AMB-25 dependency (MEDIUM):
- **Cross-invoice duplicates:** the evidence is charged twice whichever invoice came first. Which invoice carries the repeat depends on the order. MDS-01352-007's duplicate finding is MEDIUM; the invoice stays HIGH through its independent record finding. Within-invoice duplicates carry no dependency.
- **The Clause 36A adjustment placement:** MDS-01625 is LOW, through both AMB-12 and AMB-25. No invoice carries any adjustment, so it is missing wherever it belongs.
- **A rate judged only by which side of Amendment No. 3's issue date the invoice falls** (rule `rates.backdated_timing`): none occurs in the data.

Conclusions that rest on work dates or on the invoice's own period (term, cl. 32) are unaffected.

**AMB-05 changed (audit review).** The reading is now PER_DAY_THEN_MINIMUM: for each hourly service and report day, the hours the report supports, less the one rig-up hour of Clause 21A, then the 6-hour minimum. It supersedes PER_BHA_RUN, which is kept with the reason in `approved_readings.json` (`superseded`). PER_BHA_RUN, NO_DEDUCTION and MINIMUM_THEN_PER_DAY stay in sensitivity.

`audit/dependencies.py` re-runs the audit once for each alternative of each approved reading and each working reading. Only the services the reading can affect are repriced.

The measured effects are in `outputs/drilling/sensitivity.md`. They set the confidence of each finding and invoice, and they decide whether a total may be published.

## Corrected totals and confidence

**Corrected totals (STRICT).** A corrected total is published only when every line is valued from the contract and the reports, and no working (unapproved) reading changes it. Otherwise it is blank, with its reasons (`blank_reasons`).

**Confidence** is evidence quality. It uses the shared bands (HIGH 0.95, MEDIUM 0.75, LOW 0.55):

| what | band |
|---|---|
| a finding | its rule's band, lowered to the band of each reading without which it disappears |
| a flagged invoice | the strongest band among its findings, and no stronger than any reading that would clear it |
| an unflagged invoice | HIGH, lowered by each reading that would flag it; MEDIUM whenever a charge rests on the missing call-off |

Adjustments to those bands:
- **Approval:** a workflow decision, not evidence. A reading keeps its evidential grade, approved or not, for pricing and audit-phase readings alike. (Before the targeted correctness patch, approved pricing readings were floored at MEDIUM. Removing the floor moved MDS-00856, MDS-01338 and MDS-01877 to LOW through AMB-05. It also briefly moved 554 unflagged invoices to LOW through AMB-10, whose LOW rested on a feasibility observation rather than the text. AMB-10 was then re-graded MEDIUM on the text: the operative Schedule 2 Part 2 sentence says "on the well", and the history is kept in `phase4_recommendations.json`. Those invoices are back at MEDIUM. AMB-05 stays LOW as the grade of its current per-day reading.)
- **Superseded finding:** a finding that disappears only because the alternative rejects the same line for another reason does not lower confidence.
- **Timing findings:** capped at MEDIUM, because the contract prices nothing off them.

## What is not a finding

**A claim below what the record supports.** The guidelines state a consequence only for billing above the record (check 5), and the Company never pays more than is claimed. These claims are counted in `coverage.md` and `sensitivity.md`.

Under the superseded AMB-05 reading (PER_BHA_RUN), 3,897 DD-120 lines were billed exactly one hour below the record. Under the approved PER_DAY_THEN_MINIMUM, no line of any service is billed below the record.

## The well class described on the invoice

Contract review:
- Clause 34 lists what each charge states: date, code, description, hole section, day status, quantity, unit, rate, amount, and depths for PD-210.
- The Appendix B form of invoice has the columns Date, Code, Section, Status, Depths, Qty, Rate and Amount.
- Neither contains a well class. The class is the one the call-off states (P2, P3), and the call-offs are not in the data.

The invoice header's `well_class` is therefore a descriptive field, not part of the contractual billing basis. It cannot stand in for the call-off in either direction. A line billed at the rate of a class other than the described one is only a non-flagging AMB-13 query (rule `entitlement.descriptive_class_differs`). The query records the described class, the billed rate and the class it matches, and every contract class's rate.

**Whole-well class consistency** (`engine.well_class_consistency`, targeted correctness patch). The call-off fixes one class for the whole well (cl. 4, P2, P3), whatever that class is. For each class-rated line, the audit records the classes whose contract rate equals the billed rate (`permissible_classes`), and intersects these sets:
- **Across one invoice's lines:** an empty intersection proves the invoice wrong (`class.inconsistent_within_invoice`).
- **Across the consistent invoices of one well:** an empty intersection proves at least one of them wrong. Each disagreeing invoice is flagged (`class.inconsistent_across_invoices`, MEDIUM).

Lines whose rate every class gives alike, or no class gives (already a rate finding), do not take part. The descriptive class is not used. The finding does not say which class is right, and the total stays blank because the call-off is missing.

From the data, it flags exactly MDS-00215 and MDS-01445. Each bills one line at the HPHT rate among lines only Standard explains. Their other invoices on the same wells are consistent. Both findings are MEDIUM: they depend on how LWD metres are read (AMB-17, AMB-24). The first review had flagged these two lines from the descriptive class; the final freeze had removed that; this check restores the flag on a basis that does not use the descriptive class.

The conditional amount of every conditional line is taken at the described class. It is analysis only, never payable.

## Changes outside `audit/`

- **`pricing/models.py`:** `PricedQuantity.rate_without_retroactive_cents`, the per-unit rate at the rates known before Amendment No. 3. Clause 36A needs it. It is not part of any Phase 4 artifact.
- **`pricing/affected.py`:** `affected_services` moved here from `reporting/phase4_sensitivity.py`, so the audit layer can use it. Behaviour is unchanged.
- **`contract/models.py`, `contract/loader.py`:** `ContractTerms.contractor` and `ContractTerms.clauses` (billing and chargeability rule texts, for citations), loaded from the reviewed JSON.
- **Tests:** a one-line change to the frozen civil works test `test_no_combined_submission`, approved by the user. It still forbids any combined or drilling submission file, and now allows the `outputs/drilling/` drafts.
