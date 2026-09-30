# Phase 4 — Civil Works finalization (freeze before Drilling)

Tool: Claude Code (Claude Opus 5.5). Date: 2026-09-29. Given verbatim below.

---

You are continuing work in the local folder:

ContractorsAuditTask/

Phase 1, Phase 2 and Phase 3 for Civil Works are complete.

This phase is ONLY to finalize Civil Works before we move on to Drilling.

Do not build Drilling.
Do not create the combined submission yet.
Do not commit.
Do not push.
Do not create a GitHub repository yet.

==================================================
CURRENT CIVIL WORKS STATE
==================================================

Current results:

- 900 applications
- 7,746 lines
- 77 flagged applications
- 96 findings
- 37 corrected totals currently published
- 40 flagged applications with blank corrected totals
- all 900 applications have confidence
- 316 tests pass

Current flagged confidence:

- HIGH: 69
- MEDIUM: 6
- LOW: 2

Current main uncertainties:

1. indexed-rate method
2. monthly-rate treatment
3. duplicate ordering
4. backdated-adjustment trigger
5. unsigned-record consequence
6. exclusion-window interpretation
7. missing-record consequence
8. daily-cap consequence

Phase 3 already implemented sensitivity switches for these readings.

==================================================
DECISIONS FOR THIS PHASE
==================================================

Use these working decisions unless the source task/contract clearly contradicts them.

--------------------------------------------------
A. CORRECTED TOTAL POLICY
--------------------------------------------------

KEEP THE STRICT POLICY.

Publish a corrected application total only when the total can be established without relying on an unresolved interpretation that materially changes the value.

If a plausible alternative contract reading changes the expected total:

expected_total = blank

Do not choose a convenient reading merely to maximize coverage.

The task values uncertainty over confidently wrong answers.

The existing "looser 75 totals" sensitivity result may remain documented for analysis, but it must NOT become the production/default output.

--------------------------------------------------
B. TIMING-ONLY BREACHES
--------------------------------------------------

Keep an application flagged when it clearly violates an explicit contractual/application timing requirement even if the clause does not prescribe a monetary adjustment.

Example:

application_timing

The corrected monetary total may remain unchanged.

Important distinction:

contractual non-compliance != necessarily monetary repricing

Document this explicitly.

Do not invent a financial consequence.

--------------------------------------------------
C. PRIMARY CATEGORY
--------------------------------------------------

Review the current primary-category selection.

Do NOT blindly keep the current heuristic just because it exists.

The primary category should be deterministic and reviewer-friendly.

Use this priority concept:

1. explicit, high-confidence contractual violation
2. finding that directly explains a wrong billed total
3. finding with a determinable monetary effect
4. structural/data integrity issue
5. timing/documentation-only issue

When two findings have the same practical importance, use a fixed deterministic category order.

Do not let "largest monetary amount" alone decide the primary category.

Preserve all findings internally even if only one primary category appears in the prediction row.

Document the exact precedence.

==================================================
1. RE-READ THE SOURCE MATERIAL
==================================================

Before changing code, re-read:

- the Civil Works task instructions
- the Civil Works contract
- appendices
- amendments
- submission schema
- evaluation guidance

Do not rely only on our decision logs.

Create a concise checklist of every requested Civil Works check.

Map each requested check to:

- implementation rule
- finding category
- clause/source citation
- test
- output coverage

If any requested check is missing, stop and report it before making unrelated changes.

==================================================
2. ADVERSARIAL REVIEW OF THE 77 FLAGS
==================================================

Review every flagged application programmatically.

For every finding ask:

- What exact source text makes this wrong?
- Is the evidence present in the application data?
- Does the rule rely on an unresolved interpretation?
- Would another plausible reading make the finding disappear?
- Is the finding monetary or non-monetary?
- Is the stated confidence justified?
- Does another finding already explain the same defect?

Look specifically for:

- double counting
- one defect reported under two categories
- variants of the same rule creating duplicate findings
- a downstream arithmetic finding caused entirely by an upstream rate error
- findings produced only because our chosen interpretation was treated as fact

Do not suppress genuinely independent findings.

==================================================
3. REVIEW THE 823 UNFLAGGED APPLICATIONS
==================================================

Do not only test the flagged population.

Use the sensitivity framework to review unflagged applications that become flagged under another interpretation.

Current known figure:

250 unflagged applications are MEDIUM because an alternative would flag them.

