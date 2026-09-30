"""The pricing engine: explicit selections, the contract's rounding and build-up, full provenance, no invoices."""

import ast
import inspect
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

import contractor_audit.domains.drilling as drilling
from contractor_audit.domains.drilling.ingestion.reports import parse_report_text
from contractor_audit.domains.drilling.interpretation.engine import interpret
from contractor_audit.domains.drilling.pricing.build_up import DayContext, Unpriceable, build_up
from contractor_audit.domains.drilling.pricing.engine import price
from contractor_audit.domains.drilling.pricing.models import PricingStatus
from contractor_audit.domains.drilling.pricing.rates import resolve
from contractor_audit.domains.drilling.pricing.rounding import half_even_cents
from contractor_audit.domains.drilling.pricing.selection import (
    APPROVED_FILENAME, PRICING_SWITCHES, Choice, MissingSelectionError, Selection, Source, build_selection, load_approved,
)
from contractor_audit.domains.drilling.pricing.tiers import split_by_tiers
from contractor_audit.shared import paths

ART = paths.artifacts_dir("drilling")


@pytest.fixture(scope="module")
def approved(switches):
    return load_approved(ART / APPROVED_FILENAME, switches)


def full(switches, approved, **overrides):
    """The canonical selection, with the given readings replaced hypothetically (for tests and sensitivity only)."""
    sel = build_selection(switches, approved)
    for name, value in overrides.items():
        sel = sel.with_choice(name, value, Source.HYPOTHETICAL)
    return sel


# --------------------------------------------------------------------------- selections
def test_pricing_refuses_to_start_without_every_required_reading(interpretation, terms, switches, approved):
    complete = build_selection(switches, approved)
    for name in ("rig_up_hour", "pd210_class_factor", "volume_tier_scope", "calloff_evidence", "dd120_hours"):
        partial = Selection({n: c for n, c in complete.choices.items() if n != name})
        with pytest.raises(MissingSelectionError, match=name):
            price(interpretation, terms, switches, partial)


def test_approvals_are_recorded_and_cannot_be_overridden(switches, approved):
    assert {n: c.value for n, c in approved.items()} == {
        "appendix_g_reading": "LITERAL", "dd121_condition": "STANDBY_DAY_RSS_IN_HOLE", "metre_source": "DAILY_DEPTH_ADVANCE",
        "dd102_basis": "PER_COORDINATOR_RECORDED", "hc630_basis": "DAILY_COUNT", "lih_hours": "PART_E_STATED",
        "unranked_precedence": "NO_RANK_CASE_BY_CASE", "pd210_class_factor": "DO_NOT_APPLY", "standby_section_factor": "OMIT",
        "rig_services_index": "APPLY_FROM_FIRST_MONTH", "rig_up_hour": "PER_DAY_THEN_MINIMUM", "dd120_hours": "CIRCULATING_ONLY",
        "dd120_rate_from_feb_2026": "LATER_ISSUED_GOVERNS", "monthly_rate_basis": "BASE_RATE_THEN_BUILD_UP", "volume_tier_scope": "PER_WELL",
        "contract_year_2": "STARTS_2026_01_01", "lih_replacement_value": "SCHEDULE_2D_CONVERTED", "ds900_threshold_basis": "SERVICES_ONLY",
        "calloff_evidence": "UNVERIFIABLE_QUERY",
        # audit-phase decisions (prompts/drilling/08): AMB-12, 14, 15, 23 approved; AMB-25 EVIDENCE_NOT_PROVIDED
        "backdated_adjustment": "CONTRACT_WIDE_ON_OR_AFTER", "record_signatories": "DDR_SIGNATURES_COVER_PARTS",
        "report_vocabulary": "RIG_WORDS_VALID", "missing_record_consequence": "PART_REJECT", "submission_date": "UNKNOWN_QUERY"}
    with pytest.raises(ValueError, match="may not replace"):
        build_selection(switches, approved, {"metre_source": "PART_B_RUN_METRES"})
    assert build_selection(switches, approved).canonical
    assert not full(switches, approved, rig_up_hour="NO_DEDUCTION").canonical


def test_well_classes_must_be_supplied_when_the_invoice_statement_is_selected(interpretation, terms, switches, approved):
    with pytest.raises(ValueError, match="well classes"):
        price(interpretation, terms, switches, full(switches, approved, calloff_evidence="INVOICE_STATEMENT_UNVERIFIED"))


def test_every_pricing_switch_is_approved_or_text_resolved(switches, approved):
    sel = build_selection(switches, approved)
    assert all(sel.choices[n].source in (Source.APPROVED, Source.CONTRACT_TEXT) for n in PRICING_SWITCHES)
    assert Selection({n: Choice(n, c.value, Source.APPROVED) for n, c in sel.choices.items()}).canonical


