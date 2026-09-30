"""Contract period, retention, the 31A adjustment and the 45A release; valuation independence from billed figures."""

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from contractor_audit.domains.civil_works.contract_period import ContractPeriod
from contractor_audit.domains.civil_works.interpretation import WORKING_INTERPRETATION as W, RetroAdjustmentTrigger
from contractor_audit.domains.civil_works.models import Application, ApplicationLine
from contractor_audit.domains.civil_works.valuation import (Valuer, on_post_issue_side, retention_cents,
                                                            retention_release)

D = Decimal


# --------------------------------------------------------------------------- contract period

@pytest.mark.parametrize("day, measurable", [("2025-01-04", False), ("2025-01-05", True), ("2025-09-27", True), ("2025-09-28", True),
                                             ("2026-03-31", True), ("2026-04-01", True), ("2026-09-30", True), ("2026-10-01", False)])
def test_contract_in_force(terms, day, measurable):
    assert ContractPeriod(terms).status(date.fromisoformat(day)).measurable is measurable


def test_extension_attribution_and_completion_as_at(terms):
    p = ContractPeriod(terms)
    assert "A1" in p.status(date(2026, 3, 31)).reason and "A2" in p.status(date(2026, 4, 1)).reason
    assert p.completion_as_at(date(2025, 8, 17)) == date(2025, 9, 27)
    assert p.completion_as_at(date(2025, 8, 18)) == date(2026, 3, 31)
    assert p.completion_as_at(date(2026, 2, 16)) == p.final_completion == date(2026, 9, 30)
    assert [(y.start, y.end) for y in p.years] == [(date(2025, 1, 5), date(2026, 1, 4)), (date(2026, 1, 5), date(2026, 9, 30))]


def test_the_two_late_lines_are_visible_not_judged(terms, applications, lines):
    v = Valuer(terms).value(applications, lines)
    late = sorted(r for r, pl in v.lines.items() if not pl.period.measurable)
    assert late == ["PA-00375-07", "PA-00678-10"]
    assert all(v.lines[r].price.amount_cents > 0 for r in late)      # still priced; nothing is disallowed here


# --------------------------------------------------------------------------- retention

@pytest.mark.parametrize("total, expected", [(1579440, 78972), (99999, 4999), (0, 0), (19, 0)])
def test_retention_rounds_down(total, expected):
    assert retention_cents(total, D(5)) == expected


def test_retention_is_independent_of_billed_retention(terms, applications, lines):
    v = Valuer(terms).value(applications, lines)
    for app in applications[:50]:
        a = v.applications[app.application_no]
        assert a.retention_cents == retention_cents(a.measured_work_total_cents, D(5))


# --------------------------------------------------------------------------- 31A / A3

@pytest.mark.parametrize("app_day, on_or_after, after", [("2026-05-11", False, False), ("2026-05-12", True, False), ("2026-05-13", True, True)])
def test_post_issue_side_boundary(app_day, on_or_after, after):
    d, issued = date.fromisoformat(app_day), date(2026, 5, 12)
    assert on_post_issue_side(d, issued, RetroAdjustmentTrigger.ON_OR_AFTER_ISSUE) is on_or_after
    assert on_post_issue_side(d, issued, RetroAdjustmentTrigger.AFTER_ISSUE) is after


def _app(no, applied):
    return Application(no, "CW-2025-0417-CIV", "R", "S-01 Platform North", "Z1 Compound", date(2025, 11, 1), date(2025, 11, 30),
                       applied, 0, 0, 0, 0, 0, 2, {})


def _line(app, n, code, qty, day, amount_cents=0, rate="0"):
    return ApplicationLine(f"{app}-{n:02d}", app, n, day, "S-01 Platform North", code, "d", "no.", "Z1 Compound", None,
                           D(qty), D(rate), amount_cents, False, None, 2, {})


