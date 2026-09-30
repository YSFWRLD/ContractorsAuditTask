"""Rate-in-force resolver: every instrument boundary (day before / on / after) and the precedence rule."""

import dataclasses
from datetime import date, timedelta
from decimal import Decimal

import pytest

from contractor_audit.domains.civil_works.contract import RateSubstitution
from contractor_audit.domains.civil_works.rates import PricingError, RateKind, RateResolver

D = Decimal


@pytest.fixture(scope="module")
def resolver(terms):
    return RateResolver(terms)


def _around(day: str):
    d = date.fromisoformat(day)
    return d - timedelta(1), d, d + timedelta(1)


@pytest.mark.parametrize("code, boundary, before, on_and_after, source", [
    ("B.23.010", "2025-05-01", "4120.00", "4385.00", "S1"),
    ("B.21.020", "2025-05-01", "415.00", "431.50", "S1"),
    ("A.16.010", "2025-05-01", "1480.00", "1524.00", "S1"),
    ("B.23.010", "2025-10-01", "4385.00", "4450.00", "A1"),
    ("E.54.010", "2025-10-01", "876.00", "948.00", "A1"),
    ("C.32.010", "2025-11-01", "1860.00", "1984.00", "A3"),
    ("A.14.010", "2025-11-01", "53.20", "56.80", "A3"),
    ("D.41.020", "2025-12-01", "220.50", "228.00", "S2"),
])
def test_substitution_boundaries(resolver, code, boundary, before, on_and_after, source):
    prev, on, nxt = _around(boundary)
    assert resolver.resolve(code, prev).rate_in_force == D(before)
    for d in (on, nxt):
        r = resolver.resolve(code, d)
        assert r.rate_in_force == D(on_and_after) and r.source_instrument == source


def test_a1_instrument_date_differs_from_its_rate_dates(resolver):
    # A1 takes effect 2025-09-28 but states 2025-10-01 against each substituted rate.
    for d in (date(2025, 9, 27), date(2025, 9, 28), date(2025, 9, 30)):
        assert resolver.resolve("E.54.010", d).rate_in_force == D("876.00")
        assert resolver.resolve("B.23.010", d).rate_in_force == D("4385.00")


def test_d41020_monthly_rates_and_carry_forward(resolver):
    assert resolver.resolve("D.41.020", date(2025, 4, 30)).rate_in_force == D("63.50")        # Schedule 1
    cases = {date(2025, 5, 1): "214.50", date(2025, 6, 30): "219.80", date(2025, 7, 1): "226.40",
             date(2025, 8, 15): "223.10", date(2025, 9, 30): "220.50",
             date(2025, 10, 15): "220.50", date(2025, 11, 30): "220.50"}                       # last published carries
    for d, rate in cases.items():
        r = resolver.resolve("D.41.020", d)
        assert r.rate_in_force == D(rate) and r.kind is RateKind.MONTHLY
    assert resolver.resolve("D.41.020", date(2026, 6, 1)).rate_in_force == D("228.00")       # S2 still governs


def test_e54010_monthly_from_april_2026(resolver):
    prev, on, nxt = _around("2026-04-01")
    assert resolver.resolve("E.54.010", prev).rate_in_force == D("948.00")
    assert resolver.resolve("E.54.010", on).rate_in_force == D("976.00")
    assert resolver.resolve("E.54.010", date(2026, 8, 1)).rate_in_force == D("1038.00")
    assert resolver.resolve("E.54.010", date(2026, 9, 30)).rate_in_force == D("1052.00")
    assert resolver.resolve("E.54.010", date(2026, 10, 26)).rate_in_force == D("1052.00")    # last published carries


def test_unchanged_items_keep_schedule_1_rate(resolver):
    for d in (date(2025, 1, 5), date(2026, 9, 30)):
        r = resolver.resolve("A.11.010", d)
        assert r.rate_in_force == D("3.85") and r.source_instrument == "BOQ"


def test_before_commencement_and_unknown_item_refuse(resolver):
    with pytest.raises(PricingError):
        resolver.resolve("A.11.010", date(2025, 1, 4))
    with pytest.raises(PricingError):
        resolver.resolve("Z.99.999", date(2025, 6, 1))


def test_backdated_a3_depends_on_what_was_known(resolver):
    work = date(2025, 11, 15)
    assert resolver.resolve("C.32.010", work).rate_in_force == D("1984.00")                           # everything known
    assert resolver.resolve("C.32.010", work, date(2026, 5, 11)).rate_in_force == D("1860.00")       # before issue
    assert resolver.resolve("C.32.010", work, date(2026, 5, 12)).rate_in_force == D("1984.00")       # on issue, 31A
    assert resolver.resolve("C.32.010", work, date(2026, 5, 12), include_issued_on_known_at=False).rate_in_force == D("1860.00")
    assert resolver.resolve("C.32.010", work, date(2026, 5, 13), include_issued_on_known_at=False).rate_in_force == D("1984.00")
    assert resolver.resolve("C.32.010", date(2025, 10, 31), date(2026, 6, 1)).rate_in_force == D("1860.00")  # before A3 effective


def test_issue_date_and_effective_date_are_separate(terms):
    a3 = next(i for i in terms.instruments if i.id == "A3")
    assert a3.issued != a3.effective and a3.issued > a3.effective


def test_later_issued_instrument_governs_even_with_an_earlier_effective_date(terms):
    """Synthetic: a later-issued instrument backdated before an earlier one's effective date still governs from its own date."""
    s1 = next(i for i in terms.instruments if i.id == "S1")
    late = dataclasses.replace(terms.instruments[-1], id="X9", issued=date(2026, 7, 1), effective=date(2025, 4, 1),
                               rate_substitutions=(RateSubstitution("X9", "B.23.010", "tonne", D("4120.00"), D("4000.00"), date(2025, 4, 1)),))
    r = RateResolver(dataclasses.replace(terms, instruments=terms.instruments + (late,)))
    assert r.resolve("B.23.010", date(2025, 6, 1)).source_instrument == "X9"          # X9 issued after S1
    assert r.resolve("B.23.010", date(2025, 6, 1), date(2026, 6, 30)).source_instrument == s1.id   # X9 not yet issued


def test_resolution_trace_names_its_sources(resolver):
    r = resolver.resolve("B.23.010", date(2025, 10, 1))
    assert r.trace[0].source.startswith("Schedule of Variations")
    assert "A1" in r.trace[0].calculation and "later-issued governs" in r.trace[0].calculation
    assert [p.instrument_id for p in r.considered] == ["BOQ", "S1", "A1"]