# --------------------------------------------------------------------------- the contract's own worked invoice
APPB = """DAILY DRILLING REPORT
Report: DDR-900-{ymd}
Contract: DDS-2025-118
Well: NGP-XX-900
Rig: NG-Rig 99
Date: {dmy}

PART A — OPERATIONS SUMMARY
Hole section: 12-1/4"
Status: {status}
Depth start (m MD): {start}
Depth end (m MD): {end}
Circulating hours: {hours}
BHA run: 4
In the hole: MWD collar, rotary steerable
Crew on tour: 2 directional hands
Gyro surveys: 0
Pressure points: 0
Wiper trips: 0
Back-reaming hours: 0
Clean-out runs: 0

PART B — BHA RUN RECORD
Run: 4
Run first day: 03-Jun-2025
Run last day: 04-Jun-2025
Tools in run: MWD collar, rotary steerable
Run circulating hours: 18
Metres logged: 0
Metres reamed: 0
Radioactive source carried: No

Signed (Company Representative): A
Signed (lead directional driller): B
"""


@pytest.fixture(scope="module")
def appendix_b(terms, ambiguities):
    reports = [parse_report_text(APPB.format(ymd="20250603", dmy="03-Jun-2025", status="Standby", start=2930, end=2930, hours=0), "b1.txt"),
               parse_report_text(APPB.format(ymd="20250604", dmy="04-Jun-2025", status="Operating", start=2930, end=3085, hours=18), "b2.txt")]
    return interpret(reports, terms, ambiguities)


def _amounts(result, code, day):
    return [p for p in result.priced if p.service_code == code and p.date == day]


def test_appendix_b_is_reproduced_under_the_readings_it_implies(appendix_b, terms, switches, approved):
    sel = full(switches, approved, rig_services_index="NOT_APPLIED", rig_up_hour="NO_DEDUCTION", pd210_class_factor="DO_NOT_APPLY",
               calloff_evidence="INVOICE_STATEMENT_UNVERIFIED")
    r = price(appendix_b, terms, switches, sel, {"NGP-XX-900": "HPHT"})
    (dd101,) = _amounts(r, "DD-101", date(2025, 6, 3))
    assert (dd101.chargeable_quantity, dd101.parts[0].rate_cents, dd101.amount_cents) == (2, 147788, 295576)
    (mw310,) = _amounts(r, "MW-310", date(2025, 6, 4))
    assert (mw310.parts[0].rate_cents, mw310.amount_cents) == (297575, 297575)
    (dd120,) = _amounts(r, "DD-120", date(2025, 6, 4))
    assert (dd120.chargeable_quantity, dd120.parts[0].rate_cents, dd120.amount_cents) == (18, 50900, 916200)
    pd210 = sorted((p for p in _amounts(r, "PD-210", date(2025, 6, 4))), key=lambda p: p.parts[0].rate_cents)
    assert [(p.chargeable_quantity, p.parts[0].rate_cents, p.amount_cents) for p in pd210] == [(70, 5815, 407050), (85, 7645, 649825)]
    assert sum(p.amount_cents for p in (dd101, mw310, dd120, *pd210)) == 2566226   # Appendix B net amount
    assert all("ELIGIBILITY_UNVERIFIED_CALLOFF (AMB-13)" in p.flags for p in pd210)


def test_appendix_b_contradictions_are_measurable_not_hidden(appendix_b, terms, switches, approved):
    sel = full(switches, approved, rig_services_index="APPLY_FROM_FIRST_MONTH", rig_up_hour="PER_DAY_THEN_MINIMUM",
               pd210_class_factor="APPLY", calloff_evidence="INVOICE_STATEMENT_UNVERIFIED")
    r = price(appendix_b, terms, switches, sel, {"NGP-XX-900": "HPHT"})
    assert _amounts(r, "MW-310", date(2025, 6, 4))[0].parts[0].rate_cents == 308288      # 17A index 103.60 (AMB-04)
    assert _amounts(r, "DD-120", date(2025, 6, 4))[0].chargeable_quantity == 17           # 21A rig-up hour (AMB-05)
    assert sorted(p.parts[0].rate_cents for p in _amounts(r, "PD-210", date(2025, 6, 4))) == [7705, 10130]  # class factor (AMB-02)


# --------------------------------------------------------------------------- components
def test_rounding_is_half_even_to_the_cent():
    assert half_even_cents(Decimal("297575.125")) == 297575
    assert half_even_cents(Decimal("6172.5")) == 6172 and half_even_cents(Decimal("6173.5")) == 6174


