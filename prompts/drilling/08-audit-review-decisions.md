Apply the following review decisions to the completed Drilling audit.
Do not begin final combined-submission packaging yet.
1. Audit-phase ambiguity decisions
AMB-12
Approve the current working reading.
Keep the existing sensitivity to:

* "on or after" versus "after";
* contract-wide versus per-well adjustment scope;
* any other implemented alternative.

Do not remove uncertainty/confidence dependencies merely because the working reading is now approved. Preserve the audit trail showing why the reading was chosen.
AMB-14
Approve the current Phase 1 / audit working reading A.
Keep the alternative in sensitivity.
AMB-15
Approve the current Phase 1 / audit working reading A.
Keep the alternative in sensitivity.
AMB-23
Approve the current working reading consistent with the frozen Civil Works evidence policy.
A missing or contractually required unsigned record means the charge is not presently evidenced/payable where the contract makes that record/signature a condition of payment.
Do not invent a different financial consequence beyond what the contract supports.
Keep the alternative reading in sensitivity.
AMB-25
DO NOT approve the current use of invoice date as proof of submission date.
AMB-25 remains:
EVIDENCE_NOT_PROVIDED / submission date unavailable
If the contract requirement is expressed in terms of submission and the dataset supplies only invoice date, invoice date alone cannot prove that an invoice was submitted late.
Therefore:

* remove any timing flag whose sole basis is treating invoice date as submission date;
* retain the timing observation/query in internal audit evidence if useful;
* mark the actual submission-date fact as unavailable;
* do not invent a submission date;
* do not use billing behavior to infer it.

If any timing finding is independently proven by another field or contractual rule, keep it.
Regenerate counts accordingly.
2. AMB-13 corrected totals
Continue the STRICT treatment.
Because the missing call-offs affect at least one monetary component on every Drilling invoice:

* do not publish `expected_total_cents` for any invoice whose corrected total depends on AMB-13;
* keep the field blank/unresolved;
* keep contractor-claimed-class totals only as explicitly CONDITIONAL analysis;
* never promote a conditional total to canonical payable merely because it reconciles the billed total.

The fact that conditional totals equal billed totals on unflagged invoices is useful calibration evidence, but not entitlement evidence.
3. Change AMB-05
Change the approved AMB-05 reading from PER_BHA_RUN to:
PER_DAY_THEN_MINIMUM
Interpretation:
For each applicable hourly service/report day:

1. take the hours supported by that day's report;
2. deduct the one non-chargeable rig-up hour required by Clause 21A;
3. then apply the contractual 6-hour minimum where applicable.

Reason for changing the previous approval:

* Clause 21A directly states that the report states the hours run and the invoice charges one fewer.
* Under PER_BHA_RUN, 3,897 DD-120 lines are billed exactly one hour below the report-supported quantity.
* Under PER_DAY_THEN_MINIMUM, none of the hourly billed lines has that systematic one-hour discrepancy.
* The challenge README explicitly says that if a contract reading reprices invoices that otherwise reconcile exactly as billed, the reading is probably wrong.
* The previous PER_BHA_RUN approval was LOW confidence.

This is a calibration correction supported by both the contract text and a systematic reconciliation signal. It is not permission to tune other readings merely to match invoices.
Requirements:

* record the previous reading and why it was superseded;
* preserve PER_BHA_RUN, NO_DEDUCTION and MINIMUM_THEN_DEDUCT as sensitivity alternatives;
* regenerate canonical pricing affected by AMB-05;
* rerun the entire Drilling audit;
* recalculate findings, totals, dependencies and confidence;
* report exactly what changed because of this reading.

Do not alter unrelated approved readings merely because an alternative matches billing better.
4. `well_class_inconsistent`
Keep these findings.
If the invoice explicitly claims one well class but its billed rate corresponds to another valid class:

* flag the invoice as `well_class_inconsistent`;
* classify it as a query/documentary-pricing inconsistency;
* keep confidence MEDIUM;
* do not claim which class is actually correct;
* do not publish a corrected monetary total because the call-off is missing;
* preserve both:
   * the invoice's stated class;
   * the classes/rates the billed value is consistent with.

The finding means:
"the invoice's own stated pricing basis is internally inconsistent"
not:
"we know the true well class."
If further inspection shows the class field is not contractually part of the billing basis or is merely descriptive with no required consistency, STOP and report that before removing these findings.
After applying the decisions
Regenerate:

* canonical Phase 4 pricing if AMB-05 affects it;
* Drilling audit outputs;
* sensitivity/dependency reports;
* review artifacts.

Run:
`python -m pytest -W error`
Then perform the same adversarial review again.
Verify:

* Civil Works 16 artifacts are byte-identical;
* Civil Works 8 outputs are byte-identical;
* shared architecture remains unchanged unless genuinely required;
* upstream task data is untouched;
* no combined `submission.csv` exists.

Report back
Return:
DRILLING AUDIT FREEZE REVIEW
RESULT CHANGES

* flagged invoices before → after;
* findings before → after;
* category changes;
* confidence changes.

AMB-05 IMPACT

* lines repriced;
* invoices affected;
* findings added/removed;
* dollar impact;
* whether the 3,897 systematic one-hour discrepancies disappear;
* remaining DD-120/RM-530 mismatches after the new reading.

AMB-25 IMPACT

* which timing flags were removed or retained;
* why.

AMB-12/14/15/23

* approved reading;
* confidence;
* sensitivity under each alternative.

AMB-13

* confirmation no conditional total became canonical;
* number of blank corrected totals.

WELL CLASS

* confirmation the two inconsistent invoices remain queries unless contract review disproves that treatment.

FINAL DRILLING AUDIT COUNTS

* invoices audited;
* flagged invoices;
* findings;
* categories;
* HIGH/MEDIUM/LOW;
* reconstructable corrected totals;
* unresolved corrected totals.

TESTS

* Drilling count;
* full project count;
* `-W error` result.

INTEGRITY

* Civil Works unchanged;
* upstream source unchanged;
* artifacts reproducible.

GIT

* nothing committed or pushed.

STOP after this review.
Do not generate the combined submission.
Do not begin final packaging.
