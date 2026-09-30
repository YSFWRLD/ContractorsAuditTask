"""Each finding category on a synthetic case built at the contract price, plus the clean case."""

from decimal import Decimal

import pytest

from contractor_audit.domains.civil_works.audit.options import (WORKING_AUDIT_INTERPRETATION as WA,
                                                                MissingRecordConsequence, UnsignedRecord)
from contractor_audit.domains.civil_works.interpretation import WORKING_INTERPRETATION as W, ExclusionWindow

from .conftest import categories, d, week

D = Decimal


def test_clean_case_has_no_findings(case):
    case.app("PA-1", d("2025-03-20"))
    case.line("PA-1", "A.11.010", 500, d("2025-03-03"))
    case.line("PA-1", "B.21.030", 40, d("2025-03-07"), record=case.record("PR-00001", "slab pour 40 m3, 32/40", d("2025-03-07")))  # Friday
    case.line("PA-1", "C.31.010", 48, d("2025-03-04"), zone="Z2 North Spur", ground="G3 Cemented Fill")                               # indexed
    case.line("PA-1", "B.23.020", 100, d("2025-03-05"), zone="Z3 Wadi Crossing",
              record=case.record("JS-00001", "laid 100 m2 of A393 mesh with laps", d("2025-03-05")))                                    # USD
    case.line("PA-1", "E.51.010", 4, d("2025-03-06"), record=case.record("MO-00001", "rained off -- crew and plant stood for 5 hours", d("2025-03-06")))
    run = case.run()
    assert run.findings == ()
    assert run.contract_totals["PA-1"] == sum(l.amount_cents for l in case.build().lines)


# --------------------------------------------------------------------------- check 1-3

def test_contract_reference_and_issuer(case):
    case.app("PA-1", d("2025-03-20"), contract_ref="CW-2024-0417-CIV", subcontractor="Someone Else LLC")
    case.line("PA-1", "A.11.010", 5, d("2025-03-03"))
    run = case.run()
    assert [f.rule for f in run.findings] == ["contract_reference.issuer", "contract_reference.reference"]   # deterministic rule order
    assert all(not f.affects_total for f in run.findings)
    assert run.contract_totals["PA-1"] == case.build().applications[0].application_total_cents


@pytest.mark.parametrize("day, category", [("2026-09-30", None), ("2026-10-01", "work_after_final_completion")])
def test_final_completion_boundary(case, day, category):
    case.app("PA-1", d("2026-10-10"))
    ref = case.line("PA-1", "A.11.010", 5, d(day))
    run = case.run()
    assert categories(run, ref) == ([category] if category else [])
    if category:
        assert run.lines[ref].payable_quantity == 0 and run.contract_totals["PA-1"] == 0


def test_work_before_commencement_is_not_payable_and_needs_no_rate(case):
    case.app("PA-1", d("2025-01-20"))
    ref = case.line("PA-1", "A.11.010", 5, d("2025-01-04"), rate="3.85", amount=1925)
    run = case.run()
    assert categories(run, ref) == ["work_outside_contract_period"]
    assert run.contract_totals["PA-1"] == 0 and run.unresolved == ()


@pytest.mark.parametrize("applied, rules", [("2025-03-09", ["period.submitted_before_period_closed"]), ("2025-03-10", []),
                                            ("2025-03-31", []), ("2025-04-01", ["period.submitted_late"])])
def test_submission_window(case, applied, rules):
    case.app("PA-1", d(applied))
    case.line("PA-1", "A.11.010", 5, d("2025-03-10"))
    assert [f.rule for f in case.run().findings] == rules


def test_period_misstated_and_line_outside_period(case):
    case.app("PA-1", d("2025-03-20"), period_from=d("2025-03-02"), period_to=d("2025-03-05"))
    case.line("PA-1", "A.11.010", 5, d("2025-03-03"))
    out = case.line("PA-1", "A.11.010", 5, d("2025-03-09"))
    run = case.run()
    assert categories(run) == ["line_outside_application_period"] and run.lines[out].payable_quantity == 0
    case2 = type(case)(case.terms, case.raw).app("PA-2", d("2025-03-20"), period_from=d("2025-03-02"), period_to=d("2025-03-05"))
    case2.line("PA-2", "A.11.010", 5, d("2025-03-03"))
    assert categories(case2.run()) == ["application_period_misstated"]


# --------------------------------------------------------------------------- check 4 records

