"""Phase 2 artifacts: rate timeline, interpretation matrix, pricing model, sensitivity, quantity parsing."""

from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal

from contractor_audit.domains.civil_works.contract import ContractTerms
from contractor_audit.domains.civil_works.contract_period import ContractPeriod
from contractor_audit.domains.civil_works.interpretation import (SWITCHES, WORKING_INTERPRETATION, IndexedRateMethod,
                                                                 MonthlyRateTreatment, UsdReading)
from contractor_audit.domains.civil_works.models import ApplicationLine
from contractor_audit.domains.civil_works.pricing import LineContext, PricingEngine
from contractor_audit.domains.civil_works.rates import PricingError, RateResolver
from contractor_audit.domains.civil_works.rebates import RebateLedger
from contractor_audit.domains.civil_works.record_quantities import RULES, RecordQuantity
from contractor_audit.domains.civil_works.reports import GENERATED, _table
from contractor_audit.domains.civil_works.rounding import cents_to_decimal
from contractor_audit.domains.civil_works.sensitivity import CONSISTENCY_LABEL

KEY_DATES = ("2025-01-05", "2025-05-01", "2025-09-28", "2025-10-01", "2025-11-01", "2025-12-01", "2026-01-05", "2026-04-01", "2026-09-30")


def _boundary_dates() -> list[date]:
    out = []
    for text in KEY_DATES:
        d = date.fromisoformat(text)
        out += [d - timedelta(1), d, d + timedelta(1)]
    return sorted(set(out))


def instrument_items(terms: ContractTerms) -> list[str]:
    codes = set()
    for inst in terms.instruments:
        codes |= {s.code for s in inst.rate_substitutions} | {m.code for m in inst.monthly_rates}
        if inst.discount:
            codes |= set(inst.discount.codes)
    return sorted(codes)


# --------------------------------------------------------------------------- rate timeline

def rate_timeline(terms: ContractTerms) -> dict:
    resolver = RateResolver(terms)
    engine = PricingEngine(terms)
    items = instrument_items(terms)
    provisions = {code: [{"instrument": p.instrument_id, "issued": p.issued.isoformat() if p.issued else None,
                          "effective_from": p.effective_from.isoformat(), "kind": p.kind.value,
                          "rate": str(p.rate) if p.rate is not None else None,
                          "monthly": [[m, str(r)] for m, r in p.monthly], "page": p.page}
                         for p in resolver.timeline(code)] for code in items}
    boundaries = []
    for d in _boundary_dates():
        row = {"date": d.isoformat(), "weekday": d.strftime("%a")}
        for code in items:
            try:
                res = resolver.resolve(code, d)
            except PricingError:
                row[code] = {"rate": "none", "source": "before Commencement", "discount": None}
                continue
            ctx = LineContext(code, d, "Z1 Compound", "S-01 Platform North")
            discounts = engine.pre_band_rate(ctx).discount_factors
            row[code] = {"rate": str(res.rate_in_force), "source": res.source_instrument,
                         "discount": "+".join(f"{i}:{p}%" for i, p in discounts) or None}
        boundaries.append(row)
    retro = []
    for inst in (i for i in terms.instruments if i.retroactive):
        for sub in inst.rate_substitutions:
            for known in (inst.issued - timedelta(1), inst.issued, inst.issued + timedelta(1)):
                for include in (True, False):
                    r = resolver.resolve(sub.code, inst.effective, known, include_issued_on_known_at=include)
                    retro.append({"item": sub.code, "work_date": inst.effective.isoformat(), "known_at": known.isoformat(),
                                  "instrument_issued_on_known_at_counts": include, "rate": str(r.rate_in_force), "source": r.source_instrument})
    period = ContractPeriod(terms)
    extensions = [{"instrument": c.instrument_id, "issued": c.issued.isoformat(), "effective": c.effective.isoformat(),
                   "new_completion": c.new_completion.isoformat()} for c in period.changes]
    return {"items": items, "provisions": provisions, "boundaries": boundaries, "retroactive_view": retro,
            "contract_period": {"commencement": period.commencement.isoformat(), "original_completion": period.original_completion.isoformat(),
                                "extensions": extensions, "final_completion": period.final_completion.isoformat(),
                                "contract_years": [[y.year, y.start.isoformat(), y.end.isoformat()] for y in period.years]}}


