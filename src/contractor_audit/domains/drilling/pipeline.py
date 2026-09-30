"""Drilling entry point: raw files -> canonical models -> checks -> InvoiceResults.

`build_artifacts` validates the reviewed contract files (Phase 1), ingests the operational data into a
structural validation report (Phase 2), interprets the reports into service candidates and quantities
(Phase 3), and prices that evidence canonically under the approved readings, with the sensitivity of every
approved reading and the decision record (Phase 4). `run` audits every invoice against that evidence (the twelve
checks) and writes the drilling draft outputs to outputs/drilling/. Neither writes the combined submission.
"""

import csv
import json
from pathlib import Path

from contractor_audit.domains.drilling.audit.policy import AUDIT_SWITCHES, RECOMMENDATIONS_FILENAME, load_recommendations
from contractor_audit.domains.drilling.audit.runner import AuditReport, run_audit
from contractor_audit.domains.drilling.contract.loader import AMBIGUITIES_FILENAME, TERMS_FILENAME, load_ambiguities, load_contract_terms
from contractor_audit.domains.drilling.ingestion.indexes import build_indexes
from contractor_audit.domains.drilling.ingestion.loaders import load_dataset
from contractor_audit.domains.drilling.ingestion.validation import validate
from contractor_audit.domains.drilling.interpretation.engine import interpret
from contractor_audit.domains.drilling.interpretation.switches import build_switches
from contractor_audit.domains.drilling.pricing.engine import price
from contractor_audit.domains.drilling.pricing.selection import APPROVED_FILENAME, build_selection, load_approved
from contractor_audit.domains.drilling.reporting import (
    ambiguity_evidence, audit_outputs, contract_artifacts, phase3_billed_coverage, phase3_mapping_report, phase4_canonical_pricing,
    phase4_sensitivity, structural_report,
)
from contractor_audit.domains.drilling.sources import DrillingSources
from contractor_audit.shared.domain import RunContext
from contractor_audit.shared.findings import InvoiceResult


class DrillingDomain:
    name = "drilling"

    def required_sources(self, data_root: Path) -> list[Path]:
        return DrillingSources.from_data_root(data_root).required()

    def build_artifacts(self, ctx: RunContext) -> list[Path]:
        """Contract artifacts, structural validation, report interpretation, canonical pricing and sensitivity. Never audits."""
        written = contract_artifacts.build(ctx.data_root, ctx.artifacts_dir).written
        terms = load_contract_terms(ctx.artifacts_dir / TERMS_FILENAME, ctx.artifacts_dir / AMBIGUITIES_FILENAME)
        dataset = load_dataset(ctx.data_root)
        indexes = build_indexes(dataset)
        evidence = ambiguity_evidence.collect(dataset, indexes, terms)
        written += structural_report.write(dataset, validate(dataset, indexes), evidence, ctx.artifacts_dir)
        ambiguities = {a.id: a for a in load_ambiguities(ctx.artifacts_dir / AMBIGUITIES_FILENAME)}
        result = interpret(dataset.reports, terms, ambiguities)   # reports and contract only
        switches = build_switches(ambiguities)
        written += phase3_mapping_report.write(result, list(dataset.reports), terms, switches, ctx.artifacts_dir)
        written += phase3_billed_coverage.write(result, indexes, ctx.artifacts_dir)
        approved = {k: v for k, v in load_approved(ctx.artifacts_dir / APPROVED_FILENAME, switches).items() if k not in AUDIT_SWITCHES}
        canonical = price(result, terms, switches, build_selection(switches, approved))   # fails if any reading is missing
        written += phase4_canonical_pricing.write(canonical, ctx.artifacts_dir)
        written += phase4_sensitivity.write(result, dataset, terms, switches, approved, ambiguities, ctx.artifacts_dir)
        return written

    def audit(self, ctx: RunContext, measure_dependencies: bool = True) -> tuple[AuditReport, object]:
        """The audit report and the dataset it was run on; writes nothing."""
        terms = load_contract_terms(ctx.artifacts_dir / TERMS_FILENAME, ctx.artifacts_dir / AMBIGUITIES_FILENAME)
        dataset = load_dataset(ctx.data_root)
        ambiguities = {a.id: a for a in load_ambiguities(ctx.artifacts_dir / AMBIGUITIES_FILENAME)}
        result = interpret(dataset.reports, terms, ambiguities)   # reports and contract only
        switches = build_switches(ambiguities)
        approved_raw = json.loads((ctx.artifacts_dir / APPROVED_FILENAME).read_text(encoding="utf-8"))
        report = run_audit(dataset, terms, result, switches, ambiguities, load_approved(ctx.artifacts_dir / APPROVED_FILENAME, switches),
                           approved_raw, load_recommendations(ctx.artifacts_dir / RECOMMENDATIONS_FILENAME), measure_dependencies)
        return report, dataset

    def run(self, ctx: RunContext) -> list[InvoiceResult]:
        """Audit every drilling invoice and write outputs/drilling/ (draft outputs only; no combined submission)."""
        report, dataset = self.audit(ctx)
        audit_outputs.write(report, dataset, template_ids(ctx.data_root), ctx.outputs_dir)
        return [o.result for o in audit_outputs.ordered(report, template_ids(ctx.data_root))]


def template_ids(data_root: Path) -> list[str]:
    """The drilling invoice ids of submission_template.csv, in its order."""
    with open(data_root / "submission_template.csv", newline="", encoding="utf-8") as f:
        return [r["invoice_id"] for r in csv.DictReader(f) if r["invoice_id"].startswith("MDS-")]


DOMAIN = DrillingDomain()