def test_retro_adjustment_synthetic(terms):
    apps = [_app("PA-1", date(2025, 12, 10)), _app("PA-2", date(2026, 5, 12)), _app("PA-3", date(2026, 5, 14))]
    lines = [_line("PA-1", 1, "C.32.010", 2, date(2025, 11, 20)),     # valued at 1860 before A3; 1984 after -> +248.00
             _line("PA-1", 2, "C.32.010", 1, date(2025, 10, 20)),     # before A3 effective: no difference
             _line("PA-2", 1, "C.32.010", 1, date(2025, 11, 21)),     # submitted on the issue date
             _line("PA-3", 1, "A.11.010", 1, date(2026, 5, 1))]
    on = Valuer(terms, W).value(apps, lines)
    [adj31] = [a for a in on.adjustments if a.kind == "clause_31a_retroactive_rate"]
    assert (adj31.application_no, adj31.amount_cents, adj31.basis) == ("PA-2", 24800, ("PA-1-01",))
    assert on.lines["PA-2-01"].price.unit_rate == D("1984.00")
    after = Valuer(terms, W.with_(retro_adjustment_trigger=RetroAdjustmentTrigger.AFTER_ISSUE)).value(apps, lines)
    [adj31b] = [a for a in after.adjustments if a.kind == "clause_31a_retroactive_rate"]
    assert (adj31b.application_no, adj31b.amount_cents, adj31b.basis) == ("PA-3", 24800 + 12400, ("PA-1-01", "PA-2-01"))
    assert after.lines["PA-2-01"].price.unit_rate == D("1860.00")
    # Outside-measured sums never enter the measured total.
    assert on.applications["PA-2"].measured_work_total_cents == on.lines["PA-2-01"].price.amount_cents


def test_real_retro_boundary_applications(terms, applications, lines):
    same_day = sorted(a.application_no for a in applications if a.application_date == date(2026, 5, 12))
    assert same_day == ["PA-00006", "PA-00023", "PA-00380"]
    on = Valuer(terms).value(applications, lines)
    after = Valuer(terms, W.with_(retro_adjustment_trigger=RetroAdjustmentTrigger.AFTER_ISSUE)).value(applications, lines)
    a_on = next(a for a in on.adjustments if a.kind == "clause_31a_retroactive_rate")
    a_after = next(a for a in after.adjustments if a.kind == "clause_31a_retroactive_rate")
    assert a_on.application_no == "PA-00006" and a_after.application_no == "PA-00443"
    assert "3 applications share that date" in a_on.note


# --------------------------------------------------------------------------- 45A

def test_retention_release_first_application_after_completion():
    apps = [_app("A", date(2026, 9, 1)), _app("B", date(2026, 9, 30)), _app("C", date(2026, 10, 2)), _app("D", date(2026, 10, 9))]
    rel = retention_release(apps, {"A": 1001, "B": 2000, "C": 50, "D": 70}, date(2026, 9, 30))
    assert (rel.application_no, rel.amount_cents, rel.basis) == ("C", 1500, ("A", "B"))    # half of 3001 = 1500.5 -> down
    assert retention_release(apps[:2], {"A": 1, "B": 1}, date(2026, 9, 30)) is None


def test_real_release_lands_on_pa00678(terms, applications, lines):
    v = Valuer(terms).value(applications, lines)
    [rel] = [a for a in v.adjustments if a.kind == "clause_45a_retention_release"]
    assert rel.application_no == "PA-00678" and len(rel.basis) == 898


# --------------------------------------------------------------------------- independence from billed data

def test_valuation_never_reads_billed_rates_or_amounts(terms, applications, lines):
    scrambled_lines = [dataclasses.replace(l, rate_applied=D("1.23"), amount_cents=7) for l in lines]
    scrambled_apps = [dataclasses.replace(a, application_total_cents=1, retention_cents=2, net_payable_cents=3) for a in applications]
    a = Valuer(terms).value(applications, lines)
    b = Valuer(terms).value(scrambled_apps, scrambled_lines)
    assert {r: p.price.amount_cents for r, p in a.lines.items()} == {r: p.price.amount_cents for r, p in b.lines.items()}
    assert [(x.application_no, x.amount_cents) for x in a.adjustments] == [(x.application_no, x.amount_cents) for x in b.adjustments]
