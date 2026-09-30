"""Phase 3 artifacts: service mapping, quantities, switches/ambiguities, and their readable summaries.

Mapping and coverage statistics only. Nothing here prices, compares with billing or makes a finding.
"""

import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DailyReport
from contractor_audit.domains.drilling.interpretation.ambiguity import vocabularies
from contractor_audit.domains.drilling.interpretation.models import InterpretationResult, MappingStatus, Quantity
from contractor_audit.domains.drilling.interpretation.switches import Switch

MAPPING_JSON, MAPPING_MD = "phase3_service_mapping.json", "phase3_service_mapping.md"
QUANTITIES_JSON, QUANTITIES_MD = "phase3_quantities.json", "phase3_quantity_summary.md"
AMBIGUITIES_JSON = "phase3_ambiguities.json"
GENERATED = (MAPPING_JSON, MAPPING_MD, QUANTITIES_JSON, QUANTITIES_MD, AMBIGUITIES_JSON)
NOTE = "Phase 3 mapping and coverage statistics from the Daily Drilling Reports. Not prices, not findings; no invoice data was read."


def _reading_key(q: Quantity) -> str:
    return ";".join(f"{s}={v}" for s, v in q.readings) or "(reading-independent)"


def _num(value: Decimal) -> str:
    return str(int(value)) if value == value.to_integral_value() else format(value.normalize(), "f")


def canonical_digest(result: InterpretationResult) -> str:
    """sha256 over every quantity in a stable text form, so regeneration can be checked byte for byte."""
    h = hashlib.sha256()
    for q in result.quantities:
        h.update(f"{q.qid}\t{q.quantity}\t{q.unit}\t{','.join(q.report_ids)}\t{';'.join(f'{e.report_id}:{e.section}:{e.label}={e.raw_value}' for e in q.evidence)}\n".encode())
    return h.hexdigest()


# --------------------------------------------------------------------------- metrics
def mapping_metrics(result: InterpretationResult, terms: ContractTerms, reports: list[DailyReport]) -> dict:
    by_status = Counter(m.status.value for m in result.mappings)
    per_term = defaultdict(Counter)
    for m in result.mappings:
        per_term[(m.source_field.label, m.term)][m.status.value] += 1
    vocabs = vocabularies(terms)
    multi = {reading: sorted(t for t, codes in v.codes.items() if len(codes) > 1) for reading, v in vocabs.items()}
    unsupported_terms = sorted({m.term for m in result.mappings if m.status is MappingStatus.UNSUPPORTED}
                               | {m.term for m in result.mappings for r in vocabs if m.status is MappingStatus.UNRESOLVED_INTERPRETATION
                                  and not [c for c in m.candidates if ("appendix_g_reading", r) in c.readings]})
    evidenced = defaultdict(set)
    for q in result.quantities:
        evidenced[q.service_code].add(_reading_key(q))
    reports_with_service = {rid for q in result.quantities for rid in q.report_ids}
    return {
        "reports_interpreted": result.reports_interpreted,
        "reports_in_dataset": len(reports),
        "reports_with_at_least_one_mapped_service": len(reports_with_service),
        "term_mappings": len(result.mappings),
        "term_mappings_by_status": dict(sorted(by_status.items())),
        "deterministic_term_mappings": sum(v for k, v in by_status.items() if MappingStatus(k).deterministic),
        "ambiguous_term_mappings": by_status.get("AMBIGUOUS", 0),
        "switch_dependent_term_mappings": by_status.get("UNRESOLVED_INTERPRETATION", 0),
        "terms": [{"field": f, "term": t, "statuses": dict(sorted(c.items())),
                   "codes_literal": list(vocabs["LITERAL"].codes.get(t, ())), "codes_lwd_rows_shifted": list(vocabs["LWD_ROWS_SHIFTED"].codes.get(t, ()))}
                  for (f, t), c in sorted(per_term.items())],
        "terms_with_no_candidate_under_some_reading": unsupported_terms,
        "report_terms_mapping_to_more_than_one_code": multi,
        "service_coverage": {"services_in_schedule_1": len(terms.services),
                             "services_evidenced_under_some_reading": len(evidenced),
                             "services_never_evidenced": sorted(set(terms.services) - set(evidenced)),
                             "services_evidenced_only_under_some_readings": sorted(
                                 c for c, keys in evidenced.items() if "(reading-independent)" not in keys and any("appendix_g_reading" in k for k in keys)
                                 and not all(any(f"appendix_g_reading={r}" in k for k in keys) for r in vocabs))},
    }


