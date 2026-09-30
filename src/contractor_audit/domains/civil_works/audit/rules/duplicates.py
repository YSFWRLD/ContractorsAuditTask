"""Check 10 (line level): Clause 44 — the same item, work area and date measured more than once.

The later measurement is disallowed in full. A record's quantity billed twice on different dates is
a separate question, handled with the record allowance in quantity.py (DUPLICATE_RECORD).
"""

from collections import defaultdict
from decimal import Decimal

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.models import RuleOutput
from contractor_audit.domains.civil_works.audit.rules.common import finding
from contractor_audit.shared.findings import Evidence


def check(ctx, payable) -> list:
    groups = defaultdict(list)
    for line in ctx.lines:
        groups[(line.item_code, ctx.work_area_of(line), line.work_date)].append(line)
    out = []
    c44 = ctx.cite("44")
    for (code, area, day), members in sorted(groups.items()):
        if len(members) < 2:
            continue
        members.sort(key=ctx.measurement_key)
        first = members[0]
        for later in members[1:]:
            out.append(RuleOutput(finding(Category.DUPLICATE_LINE, later.application_no, "duplicates.same_item_area_date",
                                          f"{code} in {area} on {day} is already measured on {first.line_ref}; the later measurement is disallowed in full.",
                                          line=later, observed=f"measured again ({later.line_ref})", expected=f"measured once ({first.line_ref})",
                                          citations=(c44,), affects_total=True,
                                          evidence=(Evidence("earlier_measurement", first.line_ref,
                                                             f"{first.item_code} {first.quantity} {first.unit} in {first.application_no}"),)),
                                  cap=Decimal(0), cap_measurable=False))
    return out
