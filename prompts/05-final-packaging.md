Continue from the frozen checkpoint at:
`2d2e8cfbe5e51fad3901443d1e99b9f3f940dc25`
Repository:
https://github.com/YSFWRLD/ContractorsAuditTask.git
This is the FINAL PACKAGING PHASE.
Do not change audit logic unless you discover an actual correctness defect.
Current frozen state:

* Civil Works audited: 900 applications.
* Drilling audited: 1,906 invoices.
* Total required submission population: 2,806.
* Civil Works is frozen.
* Drilling is frozen.
* Drilling final state:
   * 114 flagged invoices;
   * 152 flagging findings;
   * 29,160 AMB-13 queries;
   * all Drilling corrected totals blank because entitlement cannot be fully established from the missing call-offs.
* AMB-05 = `PER_DAY_THEN_MINIMUM`.
* AMB-12, 14, 15, 23 approved at the reviewed readings.
* AMB-25 = `EVIDENCE_NOT_PROVIDED`.
* No conditional amount may be promoted to canonical/payable.
* Full suite baseline: 556 passed with `-W error`.

Goal
Produce the final challenge deliverables exactly as required by the upstream task:

1. runnable repository;
2. root `submission.csv`;
3. short final report;
4. versioned prompts;
5. one-page decision log.

Do not alter the frozen audit results merely to improve the final numbers.
1. Combined submission.csv
Create the final root:
`submission.csv`
Start from the upstream:
`invoice-auditing-level-2/submission_template.csv`
Do NOT construct row order from scratch.
For every template row:

* preserve `invoice_id` exactly;
* fill from the appropriate frozen domain `InvoiceResult`;
* use:
   * `flagged`
   * `error_category`
   * `expected_total_cents`
   * `billed_total_cents`
   * `confidence`

Required validations:

* exactly 2,806 data rows;
* exactly 900 `PA-*`;
* exactly 1,906 `MDS-*`;
* no duplicate IDs;
* no missing template IDs;
* no extra IDs;
* exact template order;
* exact column order:
`invoice_id,flagged,error_category,expected_total_cents,billed_total_cents,confidence`
* `flagged` must be 0/1;
* unflagged rows must have blank `error_category`;
* flagged rows must have nonblank `error_category`;
* money values must be integer minor units;
* confidence must be in [0,1];
* blank expected totals must remain blank, not 0;
* never replace an unresolved Drilling expected total with its conditional amount.

For unflagged Civil Works rows, preserve the existing frozen domain behavior.
For Drilling, do not invent corrected totals. The frozen audit has all 1,906 expected totals blank.
Add automated tests for all of the above.
2. Final report
Create a concise root-level final report, preferably:
`REPORT.md`
It should be SHORT and readable.
Do not dump every individual finding.
Include:
Approach
Explain briefly:

* contract extraction from scanned PDFs;
* deterministic typed ingestion;
* evidence-first mapping;
* interpretation switches;
* contract-side pricing before invoice comparison;
* audit against the 12 checks;
* uncertainty/confidence handling.

Coverage / Results
Report frozen results for both domains.
Civil Works:

* use the frozen Civil Works counts from its outputs/decision log.

Drilling:

* 1,906 invoices;
* 114 flagged;
* 152 findings;
* confidence distribution;
* corrected-total limitation from AMB-13.

Combined:

* 2,806 total invoices;
* total flagged count;
* total unflagged count.

Do not claim precision/recall because no labels are provided.
Error analysis by failure type
The challenge asks for 3–4 systematic failure types.
Group the implementation's limitations/errors into approximately 4 categories, for example:

1. missing contractual evidence / call-offs;
2. contradictory or ambiguous contract provisions;
3. free-text report-to-service interpretation;
4. invoice-level timing/adjustment/duplicate edge cases.

For each:

* explain the systematic issue;
* give one concrete example from the project;
* explain mitigation.

Do not fabricate "misses" against a hidden answer key.
Confidence and unresolved amounts
Explain:

* confidence reflects evidence quality, not statistical probability;
* why some corrected totals are blank;
* conditional totals are analysis-only.

