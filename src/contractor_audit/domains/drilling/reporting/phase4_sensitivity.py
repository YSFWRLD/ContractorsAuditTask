"""Phase 4 artifacts: sensitivity of every approved reading, the well-class scenarios, and the decision record.

The reference is the canonical selection (approved and text-resolved readings only). Each approved switch is
flipped alone to each other reading; the flipped results are hypothetical and never canonical. AMB-13 is
approved as UNKNOWN / UNVERIFIED, so the class scenarios show what each possible well class (and the
contractor's claimed class, unverified) would do; none is selected. Every figure is a total of priced report
evidence, never an invoice figure, and no invoice is compared or flagged.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

from contractor_audit.domains.drilling.contract.models import Ambiguity, ContractTerms, RateBasis
from contractor_audit.domains.drilling.ingestion.models import DrillingDataset
from contractor_audit.domains.drilling.interpretation.models import InterpretationResult
from contractor_audit.domains.drilling.interpretation.switches import NOT_DERIVED, Switch
from contractor_audit.domains.drilling.pricing.affected import affected_services
from contractor_audit.domains.drilling.pricing.engine import price
from contractor_audit.domains.drilling.pricing.models import PricingResult
from contractor_audit.domains.drilling.pricing.selection import PRICING_SWITCHES, Choice, Selection, Source, build_selection

SENSITIVITY_JSON, SENSITIVITY_MD, DECISION_MD = "phase4_pricing_sensitivity.json", "phase4_pricing_sensitivity.md", "phase4_decision_table.md"
GENERATED = (SENSITIVITY_JSON, SENSITIVITY_MD, DECISION_MD)
NOTE = ("Reference: the canonical selection (approved and contract-text readings). Each approved reading is flipped alone to each "
        "alternative; flipped figures are HYPOTHETICAL, never canonical. Totals of priced report evidence only: no invoice is compared, "
        "flagged or totalled.")


def claimed_well_classes(dataset: DrillingDataset) -> dict[str, str]:
    """The contractor's claimed class per well, from the invoice headers. Unverified; never evidence of entitlement."""
    return {i.well_name: i.well_class_stated for i in dataset.invoices}


def canonical_selection(switches: dict[str, Switch], approved: dict[str, Choice]) -> Selection:
    return build_selection(switches, approved)


def _money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def _flip(result, terms, switches, ref: Selection, base: PricingResult, name: str, reading: str, classes, background_classes, services) -> dict:
    sel = ref.with_choice(name, reading, Source.HYPOTHETICAL)
    wc = classes if (name == "calloff_evidence" and reading == "INVOICE_STATEMENT_UNVERIFIED") else background_classes
    alt = price(result, terms, switches, sel, wc, services)
    by_qid = {p.qid: p for p in base.priced if p.service_code in services}
    alt_qids = {p.qid for p in alt.priced}
    changed = sum(1 for p in alt.priced if p.qid not in by_qid or by_qid[p.qid].amount_cents != p.amount_cents)         + sum(1 for q in by_qid if q not in alt_qids)
    per_service = defaultdict(int)
    for p in alt.priced:
        per_service[p.service_code] += p.amount_cents
    for p in by_qid.values():
        per_service[p.service_code] -= p.amount_cents
    base_total = sum(p.amount_cents for p in by_qid.values())
    return {"switch": name, "ambiguity": switches[name].ambiguity_id, "approved": ref.value(name), "alternative": reading,
            "services": sorted(services), "approved_total_cents": base_total, "alternative_total_cents": alt.total_cents(),
            "delta_cents": alt.total_cents() - base_total, "quantities_changed": changed,
            "status_approved": dict(sorted(Counter(p.status.value for p in by_qid.values()).items())),
            "status_alternative": dict(sorted(Counter(p.status.value for p in alt.priced).items())),
            "delta_by_service_cents": {k: v for k, v in sorted(per_service.items()) if v}}


def class_scenarios(result, terms, switches, ref: Selection, classes: dict[str, str]) -> dict:
    """What each possible well class would do to the services that need it. Hypothetical; nothing is selected."""
    services = {c for c, d in terms.services.items() if d.class_rated and (d.rate_basis is not RateBasis.SCHEDULE_2 or ref.value("pd210_class_factor") == "APPLY")}
    sel = ref.with_choice("calloff_evidence", "INVOICE_STATEMENT_UNVERIFIED", Source.HYPOTHETICAL)
    wells = sorted(set(classes) | {q.well for q in result.quantities})
    rows = []
    for label, mapping in [(f"every well {c}", {w: c for w in wells}) for c in terms.class_factors] + [("contractor's claimed class (unverified)", classes)]:
        r = price(result, terms, switches, sel, mapping, services)
        rows.append({"scenario": label, "services": sorted(services), "priced_quantities": sum(p.status.value == "PRICED" for p in r.priced),
                     "total_cents": r.total_cents(),
                     "by_service_cents": dict(sorted(Counter({s: sum(p.amount_cents for p in r.priced if p.service_code == s) for s in services}).items()))})
    eligibility = price(result, terms, switches, sel, classes, {"PD-210"})
    pd201 = [p for p in price(result, terms, switches, ref, None, {"PD-201"}).priced if p.conditional_amount_cents is not None]
    return {"class_rated_services": sorted(services), "scenarios": rows,
            "claimed_classes": dict(sorted(Counter(classes.values()).items())),
            "pd210_if_every_allowed_size_day_were_nominated": {"priced_quantities": sum(p.status.value == "PRICED" for p in eligibility.priced),
                                                              "total_cents": eligibility.total_cents(),
                                                              "note": "Upper bound: assumes every drilled 12-1/4\" / 8-1/2\" day is a nominated performance section, which no evidence supports."},
            "pd201_if_eligibility_were_established": {"quantities": len(pd201), "total_cents": sum(p.conditional_amount_cents for p in pd201),
                                                      "note": "Conditional: the calculated rate of the PD-201 days, payable only if the call-off (not provided) "
                                                              "nominated those sections. Neither the reports nor the invoices establish that."}}


