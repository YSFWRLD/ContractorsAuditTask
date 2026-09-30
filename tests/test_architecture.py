"""Guards the dependency direction: shared never imports domains; domains never import each other."""

import ast
from pathlib import Path

from contractor_audit.domains import REGISTRY
from contractor_audit.shared import paths
from contractor_audit.shared.domain import AuditDomain

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "contractor_audit"


def _imported_modules(path: Path) -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise AssertionError(f"{path}: use absolute imports so boundaries stay checkable")
            modules.add(node.module or "")
    return modules


def test_shared_does_not_import_domains():
    for path in (PACKAGE / "shared").rglob("*.py"):
        leaks = {m for m in _imported_modules(path) if m.startswith("contractor_audit.domains")}
        assert not leaks, f"{path.name} imports {leaks}"


def test_domains_do_not_import_each_other():
    domain_dirs = [p for p in (PACKAGE / "domains").iterdir() if (p / "__init__.py").exists()]
    for domain_dir in domain_dirs:
        own = f"contractor_audit.domains.{domain_dir.name}"
        for path in domain_dir.rglob("*.py"):
            foreign = {
                m for m in _imported_modules(path)
                if m.startswith("contractor_audit.domains") and not m.startswith(own)
            }
            assert not foreign, f"{path} imports {foreign}"


def test_registered_domains_satisfy_protocol():
    assert "civil_works" in REGISTRY
    for name, domain in REGISTRY.items():
        assert isinstance(domain, AuditDomain)
        assert domain.name == name


def test_generated_dirs_are_outside_raw_task_data():
    data_root = paths.task_data_root().resolve()
    for name in REGISTRY:
        for generated in (paths.artifacts_dir(name), paths.outputs_dir(name)):
            assert not generated.resolve().is_relative_to(data_root)
