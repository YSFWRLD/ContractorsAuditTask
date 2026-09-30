"""Record quantity extraction and the quantity rules (6A, 33/33A, 47A, 31, 32/P19/P21)."""

from datetime import date
from decimal import Decimal

import pytest

from contractor_audit.domains.civil_works.interpretation import ChargeableHourScope, ExclusionWindow, SurveyQuantityRule
from contractor_audit.domains.civil_works.quantity_rules import (ExclusionEvaluator, Measurement, chargeable_hours,
                                                                 chargeable_hours_by_scope, daily_limit_use,
                                                                 exclusion_rules, recorded_payable, surveyed_payable,
                                                                 week_measurable)
from contractor_audit.domains.civil_works.record_quantities import RULES, depth_item, extract_all, extract_quantity
from contractor_audit.domains.civil_works.records import RECORD_TYPES, parse_record

D = Decimal


def _rec(prefix, body, extra="Date: 09/01/2025\n"):
    text = (f"{RECORD_TYPES[prefix]}\nTicket: {prefix}-00001\nJob: J\nArea: S-01 Platform North\n{extra}\n{body}\n\n"
            "Signed (foreman): A\nCountersigned (Engineer's representative): B\n")
    return parse_record(text, f"{prefix}-00001.txt")[0]


# --------------------------------------------------------------------------- extraction

SAMPLES = [
    ("CT", "792 square metres of sub-base in and compacted", "792", "m2", ("D.41.010",)),
    ("CT", "laid and rolled 520 m2 of Type 1", "520", "m2", ("D.41.010",)),
    ("CT", "capping layer, 121 m2 placed and compacted", "121", "m2", ("D.41.040",)),
    ("CT", "placed and whacked 309 m3 of imported stone", "309", "m3", ("A.14.010",)),
    ("CT", "brought in 89 cube of fill, compacted in layers", "89", "m3", ("A.14.010",)),
    ("CV", "surveyed 154 m of the finished run with the camera", "154", "lm", ("C.35.010",)),
    ("DX", "trench dig 210 cube, 3 m deep section", "210", "m3", ("A.12.030",)),
    ("DX", "trench over four metres, 39 m3 dug", "39", "m3", ("A.12.040",)),
    ("DX", "deep trench 267 m3, between two and four metres", "267", "m3", ("A.12.030",)),
    ("JS", "set out and agreed 3 chainage band with the Engineer", "3", "no.", ("E.52.010",)),
    ("JS", "steel fixers placed 5 t of high yield bar", "5", "tonne", ("B.23.010",)),
    ("JS", "laid 45 m2 of A393 mesh with laps", "45", "m2", ("B.23.020",)),
    ("JS", "fixed 8 tonne of bar, cut and bent to schedule", "8", "tonne", ("B.23.010",)),
    ("MO", "no work possible, weather, 6 hours standing", "6", "hour", ("E.51.010",)),
    ("MO", "rained off -- crew and plant stood for 5 hours", "5", "hour", ("E.51.010",)),
    ("PR", "foundation pour 140 cube, C32/40 off the truck", "140", "m3", ("B.21.020",)),
    ("PR", "wall pour 335 m3, 32/40 mix", "335", "m3", ("B.21.040",)),
    ("PR", "poured 140 m3 into the foundations, 32/40 mix", "140", "m3", ("B.21.020",)),
    ("PR", "slab pour 379 m3, 32/40", "379", "m3", ("B.21.030",)),
    ("PR", "poured the slab, 176 cube of C32/40", "176", "m3", ("B.21.030",)),
    ("PS", "tracked machine stood idle 7 hours waiting on access", "7", "hour", ("E.51.030",)),
    ("PS", "excavator and driver held up 3 hours", "3", "hour", ("E.51.030",)),
    ("PT", "built 3 large chamber, 1800 dia precast", "3", "no.", ("C.32.030",)),
    ("PT", "laid 302 m of 400 ductile main", "302", "lm", ("C.31.020",)),
]


def test_every_rule_has_a_sample():
    assert {r.rule_id for r in RULES} >= {extract_quantity(_rec(p, b)).rule_id for p, b, *_ in SAMPLES}
    assert len({extract_quantity(_rec(p, b)).rule_id for p, b, *_ in SAMPLES}) == len(RULES) - 2   # DW rules tested below


@pytest.mark.parametrize("prefix, body, qty, unit, items", SAMPLES)
def test_rule_extracts_quantity_with_provenance(prefix, body, qty, unit, items):
    q = extract_quantity(_rec(prefix, body))
    assert q.resolved and q.quantity == D(qty) and q.unit == unit and q.indicated_items == items
    assert q.raw_text == body and q.record_id == f"{prefix}-00001" and q.source_file == f"{prefix}-00001.txt" and q.rule_id


def test_weekly_dewatering_record():
    extra = "Week beginning: 03/02/2025\nDays on: Mon 03/02, Tue 04/02, Wed 05/02, Thu 06/02\n"
    q = extract_quantity(_rec("DW", "pumps kept going 1 week this period", extra))
    assert q.quantity == 1 and q.unit == "week" and q.details["days_on"] == 4


@pytest.mark.parametrize("body", ["poured some concrete", "wall pour 335 m3, 32/40 mix, approx", "wall pour about 335 m3, 32/40 mix", ""])
def test_unmatched_text_is_unresolved_not_guessed(body):
    q = extract_quantity(_rec("PR", body))
    assert not q.resolved and q.quantity is None and q.reason