def render_rate_timeline(tl: dict) -> str:
    out = ["# Rate timeline — civil works", "", GENERATED, "",
           "Rate in force per item and work date, as the resolver computes it from `contract_extraction.json` "
           "(`rates.py`). Precedence: instruments in the order issued; each governs work on or after its own effective date "
           "(the date stated against each rate); where two state a rate or discount for the same item, the later-issued governs.", "",
           "## Contract period", "",
           f"Commencement {tl['contract_period']['commencement']}; original completion {tl['contract_period']['original_completion']}; "
           f"final completion {tl['contract_period']['final_completion']}.", "",
           _table(["Instrument", "Issued", "Effective", "New completion"],
                  [[e["instrument"], e["issued"], e["effective"], e["new_completion"]] for e in tl["contract_period"]["extensions"]]), "",
           _table(["Contract Year", "Start", "End"], tl["contract_period"]["contract_years"]), "",
           "## Provisions per item", ""]
    for code in tl["items"]:
        out += [f"**{code}**", "", _table(["Instrument", "Issued", "Effective from", "Kind", "Rate", "Monthly", "Page"],
                                         [[p["instrument"], p["issued"], p["effective_from"], p["kind"], p["rate"],
                                           ", ".join(f"{m} {r}" for m, r in p["monthly"]), p["page"]] for p in tl["provisions"][code]]), ""]
    out += ["## Boundaries (day before / on / after each key date)", "",
            "Rate in force (source instrument) and discount in effect. Zone, ground and uplifts are not included here.", "",
            _table(["Date", "Day"] + tl["items"],
                   [[r["date"], r["weekday"]] + [f"{r[c]['rate']} ({r[c]['source']})" + (f" −{r[c]['discount']}" if r[c]["discount"] else "") for c in tl["items"]]
                    for r in tl["boundaries"]]), "",
            "## Backdated Amendment No. 3 as seen by an application", "",
            "`known_at` is the application's submission date. Whether an instrument issued on that very date counts is the "
            "`retro_adjustment_trigger` switch (31A 'on or after' = counts; A3 recital 'after' = does not).", "",
            _table(["Item", "Work date", "Known at", "Issue-date counts", "Rate", "Source"],
                   [[r["item"], r["work_date"], r["known_at"], r["instrument_issued_on_known_at_counts"], r["rate"], r["source"]] for r in tl["retroactive_view"]]), ""]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- interpretation matrix

def render_interpretation_matrix() -> str:
    out = ["# Interpretation matrix — civil works", "", GENERATED, "",
           "Each row is one field of `CivilWorksInterpretation` (`interpretation.py`). **Working** is the reading currently selected, "
           "chosen from the contract text alone. It is not a claim that the reading is proven, and billed data was not used to choose it.", "",
           "Status: `text_resolved` = the contract text settles it, alternative kept for sensitivity only; "
           "`unresolved` = the text supports more than one reading; `evidence_not_provided` = the rule is clear but the data needed to apply it is absent.", ""]
    for s in SWITCHES:
        working = getattr(WORKING_INTERPRETATION, s.field).value
        out += [f"## `{s.field}` — {s.status.value}", "", f"{s.question}", "",
                f"Clauses: {', '.join(s.clauses)}; pages {', '.join(map(str, s.pages))}" + (f"; Phase 1 ambiguity {s.ambiguity_id}" if s.ambiguity_id else ""), "",
                _table(["Reading", "Working?", "Basis"], [[k, "**working**" if k == working else "", v] for k, v in s.readings.items()]), "",
                f"Why the working reading: {s.default_rationale}", ""]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- pricing model

