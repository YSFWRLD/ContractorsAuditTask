"""The reviewed contract model: schema, money, dates, catalog and the effective-date structure."""

import copy
from datetime import date
from decimal import Decimal

import pytest

from contractor_audit.domains.drilling.contract.loader import (
    TERMS_KEYS, ContractTermsError, load_raw, validate_terms,
)
from contractor_audit.domains.drilling.contract.models import RateBasis, StandbyTreatment, StatementKind
from contractor_audit.shared import paths

TERMS_PATH = paths.artifacts_dir("drilling") / "contract_terms.json"


# --------------------------------------------------------------------------- schema and money
def test_artifact_loads_with_a_versioned_schema_and_every_top_level_section(raw_terms, terms):
    assert (raw_terms["schema"], raw_terms["schema_version"]) == ("contractor-audit/drilling-contract-terms", "1.0")
    assert all(k in raw_terms for k in TERMS_KEYS)
    assert validate_terms(raw_terms) == []
    assert terms.contract_ref == "DDS-2025-118" and terms.currency == "USD" and terms.vat_percent == Decimal("15")


def test_duplicate_service_codes_are_rejected(raw_terms):
    raw = copy.deepcopy(raw_terms)
    raw["services"].append(copy.deepcopy(raw["services"][0]))
    assert any("duplicate service codes" in p for p in validate_terms(raw))


def test_money_is_integer_minor_units_and_a_float_anywhere_is_rejected(raw_terms, tmp_path):
    raw = copy.deepcopy(raw_terms)
    raw["services"][0]["rate"]["base_rate_cents"] = 1847.35
    assert any("integer minor units" in p for p in validate_terms(raw))
    text = TERMS_PATH.read_text(encoding="utf-8").replace('"threshold_cents": 25000000', '"threshold_cents": 250000.00', 1)
    (tmp_path / "t.json").write_text(text, encoding="utf-8")
    with pytest.raises(ContractTermsError, match="float literal"):
        load_raw(tmp_path / "t.json")


def test_every_monetary_field_is_an_int(raw_terms):
    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k.endswith(("_cents", "_halalas")) and v is not None:
                    assert isinstance(v, int) and not isinstance(v, bool), k
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(raw_terms)


def test_every_material_term_has_provenance(raw_terms):
    for s in raw_terms["services"]:
        assert s["provenance"] and all(p["page"] and p["source_text"] for p in s["provenance"]), s["code"]
    for section in ("invoice_discount", "cost_build_up", "depth_bands", "volume_tiers", "price_index", "lost_in_hole", "appendix_g", "records"):
        assert raw_terms[section]["provenance"], section
    for ins in raw_terms["instruments"]:
        assert ins["provenance"] and all(ch["provenance"] for ch in ins["changes"]), ins["id"]
    for key, value in raw_terms["identity"].items():
        if isinstance(value, dict) and "value" in value:
            assert value["provenance"], key


# --------------------------------------------------------------------------- dates
def test_term_dates_and_the_extension_chain(terms, raw_terms):
    assert terms.commencement == date(2025, 1, 1)
    assert terms.original_expiry == date(2025, 12, 31)
    assert [(e.instrument_id, e.new_expiry, e.extension_days) for e in terms.extensions] == [
        ("A1", date(2026, 6, 30), 181), ("A2", date(2026, 12, 31), 184)]
    assert terms.final_expiry == date(2026, 12, 31)
    assert raw_terms["identity"]["final_expiry"]["value"] == "2026-12-31"


def test_issue_and_effective_dates_are_kept_separately_and_a3_is_retroactive(terms):
    dates = {i.id: (i.issued, i.effective, i.retroactive) for i in terms.instruments}
    assert dates == {
        "S1": (date(2025, 5, 19), date(2025, 7, 1), False),
        "A1": (date(2025, 11, 7), date(2026, 1, 1), False),
        "S2": (date(2026, 2, 24), date(2026, 4, 1), False),
        "A2": (date(2026, 5, 21), date(2026, 7, 1), False),
        "A3": (date(2026, 8, 17), date(2026, 2, 1), True),
    }
    assert [i.id for i in terms.instruments] == ["S1", "A1", "S2", "A2", "A3"]  # the order issued


