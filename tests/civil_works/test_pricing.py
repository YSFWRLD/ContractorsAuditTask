"""Clause 27 build-up: each component, each interpretation switch, and the trace."""

from datetime import date
from decimal import Decimal

import pytest

from contractor_audit.domains.civil_works.interpretation import (WORKING_INTERPRETATION as W, ConcurrentUplifts,
                                                                 ConversionRounding, DiscountInteraction,
                                                                 IndexedRateMethod, MonthlyRateTreatment, NightZoneCap,
                                                                 PostCompletionGround, UsdReading)
from contractor_audit.domains.civil_works.pricing import LineContext, PricingEngine
from contractor_audit.domains.civil_works.rates import PricingError
from contractor_audit.domains.civil_works.rounding import (amount_to_cents, round_built_up_rate, round_converted_rate,
                                                           round_down_to_halala)

D = Decimal
Z = {"Z1": "Z1 Compound", "Z2": "Z2 North Spur", "Z3": "Z3 Wadi Crossing", "Z4": "Z4 Escarpment"}


def rate(terms, code, day, zone="Z1", area="S-01 Platform North", ground=None, night=False, interp=W, **kw):
    ctx = LineContext(code, date.fromisoformat(day), Z[zone], area, ground, night, **kw)
    return PricingEngine(terms, interp).price(ctx, D(1)).unit_rate


# --------------------------------------------------------------------------- rounding policy

def test_rounding_policy_is_explicit():
    assert round_built_up_rate(D("10.005")) == D("10.01")          # Clause 28: half up
    assert round_converted_rate(D("10.005")) == D("10.00")         # 26A / 29A: half even
    assert round_converted_rate(D("10.015")) == D("10.02")
    assert round_down_to_halala(D("789.7299")) == D("789.72")      # 45: down
    assert amount_to_cents(D("48") * D("91.37")) == 438576


# --------------------------------------------------------------------------- Appendix B worked example

def test_appendix_b_lines_reproduced(terms):
    assert rate(terms, "A.12.020", "2025-05-06", "Z2", ground="G4 Weathered Rock") == D("50.72")
    assert rate(terms, "A.14.020", "2025-05-07", "Z2", ground="G2 Firm Sabkha") == D("23.74")


def test_indexed_rate_both_readings_c31010_may_2025(terms):
    """29A: 86.20 x 102.60/100 = 88.4412 -> 88.44; x 1.06 = 93.7464 -> 93.75. Appendix B prints 91.37."""
    assert rate(terms, "C.31.010", "2025-05-13", "Z2", ground="G2 Firm Sabkha") == D("93.75")
    unindexed = W.with_(indexed_rate_method=IndexedRateMethod.APPENDIX_B_UNINDEXED)
    assert rate(terms, "C.31.010", "2025-05-13", "Z2", ground="G2 Firm Sabkha", interp=unindexed) == D("91.37")


def test_indexed_rate_uses_the_month_of_execution(terms):
    assert rate(terms, "D.41.030", "2025-01-29") == D("89.40")      # SMI 100.00 (a Wednesday)
    assert rate(terms, "D.41.030", "2025-01-31") == D("120.69")     # Friday: rest-day uplift 89.40 x 1.35
    assert rate(terms, "D.41.030", "2026-02-01") == D("98.52")      # 89.40 x 110.20 / 100 = 98.5188 -> 98.52


# --------------------------------------------------------------------------- USD

@pytest.mark.parametrize("code, day, usd_expected, sar_expected", [
    ("B.23.020", "2025-01-15", "144.00", "38.40"),    # 38.40 x 375.00/100
    ("B.25.010", "2025-04-30", "821.03", "219.00"),   # 219.00 x 374.90/100 = 821.031 -> 821.03
    ("B.25.010", "2025-05-01", "821.69", "219.00"),   # 219.00 x 375.20/100 = 821.688 -> 821.69
    ("C.32.040", "2026-12-01", "1592.60", "423.00"),  # 423.00 x 376.50/100 = 1592.595 -> 1592.60 (half-even: 9 odd -> up)
])
def test_usd_both_readings(terms, code, day, usd_expected, sar_expected):
    assert rate(terms, code, day) == D(usd_expected)
    assert rate(terms, code, day, interp=W.with_(usd_reading=UsdReading.SAR_AS_PRINTED)) == D(sar_expected)


