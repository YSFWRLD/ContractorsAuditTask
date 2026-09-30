"""Phase 1 artifacts: the source manifest and readable renderings of the reviewed contract files.

Writes only derived files next to the reviewed JSON; never edits the reviewed files, never reads invoices.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from contractor_audit.domains.drilling.contract.loader import (
    AMBIGUITIES_FILENAME, TERMS_FILENAME, ContractTermsError, load_ambiguities, load_contract_terms, load_raw,
)
from contractor_audit.domains.drilling.sources import DrillingSources
from contractor_audit.shared.provenance import sha256_file, sha256_tree

MANIFEST_FILENAME = "source_manifest.json"
TERMS_MD = "contract_terms.md"
AMBIGUITIES_MD = "contract_ambiguities.md"
GENERATED = (MANIFEST_FILENAME, TERMS_MD, AMBIGUITIES_MD)


@dataclass
class BuildResult:
    written: list[Path] = field(default_factory=list)


def source_manifest(sources: DrillingSources, data_root: Path) -> dict:
    rel = lambda p: p.relative_to(data_root).as_posix()  # noqa: E731
    files = []
    for kind, path in (("contract (scanned PDF)", sources.contract_pdf), ("audit guidelines", sources.guidelines),
                       ("invoices", sources.invoices_csv), ("invoice lines", sources.invoice_lines_csv)):
        files.append({"path": rel(path), "kind": kind, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    digest, count = sha256_tree(sources.records_dir, "*.txt")
    other = sorted(rel(p) for p in sources.root.rglob("*") if p.is_file()
                   and p.parent != sources.records_dir and p not in (sources.contract_pdf, sources.guidelines,
                                                                      sources.invoices_csv, sources.invoice_lines_csv))
    return {"domain": "drilling", "root": rel(sources.root), "files": files,
            "records": {"path": rel(sources.records_dir), "kind": "Daily Drilling Reports (.txt)", "files": count, "tree_sha256": digest},
            "unclassified_files": other}


def build(data_root: Path, artifacts_dir: Path) -> BuildResult:
    """Validate the reviewed contract files against the PDF they were read from, then write the derived artifacts."""
    sources = DrillingSources.from_data_root(data_root)
    terms_path, amb_path = artifacts_dir / TERMS_FILENAME, artifacts_dir / AMBIGUITIES_FILENAME
    terms = load_contract_terms(terms_path, amb_path)
    if sha256_file(sources.contract_pdf) != terms.source_sha256:
        raise ContractTermsError("contract PDF does not match the sha256 recorded in contract_terms.json")
    result = BuildResult()

    def emit(name: str, text: str) -> None:
        path = artifacts_dir / name
        path.write_text(text, encoding="utf-8", newline="\n")
        result.written.append(path)

    emit(MANIFEST_FILENAME, json.dumps(source_manifest(sources, data_root), indent=1) + "\n")
    emit(TERMS_MD, render_terms(load_raw(terms_path)))
    emit(AMBIGUITIES_MD, render_ambiguities(load_raw(amb_path), load_ambiguities(amb_path)))
    return result


# --------------------------------------------------------------------------- rendering
def _money(cents: int | None) -> str:
    if cents is None:
        return "—"
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def _table(header: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join("" if c is None else str(c) for c in row) + " |" for row in rows]
    return out + [""]


def render_terms(raw: dict) -> str:
    ident, ex = raw["identity"], raw["extraction"]
    lines = ["# DDS-2025-118 — reviewed contract terms", "",
             "Generated from `contract_terms.json` by `build-artifacts --domain drilling`. The JSON is the source of truth; "
             "every value there carries page, section and source text.", "",
             f"Extraction: {ex['method']} Passes: {ex['passes']}; {ex['cross_check']['leaf_values_compared']} table values compared, "
             f"{ex['cross_check']['discrepancies']} discrepancies.", "", "## Sources", ""]
    lines += _table(["file", "sha256", "pages"], [[f["file"], f["sha256"][:16] + "…", f["pages"]] for f in raw["source_files"]])
    lines += ["## Documents in the package", ""]
    lines += _table(["id", "title", "pages", "in Contents", "in Clause 2", "issued", "effective"],
                    [[d["id"], d["title"], f"{d['pages'][0]}-{d['pages'][1]}", "yes" if d["in_contents"] else "**no**",
                      "yes" if d["listed_in_clause_2"] else "**no**", d.get("issued", ""), d.get("effective", "")] for d in raw["documents"]])
    lines += ["## Identity", ""]
    lines += _table(["term", "value", "status", "page"],
                    [[k, v["value"] if not isinstance(v["value"], dict) else ", ".join(f"{a}={b}" for a, b in v["value"].items()),
                      v["status"], v["provenance"][0]["page"]] for k, v in ident.items() if isinstance(v, dict) and "value" in v])
    lines += ["Expiry extensions: " + "; ".join(f"{e['instrument']} -> {e['new_expiry']} (+{e['extension_days']} days, issued {e['issued']})"
                                                 for e in ident["expiry_extensions"]), ""]
    lines += ["## Precedence", ""] + [f"- **{r['id']}** {r['rule']} (p.{r['provenance'][0]['page']})" for r in raw["precedence"]["rules"]]
    lines += ["", "Unranked: " + ", ".join(raw["precedence"]["unranked_documents"]) + ". " + raw["precedence"]["unranked_note"], ""]
    lines += ["## Service catalog (Schedule 1)", ""]
    lines += _table(["code", "description", "unit", "rate", "section", "class", "standby", "limit/day", "record", "index", "monthly", "amended", "discount", "Appendix G terms"],
                    [[s["code"], s["description"], s["unit"], s["rate"]["printed"], "✓" if s["section_rated"] else "", "✓" if s["class_rated"] else "",
                      (s["standby"]["percent"] + "%") if s["standby"]["treatment"] == "PERCENT" else s["standby"]["treatment"].lower().replace("_", " "),
                      f"{s['daily_limit']['quantity']} {s['daily_limit']['unit']}" if s["daily_limit"] else "", s["record_part_required"] or "",
                      "✓" if s["indexed"] else "", s["monthly_republished_by"] or "", ",".join(s["rate_amended_by"]), ",".join(s["rate_discounted_by"]),
                      "; ".join(s["appendix_g_terms"])] for s in raw["services"]])
    d = raw["invoice_discount"]
    lines += [f"DS-900 (Clause 38, not a Schedule 1 service): {d['percent']}% of the excess over {_money(d['threshold_cents'])} ({d['comparison']}), per invoice.", ""]
    lines += ["## Instruments (in the order issued)", ""]
    rows = []
    for ins in raw["instruments"]:
        for ch in ins["changes"]:
            if ch["kind"] == "RATE_SUBSTITUTION":
                what = f"{ch['code']} {_money(ch['previous_rate_cents'])} → {_money(ch['rate_cents'])} from {ch['effective']}"
            elif ch["kind"] == "MONTHLY_RATES":
                what = f"{ch['code']} monthly {min(ch['months'])}..{max(ch['months'])} ({', '.join(_money(v) for v in ch['months'].values())}); last carries forward"
            elif ch["kind"] == "RATE_DISCOUNT":
                what = f"{ch['percent']}% on {', '.join(ch['codes'])} from {ch['effective']}"
            else:
                what = f"expiry → {ch['new_expiry']} (+{ch['extension_days']} days)"
            rows.append([ins["id"], ins["issued"], ins["effective"], "**yes**" if ins["retroactive"] else "", ch["kind"], what, ins["page"]])
    lines += _table(["instrument", "issued", "effective", "retroactive", "change", "detail", "page"], rows)
    cb = raw["cost_build_up"]
    lines += ["## Cost build-up (stated order; not executed here)", ""]
    lines += [f"{o['step']}. {o['name']} — {o['applies_when']} (cl. {o['clause']})" for o in cb["order"]] + [""]
    lines += ["Hole-section factors: " + ", ".join(f"{k} {v}" for k, v in cb["hole_section_factors"].items()) +
              f" (section-rated: {', '.join(cb['section_rated_services'])})",
              "Well-class factors: " + ", ".join(f"{k} {v}" for k, v in cb["well_class_factors"].items()) +
              f" (class-rated as printed: {', '.join(cb['class_rated_services_as_printed'])})", ""]
    lines += ["Exclusions stated in Part IX / Part VI: "] + [f"- {e['rule']} (cl. {e['clause']}, {e['status']})" for e in cb["exclusions"]] + [""]
    lines += ["## PD-210 depth bands and Contract-Year tiers", ""]
    lines += _table(["band", "over m", "to m", "rate"], [[b["band"], b["over_m"], b["to_m"] or "—", _money(b["rate_cents"])] for b in raw["depth_bands"]["bands"]])
    lines += _table(["tier", "from m", "to m", "% of rate"], [[t["band"], t.get("from_m", f">{t.get('above_m')}"), t.get("to_m", "—"), t["percent_of_rate"]] for t in raw["volume_tiers"]["tiers"]])
    lines += [f"Tier scope: {raw['volume_tiers']['scope']}", ""]
    pi = raw["price_index"]
    lines += ["## Rig Services Index (Schedule 2C, Clause 17A)", "",
              f"Base {pi['base_index']}; services " + ", ".join(f"{s['code']} base {_money(s['base_rate_cents'])}" for s in pi["services"]), ""]
    lines += _table(["month", "index"], [[m, v] for m, v in pi["monthly_index"].items()])
    lih = raw["lost_in_hole"]
    lines += ["## Lost in hole (Clause 31, 31A, Schedules 2D and 6)", ""]
    lines += _table(["code", "SAR (2D)", "USD as let (6)"], [[c, _money(v["value_halalas"]), _money(lih["replacement_values_usd_as_let"][c]["value_cents"])]
                                                           for c, v in lih["replacement_values_sar"].items()])
    dep = lih["depreciation"]
    lines += [f"Depreciation {dep['percent_per_block']}% per complete {dep['block_hours']} circulating hours, cap {dep['cap_percent']}%. {lih['conversion']}.", ""]
    lines += _table(["month", "halalas per USD"], [[m, v] for m, v in lih["exchange_rates"]["months"].items()])
    lines += ["## Appendix G — report terms (as printed)", ""]
    lines += _table(["row", "code", "Schedule 1 description", "report term"],
                    [[r["row"], r["code"], r["schedule_1_description"], r["report_term"]] for r in raw["appendix_g"]["rows"]])
    lines += ["## Evidence not provided", ""] + [f"- **{e['id']}** {e['item']}: {e['needed_for']}" for e in raw["evidence_not_provided"]] + [""]
    return "\n".join(lines)


def render_ambiguities(raw: dict, typed) -> str:
    lines = ["# DDS-2025-118 — ambiguity register", "",
             "Generated from `contract_ambiguities.json`. " + raw["method"], ""]
    lines += _table(["id", "title", "status", "preferred", "confidence", "affects totals", "resolve in"],
                    [[a["id"], a["title"], a["status"], a["preferred_reading"] or "—", a["confidence"] or "—", a["affects_totals"], a["resolve_in_phase"]]
                     for a in raw["ambiguities"]])
    for a in raw["ambiguities"]:
        lines += [f"## {a['id']} — {a['title']}", "", a["issue"], "",
                  "Sources: " + ", ".join(f"p.{loc['page']} {loc['section']}" for loc in a["source_locations"]), ""]
        for r in a["readings"]:
            lines.append(f"- **Reading {r['id']}.** {r['reading']}")
            lines += [f"  - p.{e['page']} {e['section']}: “{e['source_text']}”" for e in r["evidence"]]
        lines += ["", f"Preferred: {a['preferred_reading'] or 'none'} ({a['confidence'] or 'no preference'}). {a['preference_basis']}",
                  f"Status: {a['status']}. Phase 0 check: {a['phase0_check']}.", ""]
    assert len(typed) == len(raw["ambiguities"])
    return "\n".join(lines)
