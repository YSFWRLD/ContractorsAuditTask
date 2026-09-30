Use the strict AMB-13 treatment for PD-201 as well.
Change the 2,561 PD-201 quantities from priced-with-an-unverified-call-off flag to:
EVIDENCE_NOT_PROVIDED / unresolved
Reason:
Although the PD-201 rate itself can be determined without the call-off, the missing call-off affects whether PD-201 was contractually chargeable at all. Therefore we cannot establish a canonical payable amount for those quantities.
Requirements:

* Do not include the 2,561 PD-201 quantities in canonical priced/payable totals.
* Keep their calculated $5,311,701.66 only as a conditional/sensitivity amount showing what they would be worth if eligibility were established.
* Preserve the underlying report evidence and calculated rate.
* Record the unresolved reason specifically as missing call-off / PD-201 eligibility not established.
* Do not use the invoice's presence of PD-201 as evidence that it was authorized.
* Apply the same `EVIDENCE_NOT_PROVIDED` semantics already used for AMB-13.
* Update canonical coverage counts and totals accordingly.
* Add/adjust tests proving that changing invoice claims cannot turn PD-201 into canonical payable evidence.
* Regenerate affected artifacts and run the full suite with `-W error`.
* Confirm Civil Works remains byte-identical.

Then STOP. Do not begin invoice comparison/audit yet.