BACKGROUNDS = {
    "canonical": "the canonical selection: class-rated services, PD-210 and PD-201 stay EVIDENCE_NOT_PROVIDED (AMB-13)",
    "claimed_class": ("HYPOTHETICAL background: calloff_evidence = INVOICE_STATEMENT_UNVERIFIED with the contractor's claimed classes, "
                      "and every allowed-size PD-210 / PD-201 day treated as nominated, so readings that act on those services show their effect"),
}


def sensitivity(result: InterpretationResult, terms: ContractTerms, switches: dict[str, Switch], approved: dict[str, Choice],
                classes: dict[str, str], recommendations: dict) -> dict:
    ref = canonical_selection(switches, approved)
    conf = {r["switch"]: r["confidence"] for r in recommendations["recommendations"]}
    backgrounds = {"canonical": (ref, None),
                   "claimed_class": (ref.with_choice("calloff_evidence", "INVOICE_STATEMENT_UNVERIFIED", Source.HYPOTHETICAL), classes)}
    rows, totals = [], {}
    for label, (bg, bg_classes) in backgrounds.items():
        base = price(result, terms, switches, bg, bg_classes)
        totals[label] = base.total_cents()
        for name in PRICING_SWITCHES:
            if ref.choices[name].source is not Source.APPROVED or (label != "canonical" and name == "calloff_evidence"):
                continue
            services = affected_services(name, terms, result)
            for reading in switches[name].values:
                if reading == ref.value(name) or (name, reading) in NOT_DERIVED:
                    continue
                row = _flip(result, terms, switches, bg, base, name, reading, classes, bg_classes, services)
                row["background"] = label
                row["confidence"] = conf.get(name) or switches[name].default_basis
                rows.append(row)
    return {"schema": "contractor-audit/drilling-phase4-sensitivity", "schema_version": "1.1", "note": NOTE,
            "backgrounds": BACKGROUNDS, "background_totals_cents": totals,
            "reference_canonical": ref.canonical, "reference_total_cents": totals["canonical"],
            "switches": rows, "well_class": class_scenarios(result, terms, switches, ref, classes)}


def decision_record(data: dict, switches: dict[str, Switch], ambiguities: dict[str, Ambiguity], recommendations: dict, approved_raw: dict) -> str:
    by_amb = {s.ambiguity_id: s for s in switches.values()}
    recs = {r["ambiguity"]: r for r in recommendations["recommendations"]}
    approvals = {a["ambiguity"]: a for a in approved_raw["approvals"]}
    effects = defaultdict(list)
    for r in data["switches"]:
        where = "canonical" if r["background"] == "canonical" else "with claimed classes (hypothetical)"
        effects[r["ambiguity"]].append(f"→ {r['alternative']} ({where}): {_money(r['delta_cents'])} over {r['quantities_changed']:,} quantities")
    special = {"AMB-01": "Meta-decision: no direct effect; each concrete conflict has its own switch.",
               "AMB-26": "None in this data (DS-900 is invoice-level; no invoice carries a non-service charge besides DS-900)."}
    lines = ["# Drilling Phase 4 — decision record", "",
             "Readings approved by the user on 2026-09-30 (`approved_readings.json`), with the effect of each alternative against the "
             "canonical selection (`phase4_pricing_sensitivity.md`). Recommendations were formed from the contract text only.", "",
             "| ambiguity | switch | approved reading | recommendation | effect of each alternative |", "|---|---|---|---|---|"]
    for amb in approved_raw["decided_in_phase4"]:
        s, a, r = by_amb[amb], approvals[amb], recs[amb]
        shown = a.get("decision") or a["value"]
        lines.append(f"| {amb} | `{s.name}` | **{shown}** ({a['ambiguity_reading']}) | {r['recommend']} ({r['confidence']}) | "
                     f"{special.get(amb) or '; '.join(effects[amb]) or '—'} |")
    lines.append("")
    for amb in approved_raw["decided_in_phase4"]:
        s, amb_obj, r, a = by_amb[amb], ambiguities[amb], recs[amb], approvals[amb]
        lines += [f"## {amb} — {amb_obj.title} (`{s.name}`)", "",
                  "1. **Relied on:** " + ", ".join(f"p.{p}" for p in amb_obj.pages),
                  "2. **Contract wording:** " + " / ".join(f"“{e.source_text}” (p.{e.page})" for rd in amb_obj.readings for e in rd.evidence[:1]),
                  f"3. **Reading A:** {next(x.reading for x in amb_obj.readings if x.id == 'A')}",
                  f"4. **Reading B:** {next(x.reading for x in amb_obj.readings if x.id == 'B')}"
                  + "".join(f" **Reading {x.id}:** {x.reading}" for x in amb_obj.readings if x.id not in ('A', 'B')),
                  f"5. **Phase 1 preference:** {amb_obj.preferred_reading + ' (' + amb_obj.confidence + ')' if amb_obj.preferred_reading else 'none'}",
                  f"6. **Measured effect of the alternatives:** {special.get(amb) or '; '.join(effects[amb]) or '—'}",
                  f"7. **Recommendation:** {r['recommend']} ({r['confidence']}). {r['basis']}",
                  f"8. **Approved:** {a.get('decision') or a['value']} (reading {a['ambiguity_reading']})." + (f" {a['note']}" if a.get("note") else ""),
                  f"9. **Still uncertain:** {r['uncertain']}", ""]
    return "\n".join(lines)