Break these down again by dependency.

Confirm that remaining unflagged HIGH-confidence applications truly have no known alternative reading that would make them erroneous.

If an unflagged application's status depends materially on an unresolved interpretation, it must not be HIGH confidence.

==================================================
4. INDEXATION REVIEW
==================================================

This is currently the largest source of uncertainty.

Current alternative:

Appendix B indexation would flag approximately 215 currently unflagged applications.

Re-read the exact indexation language and surrounding clauses.

Determine:

- whether indexation is automatic
- whether an external index/reference value is required
- whether that value exists in the supplied task data
- whether the contract gives enough information to compute it
- effective date
- whether it compounds
- whether it changes unit rates or something else

Do NOT look anything up externally unless the task explicitly permits it.

Everything needed should come from the supplied package.

If the required index value is absent, preserve the uncertainty.

Do not infer the index from billed prices.

Report whether the current production reading remains justified.

==================================================
5. MONTHLY RATE REVIEW
==================================================

Re-read the monthly-rate wording.

Current alternative affects approximately 33 applications.

Determine whether:

- monthly rate is itself the payable rate
- monthly rate is an intermediate/base figure
- daily/prorated treatment is required
- quantities or periods determine the payable amount

Build explicit boundary tests.

Do not use billed amounts to choose the interpretation.

==================================================
6. DUPLICATE REVIEW
==================================================

Current ambiguity:

Clause 44 refers to the "later measurement".

Production reading currently uses submission chronology.

Alternative uses higher application number.

Review all duplicate groups.

For each group report:

- application IDs/numbers
- relevant dates
- measurement identifiers if available
- which record is "later" under each interpretation
- whether the flag changes
- whether corrected total changes

Do not silently resolve the ambiguity unless the contract/data establishes an ordering.

If still ambiguous, keep it as a measured dependency.

==================================================
7. EXCLUSION WINDOW REVIEW
==================================================

Current production reading has an exclusion-window interpretation that changes one flag.

Review:

PA-00801

and every other exclusion pair.

Check:

- directionality
- whether "within N days" includes both before and after
- whether day N is inclusive
- same-day behavior
- whether the excluded item or trigger loses payment

Create explicit tests for:

0
+N
-N
+(N+1)
-(N+1)

If the wording remains ambiguous, keep the dependency explicit.

==================================================
8. BACKDATED ADJUSTMENT REVIEW
==================================================

Review PA-00006 and all backdated-adjustment cases.

Current issue:

whether the trigger applies "after" an event versus another reading.

Determine from the contract:

- trigger event
- effective date
- whether adjustment is retrospective
- whether it changes the application total
- whether it is a separate adjustment field instead

Preserve the existing rule that adjustment columns outside `application_total` are not silently folded into the expected application total unless the task schema requires it.

==================================================
9. RETENTION / SEPARATE ADJUSTMENTS
==================================================

Re-check:

PA-00678

and any other retention/release findings.

Verify:

- whether retention belongs inside application_total
- whether it is reported separately
- whether omission is still an error even when expected application_total remains unchanged

The output must distinguish:

"this application has a contractual error"

from:

"the application_total itself should be a different number."

==================================================
10. QUANTITY / CAP CONSEQUENCES
==================================================

For each quantity/cap rule distinguish:

A. contract explicitly defines payable quantity after breach

versus

B. contract merely defines a limit but does not establish the corrected payable quantity

If A:
corrected total may be reconstructed.

If B:
flag the breach but leave corrected total blank.

Do not import semantics from another contract/domain.

==================================================
11. SPLIT-LINE / BAND BOUNDARY REVIEW
==================================================

Phase 3 discovered that lines spanning a rebate-band edge may legitimately have no single contract unit rate.

Verify the correction thoroughly.

For every split line:

- recompute band segmentation
- recompute each segment
- recompute total
- verify the contractor's displayed/pre-rebate rate is not incorrectly flagged
- judge amount independently

Create regression tests around exact band boundaries.

==================================================
12. CHECK ALL 24 CATEGORIES
==================================================

Produce a final matrix:

category
requested guideline check
contract clause
implemented rule
test
number of findings
whether finding can affect total
known interpretation dependency

Confirm the 3 zero-occurrence categories are genuinely implemented and tested:

- work_outside_contract_period
- adjustment_incorrectly_applied
- retention_incorrect

Also confirm:

