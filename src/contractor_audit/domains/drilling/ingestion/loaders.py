"""One call from the raw task files to a DrillingDataset."""

from pathlib import Path

from contractor_audit.domains.drilling.ingestion.invoices import load_invoices, load_lines
from contractor_audit.domains.drilling.ingestion.models import DrillingDataset
from contractor_audit.domains.drilling.ingestion.reports import load_reports
from contractor_audit.domains.drilling.sources import DrillingSources
from contractor_audit.shared.provenance import sha256_file, sha256_tree


def load_dataset(data_root: Path) -> DrillingDataset:
    sources = DrillingSources.from_data_root(data_root)
    rel = lambda p: p.relative_to(data_root).as_posix()  # noqa: E731
    invoices, invoice_issues = load_invoices(sources.invoices_csv, rel(sources.invoices_csv))
    lines, line_issues = load_lines(sources.invoice_lines_csv, rel(sources.invoice_lines_csv))
    reports = load_reports(sources.records_dir, rel(sources.records_dir))
    issues = invoice_issues + line_issues + tuple(i for r in reports for i in r.issues)
    tree, _ = sha256_tree(sources.records_dir, "*.txt")
    fingerprints = {rel(sources.invoices_csv): sha256_file(sources.invoices_csv),
                    rel(sources.invoice_lines_csv): sha256_file(sources.invoice_lines_csv),
                    rel(sources.records_dir): tree}
    return DrillingDataset(invoices, lines, reports, issues, fingerprints=fingerprints)
