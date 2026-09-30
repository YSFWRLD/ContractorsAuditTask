# Drilling Phase 4 — approvals, decision table and pricing engine

Tool: Claude Code (Claude Opus 5.5). Date: 2026-09-30. Given verbatim below.

---

Phase 3 review is accepted.
Approved interpretation selections:

* AMB-17 `appendix_g_reading` = A / literal
* AMB-20 `dd121_condition` = A / rotary steerable must be in the hole on the specific Standby day
* AMB-24 `metre_source` = A / daily depth advance
* AMB-18 `dd102_basis` = A
* AMB-19 `hc630_basis` = A
* AMB-22 `lih_hours` = A / Part E figure

Approved Phase 3 assumptions:

* Assumption 1
* Assumption 2
* Assumption 4
* Assumption 5
* Assumption 6

Do NOT approve Assumption 3 as currently written. Do not infer that the rotary steerable is in the hole on every report merely because the well used one somewhere else.
Still unresolved:

* AMB-06 DD-120 hours
* AMB-13 call-offs
* AMB-01, AMB-02, AMB-03, AMB-04, AMB-05, AMB-07, AMB-08, AMB-10, AMB-11, AMB-21, AMB-26

Before I approve those, produce a compact decision table for each unresolved switch containing:

1. ambiguity ID;
2. exact contract clause/table/document relied on;
3. the relevant contract wording;
4. interpretation A;
5. interpretation B;
6. Phase 1 preference, if any;
7. measurable effect on this dataset;
8. your evidence-based recommendation;
9. what would remain uncertain after choosing it.

Do not choose a reading merely because it reconciles more billed invoices.
You may begin Phase 4 implementation of the pricing ENGINE and tests if its architecture remains switch-driven and does not hardcode unresolved decisions. However:

* do not establish a canonical priced result using unresolved switches;
* do not compare against invoices yet;
* do not flag invoices;
* do not start the audit phase;
* do not generate the final submission;
* keep sensitivity calculations available for alternative readings;
* pricing must fail explicitly if a required unresolved switch has no supplied selection.

Preserve exact provenance from:
report evidence → interpreted quantity → selected contract reading → rate statement → adjustments/factors → rounded priced amount.
Continue using Decimal/minor-unit-safe arithmetic and the contract's required rounding sequence.
After implementing the Phase 4 pricing engine, run the complete test suite and STOP.
Report:

* pricing components implemented;
* unresolved switches and their decision table;
* sensitivity impact of each material switch;
* pricing coverage;
* services/quantities that cannot yet be priced;
* tests passed;
* files changed;
* confirmation Civil Works remains unchanged;
* confirmation no invoice comparison/audit was started;
* confirmation nothing was committed or pushed.
