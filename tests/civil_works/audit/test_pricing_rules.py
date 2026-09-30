"""Rate, rebate, discount, arithmetic, totals and adjustment findings on synthetic cases."""

from decimal import Decimal

import pytest

from contractor_audit.domains.civil_works.rounding import amount_to_cents

from .conftest import categories, d

D = Decimal


def _mis(case, code, qty, day, billed_rate, **kw):
    from datetime import timedelta
    case.app("PA-1", kw.pop("applied", d(day) + timedelta(10)))
    return case.line("PA-1", code, qty, d(day), rate=billed_rate, amount=amount_to_cents(D(qty) * D(billed_rate)), **kw)


def _finding(run, ref):
    [f] = [f for f in run.findings if f.line_ref == ref]
    return f


def test_wrong_zone_factor(case):
    ref = _mis(case, "A.11.010", 100, "2025-03-03", "4.93")            # Z4 rate billed on Z1 work
    f = _finding(case.run(), ref)
    assert f.category == "unit_rate_mismatch" and f.expected == "3.85" and f.observed == "4.93"
    assert "zone_Z4 Escarpment" in f.message and f.impact_cents == 108 * 100
    assert any(e.kind == "pricing_trace" and "zone_factor" in e.reference for e in f.evidence)


def test_wrong_ground_factor(case):
    ref = _mis(case, "A.12.020", 10, "2025-03-03", "56.72", ground="G2 Firm Sabkha")   # G5 billed on G2
    assert "ground_G5 Sound Rock" in _finding(case.run(), ref).message


def test_recorded_ground_after_27a(case):
    ref = _mis(case, "A.12.020", 10, "2025-10-06", "56.72", ground="G5 Sound Rock")    # 27A: G2 after 27 Sep 2025
    f = _finding(case.run(), ref)
    assert f.expected == "34.80" and "ground_as_recorded_after_27A" in f.message


def test_night_uplift_missing_and_despite_zone_cap(case):
    a = _mis(case, "A.12.020", 10, "2025-03-03", "34.80", night=True)                   # 18% omitted in Z1
    b = case.line("PA-1", "A.12.020", 10, d("2025-03-04"), zone="Z3 Wadi Crossing", night=True, rate="47.02", amount=47020)  # 34.80 x 1.145 x 1.18
    run = case.run()
    assert "night_flag_inverted" in _finding(run, a).message
    assert "night_uplift_despite_27A_zone_cap" in _finding(run, b).message


def test_rest_day_uplift_omitted(case):
    ref = _mis(case, "D.41.030", 10, "2025-03-07", "90.38")                              # Friday; indexed 90.38 x 1.35 = 122.01
    f = _finding(case.run(), ref)
    assert f.expected == "122.01" and "rest_day_uplift_omitted" in f.message


def test_superseded_amendment_rate(case):
    ref = _mis(case, "E.54.010", 1, "2025-10-01", "876.00")                              # A1 948.00 from 2025-10-01
    f = _finding(case.run(), ref)
    assert f.expected == "948.00" and "as_if_A1_not_in_force" in f.message


def test_amendment_boundary_day_before_is_clean(case):
    _mis(case, "E.54.010", 1, "2025-09-30", "876.00")
    assert case.run().findings == ()


def test_discount_omitted(case):
    # Submitted 2025-12-12, before A3 (issued 2026-05-12): the rate then in force is 1860.00 (31A); S2 5% from 2025-12-01.
    ref = _mis(case, "C.32.010", 1, "2025-12-02", "1860.00")
    f = _finding(case.run(), ref)
    assert f.category == "discount_incorrectly_applied" and f.expected == "1767.00" and "discount_omitted" in f.message


def test_rebate_band_omitted(case):
    case.app("PA-1", d("2025-03-20"))
    case.line("PA-1", "B.23.010", 60, d("2025-03-03"), record=case.record("JS-00001", "fixed 60 tonne of bar, cut and bent to schedule", d("2025-03-03")))
    ref = case.line("PA-1", "B.23.010", 5, d("2025-03-04"), record=case.record("JS-00002", "fixed 5 tonne of bar, cut and bent to schedule", d("2025-03-04")),
                    rate="4120.00", amount=2060000)                                         # all in the 97% band, billed at 100%
    f = _finding(case.run(), ref)
    assert f.category == "rebate_incorrectly_applied" and f.expected == "3996.40"


