"""Descriptive comparison of billed service codes with report evidence. Reporting only.

This is the only Phase 3 module that reads invoice lines, and it reads them after interpretation has
finished: nothing here feeds back into mapping, quantities or readings. It compares *codes* (is there
report evidence for the code a line cites?), never quantities, prices or amounts, and makes no finding.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

from contractor_audit.domains.drilling.ingestion.indexes import DrillingIndexes
from contractor_audit.domains.drilling.interpretation.models import InterpretationResult

JSON_NAME, MD_NAME = "phase3_billed_coverage.json", "phase3_billed_coverage.md"
GENERATED = (JSON_NAME, MD_NAME)
NOTE = ("Descriptive coverage of billed service codes by report evidence, and the report/code pairs cited by several "
        "billed lines. Codes only; no quantity, price or amount is compared, and none of this is a finding.")


def build(result: InterpretationResult, ix: DrillingIndexes) -> dict:
    evidenced = defaultdict(lambda: defaultdict(set))   # report -> code -> set of reading keys
    for q in result.quantities:
        key = ";".join(f"{s}={v}" for s, v in q.readings) or "*"
        for rid in q.report_ids:
            evidenced[rid][q.service_code].add(key)
    per_code = defaultdict(Counter)
    for line in sorted((l for rid in ix.lines_by_report_ref.keys() for l in ix.lines_by_report_ref.get(rid)), key=lambda l: l.line_ref):
        keys = evidenced.get(line.report_ref, {}).get(line.service_code)
        per_code[line.service_code]["billed_lines_citing_a_report"] += 1
        if not keys:
            per_code[line.service_code]["no_report_evidence_for_the_code"] += 1
        elif "*" in keys:
            per_code[line.service_code]["evidenced_reading_independent"] += 1
        else:
            per_code[line.service_code]["evidenced_under_some_readings_only"] += 1
    unreferenced = Counter(l.service_code for l in ix.lines_by_report_ref.unkeyed)
    multi = []
    for (rid, code), lines in ix.lines_by_report_and_code.duplicates().items():
        multi.append({"report": rid, "service_code": code, "lines": [l.line_ref for l in lines],
                      "invoices": sorted({l.invoice_no for l in lines}),
                      "depth_intervals": [[l.depth_from_m, l.depth_to_m] for l in lines],
                      "distinct_depth_intervals": len({(l.depth_from_m, l.depth_to_m) for l in lines}) == len(lines)
                      and all(l.depth_from_m is not None for l in lines),
                      "report_evidence_for_code": sorted(evidenced.get(rid, {}).get(code, set()))})
    return {"schema": "contractor-audit/drilling-phase3-billed-coverage", "schema_version": "1.0", "note": NOTE,
            "by_billed_code": {c: dict(sorted(v.items())) for c, v in sorted(per_code.items())},
            "billed_lines_without_report_reference": dict(sorted(unreferenced.items())),
            "report_code_pairs_with_multiple_billed_lines": {"count": len(multi),
                                                             "by_code": dict(sorted(Counter(m["service_code"] for m in multi).items())),
                                                             "pairs": multi}}


def write(result: InterpretationResult, ix: DrillingIndexes, artifacts_dir: Path) -> list[Path]:
    data = build(result, ix)
    md = ["# Drilling Phase 3 — billed-code coverage (descriptive)", "", NOTE, "",
          "| billed code | lines citing a report | evidenced (any reading) | evidenced only under some readings | no report evidence for the code |",
          "|---|---|---|---|---|"]
    for code, c in data["by_billed_code"].items():
        md.append(f"| {code} | {c.get('billed_lines_citing_a_report', 0):,} | {c.get('evidenced_reading_independent', 0):,} | "
                  f"{c.get('evidenced_under_some_readings_only', 0):,} | {c.get('no_report_evidence_for_the_code', 0):,} |")
    pairs = data["report_code_pairs_with_multiple_billed_lines"]
    md += ["", f"Lines without a report reference: {data['billed_lines_without_report_reference']}", "",
           f"Report/code pairs cited by several billed lines: {pairs['count']} {pairs['by_code']}", ""]
    md += [f"- {p['report']} {p['service_code']}: {', '.join(p['lines'])} intervals {p['depth_intervals']}"
           for p in pairs["pairs"] if not p["distinct_depth_intervals"]]
    out = []
    for name, text in ((JSON_NAME, json.dumps(data, indent=1) + "\n"), (MD_NAME, "\n".join(md) + "\n")):
        path = artifacts_dir / name
        path.write_text(text, encoding="utf-8", newline="\n")
        out.append(path)
    return out