def _md(data: dict) -> str:
    lines = ["# Drilling Phase 4 — pricing sensitivity", "", data["note"], "",
             f"Canonical reference total of priced report evidence: {_money(data['reference_total_cents'])} (not an invoice figure).", "",
             "## Each approved reading flipped alone (hypothetical)", "",
             "\"Quantities changed\" also counts quantities that exist under only one of the two readings.", "",
             "Backgrounds: " + "; ".join(f"**{k}**: {v}" for k, v in data["backgrounds"].items()) + ".", "",
             f"Totals: canonical {_money(data['background_totals_cents']['canonical'])}; claimed-class background {_money(data['background_totals_cents']['claimed_class'])}.", "",
             "| switch | ambiguity | confidence | approved → alternative | background | delta | quantities changed | status change | by service |", "|---|---|---|---|---|---|---|---|---|"]
    for r in data["switches"]:
        status = "" if r["status_approved"] == r["status_alternative"] else f"{r['status_approved']} → {r['status_alternative']}"
        lines.append(f"| {r['switch']} | {r['ambiguity']} | {r['confidence']} | {r['approved']} → {r['alternative']} | {r['background']} | {_money(r['delta_cents'])} | "
                     f"{r['quantities_changed']:,} | {status} | {', '.join(f'{k} {_money(v)}' for k, v in r['delta_by_service_cents'].items())} |")
    wc = data["well_class"]
    lines += ["", "## Well class (AMB-13 approved as UNKNOWN / UNVERIFIED): what each possible class would do", "",
              f"Services that need the class: {', '.join(wc['class_rated_services'])}. Claimed classes on invoice headers (unverified): {wc['claimed_classes']}.", "",
              "| scenario | priced quantities | total | by service |", "|---|---|---|---|"]
    lines += [f"| {s['scenario']} | {s['priced_quantities']:,} | {_money(s['total_cents'])} | {', '.join(f'{k} {_money(v)}' for k, v in s['by_service_cents'].items())} |"
              for s in wc["scenarios"]]
    e = wc["pd210_if_every_allowed_size_day_were_nominated"]
    p = wc["pd201_if_eligibility_were_established"]
    lines += ["", f"PD-210 {e['note']} {e['priced_quantities']:,} quantities, {_money(e['total_cents'])}.", "",
              f"PD-201 {p['note']} {p['quantities']:,} quantities, {_money(p['total_cents'])}.", ""]
    return "\n".join(lines)


def write(result: InterpretationResult, dataset: DrillingDataset, terms: ContractTerms, switches: dict[str, Switch],
          approved: dict[str, Choice], ambiguities: dict[str, Ambiguity], artifacts_dir: Path) -> list[Path]:
    recommendations = json.loads((artifacts_dir / "phase4_recommendations.json").read_text(encoding="utf-8"))
    approved_raw = json.loads((artifacts_dir / "approved_readings.json").read_text(encoding="utf-8"))
    data = sensitivity(result, terms, switches, approved, claimed_well_classes(dataset), recommendations)
    texts = {SENSITIVITY_JSON: json.dumps(data, indent=1) + "\n", SENSITIVITY_MD: _md(data),
             DECISION_MD: decision_record(data, switches, ambiguities, recommendations, approved_raw) + "\n"}
    out = []
    for name in GENERATED:
        path = artifacts_dir / name
        path.write_text(texts[name], encoding="utf-8", newline="\n")
        out.append(path)
    return out