def test_conversion_rounding_switch(terms):
    # 423.00 x 376.50 / 100 = 1592.595; rounded half-even 1592.60; unrounded -> x1.28 (Z4) = 2038.5216 -> 2038.52 vs 1592.60 x 1.28 = 2038.528 -> 2038.53
    assert rate(terms, "C.32.040", "2026-12-01", "Z4") == D("2038.53")
    assert rate(terms, "C.32.040", "2026-12-01", "Z4", interp=W.with_(conversion_rounding=ConversionRounding.UNROUNDED_INTO_BUILD_UP)) == D("2038.52")


def test_missing_month_refuses(terms):
    with pytest.raises(PricingError):
        rate(terms, "B.23.020", "2027-01-05")


# --------------------------------------------------------------------------- zone

@pytest.mark.parametrize("zone, expected", [("Z1", "3.85"), ("Z2", "4.08"), ("Z3", "4.41"), ("Z4", "4.93")])
def test_zone_factors_series_a(terms, zone, expected):
    assert rate(terms, "A.11.010", "2025-02-02", zone) == D(expected)   # 3.85 x 1.06 = 4.081; x 1.145 = 4.40825; x 1.28 = 4.928


@pytest.mark.parametrize("zone", ["Z1", "Z2", "Z3", "Z4"])
def test_series_e_never_takes_a_zone_factor(terms, zone):
    assert rate(terms, "E.51.020", "2025-02-02", zone) == D("684.00")


def test_unknown_zone_refuses(terms):
    with pytest.raises(PricingError):
        PricingEngine(terms).price(LineContext("A.11.010", date(2025, 2, 2), "Z9 Nowhere", "S-01 Platform North"), D(1))


# --------------------------------------------------------------------------- ground

@pytest.mark.parametrize("ground, expected", [("G1 Loose Sand", "32.71"), ("G2 Firm Sabkha", "34.80"), ("G3 Cemented Fill", "38.98"),
                                              ("G4 Weathered Rock", "47.85"), ("G5 Sound Rock", "56.72")])
def test_ground_factors_before_27a(terms, ground, expected):
    assert rate(terms, "A.12.020", "2025-09-27", ground=ground) == D(expected)


def test_ground_ignored_for_unlisted_items(terms):
    assert rate(terms, "A.11.010", "2025-02-02", ground="G5 Sound Rock") == D("3.85")


def test_missing_ground_is_datum(terms):
    assert rate(terms, "A.12.020", "2025-02-02") == D("34.80")


def test_27a_post_completion_ground_readings(terms):
    common = dict(day="2025-09-28", ground="G5 Sound Rock")
    assert rate(terms, "A.12.020", **common) == D("34.80")                                                    # datum_g2_all_work
    rec = W.with_(post_completion_ground=PostCompletionGround.RECORDED_CLASS)
    assert rate(terms, "A.12.020", **common, interp=rec) == D("56.72")
    eot = W.with_(post_completion_ground=PostCompletionGround.DATUM_G2_EOT_AREAS_ONLY)
    assert rate(terms, "A.12.020", **common, interp=eot, area="S-04 Drainage Corridor") == D("34.80")
    assert rate(terms, "A.12.020", **common, interp=eot, area="S-01 Platform North") == D("56.72")


# --------------------------------------------------------------------------- uplifts

def test_night_uplift_and_27a_zone_cap(terms):
    # 2025-02-03 is a Monday.
    assert rate(terms, "A.12.030", "2025-02-03", "Z1", night=True) == D("56.17")        # 47.60 x 1.18 = 56.168
    assert rate(terms, "A.12.030", "2025-02-03", "Z2", night=True) == D("59.54")        # 47.60 x 1.06 x 1.18 = 59.538
    assert rate(terms, "A.12.030", "2025-02-03", "Z3", night=True) == D("54.50")        # cap: 47.60 x 1.145 = 54.502
    off = W.with_(night_zone_cap=NightZoneCap.NOT_APPLIED)
    assert rate(terms, "A.12.030", "2025-02-03", "Z3", night=True, interp=off) == D("64.31")   # 54.502 x 1.18 = 64.312
    assert rate(terms, "A.11.010", "2025-02-03", night=True) == D("3.85")                # not a Part 1 item


def test_rest_day_uplift_on_friday_and_saturday_only(terms):
    assert rate(terms, "B.21.030", "2025-03-06") == D("389.00")      # Thursday
    assert rate(terms, "B.21.030", "2025-03-07") == D("525.15")      # Friday: x 1.35
    assert rate(terms, "B.21.030", "2025-03-08") == D("525.15")      # Saturday
    assert rate(terms, "A.12.030", "2025-03-07") == D("47.60")       # not a Part 2 item