def quantity_metrics(result: InterpretationResult) -> dict:
    by_basis = Counter(q.basis.value for q in result.quantities)
    groups = defaultdict(list)
    for q in result.quantities:
        groups[(q.service_code, _reading_key(q))].append(q)
    rows = []
    for (code, key), qs in sorted(groups.items()):
        conds = Counter(f"{c.code}={c.satisfied}" for q in qs for c in q.conditions)
        rows.append({"service": code, "readings": key, "unit": qs[0].unit, "basis": qs[0].basis.value, "records": len(qs),
                     "total_quantity": _num(sum(q.quantity for q in qs)), "wells": len({q.well for q in qs}),
                     "by_day_status": dict(sorted(Counter(q.day_status or "n/a" for q in qs).items())),
                     "conditions": dict(sorted(conds.items())), "derivations": sorted({q.derivation for q in qs})})
    switch_counts = defaultdict(Counter)
    for q in result.quantities:
        for s, v in q.readings:
            switch_counts[s][v] += 1
    return {"quantities": len(result.quantities), "by_basis": dict(sorted(by_basis.items())),
            "reading_independent_quantities": sum(1 for q in result.quantities if not q.readings),
            "switch_dependent_quantities": sum(1 for q in result.quantities if q.readings),
            "quantities_by_switch_reading": {s: dict(sorted(c.items())) for s, c in sorted(switch_counts.items())},
            "by_service_and_reading": rows, "canonical_sha256": canonical_digest(result)}


def affected(result: InterpretationResult) -> dict:
    by_amb = defaultdict(set)
    by_switch = defaultdict(set)
    for q in result.quantities:
        for a in q.ambiguity_ids:
            by_amb[a].update(q.report_ids)
        for s, _ in q.readings:
            by_switch[s].update(q.report_ids)
        for s in q.depends_on:
            by_switch[s].update(q.report_ids)
    for m in result.mappings:
        for c in m.candidates:
            by_amb.update({a: by_amb[a] | {m.report_id} for a in c.ambiguity_ids})
    return {"reports_by_ambiguity": {k: len(v) for k, v in sorted(by_amb.items())},
            "reports_by_switch": {k: len(v) for k, v in sorted(by_switch.items())}}