def test_rate_resolution_under_each_reading(terms):
    may = date(2026, 5, 10)
    assert resolve(terms, "DD-120", may, "LATER_ISSUED_GOVERNS").source == "A3"
    assert resolve(terms, "DD-120", may, "LATER_EFFECTIVE_GOVERNS").rate_cents == 41150
    assert resolve(terms, "DD-120", may, "MONTHLY_TABLE_SEPARATE").month == "2026-05"
    for reading in ("LATER_ISSUED_GOVERNS", "LATER_EFFECTIVE_GOVERNS", "MONTHLY_TABLE_SEPARATE"):
        assert resolve(terms, "DD-101", date(2026, 3, 1), reading).rate_cents == 195400
        assert resolve(terms, "HC-601", date(2026, 3, 1), reading).rate_cents == 73640   # last published rate carried forward
    assert resolve(terms, "DD-101", date(2026, 3, 1), "LATER_ISSUED_GOVERNS", frozenset({"A3"})).rate_cents == 191650
    assert resolve(terms, "PD-210", date(2026, 3, 1), "LATER_ISSUED_GOVERNS") is None


def test_principal_discount_combination(terms, switches, approved):
    rate = resolve(terms, "DD-101", date(2026, 8, 1), "LATER_ISSUED_GOVERNS")
    day = DayContext(date(2026, 8, 1), "Operating", '8-1/2"', "Standard")
    replaces = build_up(terms, terms.services["DD-101"], rate, day, full(switches, approved))[1]
    cumulative = build_up(terms, terms.services["DD-101"], rate, day,
                          Selection({**full(switches, approved).choices, "principal_discount_combination": Choice("principal_discount_combination", "CUMULATIVE", Source.HYPOTHETICAL)}))[1]
    assert replaces == half_even_cents(Decimal(195400) * Decimal("0.93"))
    assert cumulative == half_even_cents(Decimal(half_even_cents(Decimal(195400) * Decimal("0.96"))) * Decimal("0.93"))


def test_missing_inputs_make_a_quantity_unpriceable(terms, switches, approved):
    sel = full(switches, approved, rig_services_index="APPLY_FROM_FIRST_MONTH")
    rate = resolve(terms, "MW-310", date(2027, 1, 5), "LATER_ISSUED_GOVERNS")
    with pytest.raises(Unpriceable, match="Index"):
        build_up(terms, terms.services["MW-310"], rate, DayContext(date(2027, 1, 5), "Operating", '6"', "Standard"), sel)
    with pytest.raises(Unpriceable, match="well class"):
        build_up(terms, terms.services["MW-320"], resolve(terms, "MW-320", date(2025, 3, 1), "LATER_ISSUED_GOVERNS"),
                 DayContext(date(2025, 3, 1), "Operating", '6"', None), sel)


def test_tier_split(terms):
    assert split_by_tiers(terms, 39990, 20) == [(10, Decimal("100"), 1), (10, Decimal("96"), 2)]
    assert split_by_tiers(terms, 0, 5) == [(5, Decimal("100"), 1)]
    assert split_by_tiers(terms, 119995, 10) == [(5, Decimal("96"), 2), (5, Decimal("92"), 3)]


# --------------------------------------------------------------------------- the real data
@pytest.fixture(scope="module")
def priced(interpretation, terms, switches, approved, dataset):
    classes = {i.well_name: i.well_class_stated for i in dataset.invoices}
    return price(interpretation, terms, switches, full(switches, approved, calloff_evidence="INVOICE_STATEMENT_UNVERIFIED"), classes)


def test_every_priced_quantity_keeps_the_full_chain(priced, interpretation):
    by_qid = {q.qid: q for q in interpretation.quantities}
    assert not priced.canonical
    for p in priced.priced:
        assert p.qid in by_qid and p.evidence == by_qid[p.qid].evidence
        if p.status is not PricingStatus.PRICED:
            assert p.amount_cents == 0 and p.reason
            continue
        assert p.amount_cents == sum(part.amount_cents for part in p.parts)
        for part in p.parts:
            steps = part.steps
            assert steps[-1].output_cents == part.rate_cents                 # the rate charged is the last step's rounded output
            if not p.service_code.startswith("LH-"):
                assert steps[0].name == "rate" and steps[0].output_cents == part.rate.rate_cents
            for a, b in zip(steps, steps[1:]):
                assert b.input_cents == a.output_cents                       # each step starts from the previous rounded result
            assert part.amount_cents == half_even_cents(part.quantity * part.rate_cents)
        assert all(src in ("APPROVED", "CONTRACT_TEXT", "HYPOTHETICAL") for _, _, src in p.readings_used)


