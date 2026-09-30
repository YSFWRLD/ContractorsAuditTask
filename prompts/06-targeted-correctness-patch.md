Continue from the current repository state at:

https://github.com/YSFWRLD/ContractorsAuditTask

Current HEAD on main:
99b85d2518436ee30805dd41e5a2031b0f88f824

Do NOT push yet.
Do NOT broadly reopen the audit.
Do NOT rewrite architecture.
Do NOT change unrelated ambiguity readings.
Do NOT tune to the stated 5–8% prevalence.

This is a TARGETED CORRECTNESS PATCH based on an independent adversarial review.

The independent review found four issues worth addressing:

1. verified false negatives from mixed incompatible well classes;
2. avoidable Civil Works amount abstention for indexed items;
3. approval incorrectly boosting LOW confidence to MEDIUM;
4. inconsistent treatment of missing submission dates.

The goal is to fix only these, preserve everything else, regenerate, test, and STOP for review.

==================================================
1. DRILLING — WHOLE-WELL CLASS CONSISTENCY
==================================================

This is the highest-priority fix.

Current behavior:

For an AMB-13 class-dependent line, `_price()` accepts the billed rate if that rate matches any possible contractual class for that line.

That is too local.

The contract basis is:

- Clause 4: the call-off states the well class.
- P2 / P3 / Appendix A: the well class governs the whole well and is not revised while drilling.

Therefore all class-rated charges for the same well must be explainable by one common contractual class.

Implement a well-level consistency check.

Required logic:

For every relevant class-rated billed line on a well:

1. derive the set of contractual well classes whose valid contract-side rate could produce the billed rate for that line under the approved pricing readings;
2. do NOT use the invoice's descriptive `well_class` field as evidence;
3. intersect those permissible-class sets across relevant lines for that well;
4. if the intersection is non-empty:
   - do not flag merely because the invoice's descriptive class differs;
   - keep AMB-13 entitlement unresolved;
5. if the intersection is empty:
   - this proves the billed lines cannot all be contractually correct under one well class;
   - raise a flagging finding;
   - do NOT claim which class is actually correct;
   - keep the corrected total blank because the call-off remains missing.

Use a category/rule that clearly describes the actual defect, for example:

`well_class_inconsistent`

or another concise equivalent.

This must be a real flagging category, not merely `entitlement_unverified`.

Known cases from the independent review:

- MDS-00215
- MDS-01445

Do NOT hard-code these IDs.
The logic must find them from the data.

Add tests for:

- mixed Standard / HPHT rates within one well -> flag;
- all class-rated lines compatible with Standard -> no inconsistency flag;
- all compatible with HPHT -> no inconsistency flag;
- invoice descriptive class disagrees, but all billed rates are mutually consistent -> query only, no flag;
- no call-off -> expected total still blank;
- no false use of the descriptive class field.

After implementation, report all invoices newly flagged by this rule.

==================================================
2. CIVIL WORKS — INDEXATION DECISION / AMOUNT COVERAGE
==================================================

Re-review only the existing Civil Works `indexed_rate_method` ambiguity.

Do NOT change Civil detection logic unless the contract review genuinely requires it.

Current situation:

- working reading already applies Clause 29A indexation;
- `indexed_rate_method` is still marked UNRESOLVED / MEDIUM;
- STRICT therefore blanks totals whose only blocker is this switch.

Contract evidence already extracted:

- Schedule 2A says the Schedule 1 rate is a base rate and "is not payable as it stands";
- Clause 29A gives the exact indexed-rate formula;
- Clause 2 makes the relevant Schedule contractual;
- Appendix B is an illustrative form and is not among the Clause 2 listed documents.

Independent review verified PA-00043:

- billed total: 23,145,744 halalas
- supported total: 23,142,526 halalas
- current expected_total_cents: blank
- sole blank reason: indexation interpretation

Task:

Re-assess whether this ambiguity should remain genuinely unresolved.

If, after direct contract review, the operative contractual hierarchy clearly establishes Clause 29A / Schedule 2A as governing:

- change `indexed_rate_method` from UNRESOLVED to TEXT_RESOLVED;
- retain the Appendix B unindexed example as documented contradictory / sensitivity evidence;
- do not remove the sensitivity branch;
- regenerate Civil totals.

Then independently validate every flagged Civil application whose only blank reason was indexation before publishing its expected total.

Do NOT assume all 19 are automatically recoverable.
Validate them through the existing contract-side valuation.

Report:

- how many Civil blank totals were recovered;
- exact application IDs;
- before/after expected totals;
- whether any Civil flags changed;
- whether PA-00043 becomes 23142526.

If you conclude the ambiguity genuinely must remain unresolved, STOP and explain exactly why before changing Civil output.

==================================================
3. DRILLING — CONFIDENCE APPROVAL FLOOR
==================================================

Current code in `audit/dependencies.py` effectively does:

approved pricing reading -> at least MEDIUM confidence

That is not justified merely by approval.

Approval is a workflow decision, not additional evidence.

Change confidence dependency treatment so:

- the original evidential grade of the interpretation is preserved;
- approval does NOT automatically raise LOW to MEDIUM;
- audit-phase readings and pricing readings are treated consistently in this respect;
- confidence still reflects whether a finding disappears under an alternative reading.

Do NOT arbitrarily change the numeric mapping 0.95 / 0.75 / 0.55 in this patch.

Only remove the unsupported approval-based boost.

Recalculate all affected finding and invoice confidence bands.

Report exact changes, especially:

- MDS-00856
- MDS-01338
- MDS-01877

Do not assume those are the only affected cases.

