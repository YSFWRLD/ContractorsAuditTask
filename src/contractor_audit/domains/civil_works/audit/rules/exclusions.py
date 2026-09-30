"""Check 9 (exclusions): Clause 32 / Sch 4 Part 5 / P19 (A.14.020 after A.14.010) and P21 (E.51.020 on a surfacing day).

Uses the Phase 2 ExclusionEvaluator under the `exclusion_window` reading; a finding that exists
only because the same day counts records that dependency (see the dependency analysis).
"""

from decimal import Decimal

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.models import RuleOutput
from contractor_audit.domains.civil_works.audit.rules.common import finding
from contractor_audit.domains.civil_works.quantity_rules import ExclusionEvaluator, Measurement, exclusion_rules
from contractor_audit.shared.findings import Evidence


def check(ctx, payable) -> list:
    by_ref = {l.line_ref: l for l in ctx.lines}
    ms = [Measurement(l.line_ref, l.item_code, ctx.work_area_of(l), l.work_date) for l in ctx.lines]
    hits = ExclusionEvaluator(exclusion_rules(ctx.terms), ctx.interp.exclusion_window).evaluate(ms)
    out = []
    for h in sorted(hits, key=lambda h: h.excluded.key):
        line = by_ref[h.excluded.key]
        clause_ids = ["P21"] if h.rule.clause.startswith("P21") else ["32", "P19"]
        when = "the same day as" if h.days_after == 0 else f"{h.days_after} day(s) after"
        out.append(RuleOutput(finding(Category.EXCLUSION_WINDOW_VIOLATION, line.application_no,
                                      "exclusions.p21_same_day" if clause_ids == ["P21"] else "exclusions.two_day_window",
                                      f"{line.item_code} measured {when} {h.excluded_by.item_code} ({h.excluded_by.key}) on {h.excluded.work_area}; "
                                      f"not measurable ({h.rule.clause}).",
                                      line=line, observed=f"{h.days_after} day(s) after {h.excluded_by.key}", expected="not measured in the window",
                                      citations=tuple(ctx.cite(c) for c in clause_ids), affects_total=True,
                                      evidence=(Evidence("excluding_measurement", h.excluded_by.key,
                                                         f"{h.excluded_by.item_code} on {h.excluded_by.work_date}", h.rule.clause, None,
                                                         f"exclusion_window={h.window}" if h.rule.window_switch_applies else None),)),
                              cap=Decimal(0), cap_measurable=False))
    return out
