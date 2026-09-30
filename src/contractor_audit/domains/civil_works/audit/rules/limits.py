"""Check 9: Schedule 4 Part 4 daily limitations (Clause 31; also Clause 19 and P6).

Clause 31 fixes the payable quantity for the day ('no more than that quantity is measurable ... A
quantity in excess of the limitation is not payable'). Clause 44 has already disallowed every second
measurement of the same item, work area and date (duplicates run first), so the cap binds a single
line and its correction is defined. Defensive guard: if several payable measurements ever shared the
day, the contract would not say which bears the excess, so each application involved is marked
`limit_allocation_unresolved`, which blanks its corrected total.
"""

from collections import defaultdict
from decimal import Decimal

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.models import RuleOutput, Unresolved
from contractor_audit.domains.civil_works.audit.rules.common import finding, qty
from contractor_audit.shared.findings import Evidence


def check(ctx, payable) -> list:
    t = ctx.terms
    groups = defaultdict(list)
    for line in ctx.lines:
        if line.item_code in t.daily_limits:
            groups[(line.item_code, ctx.work_area_of(line), line.work_date)].append(line)
    sch4 = ctx.data.raw_extraction["schedule_4"]["daily_limits"]
    out = []
    for (code, area, day), members in sorted(groups.items()):
        limit = t.daily_limits[code].limit
        members.sort(key=ctx.measurement_key)
        used = Decimal(0)
        contributing = [m for m in members if payable[m.line_ref] > 0]
        breached = sum((payable[m.line_ref] for m in contributing), Decimal(0)) > limit
        if breached and len(contributing) > 1:
            for app_no in sorted({m.application_no for m in contributing}):
                out.append(Unresolved(app_no, None, "limit_allocation_unresolved",
                                      f"{code} in {area} on {day}: {len(contributing)} measurements exceed the daily limit together; "
                                      "Clause 31 does not say which of them bears the excess"))
        for line in members:
            want = payable[line.line_ref]
            pay = max(Decimal(0), min(want, limit - used))
            used += pay
            if pay >= want:
                continue
            others = [m.line_ref for m in members if m is not line]
            out.append(RuleOutput(finding(Category.DAILY_LIMIT_EXCEEDED, line.application_no, "limits.daily",
                                          f"{code} is limited to {qty(limit)} {t.daily_limits[code].unit} per work area per day; "
                                          f"{area} on {day} would reach {qty(used - pay + want)}; line payable {qty(pay)} of {qty(want)}.",
                                          line=line, observed=qty(want), expected=qty(pay), affects_total=True,
                                          citations=(ctx.cite("31"), ctx.cite_text("Sch 4 Part 4", sch4["source_page"], sch4["source_text"])),
                                          evidence=(Evidence("same_day_measurements", f"{code}/{area}/{day}",
                                                             f"other lines that day: {', '.join(others) or 'none'}"),)),
                                  cap=pay, cap_measurable=False))
    return out
