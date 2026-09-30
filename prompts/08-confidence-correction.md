Apply one final confidence-only correction to the targeted correctness patch.

Do NOT change:
- any flags;
- any expected totals;
- any billed totals;
- any categories;
- any Civil Works results;
- any Drilling pricing/quantity reading;
- AMB-13;
- AMB-25 logic;
- well-class consistency;
- submission ordering;
- the 0.95 / 0.75 / 0.55 numerical mapping.

## 1. Regrade AMB-10

The current LOW grade for:

`volume_tier_scope / AMB-10 / PER_WELL`

is not justified by the underlying contract evidence.

The operative Schedule 2 Part 2 sentence says:

“metres already drilled on the well in the Contract Year”

This expressly scopes the tier count to the well.

The contrary evidence is only:
- the abbreviated heading;
- the abbreviated column label;

which omit “well” but do not affirmatively state contract-wide aggregation.

The old Phase 4 LOW recommendation also cited the fact that no well reaches 40,000 m, while explicitly acknowledging that this is context rather than evidence.

Therefore regrade the selected PER_WELL reading:

LOW -> MEDIUM

Preserve historical provenance.

In `phase4_recommendations.json`, retain the original grade explicitly, for example:

`"original_confidence": "LOW"`

and make the current confidence MEDIUM with a concise note explaining:

- the operative sentence expressly says “on the well”;
- heading/column wording is only abbreviated;
- the old feasibility observation was not contractual evidence;
- PER_WELL remains MEDIUM rather than HIGH because the abbreviated labels create a small textual tension.

Do not change the selected reading.

## 2. AMB-05 provenance

Review only the documentation/provenance of AMB-05.

Its original Phase 4 recommendation was PER_BHA_RUN at LOW, but the selected reading is now PER_DAY_THEN_MINIMUM.

Do NOT change the current LOW grade.

The current reading should remain LOW because:
- “period in the hole” still permits a credible per-run interpretation;
- Appendix B provides conflicting example behavior;
- the per-run alternative clears real findings such as MDS-01877.

If necessary, document explicitly that LOW is now the evidential grade of the CURRENT PER_DAY_THEN_MINIMUM reading, not merely inherited from the superseded recommendation.

Avoid code changes unless required to make the grade provenance truthful.

## 3. Expected confidence effect

After AMB-10 becomes MEDIUM:

- the 554 unflagged invoices that were LOW solely because of AMB-10 should return to MEDIUM;
- the 9 unflagged AMB-12-dependent invoices should remain LOW;
- MDS-00856 should remain LOW;
- MDS-01338 should remain LOW;
- MDS-01877 should remain LOW;
- MDS-01625 should remain LOW.

No flag should change.

No amount should change.

No category should change.

## 4. Regenerate

Regenerate all affected Drilling outputs and root `submission.csv`.

Confirm:

- Civil Works remains unchanged from the targeted correctness patch;
- Drilling flagged remains 116;
- combined flagged remains 193;
- Civil blank totals remain 21;
- all Drilling expected totals remain blank;
- combined blank expected totals remain 1,927;
- MDS-00215 and MDS-01445 remain flagged;
- PA-00043 remains 23142526.

Report the final Drilling confidence distribution.

## 5. Tests

Run:

`python -m pytest -W error`

Expected baseline before this confidence-only change:
595 passed.

Regenerate twice and confirm deterministic bytes.

## 6. Final integrity check

Compare against the state immediately before this confidence-only correction.

The only substantive submission changes should be confidence values caused by AMB-10 LOW -> MEDIUM.

No:
- flags;
- categories;
- expected totals;
- billed totals;
- invoice IDs

may change.

## 7. Commit and push

If and only if all checks above pass:

Commit the entire targeted correctness patch plus this confidence correction.

Use commit message:

`Fix audit correctness and confidence handling`

Push to:

`origin main`

Do not amend or squash earlier commits.

## FINAL REPORT

Return:

# FINAL CORRECTNESS PUSH REPORT

## COMMIT
- SHA
- branch
- message

## AUDIT RESULT
- Civil flagged
- Drilling flagged
- combined flagged
- Civil blank totals
- Drilling blank totals
- combined blank totals

## CONFIDENCE
- AMB-10 before/after
- final Drilling distribution
- count of submission confidence values changed by this final correction
- confirmation AMB-05 remains LOW with current-reading justification

## VERIFIED FIXES
- MDS-00215
- MDS-01445
- PA-00043
- submission-date proxy
- approval floor

## TESTS
- final full-suite result

## DETERMINISM
- regeneration result

## INTEGRITY
- no conditional totals leaked
- upstream data unchanged
- no unrelated audit logic changed

## GIT
- HEAD
- origin/main
- working tree status

STOP after push.
