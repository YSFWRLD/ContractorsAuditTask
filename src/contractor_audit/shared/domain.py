"""The boundary every contract domain implements so the CLI stays domain-agnostic."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from contractor_audit.shared import paths
from contractor_audit.shared.findings import InvoiceResult


@dataclass(frozen=True)
class RunContext:
    data_root: Path
    artifacts_dir: Path
    outputs_dir: Path

    @classmethod
    def for_domain(cls, name: str) -> "RunContext":
        return cls(paths.task_data_root(), paths.artifacts_dir(name), paths.outputs_dir(name))


@runtime_checkable
class AuditDomain(Protocol):
    name: str

    def required_sources(self, data_root: Path) -> list[Path]:
        """Raw task files this domain reads; used to fail fast when data is missing."""
        ...

    def build_artifacts(self, ctx: RunContext) -> list[Path]:
        """Regenerate this domain's derived artifacts from raw data; returns the files written."""
        ...

    def run(self, ctx: RunContext) -> list[InvoiceResult]:
        """Audit every invoice of this domain and return one result per invoice."""
        ...
