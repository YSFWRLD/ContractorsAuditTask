import csv

from contractor_audit.domains.civil_works import DOMAIN
from contractor_audit.domains.civil_works.sources import CivilWorksSources


def _header(path):
    with open(path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def test_required_sources_exist(data_root):
    missing = [p for p in DOMAIN.required_sources(data_root) if not p.exists()]
    assert not missing


def test_invoice_csvs_have_the_join_and_total_columns(data_root):
    sources = CivilWorksSources.from_data_root(data_root)
    assert {"application_no", "contract_ref", "application_total"} <= set(_header(sources.applications_csv))
    assert {"application_no", "line_ref", "work_date", "item_code", "amount", "record_ref"} <= set(
        _header(sources.application_lines_csv)
    )
