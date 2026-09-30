# Drilling Phase 4b — approved pricing readings and canonical pricing

Tool: Claude Code (Claude Opus 5.5). Date: 2026-09-30. Given verbatim below.

---

Phase 4 review is accepted.
Use the following approved readings:

* AMB-01 = no global precedence/rank for documents omitted from Clause 2; resolve each concrete conflict through its own switch.
* AMB-02 = do NOT apply the well-class factor to PD-210.
* AMB-03 = omit the hole-section factor on Standby days.
* AMB-04 = apply the Rig Services Index from the first month.
* AMB-05 = rig-up hour once per BHA run.
* AMB-06 = DD-120 includes circulating hours only; do not include back-reaming hours.
* AMB-07 = Amendment 3 rate of 416.00 governs from its stated effective date.
* AMB-08 = monthly published rate is the base rate, then apply the contractual build-up.
* AMB-10 = volume tiers are per well.
* AMB-11 = Contract Year 2 begins 2026-01-01.
* AMB-21 = use the Schedule 2D lost-in-hole value, with the required conversion.
* AMB-26 = DS-900 threshold counts services only.

AMB-13 is NOT approved as “use the invoice-stated class.”
For AMB-13, use:
UNKNOWN / UNVERIFIED
The missing call-offs mean well-class and performance-section eligibility cannot be proven from the available contract evidence.
Do not use the invoice itself as evidence of its own entitlement.
Requirements for AMB-13:

* retain the invoice-stated class later as the contractor's claimed class only;
* mark it explicitly as unverified;
* any price that requires the missing class/call-off must remain unresolved/unpriceable;
* unaffected services should still be capable of receiving a canonical price;
* preserve the sensitivity calculation showing what each possible class would do;
* do not silently select the class that best reconciles billed amounts.

Please adjust the pricing selection model if necessary so an explicitly UNKNOWN evidentiary state is a legitimate resolved audit decision. “We cannot establish this from the supplied evidence” is itself a valid outcome and should not force unrelated quantities to remain unpriced.
Keep sensitivity outputs for AMB-05, AMB-10 and all other material interpretation choices even though a canonical reading is now approved.
After applying these decisions:

1. regenerate Phase 4 pricing artifacts;
2. run the complete suite with `-W error`;
3. verify Civil Works remains byte-identical;
4. report canonical pricing coverage, including:
   * priced quantities;
   * clearly not-chargeable quantities;
   * unresolved quantities caused specifically by AMB-13/missing call-offs;
   * any other unresolved quantities;
5. report sensitivity of the approved low/medium-confidence readings;
6. STOP before beginning invoice comparison/audit unless the existing project plan explicitly defines that as the next separately approved phase.

Do not generate the final submission.
Do not commit or push anything.
