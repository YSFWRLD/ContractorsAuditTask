"""Artifact building runs against a scratch artifacts dir, never the committed one, and never writes to task data."""

import json
import shutil

import pytest

from contractor_audit.domains.civil_works import artifacts
from contractor_audit.domains.civil_works.contract import EXTRACTION_FILENAME
from contractor_audit.shared import paths

COMMITTED = paths.artifacts_dir("civil_works")
EXPECTED = {"source_inventory.json", "contract_extraction.md", "contract_verification.md",
            "record_inventory.json", "record_inventory.md", "source_profile.json", "source_profile.md",
            "rate_timeline.json", "rate_timeline.md", "interpretation_matrix.md", "pricing_model.md",
            "quantity_parsing.json", "quantity_parsing.md", "sensitivity.json", "sensitivity.md"}


@pytest.fixture
def scratch_artifacts(tmp_path):
    shutil.copy(COMMITTED / EXTRACTION_FILENAME, tmp_path / EXTRACTION_FILENAME)
    return tmp_path


def test_build_writes_every_artifact_deterministically(data_root, scratch_artifacts):
    first = artifacts.build(data_root, scratch_artifacts)
    assert {p.name for p in first.written} == EXPECTED
    assert (first.applications, first.lines, first.records, first.record_issues) == (900, 7746, 2169, 1)
    snapshot = {p.name: p.read_bytes() for p in first.written}
    second = artifacts.build(data_root, scratch_artifacts)
    assert {p.name: p.read_bytes() for p in second.written} == snapshot


def test_committed_artifacts_are_current(data_root, scratch_artifacts):
    """The generated files in artifacts/civil_works/ match what the code produces now."""
    result = artifacts.build(data_root, scratch_artifacts)
    stale = [p.name for p in result.written if p.read_bytes() != (COMMITTED / p.name).read_bytes()]
    assert not stale, f"rerun `contractor-audit build-artifacts --domain civil_works`: {stale}"


def test_build_refuses_extraction_for_a_different_pdf(data_root, scratch_artifacts):
    path = scratch_artifacts / EXTRACTION_FILENAME
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["source_document"]["sha256"] = "0" * 64
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="sha256"):
        artifacts.build(data_root, scratch_artifacts)


def test_generated_markdown_names_its_sources(data_root, scratch_artifacts):
    artifacts.build(data_root, scratch_artifacts)
    extraction_md = (scratch_artifacts / "contract_extraction.md").read_text(encoding="utf-8")
    for heading in ("Schedule 1", "Schedule 2A", "Schedule 2B", "Schedule 3", "Schedule 5", "Amendment No. 3", "Precedence timeline"):
        assert heading in extraction_md
    assert "UNREADABLE" in (scratch_artifacts / "contract_verification.md").read_text(encoding="utf-8")


def test_outputs_are_confined_to_civil_works_drafts():
    """Phase 3 writes civil works drafts only; there is still no combined submission."""
    allowed = {"findings.jsonl", "application_audit.csv", "draft_predictions.csv", "audit_summary.md", "coverage.md",
               "uncertainty_report.md", "sensitivity.md", "review.md"}
    produced = {p.name for p in paths.outputs_dir("civil_works").rglob("*") if p.is_file()}
    assert produced <= allowed
    assert not (paths.REPO_ROOT / "outputs" / "submission.csv").exists()
