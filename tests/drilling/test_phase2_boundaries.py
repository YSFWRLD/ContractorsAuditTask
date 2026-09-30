"""Phase 2 stays structural: no service identification, no contract rates, no findings, no submission."""

import ast
import re
from pathlib import Path

import contractor_audit.domains.drilling as drilling
from contractor_audit.shared import paths

ROOT = Path(drilling.__file__).parent
PHASE2 = [p for p in (ROOT / "ingestion").rglob("*.py")] + [ROOT / "reporting" / "structural_report.py"]
EVIDENCE = ROOT / "reporting" / "ambiguity_evidence.py"  # may read contract dates, never rates or mappings
CODE = re.compile(r"^[A-Z]{2}-\d{3}$")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(n.module or "")
    return out


def _string_constants(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs = {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    return {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs}


def test_phase2_code_does_not_touch_the_contract_or_findings():
    for path in PHASE2:
        mods = _imports(path)
        assert not any(".drilling.contract" in m or m.endswith(".findings") or ".audit" in m for m in mods), (path.name, mods)


def test_phase2_code_names_no_service_code_and_no_rate_machinery():
    for path in PHASE2 + [EVIDENCE]:
        constants = _string_constants(path)
        assert not {c for c in constants if CODE.match(c)}, f"{path.name} hardcodes a service code"
        text = path.read_text(encoding="utf-8")
        for token in ("rate_statements", "base_rate_cents", "codes_for_report_term", "appendix_g", "section_factors", "class_factors"):
            assert token not in text, f"{path.name} uses {token}"


def test_reports_keep_rig_words_and_carry_no_codes(dataset):
    words = {w for r in dataset.reports for w in r.operations.in_the_hole} | {c.role for r in dataset.reports for c in r.operations.crew}
    assert not {w for w in words if CODE.match(w)}
    assert "mud motor" in words and "directional hands" in words


def test_no_submission_and_no_audit_artifacts():
    assert not (paths.REPO_ROOT / "outputs" / "submission.csv").exists()
    artifacts = {p.name for p in paths.artifacts_dir("drilling").iterdir()}
    assert not {n for n in artifacts if "finding" in n or "prediction" in n or "submission" in n}
