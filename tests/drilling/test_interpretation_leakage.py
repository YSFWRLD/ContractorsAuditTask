"""No billed-data leakage: interpretation cannot see invoices, and its results ignore any billed change."""

import ast
import dataclasses
import inspect
from decimal import Decimal
from pathlib import Path

import contractor_audit.domains.drilling as drilling
from contractor_audit.domains.drilling.ingestion.indexes import build_indexes
from contractor_audit.domains.drilling.ingestion.models import DrillingDataset
from contractor_audit.domains.drilling.interpretation.engine import interpret
from contractor_audit.domains.drilling.reporting.phase3_mapping_report import canonical_digest
from contractor_audit.shared import paths

INTERPRETATION = Path(drilling.__file__).parent / "interpretation"
BILLED = ("amount_cents", "unit_rate", "net_cents", "total_cents", "vat_cents", "InvoiceLine", "DrillingInvoice", ".lines", ".invoices",
          "lines_by_", "invoices_by_", "service_code_billed")


def test_interpret_accepts_no_billed_input():
    assert list(inspect.signature(interpret).parameters) == ["reports", "terms", "ambiguities"]


def test_interpretation_code_never_touches_invoice_data():
    for path in INTERPRETATION.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in BILLED:
            assert token not in text, f"{path.name} mentions {token}"
        mods = {n.module for n in ast.walk(ast.parse(text)) if isinstance(n, ast.ImportFrom)}
        assert not any(m and (m.endswith(".invoices") or ".reporting" in m or ".audit" in m or m.endswith(".findings")) for m in mods), path.name


def test_results_are_unchanged_when_billed_prices_amounts_totals_and_codes_change(dataset, terms, ambiguities, interpretation):
    lines = tuple(dataclasses.replace(l, unit_rate=Decimal("1"), amount_cents=1, service_code="XX-000") for l in dataset.lines[:5000]) + dataset.lines[5000:]
    invoices = tuple(dataclasses.replace(i, net_cents=0, total_cents=0, vat_cents=0) for i in dataset.invoices)
    mutated = DrillingDataset(invoices, lines, dataset.reports, dataset.issues)
    again = interpret(mutated.reports, terms, ambiguities)
    assert canonical_digest(again) == canonical_digest(interpretation)
    assert again.mappings == interpretation.mappings
    build_indexes(mutated)   # the billed side still indexes; it simply never reaches interpret


def test_quantities_artifact_digest_matches_a_fresh_interpretation(interpretation):
    import json
    committed = json.loads((paths.artifacts_dir("drilling") / "phase3_quantities.json").read_text(encoding="utf-8"))
    assert committed["canonical_sha256"] == canonical_digest(interpretation)


def test_no_findings_prices_or_submission(interpretation):
    names = {f.name for f in dataclasses.fields(interpretation.quantities[0])}
    assert not {"price", "rate", "amount", "expected", "finding", "flag"} & names
    assert not (paths.REPO_ROOT / "outputs" / "submission.csv").exists()
