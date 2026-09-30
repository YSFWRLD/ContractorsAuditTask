"""How much each interpretation switch moves the contract-side valuation.

For every alternative reading, the whole dataset is revalued and compared with the working
interpretation. Agreement with billed amounts is reported separately and is labelled
'consistency with observed billing': it describes the data, it is not evidence for a reading,
and nothing in this module feeds back into WORKING_INTERPRETATION.
"""

from collections import defaultdict
from dataclasses import fields
from datetime import timedelta
from decimal import Decimal

from contractor_audit.domains.civil_works.contract import ContractTerms
from contractor_audit.domains.civil_works.interpretation import (SWITCHES_BY_FIELD, WORKING_INTERPRETATION,
                                                                 ChargeableHourScope, ExclusionWindow,
                                                                 SurveyQuantityRule, alternatives)
from contractor_audit.domains.civil_works.models import Application, ApplicationLine
from contractor_audit.domains.civil_works.quantity_rules import (ExclusionEvaluator, Measurement, chargeable_hours_by_scope,
                                                                 exclusion_rules, surveyed_payable)
from contractor_audit.domains.civil_works.record_quantities import RecordQuantity
from contractor_audit.domains.civil_works.rounding import cents_to_decimal
from contractor_audit.domains.civil_works.valuation import DatasetValuation, Valuer

QUANTITY_SWITCHES = ("chargeable_hour_scope", "survey_quantity_rule", "exclusion_window")
CONSISTENCY_LABEL = "consistency with observed billing (descriptive only; not evidence for a reading)"


def _money(cents: int) -> str:
    return str(cents_to_decimal(cents))


def _billing_consistency(valuation: DatasetValuation, lines: list[ApplicationLine], subset: set[str] | None = None) -> dict:
    chosen = [l for l in lines if subset is None or l.line_ref in subset]
    amount = sum(1 for l in chosen if valuation.lines[l.line_ref].price.amount_cents == l.amount_cents)
    rate = sum(1 for l in chosen if valuation.lines[l.line_ref].price.unit_rate == l.rate_applied)
    return {"lines": len(chosen), "amount_equals_billed": amount, "first_part_rate_equals_billed_rate": rate}


def compare(base: DatasetValuation, alt: DatasetValuation, lines: list[ApplicationLine]) -> dict:
    changed = [l for l in lines if base.lines[l.line_ref].price.amount_cents != alt.lines[l.line_ref].price.amount_cents]
    deltas = [alt.lines[l.line_ref].price.amount_cents - base.lines[l.line_ref].price.amount_cents for l in changed]
    apps = sorted({l.application_no for l in changed})
    base_adj = {(a.kind, a.application_no): a.amount_cents for a in base.adjustments}
    alt_adj = {(a.kind, a.application_no): a.amount_cents for a in alt.adjustments}
    adj_changes = [{"kind": k[0], "application_no": k[1], "working": _money(base_adj[k]) if k in base_adj else None,
                    "alternative": _money(alt_adj[k]) if k in alt_adj else None}
                   for k in sorted(set(base_adj) | set(alt_adj)) if base_adj.get(k) != alt_adj.get(k)]
    items = defaultdict(int)
    for l in changed:
        items[l.item_code] += 1
    subset = {l.line_ref for l in changed}
    return {
        "lines_affected": len(changed),
        "applications_affected": len(apps),
        "items_affected": dict(sorted(items.items())),
        "sum_abs_line_delta": _money(sum(abs(d) for d in deltas)),
        "net_line_delta_alternative_minus_working": _money(sum(deltas)),
        "same_price_for_every_line": not changed,
        "outside_measured_adjustment_changes": adj_changes,
        "example_lines": [l.line_ref for l in changed[:5]],
        CONSISTENCY_LABEL: {"working_on_affected_lines": _billing_consistency(base, lines, subset),
                            "alternative_on_affected_lines": _billing_consistency(alt, lines, subset)},
    }


def _record_join(lines, quantities: dict[str, RecordQuantity]):
    return [(l, quantities.get(l.record_ref)) for l in lines if l.record_ref]


