"""The committed Phase 3 artifacts: labelled as statistics, consistent with a fresh interpretation."""

import json

from contractor_audit.shared import paths

ART = paths.artifacts_dir("drilling")


def load(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_mapping_metrics():
    d = load("phase3_service_mapping.json")
    assert "Not prices, not findings" in d["note"]
    assert (d["reports_interpreted"], d["reports_with_at_least_one_mapped_service"]) == (8151, 8151)
    assert d["deterministic_term_mappings"] + d["switch_dependent_term_mappings"] + d["ambiguous_term_mappings"] == d["term_mappings"]
    assert d["service_coverage"]["services_never_evidenced"] == []
    assert d["service_coverage"]["services_evidenced_only_under_some_readings"] == ["LH-714", "LW-412"]
    assert d["report_terms_mapping_to_more_than_one_code"]["LITERAL"] == ["MWD collar", "gamma tool", "mud motor", "rotary steerable"]


def test_quantity_metrics(interpretation):
    q = load("phase3_quantities.json")
    assert q["quantities"] == len(interpretation.quantities)
    assert set(q["by_basis"]) == {"PERSON_DAY", "RENTAL_DAY", "HOUR", "COUNT", "METRE", "RUN", "WELL", "LOST_IN_HOLE", "STANDBY_DAY"}
    assert sum(q["by_basis"].values()) == q["quantities"]
    assert all("E" not in r["total_quantity"] for r in q["by_service_and_reading"])   # plain decimals, never exponent form
    lw410 = {r["readings"]: r["total_quantity"] for r in q["by_service_and_reading"] if r["service"] == "LW-410"}
    assert lw410["metre_source=DAILY_DEPTH_ADVANCE;appendix_g_reading=LITERAL"] == lw410["metre_source=PART_B_RUN_METRES;appendix_g_reading=LITERAL"] == "315300"


def test_ambiguity_artifact_lists_switches_and_evidence():
    a = load("phase3_ambiguities.json")
    assert len(a["switches"]) == 26 and a["reports_by_ambiguity"]["AMB-22"] == 54
    facts = {tuple(e["ambiguities"]): e for e in a["evidence_facts"]}
    assert facts[("AMB-17", "AMB-24")]["runs_where_both_hold"] == 500


def test_billed_coverage_is_descriptive_and_exposes_multi_line_pairs():
    b = load("phase3_billed_coverage.json")
    assert "none of this is a finding" in b["note"]
    pairs = b["report_code_pairs_with_multiple_billed_lines"]
    assert pairs["count"] == 189 and pairs["by_code"] == {"LW-401": 2, "LW-411": 1, "MW-301": 2, "PD-210": 184}
    assert sum(not p["distinct_depth_intervals"] for p in pairs["pairs"]) == 5
    assert b["billed_lines_without_report_reference"] == {"DS-900": 63}
