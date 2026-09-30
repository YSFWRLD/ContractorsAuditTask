"""The structural validation: pinned observations on the real data, detection on synthetic breakage."""

import dataclasses
import json
from datetime import date

from contractor_audit.domains.drilling.ingestion.models import DrillingDataset
from contractor_audit.domains.drilling.ingestion.validation import validate
from contractor_audit.shared import paths

EXPECTED = {
    "BLANK_SIGNATURE": 3, "CONTRACT_REF_VARIANT": 3, "INVOICE_DATED_BEFORE_PERIOD_END": 3, "INVOICE_PERIODS_OVERLAP": 13,
    "LINE_AMOUNT_NOT_QUANTITY_TIMES_RATE": 3, "LINE_DATE_DIFFERS_FROM_REPORT": 8, "LINE_DATE_OUTSIDE_INVOICE_PERIOD": 3,
    "LINE_WITHOUT_REPORT_REF": 63, "PART_C_PRESENCE_VS_GYRO_COUNT": 1, "PERIOD_DAYS_WITHOUT_REPORT": 3,
    "REPEATED_REPORT_AND_CODE": 189, "REPORT_REFERENCED_BY_MULTIPLE_INVOICES": 1, "TOTAL_NOT_NET_PLUS_VAT": 3,
}


def test_pinned_observations_on_the_real_data(structural):
    assert {code: len(obs) for code, obs in structural.by_code().items()} == EXPECTED
    assert structural.counts["wells"] == 214 and structural.counts["bha_runs"] == 1369
    assert structural.variants == {"A+B": 7258, "A+B+C": 476, "A+B+D": 363, "A+B+E": 47, "A+B+D+E": 4, "A+B+C+E": 3}


def test_specific_observations(structural):
    by = structural.by_code()
    assert sorted(o.subject[0] for o in by["CONTRACT_REF_VARIANT"]) == ["MDS-00672", "MDS-00988", "MDS-01799"]
    assert by["REPORT_REFERENCED_BY_MULTIPLE_INVOICES"][0].evidence["invoices"] == ["MDS-01340", "MDS-01352"]
    assert {o.evidence["service_code"] for o in by["LINE_WITHOUT_REPORT_REF"]} == {"DS-900"}
    assert by["PART_C_PRESENCE_VS_GYRO_COUNT"][0].subject == ("DDR-009-20251211",)
    non_pd = [o for o in by["REPEATED_REPORT_AND_CODE"] if o.subject[1] != "PD-210"]
    assert len(non_pd) == 5 and all(not o.evidence["distinct_depth_intervals"] for o in non_pd)
    assert sorted(o.subject[0] for o in by["TOTAL_NOT_NET_PLUS_VAT"]) == ["MDS-00551", "MDS-00916", "MDS-01317"]


def test_synthetic_breakage_is_detected(dataset):
    inv = dataset.invoices[0]
    lines = [l for l in dataset.lines if l.invoice_no == inv.invoice_no]
    broken = [dataclasses.replace(lines[0], report_ref="DDR-999-20990101"), dataclasses.replace(lines[1], well_name="NGP-ZZ-999")] + lines[2:]
    ds = DrillingDataset((inv, inv), tuple(broken), dataset.reports[:0], ())
    codes = {o.code for o in validate(ds).observations}
    assert {"DUPLICATE_INVOICE_ID", "LINE_REPORT_REF_MISSING", "LINE_WELL_DIFFERS_FROM_INVOICE"} <= codes


def test_ambiguity_evidence_is_recorded_without_choosing(evidence, ambiguities):
    for item in evidence:
        assert set(item["ambiguities"]) <= set(ambiguities)
        assert not {"preferred_reading", "decision", "reading"} & set(item)
    e22 = next(e for e in evidence if e["ambiguities"] == ["AMB-22"])
    assert e22["part_e_reports"] == 54 and e22["equal_to_sum_on_days_the_lost_tool_is_in_the_hole"] == 54
    e12 = next(e for e in evidence if "AMB-12" in e["ambiguities"])
    assert e12["nonzero_adjustments"] == 0 and e12["backdated_instruments"] == ["A3 issued 2026-08-17"]


def test_committed_structural_artifact_is_labelled_as_observations(structural):
    data = json.loads((paths.artifacts_dir("drilling") / "phase2_structural_validation.json").read_text(encoding="utf-8"))
    assert "None is an audit finding" in data["note"]
    assert {s["code"]: s["count"] for s in data["summary"]} == EXPECTED
    assert data["counts"]["invoices"] == 1906 and len(data["wells"]) == 214
    assert all(o["category"] in {"identity", "reference", "consistency", "timing", "report", "arithmetic", "parse"} for o in data["observations"])
    assert data["counts"]["report_dates"] == [str(date(2025, 1, 1)), str(date(2026, 11, 27))]