def test_contract_clear_exclusions(priced):
    status = {}
    for p in priced.priced:
        status.setdefault((p.service_code, p.status.value), 0)
        status[(p.service_code, p.status.value)] += 1
    assert status[("DD-120", "NOT_CHARGEABLE")] == 184          # Standby days: DD-120 not charged (cl. 21)
    assert status[("HC-640", "NOT_CHARGEABLE")] == 115          # not chargeable on Standby (Schedule 3 Part 3)
    assert status[("PD-210", "NOT_CHARGEABLE")] == 2890         # sizes Appendix A does not allow
    assert not any(p.status is PricingStatus.UNPRICEABLE for p in priced.priced)


def test_daily_limits_and_hours(priced):
    for p in priced.priced:
        if p.service_code == "DD-101":
            assert p.chargeable_quantity <= 2
        if p.service_code == "DD-120" and p.status is PricingStatus.PRICED:
            assert p.chargeable_quantity >= 6


def test_retroactive_amendment_keeps_both_figures(priced):
    a3 = [p for p in priced.priced if p.parts and p.parts[0].rate.source == "A3"]
    assert a3 and all(p.amount_without_retroactive_cents is not None for p in a3)
    # DD-101 has no monthly table, so the rate before A3 (A1's 1,916.50) is always lower. DD-120 is not asserted:
    # without A3, Supplement No. 2's monthly rates apply from April 2026, and from July they exceed A3's 416.00.
    dd101 = [p for p in a3 if p.service_code == "DD-101" and p.status is PricingStatus.PRICED]
    assert dd101 and all(p.amount_without_retroactive_cents < p.amount_cents for p in dd101)
    assert any(p.amount_without_retroactive_cents > p.amount_cents for p in a3 if p.service_code == "DD-120")


def test_lost_in_hole_valuation(priced, terms):
    lih = [p for p in priced.priced if p.service_code.startswith("LH-")]
    assert len(lih) == 54
    p = lih[0]
    convert, depreciation = p.parts[0].steps
    fx = terms.lost_in_hole.fx_halalas_per_usd[p.date.strftime("%Y-%m")]
    assert convert.output_cents == half_even_cents(Decimal(terms.lost_in_hole.replacement_sar_halalas[p.service_code]) / fx * 100)
    assert depreciation.input_cents == convert.output_cents


# --------------------------------------------------------------------------- boundaries
def test_pricing_never_reads_invoices_or_audits():
    root = Path(drilling.__file__).parent / "pricing"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        mods = {n.module for n in ast.walk(ast.parse(text)) if isinstance(n, ast.ImportFrom)}
        assert not any(m and (".ingestion" in m or ".reporting" in m or ".audit" in m or m.endswith(".findings")) for m in mods), path.name
        for token in ("InvoiceLine", "DrillingInvoice", "invoice_total", "net_cents", "billed"):
            assert token not in text, f"{path.name} mentions {token}"
    assert list(inspect.signature(price).parameters) == ["result", "terms", "switches", "selection", "well_classes", "services"]


def test_sensitivity_is_hypothetical_and_nothing_is_audited_or_submitted():
    import json
    data = json.loads((ART / "phase4_pricing_sensitivity.json").read_text(encoding="utf-8"))
    assert data["reference_canonical"] is True and "HYPOTHETICAL" in data["note"]
    assert {r["background"] for r in data["switches"]} == {"canonical", "claimed_class"}
    flipped = {(r["switch"], r["alternative"]) for r in data["switches"]}
    assert ("rig_up_hour", "PER_BHA_RUN") in flipped and ("volume_tier_scope", "CONTRACT_WIDE") in flipped
    assert not (paths.REPO_ROOT / "outputs" / "submission.csv").exists()
    names = {p.name for p in ART.iterdir()}
    assert not {n for n in names if "finding" in n or "submission" in n or "audit" in n}


def test_decision_record_covers_every_decided_ambiguity():
    import json
    record = json.loads((ART / "approved_readings.json").read_text(encoding="utf-8"))
    assert record["unresolved"] == []
    table = (ART / "phase4_decision_table.md").read_text(encoding="utf-8")
    for amb in record["decided_in_phase4"]:
        assert f"## {amb} " in table
    assert "UNKNOWN / UNVERIFIED" in table
    recs = json.loads((ART / "phase4_recommendations.json").read_text(encoding="utf-8"))
    assert {r["ambiguity"] for r in recs["recommendations"]} == set(record["decided_in_phase4"])
