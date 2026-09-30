"""invoices.csv and invoice_lines.csv -> typed rows. Every column is kept; nothing is re-identified or repriced."""

import csv
from pathlib import Path

from contractor_audit.domains.drilling.ingestion.models import DrillingInvoice, InvoiceLine, ParseIssue, Severity, SourceRef
from contractor_audit.domains.drilling.ingestion.values import parse_cents, parse_date, parse_decimal, parse_int

INVOICE_COLUMNS = ("invoice_no", "contract_ref", "contractor", "well_name", "rig", "field", "well_class", "period_start",
                   "period_end", "invoice_date", "net_amount", "vat_amount", "invoice_total", "adjustment")
LINE_COLUMNS = ("line_ref", "invoice_no", "line_no", "service_date", "well_name", "service_code", "description", "unit",
                "hole_section", "day_status", "depth_from_m", "depth_to_m", "quantity", "unit_rate", "amount", "report_ref")
# Columns that may legitimately be blank; a blank anywhere else is reported.
LINE_NULLABLE = ("service_date", "hole_section", "day_status", "depth_from_m", "depth_to_m", "report_ref")


class IngestionError(ValueError):
    """The file cannot be read as the expected table at all (wrong header, ragged rows)."""


def _rows(path: Path, expected: tuple[str, ...], rel: str):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = tuple(next(reader))
        if header != expected:
            raise IngestionError(f"{rel}: header {header} differs from the expected {expected}")
        for row in reader:
            if len(row) != len(expected):
                raise IngestionError(f"{rel} line {reader.line_num}: {len(row)} fields, expected {len(expected)}")
            yield reader.line_num, dict(zip(expected, row))


def _blank_issues(row: dict, required: tuple[str, ...], source: SourceRef) -> list[ParseIssue]:
    return [ParseIssue("BLANK_VALUE", Severity.WARNING, f"{c} is blank", source, c, "") for c in required if row[c] == ""]


def load_invoices(path: Path, rel: str) -> tuple[tuple[DrillingInvoice, ...], tuple[ParseIssue, ...]]:
    invoices, issues = [], []
    for line, row in _rows(path, INVOICE_COLUMNS, rel):
        src = SourceRef(rel, line, row["invoice_no"] or None)
        issues += _blank_issues(row, ("invoice_no", "contract_ref", "contractor", "well_name", "rig", "field", "well_class"), src)
        parsed = {}
        for col in ("period_start", "period_end", "invoice_date"):
            parsed[col], issue = parse_date(row[col], src, col)
            issues += [issue] if issue else []
        for col in ("net_amount", "vat_amount", "invoice_total", "adjustment"):
            parsed[col], issue = parse_cents(row[col], src, col)
            issues += [issue] if issue else []
        invoices.append(DrillingInvoice(
            invoice_no=row["invoice_no"], contract_ref=row["contract_ref"], contractor=row["contractor"],
            well_name=row["well_name"], rig=row["rig"], field=row["field"], well_class_stated=row["well_class"],
            period_start=parsed["period_start"], period_end=parsed["period_end"], invoice_date=parsed["invoice_date"],
            net_cents=parsed["net_amount"], vat_cents=parsed["vat_amount"], total_cents=parsed["invoice_total"],
            adjustment_cents=parsed["adjustment"], raw=tuple(row.items()), source=src))
    return tuple(invoices), tuple(issues)


def load_lines(path: Path, rel: str) -> tuple[tuple[InvoiceLine, ...], tuple[ParseIssue, ...]]:
    lines, issues = [], []
    required = tuple(c for c in LINE_COLUMNS if c not in LINE_NULLABLE)
    for line, row in _rows(path, LINE_COLUMNS, rel):
        src = SourceRef(rel, line, row["line_ref"] or None)
        issues += _blank_issues(row, required, src)
        values = {}
        values["line_no"], i1 = parse_int(row["line_no"], src, "line_no")
        values["service_date"], i2 = parse_date(row["service_date"], src, "service_date", nullable=True)
        values["depth_from_m"], i3 = parse_int(row["depth_from_m"], src, "depth_from_m", nullable=True)
        values["depth_to_m"], i4 = parse_int(row["depth_to_m"], src, "depth_to_m", nullable=True)
        values["quantity"], i5 = parse_decimal(row["quantity"], src, "quantity")
        values["unit_rate"], i6 = parse_decimal(row["unit_rate"], src, "unit_rate")
        values["amount"], i7 = parse_cents(row["amount"], src, "amount")
        # blanks in required columns were reported above; report every other value problem once
        issues += [i for i in (i1, i2, i3, i4, i5, i6, i7) if i and not (i.code == "BLANK_VALUE" and i.field in required)]
        lines.append(InvoiceLine(
            line_ref=row["line_ref"], invoice_no=row["invoice_no"], line_no=values["line_no"], service_date=values["service_date"],
            well_name=row["well_name"], service_code=row["service_code"], description=row["description"], unit=row["unit"],
            hole_section=row["hole_section"] or None, day_status=row["day_status"] or None,
            depth_from_m=values["depth_from_m"], depth_to_m=values["depth_to_m"], quantity=values["quantity"],
            unit_rate=values["unit_rate"], amount_cents=values["amount"], report_ref=row["report_ref"] or None,
            raw=tuple(row.items()), source=src))
    return tuple(lines), tuple(issues)