def quantity_switch_effects(terms: ContractTerms, base: DatasetValuation, lines: list[ApplicationLine],
                            quantities: dict[str, RecordQuantity]) -> dict:
    """Effects of the switches that decide payable quantity rather than rate."""
    out = {}
    joined = _record_join(lines, quantities)

    # Clause 33 / 33A: surveyed items with a resolved joint-survey quantity in the same unit.
    survey_rows = [(l, q) for l, q in joined if l.item_code in terms.surveyed_items and q and q.resolved and q.unit == l.unit]
    per_rule = {}
    for rule in SurveyQuantityRule:
        per_rule[rule.value] = {l.line_ref: surveyed_payable(l.quantity, q.quantity, rule).payable_quantity for l, q in survey_rows}
    differ = [l for l, _ in survey_rows if per_rule["tolerance_33a"][l.line_ref] != per_rule["exact_33"][l.line_ref]]
    money = sum(((per_rule["tolerance_33a"][l.line_ref] - per_rule["exact_33"][l.line_ref]) * base.lines[l.line_ref].price.unit_rate
                 for l in differ), Decimal(0))
    out["survey_quantity_rule"] = {
        "lines_considered": len(survey_rows),
        "lines_where_readings_differ": len(differ),
        "applications_affected": len({l.application_no for l in differ}),
        "approx_value_difference_33a_minus_33": str(money),
        "example_lines": [l.line_ref for l in differ[:5]],
        CONSISTENCY_LABEL: {f"lines_billed_at_payable_quantity_{r}": sum(1 for l, _ in survey_rows if per_rule[r][l.line_ref] == l.quantity)
                            for r in per_rule},
    }

    # Clause 6A: hour items with a resolved hours record.
    hour_rows = [(l, q) for l, q in joined if terms.boq[l.item_code].unit == "hour" and q and q.resolved and q.unit == "hour"]
    entries = [(l.line_ref, l.record_ref, (l.site, l.work_date), q.quantity) for l, q in hour_rows]
    totals = {scope.value: sum(chargeable_hours_by_scope(entries, scope).values(), Decimal(0)) for scope in ChargeableHourScope}
    rec_use = defaultdict(int)
    area_day = defaultdict(set)
    for l, q in hour_rows:
        rec_use[l.record_ref] += 1
        area_day[(l.site, l.work_date)].add(l.record_ref)
    out["chargeable_hour_scope"] = {
        "hour_lines_with_record": len(hour_rows),
        "records_quoted_on_more_than_one_hour_line": sum(1 for n in rec_use.values() if n > 1),
        "work_area_days_with_more_than_one_record": sum(1 for s in area_day.values() if len(s) > 1),
        "total_chargeable_hours": {k: str(v) for k, v in totals.items()},
        "hours_billed": str(sum((l.quantity for l, _ in hour_rows), Decimal(0))),
        "hours_recorded": str(sum((q.quantity for _, q in hour_rows), Decimal(0))),
        CONSISTENCY_LABEL: {
            "lines_billed_at_recorded_hours": sum(1 for l, q in hour_rows if l.quantity == q.quantity),
            "lines_billed_at_recorded_hours_minus_one": sum(1 for l, q in hour_rows if l.quantity == q.quantity - 1),
        },
    }

    # Clause 32 / P19 / P21 exclusions.
    ms = [Measurement(l.line_ref, l.item_code, l.site, l.work_date) for l in lines]
    rules = exclusion_rules(terms)
    hits = {w.value: {h.excluded.key for h in ExclusionEvaluator(rules, w).evaluate(ms)} for w in ExclusionWindow}
    only_incl = hits["same_day_included"] - hits["same_day_excluded"]
    out["exclusion_window"] = {
        "excluded_lines": {k: len(v) for k, v in hits.items()},
        "lines_where_readings_differ": len(only_incl),
        "value_of_lines_that_differ": _money(sum(base.lines[r].price.amount_cents for r in only_incl)),
        "example_lines": sorted(only_incl)[:5],
        "note": "P21 (E.51.020 on a surfacing day) is a same-day rule and is not affected by this switch.",
    }
    return out


def run_sensitivity(terms: ContractTerms, applications: list[Application], lines: list[ApplicationLine],
                    quantities: dict[str, RecordQuantity]) -> dict:
    base = Valuer(terms, WORKING_INTERPRETATION).value(applications, lines)
    results = {}
    for f in fields(WORKING_INTERPRETATION):
        info = SWITCHES_BY_FIELD[f.name]
        entry = {"status": info.status.value, "ambiguity_id": info.ambiguity_id, "question": info.question,
                 "working": getattr(WORKING_INTERPRETATION, f.name).value, "alternatives": {}}
        if f.name not in QUANTITY_SWITCHES:
            for alt_value in alternatives(f.name):
                alt = Valuer(terms, WORKING_INTERPRETATION.with_(**{f.name: alt_value})).value(applications, lines)
                entry["alternatives"][alt_value.value] = compare(base, alt, lines)
        results[f.name] = entry
    q = quantity_switch_effects(terms, base, lines, quantities)
    for name in QUANTITY_SWITCHES:
        results[name]["quantity_effect"] = q[name]

    apps = {a.application_no: a for a in applications}
    retro = [i for i in terms.instruments if i.retroactive]
    return {
        "working_interpretation": WORKING_INTERPRETATION.label(),
        "overall": {
            "lines": len(lines),
            "measured_work_total": _money(sum(v.measured_work_total_cents for v in base.applications.values())),
            "outside_measured_adjustments": [{"kind": a.kind, "application_no": a.application_no, "amount": _money(a.amount_cents),
                                              "basis_count": len(a.basis), "note": a.note} for a in base.adjustments],
            CONSISTENCY_LABEL: {
                **_billing_consistency(base, lines),
                "applications_where_measured_total_equals_billed_total": sum(
                    1 for a, v in base.applications.items() if v.measured_work_total_cents == apps[a].application_total_cents),
                "applications": len(applications),
            },
        },
        "switches": results,
        "boundary_notes": {
            "lines_after_final_completion": sorted(r for r, pl in base.lines.items() if not pl.period.measurable),
            "applications_on_retroactive_issue_date": sorted(a.application_no for a in applications
                                                             if any(a.application_date == i.issued for i in retro)),
            "first_application_after_issue_date": min(((a.application_date, a.application_no) for a in applications
                                                       if any(a.application_date > i.issued for i in retro)), default=(None, None))[1],
            "day_after_original_completion": str(terms.original_completion_date + timedelta(1)),
        },
    }
