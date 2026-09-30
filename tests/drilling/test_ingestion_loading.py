"""Invoices and lines: every file loads, every value is typed exactly, every record traces to its source line."""

import csv
import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from contractor_audit.domains.drilling.ingestion.invoices import IngestionError, load_invoices, load_lines
from contractor_audit.domains.drilling.ingestion.models import SourceRef
from contractor_audit.domains.drilling.ingestion.values import parse_cents, parse_date, parse_decimal, parse_int
from contractor_audit.domains.drilling.sources import DrillingSources
from contractor_audit.shared.provenance import sha256_file

SRC = SourceRef("test", 1, "X")


def test_every_input_file_loads_with_the_known_counts(dataset, data_root):
    assert (len(dataset.invoices), len(dataset.lines), len(dataset.reports)) == (1906, 91244, 8151)
    sources = DrillingSources.from_data_root(data_root)
    rel = lambda p: p.relative_to(data_root).as_posix()  # noqa: E731
    assert dataset.fingerprints[rel(sources.invoices_csv)] == sha256_file(sources.invoices_csv)
    assert dataset.fingerprints[rel(sources.invoice_lines_csv)] == sha256_file(sources.invoice_lines_csv)
    assert rel(sources.records_dir) in dataset.fingerprints


def test_csv_parsing_produced_no_issues(dataset):
    assert [i for i in dataset.issues if not i.source.file.startswith("drilling_services/records/")] == []


def test_money_is_exact_integer_cents_and_negative_discounts_survive(dataset):
    inv = dataset.invoices[0]
    assert (inv.invoice_no, inv.net_cents, inv.vat_cents, inv.total_cents, inv.adjustment_cents) == ("MDS-00001", 9982036, 1497305, 11479341, 0)
    ds900 = [l for l in dataset.lines if l.service_code == "DS-900"]
    assert len(ds900) == 63 and all(l.amount_cents < 0 for l in ds900)
    first = next(l for l in ds900 if l.line_ref == "MDS-00018-059")
    assert (first.amount_cents, first.unit_rate, first.raw_value("amount")) == (-4510968, Decimal("-45109.68"), "-45109.68")


def test_no_float_anywhere_in_the_parsed_objects(dataset):
    def check(obj):
        for f in dataclasses.fields(obj):
            value = getattr(obj, f.name)
            assert not isinstance(value, float), (type(obj).__name__, f.name)
    for obj in dataset.invoices[:50] + dataset.lines[:500]:
        check(obj)
    for r in dataset.reports[:200]:
        for part in (r, r.operations, r.bha_run):
            check(part)


def test_quantities_and_rates_are_decimals(dataset):
    line = dataset.lines[0]
    assert isinstance(line.quantity, Decimal) and isinstance(line.unit_rate, Decimal)
    assert (line.quantity, line.unit_rate, line.amount_cents) == (Decimal("2"), Decimal("1847.35"), 369470)
    assert all(l.quantity == l.quantity.to_integral_value() for l in dataset.lines)  # every quantity in the data is whole


def test_value_parsers_refuse_to_guess():
    assert parse_cents("12.345", SRC, "amount")[1].code == "MALFORMED_MONEY"
    assert parse_cents("1e3", SRC, "amount")[1].code == "MALFORMED_MONEY"
    assert parse_cents("", SRC, "amount")[1].code == "BLANK_VALUE"
    assert parse_cents("-0.50", SRC, "amount") == (-50, None)
    assert parse_date("31-Feb-2026", SRC, "d")[1].code == "IMPOSSIBLE_DATE"
    assert parse_date("2026-02-01", SRC, "d")[1].code == "MALFORMED_DATE"
    assert parse_date("01-feb-2026", SRC, "d")[1].code == "MALFORMED_DATE"
    assert parse_date("", SRC, "d", nullable=True) == (None, None)
    assert parse_date("07-Sep-2025", SRC, "d") == (date(2025, 9, 7), None)
    assert parse_int("3.5", SRC, "n")[1].code == "MALFORMED_NUMBER"
    assert parse_decimal("abc", SRC, "q")[1].code == "MALFORMED_NUMBER"
    assert parse_decimal("NaN", SRC, "q")[1].code == "MALFORMED_NUMBER"


def test_nullable_fields_are_none_not_defaults(dataset):
    ds900 = [l for l in dataset.lines if l.service_code == "DS-900"]
    assert all(l.service_date is None and l.hole_section is None and l.day_status is None and l.report_ref is None for l in ds900)
    with_depth = [l for l in dataset.lines if l.depth_from_m is not None]
    assert len(with_depth) == 2390 and {l.service_code for l in with_depth} == {"PD-210"}
    assert all((l.depth_from_m is None) == (l.depth_to_m is None) for l in dataset.lines)


def test_contractor_statements_are_kept_verbatim(dataset):
    assert {i.well_class_stated for i in dataset.invoices} == {"Standard", "Extended Reach", "HPHT"}
    assert sorted({i.contract_ref for i in dataset.invoices}) == ["DDS-2025-118", "DDS-2025-181", "DSS-2025-118"]
    assert len({l.service_code for l in dataset.lines}) == 39  # as printed, including DS-900


def test_every_record_traces_to_its_physical_source_line(dataset, data_root):
    sources = DrillingSources.from_data_root(data_root)
    physical = sources.invoice_lines_csv.read_text(encoding="utf-8").splitlines()
    for line in (dataset.lines[0], dataset.lines[45678], dataset.lines[-1]):
        assert line.source.file == "drilling_services/invoices/invoice_lines.csv" and line.source.record_id == line.line_ref
        assert next(csv.reader([physical[line.source.line - 1]])) == [v for _, v in line.raw]
    inv = dataset.invoices[-1]
    assert inv.source.line == 1907 and inv.source.record_id == "MDS-01906"
    assert inv.raw_value("period_start") == inv.raw[7][1]


def test_a_wrong_header_or_ragged_row_fails_loudly(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("invoice_no,contract_ref\nMDS-1,X\n", encoding="utf-8")
    with pytest.raises(IngestionError, match="header"):
        load_invoices(bad, "bad.csv")
    header = "line_ref,invoice_no,line_no,service_date,well_name,service_code,description,unit,hole_section,day_status,depth_from_m,depth_to_m,quantity,unit_rate,amount,report_ref"
    bad.write_text(header + "\nX,Y\n", encoding="utf-8")
    with pytest.raises(IngestionError, match="fields"):
        load_lines(bad, "bad.csv")


def test_malformed_cells_become_none_with_an_issue(tmp_path):
    header = "line_ref,invoice_no,line_no,service_date,well_name,service_code,description,unit,hole_section,day_status,depth_from_m,depth_to_m,quantity,unit_rate,amount,report_ref"
    path = tmp_path / "l.csv"
    path.write_text(header + '\nL-1,I-1,x,32-Jan-2026,W,DD-101,d,day,,,,,1.5,abc,12.3,\n', encoding="utf-8")
    lines, issues = load_lines(path, "l.csv")
    line = lines[0]
    assert (line.line_no, line.service_date, line.quantity, line.unit_rate, line.amount_cents) == (None, None, Decimal("1.5"), None, None)
    assert sorted(i.code for i in issues) == ["IMPOSSIBLE_DATE", "MALFORMED_MONEY", "MALFORMED_NUMBER", "MALFORMED_NUMBER"]
    assert all(i.source.line == 2 and i.source.record_id == "L-1" for i in issues)