==================================================
4. DRILLING — SUBMISSION-DATE PROXY CONSISTENCY
==================================================

AMB-25 already says:

submission date = EVIDENCE_NOT_PROVIDED

Keep that.

Do NOT restore the six Clause 33 timing flags.

However, audit the code for any place where invoice date is still silently treated as submission date.

Known areas:

- invoice ordering / duplicate ownership;
- Clause 36A adjustment placement;
- pre-/post-issue handling if it truly depends on submission rather than service date;
- any wording that says invoice date "stands for" submission date.

Create a single explicit policy for the proxy.

Required principles:

- invoice date may be used as a deterministic processing/order proxy where the dataset provides no submission timestamp;
- this proxy must not be presented as factual submission evidence;
- any conclusion whose correctness materially depends on actual submission order/date must carry the appropriate AMB-25 uncertainty;
- do not weaken conclusions that depend only on work date or invoice period rather than submission date;
- do not invent missing submission dates.

Specifically review:

- MDS-01625 / AMB-12;
- duplicate ownership across invoices;
- any retroactive adjustment placement.

If duplicate detection only proves the same evidence was billed twice regardless of which invoice came first, preserve the duplicate flag and only avoid overclaiming which invoice was "earlier" if necessary.

Report exactly which conclusions, messages, dependencies or confidence bands changed.

==================================================
5. KEEP AMB-13 STRICT
==================================================

Do NOT change the core AMB-13 policy.

Keep:

- call-offs missing -> EVIDENCE_NOT_PROVIDED;
- invoice `well_class` is not contractual evidence;
- all Drilling expected totals blank unless the entire invoice is independently reconstructable without the missing class/nomination;
- conditional totals remain analysis-only.

The new whole-well consistency flag does NOT establish the true class.
It only proves that the billed lines cannot all be correct under one class.

==================================================
6. DOCUMENTATION UPDATES
==================================================

Update only documentation affected by these real changes:

- REPORT.md
- DECISION_LOG.md
- relevant domain decision logs / audit docs
- generated audit summaries / coverage / uncertainty / sensitivity outputs
- prompts index if this prompt is saved

Correct any stale claim that:

- MDS-00215 and MDS-01445 are justified non-flags;
- approval itself raises evidential confidence;
- invoice date is the actual submission date;
- Civil indexation remains unresolved, if you resolve it.

Keep the report concise.

==================================================
7. TESTING
==================================================

Add targeted regression tests for the verified defects.

At minimum:

### Drilling
- mixed incompatible class rates -> flag;
- consistent class rates -> no flag;
- descriptive invoice class is not evidence;
- missing call-off still blanks total;
- LOW approved reading stays LOW if the finding depends on it;
- submission-date proxy does not create Clause 33 timing findings;
- AMB-12/date-proxy dependency is represented honestly.

### Civil
If indexation becomes TEXT_RESOLVED:
- PA-00043 expected total = 23142526;
- index-only flagged rows publish totals when all other components are determined;
- Appendix B alternative remains in sensitivity;
- no unrelated Civil flag counts change unexpectedly.

Run:

`python -m pytest -W error`

==================================================
8. REGENERATE EVERYTHING AFFECTED
==================================================

Regenerate:

- affected Civil artifacts/outputs if indexation status changes;
- affected Drilling artifacts/outputs;
- root `submission.csv`;
- REPORT.md / DECISION_LOG.md derived counts.

Generate twice and verify deterministic bytes.

Do NOT modify upstream task data.

==================================================
9. ADVERSARIAL CHECK AFTER PATCH
==================================================

Before reporting back, explicitly verify:

- MDS-00215 flag status;
- MDS-01445 flag status;
- their expected totals remain blank;
- all other new well-class inconsistency flags, if any;
- PA-00043 expected total;
- number of Civil blank totals before/after;
- total combined flagged count before/after;
- confidence distribution before/after;
- MDS-01877 confidence;
- MDS-01625 confidence/dependency treatment;
- no conditional amount leaked into submission.

Also verify:

- exact 2,806 submission rows;
- exact template order/schema;
- billed totals unchanged;
- no duplicate/missing IDs.

==================================================
10. DO NOT PUSH
==================================================

Do NOT commit or push.

STOP for review.

==================================================
FINAL RESPONSE FORMAT
==================================================

Return:

# TARGETED CORRECTNESS PATCH REPORT

## STATUS
COMPLETE / BLOCKED / NEEDS DECISION

## WELL-CLASS CONSISTENCY
- implementation;
- newly flagged invoices;
- MDS-00215;
- MDS-01445;
- total treatment;
- tests.

## CIVIL INDEXATION
- final contract interpretation;
- whether status changed to TEXT_RESOLVED;
- PA-00043;
- totals recovered;
- applications affected;
- flags changed or unchanged.

## CONFIDENCE
- approval-floor fix;
- findings/invoices whose band changed;
- before -> after distribution;
- MDS-00856;
- MDS-01338;
- MDS-01877.

## SUBMISSION-DATE POLICY
- exact policy;
- code paths changed;
- AMB-12 / MDS-01625;
- duplicate handling;
- flags changed or unchanged.

## FINAL RESULT COUNTS
- Civil flagged;
- Drilling flagged;
- combined flagged;
- total findings;
- blank expected totals;
- published expected totals.

## SUBMISSION
- 2,806 rows;
- deterministic;
- no conditional totals leaked.

## TESTS
- full count;
- `-W error` result.

## INTEGRITY
- upstream unchanged;
- unrelated audit logic unchanged;
- reproducibility result.

## FILES CHANGED
Exact list.

## GIT
Nothing committed or pushed.

STOP and wait for review.