def test_missing_record_and_nonexistent_record(case):
    case.app("PA-1", d("2025-03-20"))
    a = case.line("PA-1", "B.21.030", 10, d("2025-03-03"))
    b = case.line("PA-1", "B.21.030", 10, d("2025-03-04"), record="PR-09999")
    run = case.run()
    assert [f.rule for f in run.findings] == ["records.missing_reference", "records.record_not_found"]
    assert run.lines[a].payable_quantity == run.lines[b].payable_quantity == 0 and run.contract_totals["PA-1"] == 0
    p23 = case.run(audit_interp=WA.with_(missing_record_consequence=MissingRecordConsequence.DEDUCT_FROM_NEXT_VALUATION))
    assert categories(p23) == ["missing_record", "missing_record"] and p23.lines[a].payable_quantity == 10
    assert all(not f.affects_total for f in p23.findings)


def test_non_schedule_5_item_needs_no_record(case):
    case.app("PA-1", d("2025-03-20"))
    case.line("PA-1", "A.11.020", 10, d("2025-03-03"))
    assert case.run().findings == ()


def test_unsigned_record(case):
    case.app("PA-1", d("2025-03-20"))
    ref = case.line("PA-1", "A.12.030", 10, d("2025-03-03"), record=case.record("DX-00001", "deep trench 10 m3, between two and four metres", d("2025-03-03"), unsigned=True))
    run = case.run()
    assert categories(run, ref) == ["unsigned_record"] and run.lines[ref].payable_quantity == 0
    ok = case.run(audit_interp=WA.with_(unsigned_record=UnsignedRecord.ACCEPTED_WITH_DEFECT))
    assert categories(ok, ref) == ["unsigned_record"] and ok.lines[ref].payable_quantity == 10


def test_record_for_another_area_or_date(case):
    case.app("PA-1", d("2025-03-20"))
    a = case.line("PA-1", "B.21.030", 10, d("2025-03-03"), record=case.record("PR-00001", "slab pour 10 m3, 32/40", d("2025-03-03"), area="S-02 Platform South"))
    b = case.line("PA-1", "B.21.030", 10, d("2025-03-04"), record=case.record("PR-00002", "slab pour 10 m3, 32/40", d("2025-03-05")))
    run = case.run()
    assert categories(run, a) == categories(run, b) == ["record_line_mismatch"]


# --------------------------------------------------------------------------- check 6 item identity

def test_record_of_wrong_series_or_item(case):
    case.app("PA-1", d("2025-03-20"))
    a = case.line("PA-1", "B.23.020", 10, d("2025-03-03"), record=case.record("PT-00001", "built 3 large chamber, 1800 dia precast", d("2025-03-03")))
    b = case.line("PA-1", "B.21.030", 10, d("2025-03-04"), record=case.record("PR-00001", "wall pour 10 m3, 32/40 mix", d("2025-03-04")))
    run = case.run()
    assert categories(run, a) == categories(run, b) == ["item_record_mismatch"]
    assert "Schedule 5 requires a JS record" in next(f.message for f in run.findings if f.line_ref == a)


def test_unit_mismatch_rejects_the_line(case):
    case.app("PA-1", d("2025-03-20"))
    ref = case.line("PA-1", "D.42.010", 52, d("2025-03-03"), unit="no.")
    run = case.run()
    assert categories(run, ref) == ["unit_mismatch"] and run.lines[ref].payable_quantity == 0
    f = run.findings[0]
    assert f.impact_cents == run.lines[ref].billed_cents and f.citations[0].reference == "Clause 26"


# --------------------------------------------------------------------------- check 5 quantity

def test_quantity_above_record(case):
    case.app("PA-1", d("2025-03-20"))
    ref = case.line("PA-1", "B.21.030", 120, d("2025-03-03"), record=case.record("PR-00001", "slab pour 100 m3, 32/40", d("2025-03-03")))
    run = case.run()
    assert categories(run, ref) == ["quantity_exceeds_record"] and run.lines[ref].payable_quantity == 100
    f = run.findings[0]
    assert f.impact_cents == run.lines[ref].contract_billed.amount_cents - run.lines[ref].contract_payable.amount_cents == 20 * 38900


