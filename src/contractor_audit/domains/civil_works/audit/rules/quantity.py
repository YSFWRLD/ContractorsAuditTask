"""Check 5: billed quantity against the quantity the record establishes.

A record evidences its quantity once. Every line quoting the same record (in measurement order)
draws on one allowance, computed with the Phase 2 quantity rules:

* hour items: Clause 6A chargeable hours (scope switch `chargeable_hour_scope`);
* surveyed items: Clause 33 / 33A against the joint survey (switch `survey_quantity_rule`);
* week items with a weekly log: Clause 47A five-day rule;
* every other Schedule 5 item: the recorded quantity (Clause 47; guideline 5).

A line refused because an earlier line already used the record is DUPLICATE_RECORD; a line
billed above what its own record supports is QUANTITY_EXCEEDS_RECORD.
"""

from collections import defaultdict
from decimal import Decimal

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.models import RuleOutput, Unresolved
from contractor_audit.domains.civil_works.audit.rules.common import finding, qty
from contractor_audit.domains.civil_works.audit.rules.records import link_record, record_evidence
from contractor_audit.domains.civil_works.interpretation import ChargeableHourScope
from contractor_audit.domains.civil_works.quantity_rules import chargeable_hours, surveyed_payable, week_measurable
from contractor_audit.shared.findings import Evidence


def _group_key(ctx, line, link, kind):
    if kind == "hour":
        scope = ctx.interp.chargeable_hour_scope
        if scope is ChargeableHourScope.PER_LINE:
            return ("line", line.line_ref)
        if scope is ChargeableHourScope.PER_WORK_AREA_DAY:
            return ("area_day", line.site, line.work_date)
    return ("record", link.reference)


def check(ctx, payable) -> list:
    t = ctx.terms
    out: list = []
    groups: dict[tuple, list] = defaultdict(list)
    kinds: dict[tuple, str] = {}
    for line in ctx.lines:
        link = link_record(ctx, line)
        if link is None or link.required_series is None or line.item_code not in t.boq or not link.usable(ctx.audit_interp.unsigned_record):
            continue
        if "quantity_unresolved" in link.problems or "unit_incomparable" in link.problems:
            out.append(Unresolved(line.application_no, line.line_ref, "payable_quantity_unresolved",
                                  f"{link.reference}: record quantity cannot be read in {t.boq[line.item_code].unit}"))
            continue
        # link.usable() only tolerates 'unsigned'; unresolved quantities were handled above.
        if t.boq[line.item_code].unit == "hour":
            kind = "hour"
        elif line.item_code in t.surveyed_items:
            kind = "survey"
        elif link.record.record_type == "DW":
            kind = "week"
        else:
            kind = "record"
        key = _group_key(ctx, line, link, kind)
        groups[key].append((line, link))
        kinds[key] = kind

    for key in sorted(groups, key=str):
        members = sorted(groups[key], key=lambda m: ctx.measurement_key(m[0]))
        kind = kinds[key]
        claimed = [payable[l.line_ref] for l, _ in members]
        records = {lk.reference: lk for _, lk in members}
        if kind == "hour":
            hours = sum((lk.quantity.quantity for lk in records.values()), Decimal(0)) if key[0] != "line" else members[0][1].quantity.quantity
            allowance = chargeable_hours(hours)
            basis, cite = f"{qty(hours)} hours attended; the first hour of the attendance is not chargeable -> {qty(allowance)}", ctx.cite("6A")
            interp = f"chargeable_hour_scope={ctx.interp.chargeable_hour_scope.value}"
        elif kind == "survey":
            surveyed = members[0][1].quantity.quantity
            allowance = surveyed_payable(sum(claimed, Decimal(0)), surveyed, ctx.interp.survey_quantity_rule).payable_quantity
            basis = f"surveyed {qty(surveyed)}; {ctx.interp.survey_quantity_rule.value} allows {qty(allowance)} of {qty(sum(claimed, Decimal(0)))} measured"
            cite = ctx.cite("33A") if ctx.interp.survey_quantity_rule.value == "tolerance_33a" else ctx.cite("33")
            interp = f"survey_quantity_rule={ctx.interp.survey_quantity_rule.value}"
        elif kind == "week":
            lk = members[0][1]
            days = len(lk.record.days_on)
            allowance = lk.quantity.quantity if week_measurable(days, t.week_minimum_days) else Decimal(0)
            basis, cite, interp = f"log shows {days} days worked ({qty(lk.quantity.quantity)} week); >= {t.week_minimum_days} needed", ctx.cite("47A"), None
        else:
            allowance = members[0][1].quantity.quantity
            basis, cite, interp = f"record states {qty(allowance)} {members[0][1].quantity.unit}", ctx.cite("47"), None

        remaining = allowance
        for i, ((line, link), want) in enumerate(zip(members, claimed)):
            pay = min(want, max(remaining, Decimal(0)))
            used_before = allowance - remaining
            remaining -= pay
            if pay >= want:
                continue
            earlier = [m[0].line_ref for m in members[:i] if m[1].reference == link.reference]
            shared = bool(earlier) and used_before > 0
            category = Category.DUPLICATE_RECORD if shared else Category.QUANTITY_EXCEEDS_RECORD
            msg = (f"{link.reference} supports {qty(allowance)} {t.boq[line.item_code].unit} ({basis}); "
                   + (f"{qty(used_before)} already billed on {', '.join(earlier)}; " if shared else "")
                   + f"line bills {qty(want)}, payable {qty(pay)}.")
            ev = record_evidence(link)
            if interp:
                ev = ev + (Evidence("quantity_rule", link.reference, basis, cite.reference, qty(allowance), interp),)
            out.append(RuleOutput(finding(category, line.application_no, f"quantity.{kind}" + (".shared" if shared else ""), msg,
                                          line=line, observed=qty(want), expected=qty(pay), citations=(cite,), affects_total=True, evidence=ev),
                                  cap=pay, cap_measurable=False))
    return out