def _examples() -> list[tuple[str, dict, LineContext, Decimal]]:
    W = WORKING_INTERPRETATION
    return [
        ("C.31.010 on 13/05/2025 in Z2 (the Appendix B example line)",
         {"working (29A)": W, "Appendix B unindexed": W.with_(indexed_rate_method=IndexedRateMethod.APPENDIX_B_UNINDEXED)},
         LineContext("C.31.010", date(2025, 5, 13), "Z2 North Spur", "S-03 Access Road", "G2 Firm Sabkha"), Decimal(48)),
        ("B.23.020 mesh (Schedule 2B) on 2025-06-10 in Z3",
         {"working (USD)": W, "SAR as printed": W.with_(usd_reading=UsdReading.SAR_AS_PRINTED)},
         LineContext("B.23.020", date(2025, 6, 10), "Z3 Wadi Crossing", "S-02 Platform South"), Decimal(100)),
        ("D.41.020 binder course, July 2025 monthly rate, Z2, night",
         {"working (base in build-up)": W, "final rate": W.with_(monthly_rate_treatment=MonthlyRateTreatment.FINAL_RATE)},
         LineContext("D.41.020", date(2025, 7, 15), "Z2 North Spur", "S-03 Access Road", night_work=True), Decimal(250)),
        ("C.32.010 manhole on 2026-05-20 in Z2, recorded G4 (A3 rate, A2 8% discount, 27A G2)", {"working": W},
         LineContext("C.32.010", date(2026, 5, 20), "Z2 North Spur", "S-04 Drainage Corridor", "G4 Weathered Rock"), Decimal(2)),
        ("B.21.030 slab on Saturday 2025-03-08, night, Z1 (P11 concurrent uplifts)", {"working": W},
         LineContext("B.21.030", date(2025, 3, 8), "Z1 Compound", "S-01 Platform North", night_work=True), Decimal(10)),
    ]


def _trace_table(price) -> str:
    return _table(["Rule", "Source", "Calculation", "Result", "Interpretation"],
                  [[s.rule, s.source, s.calculation, s.result, s.interpretation or ""] for s in price.trace])


def render_pricing_model(terms: ContractTerms) -> str:
    out = ["# Pricing model — civil works", "", GENERATED, "",
           "How the engine (`pricing.py`, `rates.py`, `rebates.py`, `valuation.py`) turns a measurement into a contract price. "
           "It prices; it does not judge, and it never reads a billed rate or amount.", "",
           "## Build-up order (from the contract text)", "",
           _table(["Step", "Component", "Source", "Rounding"], [
               [1, "Rate in force: Schedule 1 base, substituted rate, or published monthly rate", "Sch 1; S1, A1, S2, A2, A3; Schedule of Variations", "none"],
               [2, "Schedule 2B USD conversion (B.23.020, B.25.010, C.32.040)", "Sch 2B p.22; 26A p.32 ('before any factor or uplift')", "half-even to halala"],
               [2, "Schedule 2A indexation (C.31.010, D.41.030): x SMI(month) / 100", "Sch 2A p.21; 29A p.32", "half-even to halala"],
               [3, "Zone factor, Series A-D only", "Sch 2 p.20; 27, 29", "none"],
               [4, "Ground factor, 15 listed items only; G2 for work after 2025-09-27", "Sch 3 p.23; 27; 27A; S4", "none"],
               [5, "Night uplift (13 items); withheld where zone factor > 1.1", "Sch 4 Part 1; 7; 27A", "none"],
               [6, "Rest-day uplift (4 items), Fri/Sat; with night only on a Clause 9 instruction (P11)", "Sch 4 Part 2; 8; P11", "none"],
               [7, "Rebate band % of rate (8 items); a measurement crossing a band edge is split", "Sch 4 Part 3; 27; 30", "none"],
               [8, "Discount: final factor, after rebate, before rounding (4 items)", "S2 2.2; A2 2.3", "none"],
               [9, "Rate rounded once", "28", "half-up to halala"],
               [10, "Amount = quantity x rounded rate, summed over band parts", "28", "exact for integer quantities"],
           ]), "",
           "Multipliers compound in the order above (each is applied to the result of the previous step, Clause 27). "
           "Uplifts are `x (1 + p%)`, bands `x p%`, discounts `x (1 - p%)`.", "",
           "Outside the measured total (Clause 45A): retention (5% of the measured total, rounded down, Clause 45), the Clause 31A "
           "single adjustment for Amendment No. 3, and the Clause 45A release of half the retention held. These are reported "
           "separately in `ApplicationValuation.outside_measured_adjustments` and are not added to any total.", "",
           "## Worked traces", ""]
    for title, modes, ctx, qty in _examples():
        out += [f"### {title}", "", f"Quantity {qty}.", ""]
        for label, interp in modes.items():
            price = PricingEngine(terms, interp).price(ctx, qty)
            out += [f"**{label}** → rate {price.unit_rate}, amount {cents_to_decimal(price.amount_cents)}", "", _trace_table(price), ""]
    ledger = RebateLedger(terms, WORKING_INTERPRETATION.rebate_counting, ContractPeriod(terms))
    ledger.allocate("A.12.010", date(2025, 2, 1), Decimal(3900))
    ctx = LineContext("A.12.010", date(2025, 2, 3), "Z1 Compound", "S-01 Platform North", "G2 Firm Sabkha")
    alloc = ledger.allocate("A.12.010", date(2025, 2, 3), Decimal(300))
    price = PricingEngine(terms).price(ctx, Decimal(300), alloc)
    out += ["### A.12.010 crossing the 4,000 m3 band edge (3,900 already measured in the Contract Year)", "",
            f"Amount {cents_to_decimal(price.amount_cents)} from parts " + "; ".join(f"{p.quantity} x {p.rate} ({p.band_printed})" for p in price.parts) + ".", "",
            _trace_table(price), ""]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- sensitivity

