"""One audit pass under one set of readings.

1. Quantity-stage rules, in order; each may cap a line's payable quantity.
2. Price the billed and the payable quantity of every line (Phase 2 engine; audit/valuation.py).
3. Valuation-stage rules compare billed rates, amounts, totals and adjustments with that pricing.
4. Attribute each quantity finding's monetary effect and reconstruct each application's total.

The result is an AuditRun without confidence; `assessment.py` compares runs across readings.
"""

import dataclasses
from decimal import Decimal

from contractor_audit.domains.civil_works.audit.categories import CATEGORIES
from contractor_audit.domains.civil_works.audit.context import AuditContext, AuditData
from contractor_audit.domains.civil_works.audit.models import AuditRun, RuleOutput, Unresolved
from contractor_audit.domains.civil_works.audit.options import (WORKING_AUDIT_INTERPRETATION, AuditInterpretation,
                                                                RebateProgression)
from contractor_audit.domains.civil_works.audit.rules import (adjustments, arithmetic, contract_reference, duplicates,
                                                              exclusions, item_identity, limits, period, quantity, rates,
                                                              records)
from contractor_audit.domains.civil_works.audit.rules.common import money
from contractor_audit.domains.civil_works.audit.valuation import value_lines
from contractor_audit.domains.civil_works.interpretation import WORKING_INTERPRETATION, CivilWorksInterpretation
from contractor_audit.domains.civil_works.valuation import Valuer
from contractor_audit.shared.findings import Evidence

QUANTITY_RULES = (contract_reference.check, period.check, item_identity.check, records.check, duplicates.check,
                  quantity.check, limits.check, exclusions.check)
_CATEGORY_ORDER = {c.value: i for i, c in enumerate(CATEGORIES)}


def finding_sort_key(f) -> tuple:
    return (f.invoice_id, f.line_ref or "", int(f.check), _CATEGORY_ORDER.get(f.category, 99), f.rule)


def run_audit(data: AuditData, interp: CivilWorksInterpretation = WORKING_INTERPRETATION,
              audit_interp: AuditInterpretation = WORKING_AUDIT_INTERPRETATION) -> AuditRun:
    ctx = AuditContext(data, interp, audit_interp)
    billed = {l.line_ref: l.quantity for l in data.lines}
    payable = dict(billed)
    measurable = dict(billed)
    binding: dict[str, tuple[str, ...]] = {}
    capped: list[RuleOutput] = []
    findings = []
    unresolved: list[Unresolved] = []

    for rule in QUANTITY_RULES:
        for item in rule(ctx, payable):
            if isinstance(item, Unresolved):
                unresolved.append(item)
                continue
            findings.append(item.finding)
            if item.cap is None:
                continue
            capped.append(item)
            ref = item.finding.line_ref
            if item.cap < payable[ref]:
                payable[ref] = item.cap
                binding[ref] = (item.finding.rule,)
            elif item.cap == payable[ref] and item.cap < billed[ref]:
                binding[ref] = binding.get(ref, ()) + (item.finding.rule,)
            if not item.cap_measurable:
                measurable[ref] = min(measurable[ref], item.cap)

    progression = {RebateProgression.MEASURABLE_ONLY: measurable, RebateProgression.PAYABLE_ONLY: payable,
                   RebateProgression.ALL_BILLED: billed}[audit_interp.rebate_progression]
    valuations, priced_unresolved = value_lines(ctx, payable, progression, binding)
    unresolved += priced_unresolved

    # Monetary effect of each quantity finding on the line whose payable quantity it decided.
    impacts = {}
    for item in capped:
        ref = item.finding.line_ref
        v = valuations[ref]
        if item.cap != v.payable_quantity:
            continue
        if v.contract_billed is None:      # no contract rate on this date: the whole billed amount is disallowed
            if v.payable_quantity == 0:
                impacts[item.finding.key] = (v.billed_cents, Evidence("contract_price", ref, "no rate in force on the work date; nothing payable", None, "0.00"))
            continue
        impacts[item.finding.key] = (v.billed_cents if v.payable_quantity == 0 else v.contract_billed.amount_cents - v.contract_payable.amount_cents,
                                     Evidence("contract_price", ref,
                                              f"billed {v.billed_quantity} priced at contract {money(v.contract_billed.amount_cents)}; payable {v.payable_quantity} "
                                              f"priced at {money(v.contract_payable.amount_cents)} (rate {v.contract_payable.unit_rate}); binding rule(s): {', '.join(v.binding_rules)}",
                                              "Clauses 27-28", money(v.contract_payable.amount_cents)))
    findings = [dataclasses.replace(f, impact_cents=impacts[f.key][0], evidence=f.evidence + (impacts[f.key][1],))
                if f.key in impacts and f.impact_cents is None else f for f in findings]

    findings += [o.finding for o in rates.check(ctx, valuations)]
    findings += [o.finding for o in arithmetic.check(ctx, valuations)]
    # Clause 31A / 45A sums from the Phase 2 valuation of billed work; lines with no rate in force cannot be valued.
    priceable = [l for l in data.lines if valuations[l.line_ref].contract_billed is not None]
    phase2 = Valuer(data.terms, interp).value(list(data.applications), priceable)
    findings += [o.finding for o in adjustments.check(ctx, phase2)]

    totals: dict[str, int | None] = {}
    for app in data.applications:
        vals = [valuations[l.line_ref] for l in ctx.lines_by_app[app.application_no]]
        totals[app.application_no] = None if any(v.payable_cents is None for v in vals) else sum(v.payable_cents for v in vals)
    outside = {}
    for adj in phase2.adjustments:
        outside.setdefault(adj.application_no, []).append((adj.kind, adj.amount_cents, adj.clause, adj.note))

    label = {**interp.label(), **audit_interp.label()}
    return AuditRun(label, tuple(sorted(findings, key=finding_sort_key)), valuations, totals,
                    tuple(sorted(unresolved, key=lambda u: (u.application_no, u.line_ref or "", u.reason))),
                    {k: tuple(v) for k, v in outside.items()})