def test_band_split_line_is_judged_on_amount_only(case):
    case.app("PA-1", d("2025-03-20"))
    case.line("PA-1", "B.23.010", 58, d("2025-03-03"), record=case.record("JS-00001", "fixed 58 tonne of bar, cut and bent to schedule", d("2025-03-03")))
    # 4 tonnes crossing the 60 t edge: 2 x 4120.00 + 2 x 3996.40 = 16232.80; printed at the pre-rebate rate.
    ref = case.line("PA-1", "B.23.010", 4, d("2025-03-04"), record=case.record("JS-00002", "fixed 4 tonne of bar, cut and bent to schedule", d("2025-03-04")),
                    rate="4120.00", amount=1623280)
    assert case.run().findings == ()
    case.lines[-1]["amount_cents"] = 1648000                                                 # whole line at 100%
    f = _finding(case.run(), ref)
    assert f.rule == "rates.band_split_amount" and f.category == "rebate_incorrectly_applied" and f.impact_cents == 24720


def test_line_arithmetic_and_rate_on_one_line(case):
    case.app("PA-1", d("2025-03-20"))
    ref = case.line("PA-1", "A.11.010", 100, d("2025-03-03"), rate="4.00", amount=40500)
    run = case.run()
    assert categories(run, ref) == ["line_total_arithmetic", "unit_rate_mismatch"]
    arith, rate = sorted((f for f in run.findings if f.line_ref == ref), key=lambda f: f.category)
    assert arith.impact_cents == 500 and rate.impact_cents == 1500                           # 405.00 billed = 400 + 5; contract 385
    assert arith.impact_cents + rate.impact_cents == 40500 - run.lines[ref].contract_payable.amount_cents


def test_application_total_and_net(case):
    case.app("PA-1", d("2025-03-20"), total=99999, net=1)
    case.line("PA-1", "A.11.010", 5, d("2025-03-03"))
    run = case.run()
    assert [f.rule for f in run.findings] == ["arithmetic.header_total", "arithmetic.net_payable"]   # retention is 5% of the stated total
    header, net = run.findings
    assert header.affects_total and header.impact_cents == 99999 - 1925
    assert net.outside_total and not net.affects_total


def test_retention_incorrect(case):
    case.app("PA-1", d("2025-03-20"), retention=1)
    case.line("PA-1", "A.11.010", 500, d("2025-03-03"))
    [f] = case.run().findings
    assert f.category == "retention_incorrect" and f.expected == "96.25"


def test_retro_adjustment_missing_and_incorrect(case):
    case.app("PA-1", d("2025-12-10")).app("PA-2", d("2026-05-14")).app("PA-3", d("2026-06-01"), adjustment=500)
    case.line("PA-1", "C.32.010", 2, d("2025-11-20"))                                         # valued at 1860 before A3
    case.line("PA-2", "A.11.010", 1, d("2026-05-01"))
    case.line("PA-3", "A.11.010", 1, d("2026-05-20"))
    run = case.run()
    assert [(f.invoice_id, f.category) for f in run.findings] == [("PA-2", "adjustment_missing"), ("PA-3", "adjustment_incorrectly_applied")]
    assert run.findings[0].expected == "248.00" and all(f.outside_total and not f.affects_total for f in run.findings)


def test_retention_release_after_completion(case):
    case.app("PA-1", d("2026-09-20")).app("PA-2", d("2026-10-05"))
    case.line("PA-1", "A.11.010", 1000, d("2026-09-10"))
    case.line("PA-2", "A.11.010", 10, d("2026-09-29"))
    [f] = case.run().findings
    assert (f.invoice_id, f.category, f.expected) == ("PA-2", "adjustment_missing", "96.25")   # half of 192.50 retention on PA-1