def render_sensitivity(s: dict) -> str:
    o = s["overall"]
    c = o[CONSISTENCY_LABEL]
    out = ["# Sensitivity of the contract-side valuation — civil works", "", GENERATED, "",
           "Each alternative reading is applied on its own to all lines and compared with the working interpretation. "
           "No application is judged here.", "",
           f"> **{CONSISTENCY_LABEL[0].upper() + CONSISTENCY_LABEL[1:]}.** How often a reading reproduces a billed figure describes the data. "
           "It is not evidence that the reading is right, and no working reading was chosen or changed because of it. "
           "A contractor who systematically misapplied a clause would make the wrong reading reconcile.", "",
           "## Working interpretation, overall", "",
           _table(["Measure", "Value"], [
               ["lines", o["lines"]], ["measured work total (SAR)", o["measured_work_total"]],
               ["lines whose contract amount equals the billed amount", f"{c['amount_equals_billed']} of {c['lines']}"],
               ["lines whose first-part rate equals the billed rate", c["first_part_rate_equals_billed_rate"]],
               ["applications whose measured total equals application_total", f"{c['applications_where_measured_total_equals_billed_total']} of {c['applications']}"],
           ]), "",
           "Outside the measured total:", "",
           _table(["Kind", "Application", "Amount (SAR)", "Basis size", "Note"],
                  [[a["kind"], a["application_no"], a["amount"], a["basis_count"], a["note"]] for a in o["outside_measured_adjustments"]]), "",
           "## Per switch (rate-level)", "",
           _table(["Switch", "Status", "Working", "Alternative", "Lines", "Applications", "Σ|Δ| (SAR)", "Net Δ (SAR)", "Same price?",
                   "Billing consistency on affected lines (working / alternative)"],
                  [[k, v["status"], v["working"], alt, r["lines_affected"], r["applications_affected"], r["sum_abs_line_delta"],
                    r["net_line_delta_alternative_minus_working"], "yes" if r["same_price_for_every_line"] else "no",
                    f"{r[CONSISTENCY_LABEL]['working_on_affected_lines']['amount_equals_billed']} / {r[CONSISTENCY_LABEL]['alternative_on_affected_lines']['amount_equals_billed']}"]
                   for k, v in s["switches"].items() for alt, r in v["alternatives"].items()]), ""]
    for k, v in s["switches"].items():
        for alt, r in v["alternatives"].items():
            if r["outside_measured_adjustment_changes"]:
                out += [f"- `{k}` → `{alt}` changes outside-measured sums: " +
                        "; ".join(f"{x['kind']} on {x['application_no']}: {x['working']} → {x['alternative']}" for x in r["outside_measured_adjustment_changes"])]
    out += ["", "## Quantity switches", ""]
    for k in ("survey_quantity_rule", "chargeable_hour_scope", "exclusion_window"):
        q = s["switches"][k]["quantity_effect"]
        out += [f"### `{k}` ({s['switches'][k]['status']}; working `{s['switches'][k]['working']}`)", "",
                _table(["Measure", "Value"], [[m, v] for m, v in q.items()]), ""]
    b = s["boundary_notes"]
    out += ["## Boundary cases surfaced for later phases (not judged)", "",
            f"- Lines executed after the final Date for Completion: {', '.join(b['lines_after_final_completion'])}.",
            f"- Applications submitted on the Amendment No. 3 issue date: {', '.join(b['applications_on_retroactive_issue_date'])}; "
            f"first application after it: {b['first_application_after_issue_date']}.", ""]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- quantity parsing

