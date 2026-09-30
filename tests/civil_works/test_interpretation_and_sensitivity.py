import json
from dataclasses import fields
from enum import Enum

from contractor_audit.domains.civil_works.interpretation import (SWITCHES, SWITCHES_BY_FIELD, WORKING_INTERPRETATION,
                                                                 CivilWorksInterpretation, SwitchStatus, alternatives)
from contractor_audit.domains.civil_works.record_quantities import extract_all
from contractor_audit.domains.civil_works.sensitivity import CONSISTENCY_LABEL, run_sensitivity


def test_every_switch_is_documented_with_every_reading():
    assert [s.field for s in SWITCHES] == [f.name for f in fields(CivilWorksInterpretation)]
    for f in fields(CivilWorksInterpretation):
        value = getattr(WORKING_INTERPRETATION, f.name)
        assert isinstance(value, Enum)
        info = SWITCHES_BY_FIELD[f.name]
        assert set(info.readings) == {v.value for v in type(value)}, f.name
        assert info.clauses and info.pages and info.default_rationale
        assert alternatives(f.name) and value not in alternatives(f.name)


def test_interpretation_is_immutable_and_labelled():
    alt = WORKING_INTERPRETATION.with_(rebate_counting=alternatives("rebate_counting")[0])
    assert alt != WORKING_INTERPRETATION and WORKING_INTERPRETATION.label()["rebate_counting"] == "contract_year"


def test_status_vocabulary():
    assert {s.status for s in SWITCHES} <= set(SwitchStatus)
    assert any(s.status is SwitchStatus.UNRESOLVED for s in SWITCHES)


def test_sensitivity_on_real_data(terms, applications, lines, record_set):
    s = run_sensitivity(terms, applications, lines, {q.record_id: q for q in extract_all(record_set.records)})
    assert set(s["switches"]) == {f.name for f in fields(CivilWorksInterpretation)}
    # the theoretical concurrent-uplift branch is never reached by the data
    assert s["switches"]["concurrent_uplifts"]["alternatives"]["both_assumed_instructed"]["lines_affected"] == 0
    assert s["switches"]["indexed_rate_method"]["alternatives"]["appendix_b_unindexed"]["lines_affected"] > 0
    assert CONSISTENCY_LABEL in s["overall"]
    assert s["boundary_notes"]["lines_after_final_completion"] == ["PA-00375-07", "PA-00678-10"]
    # descriptive vocabulary only: no audit verdicts
    text = json.dumps(s).lower()
    for word in ("flagged", "error_category", "wrong_rate", "confidence", "expected_total_cents"):
        assert word not in text