@pytest.mark.parametrize("billed, payable", [(4, 4), (5, 4)])
def test_first_hour_rule(case, billed, payable):
    case.app("PA-1", d("2025-03-20"))
    ref = case.line("PA-1", "E.51.010", billed, d("2025-03-03"), record=case.record("MO-00001", "no work possible, weather, 5 hours standing", d("2025-03-03")))
    assert case.run().lines[ref].payable_quantity == payable


@pytest.mark.parametrize("billed, payable", [(102, 102), (103, 100)])
def test_survey_tolerance(case, billed, payable):
    case.app("PA-1", d("2025-03-20"))
    ref = case.line("PA-1", "B.23.020", billed, d("2025-03-03"), record=case.record("JS-00001", "laid 100 m2 of A393 mesh with laps", d("2025-03-03")))
    run = case.run()
    assert run.lines[ref].payable_quantity == payable
    assert case.run(interp=W.with_(survey_quantity_rule=type(W.survey_quantity_rule).EXACT_33)).lines[ref].payable_quantity == 100


def test_week_needs_five_days(case):
    case.app("PA-1", d("2025-03-20"))
    wb = d("2025-03-03")
    ref = case.line("PA-1", "A.16.010", 1, d("2025-03-04"), record=case.record("DW-00001", "pumps kept going 1 week this period", week_beginning=wb, days_on=week(wb, 4)))
    run = case.run()
    assert categories(run, ref) == ["quantity_exceeds_record"] and run.lines[ref].payable_quantity == 0


def test_one_week_record_billed_twice_is_a_duplicate_record(case):
    case.app("PA-1", d("2025-03-12")).app("PA-2", d("2025-03-11"))    # PA-2 submitted first
    wb = d("2025-03-03")
    rec = case.record("DW-00001", "wellpoints running, 1 week on the dewatering", week_beginning=wb, days_on=week(wb, 6))
    a = case.line("PA-1", "A.16.010", 1, d("2025-03-04"), record=rec)
    b = case.line("PA-2", "A.16.010", 1, d("2025-03-06"), record=rec)
    run = case.run()
    assert categories(run, a) == ["duplicate_record"] and categories(run, b) == []            # later submission loses
    by_number = case.run(audit_interp=WA.with_(measurement_order=type(WA.measurement_order).APPLICATION_NUMBER))
    assert categories(by_number, b) == ["duplicate_record"] and categories(by_number, a) == []


# --------------------------------------------------------------------------- checks 9-10

def test_duplicate_line_same_item_area_date(case):
    case.app("PA-1", d("2025-03-20"))
    case.line("PA-1", "A.11.010", 5, d("2025-03-03"))
    later = case.line("PA-1", "A.11.010", 5, d("2025-03-03"))
    other_area = case.line("PA-1", "A.11.010", 5, d("2025-03-03"), area="S-02 Platform South")
    run = case.run()
    assert categories(run) == ["duplicate_line"] and run.findings[0].line_ref == later
    assert run.lines[other_area].payable_quantity == 5


def test_daily_limit(case):
    case.app("PA-1", d("2025-03-20"))
    ref = case.line("PA-1", "E.51.020", 3, d("2025-03-03"))
    run = case.run()
    assert categories(run) == ["daily_limit_exceeded"] and run.lines[ref].payable_quantity == 1


@pytest.mark.parametrize("gap, included, excluded", [(0, True, False), (2, True, True), (3, False, False)])
def test_exclusion_window_boundary(case, gap, included, excluded):
    from datetime import timedelta
    case.app("PA-1", d("2025-03-20"))
    case.line("PA-1", "A.14.010", 5, d("2025-03-03"), record=case.record("CT-00001", "brought in 5 cube of fill, compacted in layers", d("2025-03-03")))
    ref = case.line("PA-1", "A.14.020", 5, d("2025-03-03") + timedelta(gap))
    assert (categories(case.run(), ref) == ["exclusion_window_violation"]) is included
    alt = case.run(interp=W.with_(exclusion_window=ExclusionWindow.SAME_DAY_EXCLUDED))
    assert (categories(alt, ref) == ["exclusion_window_violation"]) is excluded


def test_p21_traffic_management_on_surfacing_day(case):
    case.app("PA-1", d("2025-03-20"))
    case.line("PA-1", "D.41.050", 50, d("2025-03-03"))
    ref = case.line("PA-1", "E.51.020", 1, d("2025-03-03"))
    run = case.run()
    assert categories(run, ref) == ["exclusion_window_violation"] and run.findings[0].rule == "exclusions.p21_same_day"
