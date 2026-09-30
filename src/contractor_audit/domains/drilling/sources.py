"""Layout of the raw drilling task files under <data_root>/drilling_services/ (read-only)."""

from dataclasses import dataclass
from pathlib import Path

SOURCE_DIRNAME = "drilling_services"


@dataclass(frozen=True)
class DrillingSources:
    root: Path

    @classmethod
    def from_data_root(cls, data_root: Path) -> "DrillingSources":
        return cls(data_root / SOURCE_DIRNAME)

    @property
    def contract_pdf(self) -> Path:
        return self.root / "contract" / "DDS-2025-118.pdf"

    @property
    def guidelines(self) -> Path:
        return self.root / "guidelines" / "INVOICE_AUDIT_GUIDELINES.md"

    @property
    def invoices_csv(self) -> Path:
        return self.root / "invoices" / "invoices.csv"

    @property
    def invoice_lines_csv(self) -> Path:
        return self.root / "invoices" / "invoice_lines.csv"

    @property
    def records_dir(self) -> Path:
        """Daily Drilling Reports, one file per well and day; identified by their `Report:` field, not the file name."""
        return self.root / "records"

    def required(self) -> list[Path]:
        return [
            self.contract_pdf,
            self.guidelines,
            self.invoices_csv,
            self.invoice_lines_csv,
            self.records_dir,
        ]
