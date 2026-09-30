import csv

from contractor_audit.domains.drilling import DOMAIN
from contractor_audit.domains.drilling.sources import DrillingSources


def _rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _header(path):
    with open(path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def test_required_sources_exist(data_root):
    missing = [p for p in DOMAIN.required_sources(data_root) if not p.exists()]
    assert not missing


def test_invoice_csvs_have_the_join_and_total_columns(data_root):
    sources = DrillingSources.from_data_root(data_root)
    assert {"invoice_no", "contract_ref", "well_name", "well_class", "period_start", "period_end", "invoice_date",
            "net_amount", "vat_amount", "invoice_total"} <= set(_header(sources.invoices_csv))
    assert {"line_ref", "invoice_no", "service_date", "service_code", "unit", "hole_section", "day_status",
            "depth_from_m", "depth_to_m", "quantity", "unit_rate", "amount", "report_ref"} <= set(
        _header(sources.invoice_lines_csv)
    )


def test_every_template_mds_row_has_exactly_one_invoice(data_root):
    invoices = [r["invoice_no"] for r in _rows(DrillingSources.from_data_root(data_root).invoices_csv)]
    template = [r["invoice_id"] for r in _rows(data_root / "submission_template.csv") if r["invoice_id"].startswith("MDS-")]
    assert len(invoices) == len(set(invoices)) == 1906
    assert set(invoices) == set(template)
