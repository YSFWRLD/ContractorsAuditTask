"""Drilling domain boundary: layer order inside the domain; build-artifacts writes derived artifacts only; run writes the draft outputs only."""

import ast
import shutil
from pathlib import Path

import pytest

import contractor_audit.domains.drilling as drilling
from contractor_audit.domains import REGISTRY
from contractor_audit.domains.drilling import DOMAIN
from contractor_audit.domains.drilling.reporting import (
    contract_artifacts, phase3_billed_coverage, phase3_mapping_report, phase4_canonical_pricing, phase4_sensitivity, structural_report,
)
from contractor_audit.shared import paths
from contractor_audit.shared.domain import AuditDomain, RunContext

ROOT = Path(drilling.__file__).parent
PKG = "contractor_audit.domains.drilling"
# layer -> drilling modules/layers it may import (besides itself and contractor_audit.shared)
ALLOWED = {
    "ingestion": {"sources"},
    "contract": {"sources"},
    "interpretation": {"sources", "ingestion", "contract"},
    "pricing": {"sources", "contract", "interpretation"},
    "audit": {"sources", "ingestion", "contract", "interpretation", "pricing"},
    "reporting": {"sources", "ingestion", "contract", "interpretation", "pricing", "audit"},
}


def _drilling_imports(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
        found.update(n[len(PKG) + 1:].split(".")[0] for n in names if n.startswith(PKG + "."))
    return found


def test_layers_exist_as_packages():
    assert all((ROOT / layer / "__init__.py").is_file() for layer in ALLOWED)


def test_layers_import_only_downward():
    for layer, allowed in ALLOWED.items():
        for path in (ROOT / layer).rglob("*.py"):
            illegal = _drilling_imports(path) - allowed - {layer}  # "pipeline" is never allowed
            assert not illegal, f"{path.relative_to(ROOT)} imports drilling.{illegal}"


def test_sources_module_depends_on_no_layer():
    assert _drilling_imports(ROOT / "sources.py") == set()


def test_registered_under_its_own_name():
    assert REGISTRY["drilling"] is DOMAIN and isinstance(DOMAIN, AuditDomain)


GENERATED = contract_artifacts.GENERATED + structural_report.GENERATED + phase3_mapping_report.GENERATED + phase3_billed_coverage.GENERATED + phase4_sensitivity.GENERATED + phase4_canonical_pricing.GENERATED


@pytest.fixture(scope="module")
def fresh_build(tmp_path_factory, data_root):
    tmp = tmp_path_factory.mktemp("drilling_build")
    artifacts = tmp / "artifacts"
    artifacts.mkdir()
    for name in ("contract_terms.json", "contract_ambiguities.json", "approved_readings.json", "phase4_recommendations.json"):
        shutil.copy(paths.artifacts_dir("drilling") / name, artifacts / name)
    written = DOMAIN.build_artifacts(RunContext(data_root, artifacts, tmp / "outputs"))
    return tmp, artifacts, written


def test_build_artifacts_writes_only_the_derived_artifacts(fresh_build):
    tmp, artifacts, written = fresh_build
    assert sorted(p.name for p in written) == sorted(GENERATED)
    assert sorted(p.name for p in artifacts.iterdir()) == sorted(GENERATED + ("contract_terms.json", "contract_ambiguities.json", "approved_readings.json", "phase4_recommendations.json"))
    assert not (tmp / "outputs").exists()


def test_committed_derived_artifacts_match_a_fresh_build(fresh_build):
    _, artifacts, _ = fresh_build
    for name in GENERATED:
        assert (artifacts / name).read_bytes() == (paths.artifacts_dir("drilling") / name).read_bytes(), name


def test_drilling_outputs_are_the_draft_files_only():
    from contractor_audit.domains.drilling.reporting.audit_outputs import FILES
    assert sorted(p.name for p in paths.outputs_dir("drilling").iterdir()) == sorted(FILES)
    assert not (paths.REPO_ROOT / "outputs" / "submission.csv").exists()
