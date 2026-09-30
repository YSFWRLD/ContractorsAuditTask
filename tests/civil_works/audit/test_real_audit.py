"""The full audit of the task data: pinned cases, policy invariants, outputs and determinism.

Uses one session-scoped audit (about half a minute: the audit plus one re-run per alternative reading).
"""

import csv
import io
from pathlib import Path

import pytest

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.reports import (TEMPLATE_COLUMNS, draft_predictions_csv, invoice_results,
                                                                write_outputs)
from contractor_audit.shared import paths
from contractor_audit.shared.findings import ConfidenceBand


def _finding(result, line_ref, category):
    return next(f for f in result.findings if f.line_ref == line_ref and f.category == category)


def test_every_application_assessed(audit_result):
    assert len(audit_result.applications) == 900 and len(audit_result.base.lines) == 7746
    assert audit_result.base.unresolved == ()


@pytest.mark.parametrize("line_ref, record", [("PA-00609-01", "CT-00126"), ("PA-00678-06", "MO-00089"), ("PA-00672-04", "PS-00039")])
def test_three_missing_record_files(audit_result, line_ref, record):
    f = _finding(audit_result, line_ref, "missing_record")
    assert f.rule == "records.record_not_found" and f.observed == record and f.confidence is ConfidenceBand.HIGH


def test_mesh_line_quoting_a_pressure_test(audit_result):
    f = _finding(audit_result, "PA-00170-04", "item_record_mismatch")
    assert "PT" in f.observed and "JS" in f.expected


def test_work_after_final_completion(audit_result):
    late = sorted(f.line_ref for f in audit_result.findings if f.category == "work_after_final_completion")
    assert late == ["PA-00375-07", "PA-00678-10"]
    assert all(audit_result.base.lines[r].payable_quantity == 0 for r in late)


def test_known_single_cases(audit_result):
    assert _finding(audit_result, "PA-00845-03", "daily_limit_exceeded").expected == "3200"
    assert _finding(audit_result, "PA-00801-05", "exclusion_window_violation").confidence is ConfidenceBand.LOW
    assert _finding(audit_result, "PA-00613-01", "unsigned_record").observed.startswith("unsigned")
    assert {a.application_no for a in audit_result.applications if Category.CONTRACT_REFERENCE_MISMATCH.value in a.categories} == {"PA-00560", "PA-00711"}
    [hdr] = [f for f in audit_result.findings if f.category == "application_total_mismatch"]
    assert hdr.invoice_id == "PA-00043" and hdr.impact_cents == 3218


def test_outside_total_sums_are_findings_not_totals(audit_result):
    by_no = {a.application_no: a for a in audit_result.applications}
    adj = [f for f in audit_result.findings if f.category == "adjustment_missing"]
    assert {(f.invoice_id, f.rule) for f in adj} == {("PA-00006", "adjustments.clause_31a_retroactive_rate"),
                                                      ("PA-00678", "adjustments.clause_45a_retention_release")}
    assert all(f.outside_total and not f.affects_total for f in adj)
    # PA-00006 has no other finding, so its working contract total equals what it billed.
    assert by_no["PA-00006"].contract_total_cents == by_no["PA-00006"].billed_total_cents


def test_policy_invariants(audit_result):
    for a in audit_result.applications:
        if not a.flagged:
            assert a.expected_total_cents == a.billed_total_cents and not a.blank_reasons and not a.findings
            continue
        assert a.primary_category in a.categories
        if a.expected_total_cents is None:
            assert a.blank_reasons
        else:
            assert a.expected_total_cents == a.contract_total_cents
            assert all(d.band is ConfidenceBand.HIGH for d in a.total_dependencies)     # STRICT
        assert a.confidence.rank <= max(f.confidence.rank for f in a.findings)       # never above its best finding


def test_every_finding_is_traceable(audit_result):
    for f in audit_result.findings:
        assert f.category in {c.value for c in Category} and f.rule and f.message
        assert f.citations and all(c.page for c in f.citations), f.key
        if f.line_ref:
            assert f.evidence[0].kind == "billed_line" and f.evidence[0].reference == f.line_ref
        if f.rule.startswith("rates."):
            assert any(e.kind == "pricing_trace" for e in f.evidence)


def test_dependencies_are_measured_and_graded(audit_result):
    f = _finding(audit_result, "PA-00801-05", "exclusion_window_violation")
    assert [(d.switch, d.effect) for d in f.dependencies if d.effect == "finding_absent"] == [("exclusion_window", "finding_absent")]
    unflagged = [a for a in audit_result.applications if not a.flagged]
    assert any(d.switch == "indexed_rate_method" for a in unflagged for d in a.would_flag_under)
    assert all(a.confidence is ConfidenceBand.HIGH for a in unflagged if not any(d.band is not ConfidenceBand.HIGH for d in a.would_flag_under))


def test_draft_predictions_schema(audit_result):
    rows = list(csv.DictReader(io.StringIO(draft_predictions_csv(audit_result))))
    assert list(rows[0]) == TEMPLATE_COLUMNS and len(rows) == 900
    with open(paths.task_data_root() / "submission_template.csv", encoding="utf-8", newline="") as fh:
        template = [r["invoice_id"] for r in csv.DictReader(fh) if r["invoice_id"].startswith("PA-")]
    assert [r["invoice_id"] for r in rows] == template
    for r in rows:
        assert r["flagged"] in ("0", "1") and r["confidence"] in ("0.95", "0.75", "0.55")
        assert (r["error_category"] != "") == (r["flagged"] == "1")
        assert r["billed_total_cents"].isdigit() and (r["expected_total_cents"] == "" or r["expected_total_cents"].lstrip("-").isdigit())
    assert len(invoice_results(audit_result)) == 900


def test_committed_outputs_are_current_and_deterministic(audit_result, tmp_path):
    written = write_outputs(audit_result, tmp_path)
    committed = paths.outputs_dir("civil_works")
    stale = [p.name for p in written if p.read_bytes() != (committed / p.name).read_bytes()]
    assert not stale, f"rerun `contractor-audit run --domain civil_works`: {stale}"
    again = write_outputs(audit_result, tmp_path / "again")
    assert [p.read_bytes() for p in written] == [p.read_bytes() for p in again]


def test_no_combined_submission(audit_result):
    assert not (paths.REPO_ROOT / "outputs" / "submission.csv").exists()
    assert not [p for p in Path(paths.REPO_ROOT / "outputs").glob("drilling*") if "submission" in p.name or (p / "submission.csv").exists()]