def test_contract_years_record_the_contested_second_year(terms):
    y1, y2 = terms.contract_years
    assert (y1.start, y1.end, y1.status.value) == (date(2025, 1, 1), date(2025, 12, 31), "STATED")
    assert (y2.start, y2.end, y2.status.value, y2.ambiguities) == (date(2026, 1, 1), date(2026, 12, 31), "AMBIGUOUS", ("AMB-11",))


# --------------------------------------------------------------------------- catalog
def test_schedule_1_has_38_services_and_ds900_is_the_separate_clause_38_discount(terms, raw_terms):
    assert len(terms.services) == 38
    assert "DS-900" not in terms.services
    assert raw_terms["invoice_discount"]["code"] == "DS-900" and raw_terms["invoice_discount"]["in_schedule_1"] is False
    series = {}
    for s in terms.services.values():
        series[s.series] = series.get(s.series, 0) + 1
    assert series == {100: 8, 200: 4, 300: 4, 400: 7, 500: 4, 600: 5, 700: 6}


def test_unit_bases_and_rate_bases(terms):
    assert {s.unit for s in terms.services.values()} == {"person-day", "day", "run", "hour", "survey", "well", "metre", "point", "trip", "each"}
    assert terms.services["PD-210"].rate_basis is RateBasis.SCHEDULE_2
    assert {c for c, s in terms.services.items() if s.rate_basis is RateBasis.CLAUSE_31} == {"LH-711", "LH-712", "LH-713", "LH-714"}
    assert terms.services["DD-101"].base_rate_cents == 184735 and terms.services["MB-701"].base_rate_cents == 1849750


def test_factor_tables_and_standby_treatments(terms):
    assert terms.section_factors == {'26"': Decimal("1.315"), '17-1/2"': Decimal("1.145"), '12-1/4"': Decimal("1.00"),
                                     '8-1/2"': Decimal("0.945"), '6"': Decimal("0.885")}
    assert terms.class_factors == {"Standard": Decimal("1.00"), "Extended Reach": Decimal("1.175"), "HPHT": Decimal("1.325")}
    assert {c for c, s in terms.services.items() if s.section_rated} == {"DD-110", "DD-120", "PD-220", "MW-310", "RM-510", "RM-511"}
    assert {c for c, s in terms.services.items() if s.class_rated} == {"DD-120", "PD-210", "MW-310", "MW-320", "LW-410", "LW-411", "LW-412", "LW-413"}
    treatments = {}
    for c, s in terms.services.items():
        treatments.setdefault(s.standby.treatment, set()).add(c)
    assert treatments[StandbyTreatment.STANDBY_ONLY] == {"DD-121"}
    assert treatments[StandbyTreatment.FULL_WHATEVER_STATUS] == {"DD-140", "LW-430", "MB-701", "MB-702", "LH-711", "LH-712", "LH-713", "LH-714"}
    assert len(treatments[StandbyTreatment.NOT_CHARGEABLE]) == 12 and len(treatments[StandbyTreatment.PERCENT]) == 17


def test_depth_bands_tiers_index_and_lost_in_hole_tables(terms):
    assert [(b.over_m, b.to_m, b.rate_cents) for b in terms.depth_bands] == [(0, 1500, 4235), (1500, 3000, 5815), (3000, 4500, 7645), (4500, None, 9870)]
    assert [(t.from_m, t.to_m, t.percent_of_rate) for t in terms.volume_tiers] == [(1, 40000, Decimal("100")), (40001, 120000, Decimal("96")), (120001, None, Decimal("92"))]
    assert terms.price_index.base_rates_cents == {"MW-310": 224585, "HC-620": 53965}
    assert len(terms.price_index.monthly) == 24 and terms.price_index.monthly["2025-06"] == Decimal("103.60")
    lih = terms.lost_in_hole
    assert lih.replacement_sar_halalas["LH-712"] == 468750000 and lih.replacement_usd_cents_as_let["LH-712"] == 125000000
    assert len(lih.fx_halalas_per_usd) == 24 and (lih.depreciation_block_hours, lih.depreciation_cap_percent) == (25, Decimal("50"))
    assert (terms.invoice_discount.threshold_cents, terms.invoice_discount.comparison, terms.invoice_discount.percent) == (25000000, "GREATER_THAN", Decimal("4"))


