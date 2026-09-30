"""The reviewed contract extraction: schema, provenance, and a few values pinned independently of the JSON."""

import copy
from datetime import date
from decimal import Decimal

import pytest

from contractor_audit.domains.civil_works.contract import (CONTRACT_PAGE_COUNT, ContractExtractionError, iter_provenance,
                                                           terms_from_raw, validate_extraction)
from contractor_audit.shared.provenance import sha256_file


def test_extraction_is_valid(raw_extraction):
    assert validate_extraction(raw_extraction) == []


def test_every_provenance_node_is_complete(raw_extraction):
    nodes = list(iter_provenance(raw_extraction))
    assert len(nodes) > 400
    for path, node in nodes:
        assert 1 <= node["source_page"] <= CONTRACT_PAGE_COUNT, path
        assert node["source_section"] and node["source_text"], path
        assert node["review_status"] in raw_extraction["status_definitions"], path


def test_pdf_fingerprint_matches_extraction(raw_extraction, cw_sources):
    assert sha256_file(cw_sources.contract_pdf) == raw_extraction["source_document"]["sha256"]


def test_nothing_marked_unreadable(raw_extraction):
    statuses = {n["review_status"] for _, n in iter_provenance(raw_extraction)}
    assert "UNREADABLE" not in statuses
    assert raw_extraction["unreadable"] == []


def test_boq_has_sixty_unique_items_across_five_series(terms):
    assert len(terms.boq) == 60
    assert {i.series for i in terms.boq.values()} == set("ABCDE")
    assert all(i.provenance.page in (17, 18, 19) and i.provenance.passes == 2 for i in terms.boq.values())


# Values re-read from the scan for this test, deliberately not copied from the JSON.
@pytest.mark.parametrize("code, unit, rate", [
    ("A.11.010", "m2", "3.85"), ("A.16.010", "week", "1480.00"), ("B.23.010", "tonne", "4120.00"),
    ("C.32.030", "no.", "3120.00"), ("D.41.020", "m2", "63.50"), ("E.54.010", "week", "876.00"),
])
def test_pinned_boq_values(terms, code, unit, rate):
    assert terms.boq[code].unit == unit
    assert terms.boq[code].base_rate == Decimal(rate)


def test_factors_and_uplifts(terms):
    assert terms.zone_factors == {"Z1 Compound": Decimal("1"), "Z2 North Spur": Decimal("1.06"),
                                  "Z3 Wadi Crossing": Decimal("1.145"), "Z4 Escarpment": Decimal("1.28")}
    assert terms.zone_factor_series == frozenset("ABCD")
    assert terms.ground_factors["G4 Weathered Rock"] == Decimal("1.375")
    assert terms.ground_factors["G2 Firm Sabkha"] == Decimal("1")
    assert len(terms.ground_factor_items) == 15
    assert len(terms.night_uplift_percent) == 13 and terms.night_uplift_percent["D.43.020"] == Decimal("25")
    assert set(terms.rest_day_uplift_percent) == {"B.21.020", "B.21.030", "B.21.040", "D.41.030"}


def test_limits_bands_records(terms):
    assert terms.daily_limits["E.53.010"].limit == Decimal("2")
    assert len(terms.bands) == 8 and all(len(b) == 3 for b in terms.bands.values())
    top = terms.bands["B.23.010"][-1]
    assert (top.above, top.percent_of_rate) == (240, Decimal("94"))
    assert terms.exclusions[0].excluded_item == "A.14.020" and terms.exclusions[0].period_days == 2
    assert terms.surveyed_items == frozenset({"B.23.010", "B.23.020", "E.52.010"})
    assert len(terms.required_records) == 17
    assert terms.required_records["A.16.010"].reference_series == "DW"
    assert terms.week_minimum_days == 5


def test_indexed_and_usd_tables_cover_every_month(terms):
    months = {f"{y}-{m:02d}" for y in (2025, 2026) for m in range(1, 13)}
    assert set(terms.site_materials_index) == months
    assert set(terms.fx_halalas_per_usd) == months
    assert terms.index_base == Decimal("100.00")
    assert terms.usd_items == {"B.23.020": Decimal("38.40"), "B.25.010": Decimal("219.00"), "C.32.040": Decimal("423.00")}


def test_instruments_and_timeline(terms):
    assert [i.id for i in terms.instruments] == ["S1", "A1", "S2", "A2", "A3"]   # order issued
    a3 = terms.instruments[-1]
    assert a3.retroactive and a3.effective == date(2025, 11, 1) and a3.issued == date(2026, 5, 12)
    assert all(i.effective >= i.issued for i in terms.instruments if not i.retroactive)
    assert terms.completion_date == date(2026, 9, 30)
    a1 = terms.instruments[1]
    assert a1.effective == date(2025, 9, 28)
    assert {s.effective for s in a1.rate_substitutions} == {date(2025, 10, 1)}
    assert [d.percent for d in (terms.instruments[2].discount, terms.instruments[3].discount)] == [Decimal("5"), Decimal("8")]
    assert [(y.start, y.end) for y in terms.contract_years] == [(date(2025, 1, 5), date(2026, 1, 4)), (date(2026, 1, 5), date(2026, 9, 30))]


def test_ambiguities_keep_every_reading(terms):
    assert {"AMB-BANDS", "AMB-A3-ADJUSTMENT", "AMB-MISSING-RECORD", "AMB-INDEX-APPENDIX-B"} <= {a.id for a in terms.ambiguities}
    assert all(a.readings and a.status != "VERIFIED" for a in terms.ambiguities)


# --------------------------------------------------------------------------- validator catches bad extractions

def _first_boq_item(raw):
    return raw["schedule_1"]["items"][0]


@pytest.mark.parametrize("mutate, expected", [
    (lambda r: _first_boq_item(r).pop("source_page"), "missing source_page"),
    (lambda r: _first_boq_item(r).update(source_page=44), "outside 1..43"),
    (lambda r: _first_boq_item(r).update(review_status="LOOKS_OK"), "review_status"),
    (lambda r: _first_boq_item(r).update(review_passes=1), "single pass"),
    (lambda r: _first_boq_item(r).update(source_text=" "), "empty source_text"),
    (lambda r: r["schedule_5"]["items"][0].update(code="Z.99.999"), "not in Schedule 1"),
    (lambda r: r["schedule_1"]["items"].append(dict(r["schedule_1"]["items"][0])), "duplicate item codes"),
    (lambda r: r["ambiguities"][0].update(readings=[]), "no readings"),
    (lambda r: r.pop("instruments"), "missing top-level key"),
])
def test_validator_rejects(raw_extraction, mutate, expected):
    broken = copy.deepcopy(raw_extraction)
    mutate(broken)
    problems = validate_extraction(broken)
    assert any(expected in p for p in problems), problems
    with pytest.raises(ContractExtractionError):
        terms_from_raw(broken)
