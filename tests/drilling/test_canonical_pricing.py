"""Canonical pricing under the approved readings, with AMB-13 approved as UNKNOWN / UNVERIFIED."""

import json
from collections import Counter

import pytest

from contractor_audit.domains.drilling.pricing.engine import price
from contractor_audit.domains.drilling.pricing.models import PricingStatus
from contractor_audit.domains.drilling.pricing.selection import APPROVED_FILENAME, Source, build_selection, load_approved
from contractor_audit.domains.drilling.reporting.phase4_canonical_pricing import digest, summary
from contractor_audit.shared import paths

ART = paths.artifacts_dir("drilling")
CLASS_RATED = {"DD-120", "MW-310", "MW-320", "LW-410", "LW-411", "LW-412", "LW-413"}
NEEDS_CALLOFF = CLASS_RATED | {"PD-210", "PD-201"}
PD201_CONDITIONAL_CENTS = 531170166


@pytest.fixture(scope="module")
def canonical(interpretation, terms, switches):
    return price(interpretation, terms, switches, build_selection(switches, load_approved(ART / APPROVED_FILENAME, switches)))


def test_the_result_is_canonical(canonical):
    assert canonical.canonical and canonical.hypothetical_switches == ()
    assert all(src in ("APPROVED", "CONTRACT_TEXT") for _, _, src in canonical.selection)


def test_coverage(canonical):
    status = Counter(p.status for p in canonical.priced)
    assert status == {PricingStatus.PRICED: 61995, PricingStatus.NOT_CHARGEABLE: 3189, PricingStatus.EVIDENCE_NOT_PROVIDED: 31316}
    assert PricingStatus.UNPRICEABLE not in status


def test_only_what_needs_the_call_off_is_left_unresolved(canonical):
    missing = [p for p in canonical.priced if p.status is PricingStatus.EVIDENCE_NOT_PROVIDED]
    assert {p.service_code for p in missing} == NEEDS_CALLOFF
    assert all("AMB-13" in p.reason and p.amount_cents == 0 for p in missing)
    pd210 = [p for p in missing if p.service_code == "PD-210"]
    assert all("performance-drilled section not established" in p.reason for p in pd210)
    # everything else is priced (or clearly not chargeable) without any well class
    unaffected = [p for p in canonical.priced if p.service_code not in NEEDS_CALLOFF]
    assert {p.status for p in unaffected} <= {PricingStatus.PRICED, PricingStatus.NOT_CHARGEABLE}
    assert all(p.status is PricingStatus.PRICED for p in canonical.priced if p.service_code == "DD-101")


def test_the_invoice_claimed_class_is_never_used_canonically(canonical, interpretation, terms, switches, dataset):
    claimed = {i.well_name: i.well_class_stated for i in dataset.invoices}
    again = price(interpretation, terms, switches, build_selection(switches, load_approved(ART / APPROVED_FILENAME, switches)), claimed)
    assert digest(again) == digest(canonical)
    assert not any("WELL_CLASS_FROM_INVOICE" in f for p in canonical.priced for f in p.flags)


def test_pd201_eligibility_is_not_established_but_its_rate_is_kept_as_conditional(canonical):
    pd201 = [p for p in canonical.priced if p.service_code == "PD-201"]
    assert len(pd201) == 2561
    for p in pd201:
        assert p.status is PricingStatus.EVIDENCE_NOT_PROVIDED and p.amount_cents == 0
        assert p.reason.startswith("PD-201 eligibility not established: the call-off is not provided")
        assert ("calloff_evidence", "UNVERIFIABLE_QUERY", "APPROVED") in p.readings_used
        assert any(f.startswith("ELIGIBILITY_UNVERIFIED_CALLOFF") for f in p.flags)
        # the calculated rate and the report evidence are preserved
        assert p.parts and p.parts[0].steps and p.parts[0].rate_cents > 0
        assert p.conditional_amount_cents == p.parts[0].amount_cents > 0
        assert p.evidence and all(ref.report_id in p.report_ids for ref in p.evidence)
    assert sum(p.conditional_amount_cents for p in pd201) == PD201_CONDITIONAL_CENTS
    # conditional amounts never reach a canonical total
    assert canonical.total_cents() == sum(p.amount_cents for p in canonical.priced if p.status is PricingStatus.PRICED)
    assert canonical.total_cents({"PD-201"}) == 0