def test_a_phrase_from_another_record_type_does_not_match():
    assert not extract_quantity(_rec("PT", "wall pour 335 m3, 32/40 mix")).resolved


@pytest.mark.parametrize("depth, item", [("1.5", "A.12.020"), ("2", "A.12.020"), ("3", "A.12.030"), ("4", "A.12.030"), ("4.5", "A.12.040")])
def test_trench_depth_bands(depth, item):
    assert depth_item(D(depth)) == item


def test_all_real_records_resolve(record_set):
    qs = extract_all(record_set.records)
    assert len(qs) == 2169 and all(q.resolved for q in qs)


# --------------------------------------------------------------------------- 6A chargeable hour

@pytest.mark.parametrize("hours, chargeable", [("0.5", "0"), ("1", "0"), ("1.5", "0.5"), ("2", "1"), ("9", "8")])
def test_first_hour_not_chargeable(hours, chargeable):
    assert chargeable_hours(D(hours)) == D(chargeable)


def test_chargeable_hour_scopes():
    # two lines quoting one 5-hour record, plus a second 3-hour record in the same work area and day
    entries = [("L1", "MO-1", ("S-01", date(2025, 1, 1)), D(5)), ("L2", "MO-1", ("S-01", date(2025, 1, 1)), D(0)),
               ("L3", "MO-2", ("S-01", date(2025, 1, 1)), D(3))]
    assert sum(chargeable_hours_by_scope(entries, ChargeableHourScope.PER_RECORD).values()) == D(6)       # 4 + 2
    assert sum(chargeable_hours_by_scope(entries, ChargeableHourScope.PER_LINE).values()) == D(6)         # 4 + 0 + 2
    assert sum(chargeable_hours_by_scope(entries, ChargeableHourScope.PER_WORK_AREA_DAY).values()) == D(7)  # 8 - 1


# --------------------------------------------------------------------------- 33 / 33A

@pytest.mark.parametrize("measured, t33a, t33", [("100", "100", "100"), ("102", "102", "100"), ("102.01", "100", "100"),
                                                  ("95", "95", "95"), ("101", "101", "100")])
def test_survey_rules(measured, t33a, t33):
    assert surveyed_payable(D(measured), D(100), SurveyQuantityRule.TOLERANCE_33A).payable_quantity == D(t33a)
    assert surveyed_payable(D(measured), D(100), SurveyQuantityRule.EXACT_33).payable_quantity == D(t33)


def test_survey_allowance_carries_its_clause():
    a = surveyed_payable(D(103), D(100), SurveyQuantityRule.TOLERANCE_33A)
    assert a.clause.startswith("33A") and a.payable_as_measured_up_to == D("102.00")


def test_record_cap():
    assert recorded_payable(D(12), D(10)).payable_quantity == 10
    assert recorded_payable(D(8), D(10)).payable_quantity == 8


# --------------------------------------------------------------------------- 47A week

@pytest.mark.parametrize("days, ok", [(4, False), (5, True), (7, True)])
def test_week_rule(days, ok):
    assert week_measurable(days) is ok


# --------------------------------------------------------------------------- exclusions and daily limits

def _m(key, code, day, area="S-01"):
    return Measurement(key, code, area, date(2025, 3, day))


@pytest.mark.parametrize("day_of_backfill, included, excluded", [(10, True, False), (11, True, True), (12, True, True), (13, False, False)])
def test_exclusion_window_readings(terms, day_of_backfill, included, excluded):
    ms = [_m("fill", "A.14.010", 10), _m("backfill", "A.14.020", day_of_backfill)]
    rules = exclusion_rules(terms)
    assert bool(ExclusionEvaluator(rules, ExclusionWindow.SAME_DAY_INCLUDED).evaluate(ms)) is included
    assert bool(ExclusionEvaluator(rules, ExclusionWindow.SAME_DAY_EXCLUDED).evaluate(ms)) is excluded


def test_exclusion_needs_same_work_area_and_prior_measurement(terms):
    rules = exclusion_rules(terms)
    ev = ExclusionEvaluator(rules, ExclusionWindow.SAME_DAY_INCLUDED)
    assert not ev.evaluate([_m("fill", "A.14.010", 10, "S-02"), _m("backfill", "A.14.020", 11, "S-01")])
    assert not ev.evaluate([_m("fill", "A.14.010", 12), _m("backfill", "A.14.020", 11)])


def test_p21_traffic_management_on_a_surfacing_day(terms):
    rules = exclusion_rules(terms)
    for window in ExclusionWindow:
        hits = ExclusionEvaluator(rules, window).evaluate([_m("sm", "D.41.030", 10), _m("tm", "E.51.020", 10), _m("tm2", "E.51.020", 11)])
        assert [(h.excluded.key, h.rule.clause) for h in hits] == [("tm", "P21 p.13")]


def test_daily_limits(terms):
    uses = daily_limit_use(terms, [(_m("a", "C.32.030", 5), D(2)), (_m("b", "C.32.030", 5), D(2)), (_m("c", "C.32.030", 6), D(3)),
                                   (_m("d", "A.11.020", 5), D(9999))])
    assert [(u.work_date.day, u.measured, u.limit, u.excess) for u in uses] == [(5, 4, 3, 1), (6, 3, 3, 0)]
