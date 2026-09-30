"""Task-wide source files that every domain's output is eventually merged into."""

import csv

TEMPLATE_COLUMNS = [
    "invoice_id", "flagged", "error_category",
    "expected_total_cents", "billed_total_cents", "confidence",
]


def test_submission_template_lists_every_invoice_once(data_root):
    with open(data_root / "submission_template.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == TEMPLATE_COLUMNS
        ids = [row["invoice_id"] for row in reader]
    assert len(ids) == 2806
    assert len(set(ids)) == len(ids)
    assert sum(i.startswith("PA-") for i in ids) == 900
    assert sum(i.startswith("MDS-") for i in ids) == 1906
