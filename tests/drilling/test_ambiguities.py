"""The ambiguity register keeps contested readings apart instead of collapsing them."""

import copy

from contractor_audit.domains.drilling.contract.loader import validate_ambiguities
from contractor_audit.domains.drilling.contract.models import AmbiguityStatus


def test_register_is_valid_and_ids_are_unique(raw_ambiguities, ambiguities):
    assert validate_ambiguities(raw_ambiguities) == []
    assert len(ambiguities) == len(raw_ambiguities["ambiguities"]) == 27
    for a in ambiguities.values():
        assert len(a.readings) >= 2 and a.pages and a.issue and a.resolve_in_phase


def test_every_ambiguity_cited_by_the_terms_is_registered(terms, ambiguities):
    assert terms.ambiguity_refs and terms.ambiguity_refs <= set(ambiguities)


def test_every_reading_with_evidence_cites_a_page_and_text(raw_ambiguities):
    for a in raw_ambiguities["ambiguities"]:
        for r in a["readings"]:
            for e in r["evidence"]:
                assert e["page"] and e["source_text"], (a["id"], r["id"])


def _open(ambiguities, amb_id):
    a = ambiguities[amb_id]
    assert a.status in (AmbiguityStatus.OPEN, AmbiguityStatus.EVIDENCE_NOT_PROVIDED), amb_id
    return a


def test_pd210_class_factor_conflict_is_preserved(ambiguities, terms, raw_terms):
    a = _open(ambiguities, "AMB-02")
    assert a.preferred_reading is None and {r.id for r in a.readings} == {"A", "B"}
    assert {e.page for r in a.readings for e in r.evidence} >= {17, 20, 35, 30}
    assert terms.services["PD-210"].class_rated  # as printed in Schedule 3 Part 2 ...
    assert any(x["clause"] == "17B" and "PD-210" in x["rule"] for x in raw_terms["cost_build_up"]["exclusions"])  # ... and 17B kept too


def test_contract_year_volume_scope_is_not_decided(ambiguities, raw_terms):
    a = _open(ambiguities, "AMB-10")
    assert a.preferred_reading is None
    assert raw_terms["volume_tiers"]["status"] == "AMBIGUOUS"


def test_backdated_adjustment_placement_keeps_every_reading(ambiguities):
    a = _open(ambiguities, "AMB-12")
    texts = " ".join(e.source_text for r in a.readings for e in r.evidence)
    assert "on or after the date of issue" in texts and "submitted after the date of issue" in texts
    assert len(a.readings) >= 3 and a.preferred_reading is None


def test_missing_call_offs_are_evidence_not_provided(ambiguities, raw_terms):
    a = ambiguities["AMB-13"]
    assert a.status is AmbiguityStatus.EVIDENCE_NOT_PROVIDED
    assert {"PD-210", "PD-201"} <= set(a.services)
    assert any(e["id"] == "NP-01" and "call-off" in e["item"].lower() for e in raw_terms["evidence_not_provided"])


def test_unranked_material_is_an_open_precedence_question(ambiguities, raw_terms):
    a = _open(ambiguities, "AMB-01")
    assert a.preferred_reading is None
    assert set(raw_terms["precedence"]["unranked_documents"]) >= {"PART-VIII", "PART-IX", "SCH-2C", "SCH-2D", "SCH-7", "SCH-8",
                                                                   "APP-D", "APP-E", "APP-F", "APP-G", "SOV"}


def test_other_pinned_contradictions_stay_open(ambiguities):
    for amb_id in ("AMB-03", "AMB-04", "AMB-05", "AMB-07", "AMB-21"):
        _open(ambiguities, amb_id)


def test_validation_rejects_a_collapsed_ambiguity(raw_ambiguities):
    raw = copy.deepcopy(raw_ambiguities)
    raw["ambiguities"][1]["readings"] = raw["ambiguities"][1]["readings"][:1]
    assert any("fewer than two readings" in p for p in validate_ambiguities(raw))
    raw = copy.deepcopy(raw_ambiguities)
    raw["ambiguities"][1]["preferred_reading"] = "Z"
    assert any("not one of its readings" in p for p in validate_ambiguities(raw))