def evidence_facts(reports: list[DailyReport], terms: ContractTerms) -> list[dict]:
    """Report facts that bear on open ambiguities, computed from the reports only. Recorded, never used to choose."""
    literal = vocabularies(terms)["LITERAL"]
    word = lambda code: literal.term_for(code)[0]  # noqa: E731  (the contract's own Appendix G term)
    runs = defaultdict(list)
    for r in reports:
        if r.bha_run and r.operations:
            runs[(r.well, r.bha_run.run)].append(r)
    first = [sorted(rs, key=lambda r: r.date)[0] for rs in runs.values()]
    tools = lambda r: set(r.bha_run.tools_in_run)  # noqa: E731
    g, res, dn, ho = word("LW-410"), word("LW-411"), word("LW-412"), word("RM-511")
    logging_crew, perf_crew = word("LW-401"), word("PD-201")
    lwd_words = {g, res, dn}
    ops = [r for r in reports if r.operations]
    return [
        {"ambiguities": ["AMB-17", "AMB-24"], "fact": f"Runs whose tools include '{g}' (literal LW-410) and runs with Part B metres logged > 0.",
         "runs": len(first), f"runs_with_{g.replace(' ', '_')}": sum(g in tools(r) for r in first),
         "runs_with_metres_logged": sum(bool(r.bha_run.metres_logged) for r in first),
         "runs_where_both_hold": sum(g in tools(r) and bool(r.bha_run.metres_logged) for r in first)},
        {"ambiguities": ["AMB-17"], "fact": f"Runs whose tools include '{res}' (literal LW-411 density and neutron) and runs carrying a radioactive source (T9: density and neutron need one).",
         f"runs_with_{res.replace(' ', '_')}": sum(res in tools(r) for r in first),
         "runs_carrying_source": sum(bool(r.bha_run.radioactive_source_carried) for r in first),
         "runs_where_both_hold": sum(res in tools(r) and bool(r.bha_run.radioactive_source_carried) for r in first),
         f"runs_with_{dn.replace('-', '_')}": sum(dn in tools(r) for r in first)},
        {"ambiguities": ["AMB-24"], "fact": f"Runs whose tools include '{ho}' (RM-511, the underreamer of cl. 25) and runs with metres reamed > 0.",
         f"runs_with_{ho.replace(' ', '_')}": sum(ho in tools(r) for r in first), "runs_with_metres_reamed": sum(bool(r.bha_run.metres_reamed) for r in first),
         "runs_where_both_hold": sum(ho in tools(r) and bool(r.bha_run.metres_reamed) for r in first)},
        {"ambiguities": ["AMB-17"], "fact": f"Days with '{logging_crew}' on tour, and days with any literal LWD tool word in the hole.",
         "days_with_logging_crew": sum(any(c.role == logging_crew for c in r.operations.crew) for r in ops),
         "days_with_lwd_word": sum(bool(set(r.operations.in_the_hole) & lwd_words) for r in ops),
         "days_where_both_hold": sum(any(c.role == logging_crew for c in r.operations.crew) and bool(set(r.operations.in_the_hole) & lwd_words) for r in ops)},
        {"ambiguities": ["AMB-13"], "fact": f"Hole sections on days with '{perf_crew}' on tour (performance-drilled sections are nominated in call-offs, which are not provided).",
         "sections": dict(sorted(Counter(r.operations.hole_section for r in ops if any(c.role == perf_crew for c in r.operations.crew)).items()))},
        {"ambiguities": ["AMB-05", "AMB-06", "AMB-20"], "fact": "Standby days: circulating hours are still recorded on some; the rotary steerable is in the hole on some.",
         "standby_days": sum(r.operations.status == "Standby" for r in ops),
         "standby_days_with_circulating_hours": sum(r.operations.status == "Standby" and bool(r.operations.circulating_hours) for r in ops),
         "standby_days_with_rss_in_hole": sum(r.operations.status == "Standby" and word("DD-120") in r.operations.in_the_hole for r in ops)},
        {"ambiguities": ["AMB-14", "AMB-23"], "fact": "Records named by Schedule 5 that are absent on a day they apply (structural; consequence undecided).",
         "gyro_count_without_part_c": sorted(r.report_id for r in ops if r.operations.gyro_surveys and r.gyro is None),
         "source_runs_without_part_d_on_first_day": sorted(r.report_id for r in first if r.bha_run.radioactive_source_carried and r.source_handling is None)},
    ]


def switch_table(switches: dict[str, Switch], result: InterpretationResult) -> list[dict]:
    counts = defaultdict(Counter)
    for q in result.quantities:
        for s, v in q.readings:
            counts[s][v] += 1
    return [{"name": s.name, "ambiguity": s.ambiguity_id, "applies_in": s.applies_in.value,
             "readings": [{"value": r.value, "ambiguity_reading": r.ambiguity_reading, "description": r.description,
                           "phase3_quantities": counts[s.name].get(r.value, 0)} for r in s.readings],
             "default": s.default, "default_basis": s.default_basis, "requires_approval": s.requires_approval,
             "explanation": s.explanation} for s in switches.values()]


# --------------------------------------------------------------------------- writing
def build(result: InterpretationResult, reports: list[DailyReport], terms: ContractTerms, switches: dict[str, Switch]) -> dict[str, dict]:
    head = {"schema_version": "1.0", "note": NOTE}
    return {
        MAPPING_JSON: {**head, "schema": "contractor-audit/drilling-phase3-service-mapping", **mapping_metrics(result, terms, reports)},
        QUANTITIES_JSON: {**head, "schema": "contractor-audit/drilling-phase3-quantities", **quantity_metrics(result)},
        AMBIGUITIES_JSON: {**head, "schema": "contractor-audit/drilling-phase3-ambiguities", "switches": switch_table(switches, result),
                           **affected(result), "evidence_facts": evidence_facts(reports, terms)},
    }