def quantity_parsing(quantities: list[RecordQuantity], lines: list[ApplicationLine]) -> dict:
    by_rule = Counter(q.rule_id for q in quantities if q.resolved)
    by_type = defaultdict(lambda: [0, 0])
    for q in quantities:
        by_type[q.record_type][0] += 1
        by_type[q.record_type][1] += q.resolved
    qmap = {q.record_id: q for q in quantities}
    joined = Counter()
    for l in lines:
        if not l.record_ref:
            continue
        q = qmap.get(l.record_ref)
        if q is None:
            joined["reference_without_record"] += 1
            continue
        if not q.resolved:
            joined["record_unresolved"] += 1
            continue
        joined["item_indicated_by_phrase" if l.item_code in q.indicated_items else "item_not_indicated_by_phrase"] += 1
        joined["unit_equal" if q.unit == l.unit else "unit_differs"] += 1
        if q.unit == l.unit:
            joined["billed_equals_record" if l.quantity == q.quantity else "billed_above_record" if l.quantity > q.quantity else "billed_below_record"] += 1
    return {
        "records": len(quantities), "resolved": sum(q.resolved for q in quantities),
        "unresolved": [{"record": q.record_id, "text": q.raw_text, "reason": q.reason} for q in quantities if not q.resolved],
        "by_type": {t: {"records": n, "resolved": r} for t, (n, r) in sorted(by_type.items())},
        "rules": [{"rule_id": r.rule_id, "record_type": r.record_type, "pattern": r.pattern.pattern, "unit": r.unit,
                   "indicated_items": list(r.indicated_items), "records": by_rule.get(r.rule_id, 0), "note": r.note} for r in RULES],
        "reference_lookup_descriptive": dict(sorted(joined.items())),
    }


def render_quantity_parsing(qp: dict) -> str:
    out = ["# Site-record quantity parsing — civil works", "", GENERATED, "",
           "Deterministic, anchored rules (`record_quantities.py`); no language model. A description that no rule matches exactly is left unresolved.", "",
           f"**{qp['resolved']} of {qp['records']} records resolved.** Unresolved: {qp['unresolved'] or 'none'}.", "",
           _table(["Type", "Records", "Resolved"], [[t, v["records"], v["resolved"]] for t, v in qp["by_type"].items()]), "",
           "## Rules", "",
           _table(["Rule", "Type", "Pattern", "Unit", "Phrase indicates", "Records", "Note"],
                  [[r["rule_id"], r["record_type"], f"`{r['pattern']}`", r["unit"], ", ".join(r["indicated_items"]) or "by depth (P13)", r["records"], r["note"]]
                   for r in qp["rules"]]), "",
           "## Direct record-reference lookup (descriptive only)", "",
           "For lines quoting a record reference: whether the record's phrase describes the billed item, and how the record quantity compares with the billed quantity. "
           "These are counts, not findings.", "",
           _table(["Measure", "Lines"], [[k, v] for k, v in qp["reference_lookup_descriptive"].items()]), ""]
    return "\n".join(out) + "\n"
