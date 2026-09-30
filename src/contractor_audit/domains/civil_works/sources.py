"""Layout of the raw civil works task files under <data_root>/civilwork/ (read-only)."""

from dataclasses import dataclass
from pathlib import Path

SOURCE_DIRNAME = "civilwork"


@dataclass(frozen=True)
class CivilWorksSources:
    root: Path

    @classmethod
    def from_data_root(cls, data_root: Path) -> "CivilWorksSources":
        return cls(data_root / SOURCE_DIRNAME)

    @property
    def contract_pdf(self) -> Path:
        return self.root / "contract" / "CW-2025-0417-CIV.pdf"

    @property
    def guidelines(self) -> Path:
        return self.root / "guidelines" / "INVOICE_AUDIT_GUIDELINES.md"

    @property
    def applications_csv(self) -> Path:
        return self.root / "invoices" / "applications.csv"

    @property
    def application_lines_csv(self) -> Path:
        return self.root / "invoices" / "application_lines.csv"

    @property
    def records_dir(self) -> Path:
        return self.root / "records"

    def required(self) -> list[Path]:
        return [
            self.contract_pdf,
            self.guidelines,
            self.applications_csv,
            self.application_lines_csv,
            self.records_dir,
        ]
