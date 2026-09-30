"""Targeted correctness patch: Clause 29A / Schedule 2A indexation is settled by the contract text.

Clause 2 makes Schedules 1 to 5 part of the whole agreement and lets a Schedule prevail; Schedule 2A says the Schedule 1
rate "is not payable as it stands". Appendix B's unindexed example is outside the whole agreement. The alternative stays
in sensitivity; totals whose only blocker was this reading are now published from the existing contract-side valuation.
"""

import csv
import json
from collections import Counter

from contractor_audit.domains.civil_works.interpretation import SWITCHES_BY_FIELD, SwitchStatus
from contractor_audit.shared import paths

OUT = paths.outputs_dir("civil_works")
RECOVERED = {"PA-00043": 23142526, "PA-00052": 9785999, "PA-00090": 11943070, "PA-00120": 14015985, "PA-00138": 9447752,
             "PA-00219": 7392021, "PA-00312": 28548574, "PA-00489": 12858656, "PA-00496": 24440766, "PA-00503": 13349662,
             "PA-00529": 30438929, "PA-00580": 53062928, "PA-00610": 4790444, "PA-00707": 3367634, "PA-00708": 21303190,
             "PA-00768": 7245167, "PA-00845": 36828425, "PA-00889": 31157868, "PA-00892": 7322310}


def _rows():
    with open(OUT / "application_audit.csv", newline="", encoding="utf-8") as f:
        return {r["application_no"]: r for r in csv.DictReader(f)}


def test_indexation_is_text_resolved_and_its_alternative_kept_for_sensitivity():
    assert SWITCHES_BY_FIELD["indexed_rate_method"].status is SwitchStatus.TEXT_RESOLVED
    s = json.loads((paths.artifacts_dir("civil_works") / "sensitivity.json").read_text(encoding="utf-8"))
    assert s["switches"]["indexed_rate_method"]["alternatives"]["appendix_b_unindexed"]["lines_affected"] > 0
    assert "appendix_b_unindexed" in (OUT / "sensitivity.md").read_text(encoding="utf-8")


def test_index_only_blanks_are_published_from_the_contract_side_valuation():
    rows = _rows()
    assert rows["PA-00043"]["expected_total_cents"] == "23142526" and rows["PA-00043"]["billed_total_cents"] == "23145744"
    for no, total in RECOVERED.items():
        r = rows[no]
        assert r["flagged"] == "1" and int(r["expected_total_cents"]) == total == int(r["contract_total_cents"])
        assert r["blank_reasons"] == "" and r["total_status"] in ("corrected", "unchanged")
    assert not any("indexed_rate_method" in r["blank_reasons"] for r in rows.values())


def test_no_unrelated_civil_flag_changed():
    rows = _rows()
    flagged = [r for r in rows.values() if r["flagged"] == "1"]
    assert len(flagged) == 77 and sum(r["expected_total_cents"] == "" for r in flagged) == 21
    assert Counter(r["primary_category"] for r in flagged) == {
        "unit_rate_mismatch": 26, "duplicate_record": 19, "unit_mismatch": 4, "missing_record": 4, "application_timing": 3,
        "rebate_incorrectly_applied": 3, "line_outside_application_period": 2, "quantity_exceeds_record": 2, "work_after_final_completion": 2,
        "contract_reference_mismatch": 2, "line_total_arithmetic": 2, "adjustment_missing": 1, "application_total_mismatch": 1,
        "duplicate_line": 1, "item_record_mismatch": 1, "discount_incorrectly_applied": 1, "unsigned_record": 1,
        "exclusion_window_violation": 1, "daily_limit_exceeded": 1}