AI assistance
Briefly disclose that AI assistance was used and direct the reviewer to `prompts/`.
3. One-page combined decision log
Create:
`DECISION_LOG.md`
Keep it genuinely concise.
Do NOT copy the massive Civil Works decision log.
Summarize only the major decisions that materially affect the final submission.
Include two compact sections:
Civil Works
Major accepted/open interpretations affecting flags/totals.
Drilling
Major decisions, especially:

* AMB-05 per-day deduction;
* AMB-13 missing call-offs → EVIDENCE_NOT_PROVIDED;
* AMB-25 missing submission dates;
* AMB-12/14/15/23;
* well-class descriptive field not evidence.

For each decision:

* decision;
* basis;
* confidence/status;
* effect on final result.

Link to detailed domain decision/sensitivity artifacts for full history.
Aim for roughly one rendered page, not a giant document.
4. Fix known documentation drift
Fix the stale generated Drilling summary sentence.
`outputs/drilling/audit_summary.md` currently says the five audit-phase switches are "WORKING readings ... not approved".
That is stale.
Update the generator so regenerated output says, in substance:
"The audit-phase readings were selected from the contract text and subsequently approved in the Phase 5 review. Their original confidence grades and alternative sensitivities are retained."
Regenerate the affected Drilling output.
Do NOT manually edit generated output without fixing its writer.
5. Dependency pinning / reproducibility
The challenge asks to pin dependencies.
Review `pyproject.toml`.
`pytest` is already pinned.
The current build requirement uses `setuptools>=69`.
Make the build/dependency setup reproducible enough to satisfy "Pin your dependencies".
Prefer the smallest clean change.
Do not introduce unnecessary tooling.
Then verify:

* fresh virtual environment;
* install from repo instructions;
* run source checks;
* run artifact generation;
* run both audits;
* generate final submission;
* run tests.

If exact build-backend pinning creates compatibility problems, document the reason rather than forcing a brittle setup.
6. Final CLI / reproducibility
Add a clean final command for generating the combined submission.
For example:
`python -m contractor_audit submission`
or a similarly clear command.
It should:

1. use frozen domain audit results;
2. validate against the upstream template;
3. write root `submission.csv`;
4. fail loudly on:
   * missing IDs;
   * duplicate IDs;
   * extra IDs;
   * bad schema;
   * invalid amounts;
   * invalid confidence;
   * missing domain results.

Do not silently repair malformed results.
Update README with exact end-to-end reproduction commands.
7. Final validation
Perform a final adversarial packaging review.
Check:

* final submission has 2,806 rows;
* exact template order;
* Civil Works rows unchanged from frozen draft predictions;
* Drilling rows unchanged from frozen draft predictions;
* no conditional Drilling total leaked into expected_total_cents;
* all flagged rows have categories;
* all unflagged rows have blank category;
* billed totals exactly match task source;
* confidence values match frozen domain outputs;
* no NaN/None/string corruption;
* CSV line endings/encoding stable;
* repeated generation is byte-identical.

Run:
`python -m pytest -W error`
Also regenerate final deliverables twice and compare bytes.
8. Do NOT
Do NOT:

* reopen audit logic;
* tune to the challenge's stated 5–8% prevalence;
* change contract readings without a discovered correctness defect;
* promote conditional totals;
* rewrite Civil Works;
* modify upstream task data;
* remove detailed internal artifacts;
* squash history;
* commit/push yet.

Final report back
When finished, STOP and return:
FINAL PACKAGING REPORT
STATUS
COMPLETE / BLOCKED / NEEDS DECISION
SUBMISSION

* row count;
* Civil Works rows;
* Drilling rows;
* flagged total;
* unflagged total;
* blank expected totals;
* schema/order validation;
* byte-deterministic confirmation.

FINAL REPORT

* file created;
* sections included.

DECISION LOG

* file created;
* approximate length;
* links/references to detailed domain logs.

DOCUMENTATION FIX

* stale Drilling summary wording fixed at generator level.

REPRODUCIBILITY

* fresh install result;
* end-to-end commands tested;
* dependency pinning changes.

TESTS

* final full-suite count;
* `-W error` result.

INTEGRITY

* Civil Works frozen results unchanged;
* Drilling frozen results unchanged;
* upstream task data unchanged;
* no conditional amount promoted.

FILES CHANGED

* code;
* tests;
* README;
* submission;
* final report;
* decision log;
* generated output.

GIT
Nothing committed or pushed.
STOP and wait for review.
