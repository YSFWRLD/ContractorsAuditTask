"""Typed drilling source records, exactly as the task files state them.

No contract knowledge: a service code is the code the contractor printed, a tool is the rig's own word,
a well class is what the invoice says. Every object keeps its source location and raw values.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Severity(StrEnum):
    INFO = "INFO"          # worth knowing; parsing was unaffected
    WARNING = "WARNING"    # a value is missing, blank, malformed or inconsistent; the field is None
    ERROR = "ERROR"        # the record could not be parsed into its typed form


@dataclass(frozen=True)
class SourceRef:
    """Where a record came from: file (relative to the task data root), 1-based physical line, own identifier."""
    file: str
    line: int | None
    record_id: str | None


@dataclass(frozen=True)
class ParseIssue:
    code: str
    severity: Severity
    message: str
    source: SourceRef
    field: str | None = None
    raw: str | None = None


# --------------------------------------------------------------------------- invoices
@dataclass(frozen=True)
class DrillingInvoice:
    invoice_no: str
    contract_ref: str               # as printed; variants are kept, not corrected
    contractor: str
    well_name: str
    rig: str
    field: str
    well_class_stated: str          # the contractor's statement, not the call-off
    period_start: date | None
    period_end: date | None
    invoice_date: date | None
    net_cents: int | None
    vat_cents: int | None
    total_cents: int | None
    adjustment_cents: int | None
    raw: tuple[tuple[str, str], ...]
    source: SourceRef

    def raw_value(self, column: str) -> str:
        return dict(self.raw)[column]


@dataclass(frozen=True)
class InvoiceLine:
    line_ref: str
    invoice_no: str
    line_no: int | None
    service_date: date | None
    well_name: str
    service_code: str               # as printed by the contractor; never re-identified here
    description: str
    unit: str
    hole_section: str | None
    day_status: str | None
    depth_from_m: int | None
    depth_to_m: int | None
    quantity: Decimal | None
    unit_rate: Decimal | None
    amount_cents: int | None
    report_ref: str | None
    raw: tuple[tuple[str, str], ...]
    source: SourceRef

    def raw_value(self, column: str) -> str:
        return dict(self.raw)[column]


# --------------------------------------------------------------------------- daily drilling reports
@dataclass(frozen=True)
class RawField:
    """One `Label: value` line exactly as written, with the part it sits in and its physical line."""
    section: str        # "HEADER", "A".."E" or "SIGNATURES"
    label: str
    value: str
    line: int


@dataclass(frozen=True)
class CrewEntry:
    count: int | None
    role: str           # rig wording, verbatim ("directional hands")
    raw: str


@dataclass(frozen=True)
class Signature:
    role: str           # the printed role inside "Signed (...)"
    name: str | None    # None when the line is blank or only underscores
    raw: str

    @property
    def blank(self) -> bool:
        return self.name is None


@dataclass(frozen=True)
class OperationsSummary:
    """Part A."""
    hole_section: str | None
    status: str | None
    depth_start_m: int | None
    depth_end_m: int | None
    circulating_hours: int | None
    bha_run: int | None
    in_the_hole: tuple[str, ...]    # rig words, verbatim, in printed order
    crew: tuple[CrewEntry, ...]
    gyro_surveys: int | None
    pressure_points: int | None
    wiper_trips: int | None
    back_reaming_hours: int | None
    clean_out_runs: int | None


@dataclass(frozen=True)
class BhaRunRecord:
    """Part B: the run as the report states it (repeated on every day of the run)."""
    run: int | None
    run_first_day: date | None
    run_last_day: date | None
    tools_in_run: tuple[str, ...]
    run_circulating_hours: int | None
    metres_logged: int | None
    metres_reamed: int | None
    radioactive_source_carried: bool | None


@dataclass(frozen=True)
class GyroSurveyRecord:
    """Part C."""
    surveys_taken: int | None
    surveyed_section: str | None


@dataclass(frozen=True)
class SourceHandlingRecord:
    """Part D."""
    source_run: int | None
    sources_handled: str | None
    certified: bool | None


@dataclass(frozen=True)
class LostInHoleRecord:
    """Part E."""
    run: int | None
    tool: str | None    # rig word, verbatim
    circulating_hours_accumulated_on_well: int | None


@dataclass(frozen=True)
class DailyReport:
    report_id: str | None           # the report's own `Report:` field (the join key); not the file name
    title: str
    contract_ref: str | None
    well: str | None
    rig: str | None
    date: date | None
    parts: tuple[str, ...]          # parts present, in printed order ("A", "B", ...)
    operations: OperationsSummary | None
    bha_run: BhaRunRecord | None
    gyro: GyroSurveyRecord | None
    source_handling: SourceHandlingRecord | None
    lost_in_hole: LostInHoleRecord | None
    signatures: tuple[Signature, ...]
    fields: tuple[RawField, ...]
    issues: tuple[ParseIssue, ...]
    source: SourceRef

    @property
    def variant(self) -> str:
        return "+".join(self.parts)

    def raw_value(self, section: str, label: str) -> str | None:
        return next((f.value for f in self.fields if f.section == section and f.label == label), None)


@dataclass(frozen=True)
class DrillingDataset:
    invoices: tuple[DrillingInvoice, ...]
    lines: tuple[InvoiceLine, ...]
    reports: tuple[DailyReport, ...]
    issues: tuple[ParseIssue, ...]
    currency: str = "USD"
    currency_source: str = "README.md: money is printed in the contract's own currency (USD for drilling); the CSVs carry no currency column"
    fingerprints: dict[str, str] = field(default_factory=dict)
