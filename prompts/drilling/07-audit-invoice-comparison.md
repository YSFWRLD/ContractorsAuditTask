Continue the project from the current GitHub checkpoint.
Repository:
https://github.com/YSFWRLD/ContractorsAuditTask.git
Current checkpoint:

* Civil Works is frozen and must remain unchanged.
* Drilling Phases 1–4b are complete.
* Canonical Drilling pricing exists under the approved readings.
* AMB-13 is UNKNOWN / UNVERIFIED.
* PD-201, PD-210 and class-dependent services that require missing call-offs are `EVIDENCE_NOT_PROVIDED`, not canonically payable.
* Full suite currently passes.
* Nothing after the pricing phase has been implemented yet for Drilling.

Your task now is:
DRILLING AUDIT / INVOICE-COMPARISON PHASE
Implement the actual Drilling invoice audit on top of the existing ingestion, interpretation and pricing layers.
Do NOT start final combined-submission packaging yet.
Before implementing anything:

1. Pull and inspect the current repository.
2. Read:
   * the upstream task README;
   * `drilling_services/guidelines/INVOICE_AUDIT_GUIDELINES.md`;
   * the Drilling contract model and reviewed artifacts;
   * approved readings;
   * Phase 2 ingestion;
   * Phase 3 interpretation;
   * Phase 4 pricing;
   * all Drilling docs/prompts/tests.
3. Treat the current repository files as the source of truth if any older handoff differs.

Goal
Audit all 1,906 Drilling invoices against the contract and the 12 required checks.
The 12 checks are:

1. invoice belongs to the contract;
2. contract live on work dates;
3. invoice raised inside its allowed window and after the billed period closed;
4. every line has the required supporting record/signature;
5. billed quantities match supported recorded quantities;
6. each line is identified to a priced contractual item;
7. correct rate in force on the work date;
8. adjustments applied in the correct order with correct discount/rounding;
9. contractual limits/caps/exclusions/once-only/minimums hold;
10. nothing billed twice;
11. arithmetic reconciles;
12. outcome records pass/query/part-reject, clause, payable figure and unresolved information.

Do not invent a different checklist.
Very important audit principles
The invoice is a claim, not evidence of entitlement.
Do not use:

* invoice-stated well class;
* invoice service code;
* invoice amount;
* invoice total;
* billed rate;
* billed quantity;

to decide what the contract or report evidence "must have meant".
Those values may be used only after the contract-side evidence has already been established, for comparison.
Preserve the separation:
report evidence
→ interpreted quantity
→ entitlement status
→ contractual price
→ invoice comparison
→ finding
→ invoice result
AMB-13 and missing call-offs
Maintain the existing strict treatment.
`EVIDENCE_NOT_PROVIDED` means the entitlement cannot be established from supplied evidence.
For:

* PD-201;
* PD-210;
* class-rated services;
* any other service whose eligibility genuinely depends on a missing call-off;

do not convert the contractor's invoice claim into canonical evidence.
If an invoice bills such a service:

* compare the claim to the known report evidence where possible;
* preserve the conditional price;
* record that entitlement is unresolved;
* do not pretend a definitive payable amount exists unless the contract-side evidence proves it.

Do not automatically treat "unresolved" as "wrong".
The audit must distinguish:

* proven overcharge / undercharge / duplicate / incorrect rate;
* evidence missing;
* contractual ambiguity;
* correct claim.

Invoice-level checks that now need implementation
At minimum, investigate and implement where supported by the contract:

* contract reference / issuer / period;
* contract term and work-date validity;
* invoice timing/window;
* report reference presence;
* report signature requirements;
* billed quantity vs report-supported quantity;
* service-code / service-description consistency;
* unsupported billed services;
* incorrect rates;
* wrong build-up / factors / index / discount;
* minimum charges;
* once-per-run / once-per-well restrictions;
* operating-day vs Standby exclusions;
* PD-201 / PD-210 eligibility queries;
* well-class entitlement queries;
* duplicate billing:
   * within one invoice;
   * across earlier invoices;
   * repeated report/service/date/run evidence;
* arithmetic:
   * line quantity × rate;
   * line amount;
   * subtotal;
   * invoice total;
* Amendment 3 back-dated adjustment logic;
* DS-900;
* VAT;
* any other invoice-level adjustment explicitly required by the contract.

Do not implement a rule merely because it seems commercially sensible. Every audit rule must trace to contract/guideline evidence.
Corrected totals
Be conservative.
A finding does NOT automatically mean the corrected invoice total is known.
Publish an expected/corrected total only if:

* all components affecting the invoice total are determined;
* no unresolved entitlement or interpretation materially changes that total;
* arithmetic can be reconstructed defensibly.

Otherwise leave the expected total unresolved/blank according to the shared output semantics.
Conditional values may be preserved in audit artifacts for analysis, but must not be presented as canonical payable totals.
Findings
Use the existing shared `Finding` and `InvoiceResult` models.
Each finding should preserve enough information to answer:

