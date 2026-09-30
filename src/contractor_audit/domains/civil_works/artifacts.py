"""Builds the Phase 1 derived artifacts under artifacts/civil_works/.

Inputs: the untouched task data plus the reviewed `contract_extraction.json`
(which is itself a committed, hand-reviewed artifact and is never regenerated here).
Outputs are deterministic, so rebuilding on unchanged inputs produces identical files.
"""

import csv
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from contractor_audit.domains.civil_works.contract import (EXTRACTION_FILENAME, iter_provenance, load_raw_extraction,
                                                           terms_from_raw)
from contractor_audit.domains.civil_works.loaders import load_application_lines, load_applications
from contractor_audit.domains.civil_works.pricing_reports import (quantity_parsing, rate_timeline, render_interpretation_matrix,
                                                                  render_pricing_model, render_quantity_parsing,
                                                                  render_rate_timeline, render_sensitivity)
from contractor_audit.domains.civil_works.profiling import record_inventory, source_profile
from contractor_audit.domains.civil_works.record_quantities import extract_all
from contractor_audit.domains.civil_works.records import load_records
from contractor_audit.domains.civil_works.sensitivity import run_sensitivity
from contractor_audit.domains.civil_works.reports import (render_contract_extraction, render_contract_verification,
                                                          render_record_inventory, render_source_profile)
from contractor_audit.domains.civil_works.sources import CivilWorksSources
from contractor_audit.shared.provenance import sha256_file, sha256_tree

SOURCE_INVENTORY = "source_inventory.json"


def _json_default(value):
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")


def _csv_rows(path: Path) -> int:
    with open(path, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def source_inventory(sources: CivilWorksSources, data_root: Path) -> dict:
    """Fingerprint of every raw civil works input; also the reference for the 'task data untouched' test."""
    rel = lambda p: p.relative_to(data_root).as_posix()  # noqa: E731
    files = []
    for path, kind in ((sources.contract_pdf, "contract (scanned PDF, no text layer)"),
                       (sources.guidelines, "audit guidelines"),
                       (sources.applications_csv, "applications"),
                       (sources.application_lines_csv, "application lines")):
        entry = {"path": rel(path), "kind": kind, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        if path.suffix == ".csv":
            entry["data_rows"] = _csv_rows(path)
        files.append(entry)
    tree_digest, count = sha256_tree(sources.records_dir, "*.txt")
    template = data_root / "submission_template.csv"
    return {
        "domain": "civil_works",
        "data_root_layout": "invoice-auditing-level-2/",
        "files": files,
        "records": {"path": rel(sources.records_dir), "kind": "site records (.txt)", "files": count, "tree_sha256": tree_digest},
        "task_wide": [{"path": rel(template), "kind": "submission template (all domains)", "bytes": template.stat().st_size,
                       "sha256": sha256_file(template), "data_rows": _csv_rows(template)}],
    }


@dataclass(frozen=True)
class BuildResult:
    written: list[Path]
    applications: int
    lines: int
    records: int
    record_issues: int


def build(data_root: Path, artifacts_dir: Path) -> BuildResult:
    sources = CivilWorksSources.from_data_root(data_root)
    extraction_path = artifacts_dir / EXTRACTION_FILENAME
    raw = load_raw_extraction(extraction_path)
    terms = terms_from_raw(raw)  # validates schema and provenance, raises if invalid
    if sha256_file(sources.contract_pdf) != terms.source_sha256:
        raise ValueError("contract PDF does not match the sha256 recorded in the reviewed extraction")

    apps = load_applications(sources.applications_csv)
    lines = load_application_lines(sources.application_lines_csv)
    record_set = load_records(sources.records_dir)
    inventory = record_inventory(record_set)
    profile = source_profile(apps, lines, record_set, terms)

    written = []

    def emit(name: str, content) -> None:
        path = artifacts_dir / name
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            write_json(path, content)
        written.append(path)

    emit(SOURCE_INVENTORY, source_inventory(sources, data_root))
    emit("contract_extraction.md", render_contract_extraction(raw))
    emit("contract_verification.md", render_contract_verification(raw, list(iter_provenance(raw)), raw["extraction"]["cross_check"]))
    emit("record_inventory.json", inventory)
    emit("record_inventory.md", render_record_inventory(inventory))
    emit("source_profile.json", profile)
    emit("source_profile.md", render_source_profile(profile, terms.contract_ref))

    # Phase 2: pricing mechanics (descriptive; no findings).
    quantities = extract_all(record_set.records)
    timeline = rate_timeline(terms)
    emit("rate_timeline.json", timeline)
    emit("rate_timeline.md", render_rate_timeline(timeline))
    emit("interpretation_matrix.md", render_interpretation_matrix())
    emit("pricing_model.md", render_pricing_model(terms))
    parsing = quantity_parsing(quantities, lines)
    emit("quantity_parsing.json", parsing)
    emit("quantity_parsing.md", render_quantity_parsing(parsing))
    sensitivity = run_sensitivity(terms, apps, lines, {q.record_id: q for q in quantities})
    emit("sensitivity.json", sensitivity)
    emit("sensitivity.md", render_sensitivity(sensitivity))
    return BuildResult(written, len(apps), len(lines), len(record_set.records), len(record_set.issues))
