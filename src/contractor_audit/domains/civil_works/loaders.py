"""Strict loaders for civilwork/invoices/*.csv.

A value that does not parse is an error, not a default: the loader raises
LoadError naming the file, row and column rather than guessing.
"""

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from contractor_audit.domains.civil_works.models import Application, ApplicationLine
from contractor_audit.shared.money import parse_amount, to_minor_units

APPLICATION_COLUMNS = (
    "application_no", "contract_ref", "subcontractor", "site", "site_zone", "period_from", "period_to",
    "application_date", "application_total", "retention", "net_payable", "adjustment", "retention_released",
)
LINE_COLUMNS = (
    "line_ref", "application_no", "line_no", "work_date", "site", "item_code", "description", "unit",
    "site_zone", "ground_class", "quantity", "rate_applied", "amount", "night_work", "record_ref",
)
NIGHT_FLAGS = {"Y": True, "N": False}


class LoadError(ValueError):
    def __init__(self, path: Path, row: int, column: str, message: str):
        super().__init__(f"{path.name} row {row} [{column}]: {message}")
        self.path, self.row, self.column = path, row, column


def parse_iso_date(text: str) -> date:
    if len(text) != 10:
        raise ValueError(f"expected YYYY-MM-DD, got {text!r}")
    return date.fromisoformat(text)


def parse_decimal(text: str) -> Decimal:
    try:
        value = Decimal(text.strip())
    except InvalidOperation as exc:
        raise ValueError(f"not a number: {text!r}") from exc
    if not value.is_finite():
        raise ValueError(f"not a number: {text!r}")
    return value


def _cents(text: str) -> int:
    return to_minor_units(parse_amount(text))


def _read_rows(path: Path, expected: tuple[str, ...]):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != expected:
            raise LoadError(path, 1, "header", f"unexpected columns {reader.fieldnames}")
        # Row 1 is the header, so data rows start at 2 (matches a spreadsheet view of the file).
        for row_no, row in enumerate(reader, start=2):
            if None in row or any(v is None for v in row.values()):
                raise LoadError(path, row_no, "*", "wrong number of fields")
            yield row_no, row


def _field(path: Path, row_no: int, row: dict, column: str, parse):
    try:
        return parse(row[column])
    except ValueError as exc:
        raise LoadError(path, row_no, column, str(exc)) from None


def _required(text: str) -> str:
    if not text.strip():
        raise ValueError("required value is blank")
    return text


def load_applications(path: Path) -> list[Application]:
    apps = []
    for row_no, row in _read_rows(path, APPLICATION_COLUMNS):
        f = lambda col, parse: _field(path, row_no, row, col, parse)  # noqa: E731
        apps.append(Application(
            application_no=f("application_no", _required),
            contract_ref=f("contract_ref", _required),
            subcontractor=f("subcontractor", _required),
            site=f("site", _required),
            site_zone=f("site_zone", _required),
            period_from=f("period_from", parse_iso_date),
            period_to=f("period_to", parse_iso_date),
            application_date=f("application_date", parse_iso_date),
            application_total_cents=f("application_total", _cents),
            retention_cents=f("retention", _cents),
            net_payable_cents=f("net_payable", _cents),
            adjustment_cents=f("adjustment", _cents),
            retention_released_cents=f("retention_released", _cents),
            source_row=row_no,
            raw=dict(row),
        ))
    return apps


def _night_flag(text: str) -> bool:
    if text not in NIGHT_FLAGS:
        raise ValueError(f"night_work must be Y or N, got {text!r}")
    return NIGHT_FLAGS[text]


def _positive_int(text: str) -> int:
    if not text.isdigit():
        raise ValueError(f"expected a positive integer, got {text!r}")
    return int(text)


def load_application_lines(path: Path) -> list[ApplicationLine]:
    lines = []
    for row_no, row in _read_rows(path, LINE_COLUMNS):
        f = lambda col, parse: _field(path, row_no, row, col, parse)  # noqa: E731
        lines.append(ApplicationLine(
            line_ref=f("line_ref", _required),
            application_no=f("application_no", _required),
            line_no=f("line_no", _positive_int),
            work_date=f("work_date", parse_iso_date),
            site=f("site", _required),
            item_code=f("item_code", _required),
            description=row["description"],
            unit=f("unit", _required),
            site_zone=f("site_zone", _required),
            ground_class=row["ground_class"] or None,
            quantity=f("quantity", parse_decimal),
            rate_applied=f("rate_applied", parse_decimal),
            amount_cents=f("amount", _cents),
            night_work=f("night_work", _night_flag),
            record_ref=row["record_ref"] or None,
            source_row=row_no,
            raw=dict(row),
        ))
    return lines
