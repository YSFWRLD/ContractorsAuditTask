Apply the final Drilling audit review decision.
WELL CLASS DECISION
Remove `well_class_inconsistent` as a flagging audit finding for MDS-00215 and MDS-01445.
Reason:
The contract review establishes that the invoice's `well_class` field is not part of the contractual billing basis:

* Clause 34 specifies the required charge fields and does not require well class.
* Appendix B's contractual invoice form has no well-class field.
* P2/P3 state that well class is determined by the call-off.
* The call-offs are not provided in the task data.

Therefore a disagreement between:

* the contractor's descriptive `well_class` field, and
* the class whose rate happens to match the billed rate

does not prove a contractual billing error.
The invoice's descriptive field must not substitute for the missing call-off, in either direction.
Required treatment
For MDS-00215 and MDS-01445:

* remove the `well_class_inconsistent` flagging finding;
* do not claim the billed class is correct;
* do not claim the invoice-stated class is correct;
* retain the discrepancy as a non-flagging AMB-13 observation/query for reviewer visibility;
* preserve:
   * the invoice's descriptive class;
   * each possible contractual class;
   * the rate under each class;
   * the billed rate;
* keep entitlement `EVIDENCE_NOT_PROVIDED`;
* keep corrected total blank;
* do not use the descriptive class to determine canonical pricing.

If either invoice has another independent flagging finding, it must remain flagged for that independent reason.
Do not assume the overall flagged-invoice count falls by exactly two until the audit is rerun.
FINAL DRILLING FREEZE
After making this change:

1. regenerate all affected Drilling audit outputs;
2. rerun the full suite:
`python -m pytest -W error`
3. rerun the adversarial review;
4. confirm all generated artifacts/outputs are deterministic;
5. confirm Civil Works artifacts and outputs remain byte-identical;
6. confirm the upstream challenge data remains untouched.

Report the exact final:

* invoices audited;
* flagged invoice count;
* total flagging findings;
* category counts;
* confidence counts;
* corrected-total coverage;
* AMB-13 query counts;
* final status of MDS-00215 and MDS-01445;
* full test count.

Also confirm:

* AMB-05 remains `PER_DAY_THEN_MINIMUM`;
* AMB-12, AMB-14, AMB-15 and AMB-23 remain approved at the reviewed readings;
* AMB-25 remains `EVIDENCE_NOT_PROVIDED`;
* no conditional amount is promoted to canonical;
* no combined `submission.csv` has been generated.

If the full suite was not rerun after the final wording/output change from the previous review, rerun the COMPLETE suite now, not only targeted tests.
Then STOP.
Do not begin final packaging.
Do not commit or push yet.