# --------------------------------------------------------------------------- effective-date structure
def test_amended_services_keep_their_whole_rate_history(terms):
    history = [(st.source, st.kind, st.rate_cents, st.effective) for st in terms.rate_statements("DD-120") if st.kind is not StatementKind.MONTHLY]
    assert history == [("SCHEDULE_1", StatementKind.SCHEDULE_1, 38415, date(2025, 1, 1)),
                       ("S1", StatementKind.SUBSTITUTION, 39850, date(2025, 7, 1)),
                       ("A3", StatementKind.SUBSTITUTION, 41600, date(2026, 2, 1))]
    monthly = [st for st in terms.rate_statements("DD-120") if st.kind is StatementKind.MONTHLY]
    assert [m.month for m in monthly] == [f"2026-{m:02d}" for m in range(4, 13)] and monthly[0].rate_cents == 40600
    assert [st.rate_cents for st in terms.rate_statements("DD-101")] == [184735, 191650, 195400]


def test_statements_on_a_date_list_every_candidate_without_choosing(terms):
    def on(code, d):
        return [(s.source, s.rate_cents, s.carried_forward) for s in terms.rate_statements_on(code, d)]
    assert on("DD-120", date(2025, 6, 30)) == [("SCHEDULE_1", 38415, False)]
    assert on("DD-120", date(2025, 7, 1)) == [("SCHEDULE_1", 38415, False), ("S1", 39850, False)]
    # From April 2026 both A3 (issued last) and the S2 monthly table speak to DD-120: both are returned (AMB-07).
    assert on("DD-120", date(2026, 4, 10)) == [("SCHEDULE_1", 38415, False), ("S1", 39850, False), ("A3", 41600, False), ("S2", 40600, False)]
    # HC-601 after December 2025 carries the last published rate forward.
    assert on("HC-601", date(2026, 3, 3))[-1] == ("S1", 73640, True)
    assert [d.percent for d in terms.discounts_on("DD-120", date(2026, 8, 1))] == [Decimal("4"), Decimal("7")]
    assert terms.discounts_on("DD-120", date(2026, 3, 31)) == ()


def test_no_instrument_adds_or_removes_a_service_and_the_model_can_say_so(terms):
    assert all(i.added_services == () and i.removed_services == () for i in terms.instruments)
    referenced = {s.code for i in terms.instruments for s in i.substitutions} | {m.code for i in terms.instruments for m in i.monthly_rates} \
        | {c for i in terms.instruments for d in i.discounts for c in d.codes}
    assert referenced <= set(terms.services)


def test_substitution_chain_is_internally_consistent(raw_terms):
    raw = copy.deepcopy(raw_terms)
    a3 = next(i for i in raw["instruments"] if i["id"] == "A3")
    a3["changes"][0]["previous_rate_cents"] = 38415
    assert any("previous rate" in p for p in validate_terms(raw))


# --------------------------------------------------------------------------- the contract's own examples reconcile as transcribed
def test_worked_examples_reconcile_as_printed(raw_terms):
    b = raw_terms["worked_examples"]["appendix_b"]
    assert sum(line["amount_cents"] for line in b["lines"]) == b["net_cents"] == 2566226
    assert b["net_cents"] + b["vat_cents"] == b["total_cents"]
    assert all(line["quantity"] * line["rate_cents"] == line["amount_cents"] for line in b["lines"])
    ex = raw_terms["worked_examples"]["clause_38"]
    assert (ex["services_total_cents"] - raw_terms["invoice_discount"]["threshold_cents"]) * 4 // 100 == -ex["discount_cents"]
    assert 412 // 25 == int(raw_terms["worked_examples"]["appendix_f"]["depreciation_percent"])


def test_schedule_6_equals_schedule_2d_at_the_rate_when_let(terms):
    lih = terms.lost_in_hole
    rate = lih.fx_halalas_per_usd["2025-01"]
    for code, halalas in lih.replacement_sar_halalas.items():
        assert Decimal(halalas) / rate * 100 == lih.replacement_usd_cents_as_let[code]
