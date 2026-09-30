"""Rebate-band ledger: edges, crossings, and both counting readings."""

from datetime import date
from decimal import Decimal

import pytest

from contractor_audit.domains.civil_works.contract import Band
from contractor_audit.domains.civil_works.contract_period import ContractPeriod
from contractor_audit.domains.civil_works.interpretation import RebateCounting
from contractor_audit.domains.civil_works.pricing import LineContext, PricingEngine
from contractor_audit.domains.civil_works.rebates import RebateLedger, band_edges, band_order_key

D = Decimal


def ledger(terms, counting=RebateCounting.CONTRACT_YEAR):
    return RebateLedger(terms, counting, ContractPeriod(terms))


def test_band_edges_read_as_cumulative_intervals(terms):
    edges = band_edges("A.12.010", terms.bands["A.12.010"])
    assert [(e.lower, e.upper, e.percent_of_rate) for e in edges] == [(0, 4000, 100), (4000, 16000, 96), (16000, None, 93)]


def test_malformed_bands_are_rejected():
    with pytest.raises(ValueError):
        band_edges("X", (Band("1 to 10", 1, 10, None, D(100)), Band("12 to 20", 12, 20, None, D(96))))


def test_exact_edge_then_first_unit_of_next_band(terms):
    lg = ledger(terms)
    a = lg.allocate("A.12.010", date(2025, 2, 1), D(4000))
    assert [(s.quantity, s.percent_of_rate) for s in a.slices] == [(4000, 100)] and a.volume_after == 4000
    b = lg.allocate("A.12.010", date(2025, 2, 2), D(1))
    assert [(s.quantity, s.percent_of_rate) for s in b.slices] == [(1, 96)] and b.volume_before == 4000


def test_one_measurement_crossing_two_edges(terms):
    lg = ledger(terms)
    lg.allocate("B.23.010", date(2025, 2, 1), D(50))
    a = lg.allocate("B.23.010", date(2025, 2, 2), D(200))                    # 50 -> 250 crosses 60 and 240
    assert [(s.quantity, s.percent_of_rate, s.cumulative_from, s.cumulative_to) for s in a.slices] == [
        (10, 100, 50, 60), (180, 97, 60, 240), (10, 94, 240, 250)]
    assert a.crosses_band_edge


def test_split_line_prices_each_part_at_its_own_rounded_rate(terms):
    lg = ledger(terms)
    lg.allocate("A.12.010", date(2025, 2, 1), D(3900))
    alloc = lg.allocate("A.12.010", date(2025, 2, 3), D(300))
    price = PricingEngine(terms).price(LineContext("A.12.010", date(2025, 2, 3), "Z1 Compound", "S-01 Platform North"), D(300), alloc)
    assert [(p.quantity, p.rate, p.amount_cents) for p in price.parts] == [(100, D("21.50"), 215000), (200, D("20.64"), 412800)]
    assert price.amount_cents == 627800 and price.is_split


def test_contract_year_reset_versus_whole_works(terms):
    cy, ww = ledger(terms), ledger(terms, RebateCounting.WHOLE_WORKS)
    for lg in (cy, ww):
        lg.allocate("D.41.040", date(2025, 12, 1), D(3500))                  # fills the first band in Contract Year 1
    a = cy.allocate("D.41.040", date(2026, 1, 5), D(10))                     # first day of Contract Year 2
    b = ww.allocate("D.41.040", date(2026, 1, 5), D(10))
    assert (a.period_key, a.volume_before, a.slices[0].percent_of_rate) == ("contract_year_2", 0, 100)
    assert (b.period_key, b.volume_before, b.slices[0].percent_of_rate) == ("whole_works", 3500, 95)
    c = cy.allocate("D.41.040", date(2026, 1, 4), D(1))                      # last day of Contract Year 1
    assert (c.period_key, c.volume_before, c.slices[0].percent_of_rate) == ("contract_year_1", 3500, 95)


def test_work_after_final_completion_counts_in_final_year_with_a_note(terms):
    a = ledger(terms).allocate("A.12.010", date(2026, 10, 10), D(5))
    assert a.period_key == "contract_year_2" and a.notes


def test_zero_quantity_and_negative(terms):
    lg = ledger(terms)
    z = lg.allocate("A.12.010", date(2025, 2, 1), D(0))
    assert z.slices[0].quantity == 0 and z.volume_after == 0
    with pytest.raises(ValueError):
        lg.allocate("A.12.010", date(2025, 2, 1), D(-1))


def test_counters_are_per_item(terms):
    lg = ledger(terms)
    lg.allocate("A.12.010", date(2025, 2, 1), D(5000))
    assert lg.allocate("A.12.020", date(2025, 2, 1), D(1)).volume_before == 0


def test_order_key_is_date_then_application_then_line():
    keys = [band_order_key(date(2025, 3, 2), "PA-00002", 1), band_order_key(date(2025, 3, 1), "PA-00009", 5),
            band_order_key(date(2025, 3, 2), "PA-00001", 7), band_order_key(date(2025, 3, 2), "PA-00001", 2)]
    assert sorted(keys) == [keys[1], keys[3], keys[2], keys[0]]


def test_non_banded_item(terms):
    assert not ledger(terms).is_banded("A.11.010") and ledger(terms).is_banded("D.41.010")