def _md_mapping(d: dict) -> str:
    lines = ["# Drilling Phase 3 — service mapping", "", d["note"], "",
             f"- reports interpreted: {d['reports_interpreted']:,} of {d['reports_in_dataset']:,}; with at least one mapped service: {d['reports_with_at_least_one_mapped_service']:,}",
             f"- term mappings: {d['term_mappings']:,} — deterministic {d['deterministic_term_mappings']:,}, ambiguous {d['ambiguous_term_mappings']:,}, switch-dependent {d['switch_dependent_term_mappings']:,}",
             f"- by status: {d['term_mappings_by_status']}",
             f"- service coverage: {d['service_coverage']}",
             f"- terms with no candidate under some reading: {d['terms_with_no_candidate_under_some_reading']}",
             f"- terms mapping to more than one code: {d['report_terms_mapping_to_more_than_one_code']}", "",
             "| field | term | statuses | codes (literal) | codes (LWD rows shifted) |", "|---|---|---|---|---|"]
    lines += [f"| {t['field']} | {t['term']} | {t['statuses']} | {', '.join(t['codes_literal'])} | {', '.join(t['codes_lwd_rows_shifted'])} |" for t in d["terms"]]
    return "\n".join(lines) + "\n"


def _md_quantities(q: dict, a: dict) -> str:
    lines = ["# Drilling Phase 3 — quantity summary", "", q["note"], "",
             f"- quantities: {q['quantities']:,} (reading-independent {q['reading_independent_quantities']:,}; switch-dependent {q['switch_dependent_quantities']:,})",
             f"- by basis: {q['by_basis']}", f"- canonical sha256: `{q['canonical_sha256']}`", "",
             "| service | readings | basis | unit | records | total | wells | day status | conditions |", "|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {r['service']} | {r['readings']} | {r['basis']} | {r['unit']} | {r['records']:,} | {r['total_quantity']} | {r['wells']} | {r['by_day_status']} | {r['conditions']} |"
              for r in q["by_service_and_reading"]]
    lines += ["", "## Interpretation switches", "", "| switch | ambiguity | applies in | readings (Phase 3 quantities) | default | approval needed |", "|---|---|---|---|---|---|"]
    lines += [f"| {s['name']} | {s['ambiguity']} | {s['applies_in']} | {', '.join(f'{r['value']} ({r['phase3_quantities']})' for r in s['readings'])} | {s['default'] or '—'} | {'yes' if s['requires_approval'] else 'no'} |"
              for s in a["switches"]]
    lines += ["", "## Reports affected", "", f"- by ambiguity: {a['reports_by_ambiguity']}", f"- by switch: {a['reports_by_switch']}", "",
              "## Evidence facts (recorded, not used to choose a reading)", ""]
    lines += [f"- **{', '.join(e['ambiguities'])}** {e['fact']} {({k: v for k, v in e.items() if k not in ('ambiguities', 'fact')})}" for e in a["evidence_facts"]]
    return "\n".join(lines) + "\n"


def write(result: InterpretationResult, reports: list[DailyReport], terms: ContractTerms, switches: dict[str, Switch], artifacts_dir: Path) -> list[Path]:
    data = build(result, reports, terms, switches)
    texts = {name: json.dumps(obj, indent=1, ensure_ascii=False) + "\n" for name, obj in data.items()}
    texts[MAPPING_MD] = _md_mapping(data[MAPPING_JSON])
    texts[QUANTITIES_MD] = _md_quantities(data[QUANTITIES_JSON], data[AMBIGUITIES_JSON])
    out = []
    for name in GENERATED:
        path = artifacts_dir / name
        path.write_text(texts[name], encoding="utf-8", newline="\n")
        out.append(path)
    return out