@pytest.mark.parametrize("claims", ["claimed", "Standard", "Extended Reach", "HPHT", "none"])
def test_invoice_claims_cannot_make_pd201_canonically_payable(canonical, interpretation, terms, switches, dataset, claims):
    # whatever the invoices claim, the canonical run is the same: pricing reads no invoice, and the claimed class is ignored
    wells = {q.well for q in interpretation.quantities} | {i.well_name for i in dataset.invoices}
    mapping = ({i.well_name: i.well_class_stated for i in dataset.invoices} if claims == "claimed"
               else {} if claims == "none" else {w: claims for w in wells})
    approved = load_approved(ART / APPROVED_FILENAME, switches)
    again = price(interpretation, terms, switches, build_selection(switches, approved), mapping, {"PD-201"})
    assert again.canonical and again.total_cents() == 0
    assert all(p.status is PricingStatus.EVIDENCE_NOT_PROVIDED for p in again.priced)


def test_only_a_hypothetical_reading_prices_pd201_and_it_is_never_canonical(interpretation, terms, switches, dataset):
    approved = load_approved(ART / APPROVED_FILENAME, switches)
    with pytest.raises(ValueError, match="may not replace"):
        build_selection(switches, approved, {"calloff_evidence": "INVOICE_STATEMENT_UNVERIFIED"})
    claimed = {i.well_name: i.well_class_stated for i in dataset.invoices}
    sel = build_selection(switches, approved).with_choice("calloff_evidence", "INVOICE_STATEMENT_UNVERIFIED", Source.HYPOTHETICAL)
    hypothetical = price(interpretation, terms, switches, sel, claimed, {"PD-201"})
    assert not hypothetical.canonical and hypothetical.total_cents() == PD201_CONDITIONAL_CENTS
    with pytest.raises(ValueError, match="not canonical"):
        summary(hypothetical)


def test_pd201_evidence_is_report_evidence_only(canonical):
    for p in canonical.priced:
        if p.service_code == "PD-201":
            assert all(ref.section in ("HEADER", "A", "B", "C", "D", "E") and "/records/" in ref.source_file.replace("\\", "/")
                       for ref in p.evidence)


def test_approved_readings_shape_the_price(canonical):
    for p in canonical.priced:
        used = {s: v for s, v, _ in p.readings_used}
        if p.service_code == "RM-530" and p.status is PricingStatus.PRICED:
            assert used["rig_up_hour"] == "PER_BHA_RUN"
        if p.service_code in ("MW-310", "HC-620") and p.status is PricingStatus.PRICED:
            assert used["rig_services_index"] == "APPLY_FROM_FIRST_MONTH"
    hc620 = next(p for p in canonical.priced if p.service_code == "HC-620" and p.status is PricingStatus.PRICED)
    assert [s.name for s in hc620.parts[0].steps][:2] == ["rate", "index"]


def test_committed_canonical_artifact_matches(canonical):
    data = json.loads((ART / "phase4_canonical_pricing.json").read_text(encoding="utf-8"))
    assert data["canonical"] is True and data["priced_quantities_sha256"] == digest(canonical)
    assert data["by_status"] == {"EVIDENCE_NOT_PROVIDED": 31316, "NOT_CHARGEABLE": 3189, "PRICED": 61995}
    assert data["priced_total_cents"] == canonical.total_cents() == 14742686878
    assert data["by_service"]["PD-201"] == {"EVIDENCE_NOT_PROVIDED": 2561, "amount_cents": 0}
    [row] = data["conditional_not_payable"]["rows"]
    assert row["service"] == "PD-201" and row["count"] == 2561 and row["conditional_amount_cents"] == PD201_CONDITIONAL_CENTS
    assert "ELIGIBILITY_UNVERIFIED_CALLOFF" not in data["flags_on_priced_quantities"]


def test_class_sensitivity_shows_every_possible_class_without_choosing():
    data = json.loads((ART / "phase4_pricing_sensitivity.json").read_text(encoding="utf-8"))
    scenarios = {s["scenario"]: s["total_cents"] for s in data["well_class"]["scenarios"]}
    assert set(scenarios) == {"every well Standard", "every well Extended Reach", "every well HPHT", "contractor's claimed class (unverified)"}
    assert scenarios["every well Standard"] < scenarios["every well Extended Reach"] < scenarios["every well HPHT"]
    assert set(data["well_class"]["class_rated_services"]) == CLASS_RATED
    pd201 = data["well_class"]["pd201_if_eligibility_were_established"]
    assert pd201["quantities"] == 2561 and pd201["total_cents"] == PD201_CONDITIONAL_CENTS
