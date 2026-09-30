"""The committed root submission.csv: the upstream template filled from the frozen domain results, exactly."""

import csv
from collections import Counter

from contractor_audit import cli
from contractor_audit.shared import paths
from contractor_audit.shared.money import parse_amount, to_minor_units
from contractor_audit.shared.submission import COLUMNS, Source, combine, render, validate_row

DOMAINS = ("civil_works", "drilling")


def _rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _sources():
    return [Source(d, paths.outputs_dir(d) / "draft_predictions.csv") for d in DOMAINS]


def test_submission_is_the_template_filled_from_the_frozen_domain_results(data_root):
    committed = paths.submission_path().read_bytes()
    assert committed == render(combine(data_root / "submission_template.csv", _sources())).encode()   # current and reproducible
    assert committed.decode("ascii") and b"\r" not in committed and not committed.startswith(b"\xef\xbb\xbf")
    rows = _rows(paths.submission_path())
    template = _rows(data_root / "submission_template.csv")
    assert list(rows[0]) == COLUMNS == list(template[0])
    assert [r["invoice_id"] for r in rows] == [r["invoice_id"] for r in template]
    assert len(rows) == 2806 and len({r["invoice_id"] for r in rows}) == 2806
    assert Counter(r["invoice_id"][:3] for r in rows) == {"PA-": 900, "MDS": 1906}
    for r in rows:
        validate_row(r, r["invoice_id"])


def test_domain_rows_are_unchanged():
    rows = {r["invoice_id"]: r for r in _rows(paths.submission_path())}
    for domain in DOMAINS:
        for r in _rows(paths.outputs_dir(domain) / "draft_predictions.csv"):
            assert rows[r["invoice_id"]] == r, (domain, r["invoice_id"])      # flags, categories, totals and confidence verbatim


def test_no_drilling_total_is_invented_or_taken_from_a_conditional_amount():
    rows = [r for r in _rows(paths.submission_path()) if r["invoice_id"].startswith("MDS-")]
    assert all(r["expected_total_cents"] == "" for r in rows)
    conditional = {r["invoice_no"]: r["conditional_total_cents"] for r in _rows(paths.outputs_dir("drilling") / "invoice_audit.csv")}
    assert all(conditional[r["invoice_id"]] and r["expected_total_cents"] != conditional[r["invoice_id"]] for r in rows)
    civil = [r for r in _rows(paths.submission_path()) if r["invoice_id"].startswith("PA-")]
    assert sum(r["expected_total_cents"] == "" for r in civil) == 21                  # the STRICT blanks, not zeros
    assert all(r["expected_total_cents"] == r["billed_total_cents"] for r in civil if r["flagged"] == "0")


def test_billed_totals_are_the_task_source_totals(data_root):
    rows = {r["invoice_id"]: r for r in _rows(paths.submission_path())}
    source = {r["application_no"]: r["application_total"] for r in _rows(data_root / "civilwork" / "invoices" / "applications.csv")}
    source |= {r["invoice_no"]: r["invoice_total"] for r in _rows(data_root / "drilling_services" / "invoices" / "invoices.csv")}
    assert set(source) == set(rows)
    assert all(int(rows[i]["billed_total_cents"]) == to_minor_units(parse_amount(t)) for i, t in source.items())


def test_counts():
    rows = _rows(paths.submission_path())
    flagged = Counter((r["invoice_id"][:3], r["flagged"]) for r in rows)
    assert flagged == {("PA-", "1"): 77, ("PA-", "0"): 823, ("MDS", "1"): 116, ("MDS", "0"): 1790}
    assert all((r["error_category"] != "") == (r["flagged"] == "1") for r in rows)


def test_cli_writes_the_submission_and_fails_loudly(tmp_path, monkeypatch, capsys):
    out = tmp_path / "submission.csv"
    monkeypatch.setattr(paths, "submission_path", lambda: out)
    assert cli.main(["submission"]) == 0
    assert out.read_bytes() == paths.REPO_ROOT.joinpath("submission.csv").read_bytes()
    monkeypatch.setattr(paths, "outputs_dir", lambda domain: tmp_path / "nowhere" / domain)
    out.unlink()
    assert cli.main(["submission"]) == 1
    assert "not found" in capsys.readouterr().err and not out.exists()