service_not_contracted_on_date

if it exists as a valid Civil Works category/rule.

Do not remove a valid rule merely because the dataset has zero cases.

==================================================
13. CORRECTED TOTAL REVIEW
==================================================

For all currently published corrected totals:

independently reconstruct them from accepted contract rules.

No corrected total may rely on:

- unresolved identity
- unresolved interpretation
- unknown record consequence
- guessed external data
- billed amount as contract evidence
- inferred rates from neighboring applications

Produce:

published totals
blank totals

and a mutually exclusive blank-reason breakdown.

Confirm:

published + blank = number of flagged applications

unless the task requires expected totals for unflagged rows as well.

Follow the actual submission schema.

==================================================
14. CONFIDENCE REVIEW
==================================================

Review the confidence logic.

Confidence should reflect evidence strength, not just whether a finding exists.

Suggested interpretation:

HIGH
- deterministic contract/data evidence
- no material unresolved reading

MEDIUM
- conclusion supported, but a documented alternative can affect classification or amount

LOW
- finding depends heavily on a genuinely ambiguous contractual reading

Do not claim statistical calibration unless we actually have labelled Civil Works truth.

Review especially:

PA-00801
PA-00006
duplicate-ordering cases
timing-only cases

==================================================
15. OUTPUT CLEANUP
==================================================

Review:

outputs/civil_works/

Current files:

- findings.jsonl
- application_audit.csv
- draft_predictions.csv
- audit_summary.md
- coverage.md
- uncertainty_report.md
- sensitivity.md

Make sure:

- names are clear
- no temporary/debug outputs exist
- every file has a purpose
- prediction output schema matches the task
- uncertainty is not hidden
- reports agree numerically

These may remain Civil Works-specific drafts.

Do NOT create the combined Civil Works + Drilling submission yet.

==================================================
16. DOCUMENTATION
==================================================

Update Civil Works documentation only where the review establishes something.

Keep:

docs/civil_works/decision_log.md

clear and concise.

It should state:

- accepted readings
- unresolved readings
- sensitivity of each unresolved reading
- corrected-total policy
- timing-only policy
- primary-category precedence
- adjustment-vs-total distinction

Do not bury current decisions under historical debugging notes.

Historical details can remain where useful, but the current policy must be immediately obvious.

==================================================
17. TESTS
==================================================

Add tests only where needed by this review.

At minimum ensure tests pin:

- strict corrected-total policy
- timing-only breach remains flaggable without changing monetary total
- deterministic primary-category precedence
- indexation uncertainty
- monthly-rate uncertainty
- duplicate-order ambiguity
- exclusion boundaries
- backdated-adjustment sensitivity
- retention outside application_total
- cap breach blanking
- split-band pricing
- clean application
- multiple independent findings
- no floats
- no network
- deterministic outputs

Run with warnings as errors.

==================================================
18. REGRESSION
==================================================

Verify:

- Phase 1 artifacts unchanged unless documentation legitimately needs updating
- Phase 2 contract/pricing artifacts unchanged
- pricing engine behavior unchanged unless a true Phase 2 bug is discovered
- task source data unchanged
- no Drilling files created

If you discover a genuine Phase 2 pricing bug:

STOP.

Do not quietly repair it inside Phase 4.

Report it separately first.

==================================================
19. FINAL REPORT
==================================================

Do NOT commit.
Do NOT push.

Report back with:

1. final verdict:
   READY FOR DRILLING
   or
   NEEDS ANOTHER CIVIL WORKS PASS

2. final Civil Works counts:
   - applications
   - lines
   - flagged
   - findings
   - corrected totals published
   - blank totals
   - HIGH/MEDIUM/LOW confidence

3. category counts

4. exact blank-reason breakdown

5. exact sensitivity table

6. which findings can disappear under alternatives

7. which totals change under alternatives

8. result of indexation review

9. result of monthly-rate review

10. duplicate-ordering conclusion

11. exclusion-window conclusion

12. backdated-adjustment conclusion

13. timing-only policy confirmation

14. primary-category precedence chosen

15. all files created/modified/deleted in this phase

16. test count and result

17. regression status

18. confirmation:
   - no Drilling implementation
   - no combined submission
   - no commit
   - no push

Important:

Do not optimize for more published totals.

The goal of Phase 4 is to FREEZE a defensible Civil Works implementation that we can stop touching while we build Drilling.