def test_concurrent_uplifts_need_an_instruction(terms):
    sat = "2025-03-08"
    assert rate(terms, "B.21.030", sat, night=True) == D("525.15")                                      # P11: rest-day alone
    both = W.with_(concurrent_uplifts=ConcurrentUplifts.BOTH_ASSUMED_INSTRUCTED)
    assert rate(terms, "B.21.030", sat, night=True, interp=both) == D("640.68")                         # 389 x 1.22 x 1.35 = 640.683
    assert rate(terms, "B.21.030", sat, night=True, engineer_instruction_both_uplifts=True) == D("640.68")


# --------------------------------------------------------------------------- monthly rates, discounts

def test_monthly_rate_treatment(terms):
    assert rate(terms, "D.41.020", "2025-07-15", "Z2", night=True) == D("299.98")                     # 226.40 x 1.06 x 1.25
    final = W.with_(monthly_rate_treatment=MonthlyRateTreatment.FINAL_RATE)
    assert rate(terms, "D.41.020", "2025-07-15", "Z2", night=True, interp=final) == D("226.40")
    # E.54.010 is Series E with no uplift, band or discount: both readings agree.
    assert rate(terms, "E.54.010", "2026-06-10", "Z4") == rate(terms, "E.54.010", "2026-06-10", "Z4", interp=final) == D("1013.00")


@pytest.mark.parametrize("day, expected", [("2025-11-30", "1984.00"), ("2025-12-01", "1884.80"), ("2026-03-31", "1884.80"), ("2026-04-01", "1825.28")])
def test_discount_timeline_c32010(terms, day, expected):
    assert rate(terms, "C.32.010", day) == D(expected)          # 1984 x 0.95 = 1884.80; x 0.92 = 1825.28


def test_discount_stacking_switch(terms):
    comp = W.with_(discount_interaction=DiscountInteraction.COMPOUND)
    assert rate(terms, "C.32.010", "2026-04-01", interp=comp) == D("1734.02")     # 1984 x 0.95 x 0.92 = 1734.016
    assert rate(terms, "C.32.010", "2026-03-31", interp=comp) == D("1884.80")     # only S2 in effect


def test_discount_applies_after_band_before_rounding(terms):
    from contractor_audit.domains.civil_works.contract_period import ContractPeriod
    from contractor_audit.domains.civil_works.rebates import RebateLedger
    ledger = RebateLedger(terms, W.rebate_counting, ContractPeriod(terms))
    ledger.allocate("B.23.010", date(2026, 4, 1), D(100))                         # into the 97% band
    alloc = ledger.allocate("B.23.010", date(2026, 4, 2), D(1))
    price = PricingEngine(terms).price(LineContext("B.23.010", date(2026, 4, 2), "Z1 Compound", "S-01 Platform North"), D(1), alloc)
    assert price.parts[0].rate == D("3971.18")                                    # 4450 x 0.97 x 0.92 = 3971.18
    rules = [s.rule for s in price.trace]
    assert rules.index("rebate_band") < rules.index("discount") < rules.index("rounding")


# --------------------------------------------------------------------------- trace and exactness

def test_every_trace_step_has_a_source_and_result(terms):
    price = PricingEngine(terms).price(LineContext("C.31.010", date(2025, 5, 13), "Z2 North Spur", "S-03 Access Road", "G2 Firm Sabkha", True), D(48))
    assert price.trace and all(s.source and s.result is not None and s.rule for s in price.trace)
    assert [s.rule for s in price.trace][:3] == ["rate_in_force", "indexation", "zone_factor"]
    assert any(s.interpretation and "indexed_rate_method" in s.interpretation for s in price.trace)


def test_prices_are_decimal_and_integer_cents(terms):
    price = PricingEngine(terms).price(LineContext("B.23.020", date(2025, 6, 10), "Z3 Wadi Crossing", "S-02 Platform South"), D(100))
    assert isinstance(price.amount_cents, int)
    for part in price.parts:
        assert isinstance(part.rate, Decimal) and isinstance(part.unrounded_rate, Decimal) and isinstance(part.amount_cents, int)


def test_no_binary_float_in_pricing_code():
    """No float literals, float() or built-in round() anywhere in the civil works money path."""
    import ast
    from pathlib import Path
    import contractor_audit.domains.civil_works as cw
    root = Path(cw.__file__).parent
    for name in ("rates.py", "pricing.py", "rebates.py", "valuation.py", "rounding.py", "quantity_rules.py",
                 "record_quantities.py", "contract.py", "contract_period.py", "loaders.py"):
        for node in ast.walk(ast.parse((root / name).read_text(encoding="utf-8"))):
            assert not (isinstance(node, ast.Constant) and isinstance(node.value, float)), f"{name}: float literal"
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ("float", "round"), f"{name}: {node.func.id}()"