* what failed;
* invoice id;
* line/reference;
* report evidence;
* observed billed value;
* expected/contract value where determinable;
* clause/table relied on;
* audit check number;
* monetary impact if determinable;
* whether it changes the invoice total;
* whether it blocks total reconstruction;
* interpretation/evidence dependencies;
* confidence.

Create a consistent Drilling error-category vocabulary.
Do not reuse Civil Works categories blindly if the underlying contractual issue is different.
Confidence
Confidence must describe evidence quality, not how strongly a number differs from the invoice.
Maintain the existing shared confidence bands unless there is a real architectural reason not to.
Examples:

* direct contract/data contradiction with complete evidence → HIGH;
* depends on a defensible unresolved reading → MEDIUM;
* depends on weak/limited evidence → LOW.

An evidence query is not automatically LOW if the fact that evidence is missing is itself certain.
Testing
Add strong targeted Drilling audit tests.
Cover:

* correct invoice;
* incorrect contract reference;
* work outside contract period;
* invalid invoice timing;
* missing report;
* unsigned report;
* billed quantity above evidence;
* unsupported service;
* wrong rate;
* incorrect factor/build-up;
* Standby exclusions;
* minimums;
* once-only rules;
* duplicate within invoice;
* duplicate across invoices;
* arithmetic mismatch;
* Amendment 3 adjustment;
* DS-900;
* VAT;
* AMB-13 unresolved behavior;
* PD-201 unresolved behavior;
* PD-210 unresolved behavior;
* corrected total reconstructable;
* corrected total blocked;
* confidence behavior;
* multiple findings on one invoice;
* category precedence;
* malformed data where relevant.

Prefer small fixtures and focused tests.
Then run the complete project suite with:
`python -m pytest -W error`
Civil Works must remain byte-identical.
Outputs for this phase
Create Drilling draft audit outputs under:
`outputs/drilling/`
These may include:

* `draft_predictions.csv`
* `invoice_audit.csv`
* `findings.jsonl`
* `audit_summary.md`
* `coverage.md`
* `uncertainty_report.md`
* `sensitivity.md`
* `review.md`

Use the Civil Works outputs as a structural reference where helpful, but do not force Drilling into Civil Works-specific logic.
Do NOT create the final combined root `submission.csv` yet.
Review requirements
After implementation, perform an adversarial review.
Specifically inspect:

* invoices with several lines sharing one report;
* same report/service/date appearing across invoices;
* repeated runs/wells;
* split lines;
* exact threshold boundaries;
* date/effective-date boundaries;
* Standby/Operating transitions;
* Amendment 3 boundary dates;
* rounding boundaries;
* zero/negative/unusual values;
* missing fields;
* unresolved AMB-13 invoices;
* invoices whose billed total happens to reconcile despite a line-level error;
* invoices that look unusual but are contractually correct.

Do not tune results to the challenge statement that 5–8% of invoices are wrong.
That percentage may be reported only as a final sanity observation, never used to create or remove findings.
Documentation cleanup
While doing this phase, fix the known README drift:

* Civil Works `pipeline.run()` is implemented, not "deliberately not implemented".
* Drilling now has canonical Phase 4 pricing under approved readings.

Do not make unrelated documentation rewrites.
Final report for this phase
When finished, STOP and report:
DRILLING AUDIT REPORT
STATUS:
COMPLETE / BLOCKED / NEEDS DECISION
IMPLEMENTED:

* audit checks implemented;
* audit modules created;
* outputs created.

FINDINGS:

* number of flagged invoices;
* number of findings;
* counts by category;
* counts by audit check;
* HIGH / MEDIUM / LOW confidence breakdown.

CORRECTED-TOTAL COVERAGE:

* flagged invoices with reconstructable totals;
* flagged invoices with blank/unresolved totals;
* why totals are unresolved.

EVIDENCE-NOT-PROVIDED:

* invoices affected by missing call-offs;
* PD-201;
* PD-210;
* class-rated services;
* how these are represented.

DUPLICATES:

* within-invoice;
* cross-invoice;
* ambiguous repeat evidence.

ADJUSTMENTS:

* Amendment 3;
* DS-900;
* VAT;
* any other invoice-level adjustment.

DATA QUALITY:

* missing reports;
* unsigned reports;
* malformed references;
* other source issues.

SENSITIVITY / INTERPRETATIONS:

* findings or totals materially affected by approved LOW/MEDIUM readings;
* unresolved items needing a decision.

TESTS:

* Drilling test count;
* full project test count;
* `-W error` result.

FILES CHANGED:

* code;
* tests;
* outputs;
* docs;
* prompts.

ARCHITECTURE:

* confirmation shared remains domain-neutral;
* confirmation Civil Works is byte-identical.

README:

* confirmation the two known stale statements were corrected.

GIT:

* do not commit or push yet unless explicitly instructed later.

Do not generate the combined submission.
Do not start the final report/decision-log packaging phase.
Stop and wait for review.
