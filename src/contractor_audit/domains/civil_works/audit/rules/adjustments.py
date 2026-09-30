"""Check 8 (outside the measured total): the Clause 31A retroactive-rate adjustment and the Clause 45A release.

The amounts come from the Phase 2 valuation (`valuation.Valuer`), which computes them from the
contract; this rule only compares them with the application's `adjustment` and
`retention_released` columns. Both sit outside application_total (Clause 45A), so neither
changes the corrected invoice total.
"""

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.models import RuleOutput
from contractor_audit.domains.civil_works.audit.rules.common import finding, money
from contractor_audit.shared.findings import Evidence

_COLUMN = {"clause_31a_retroactive_rate": ("adjustment_cents", "adjustment", "31A"),
           "clause_45a_retention_release": ("retention_released_cents", "retention_released", "45A")}


def check(ctx, phase2) -> list:
    expected: dict[tuple[str, str], object] = {(a.kind, a.application_no): a for a in phase2.adjustments}
    out = []
    for app in ctx.data.applications:
        for kind, (attr, column, clause) in _COLUMN.items():
            adj = expected.get((kind, app.application_no))
            want = adj.amount_cents if adj else 0
            have = getattr(app, attr)
            if want == have:
                continue
            what = "retroactive-rate adjustment (Amendment No. 3)" if kind.startswith("clause_31a") else "release of half the retention held"
            ev = (Evidence("contract_adjustment", app.application_no, adj.note if adj else f"no {what} is due on this application",
                           adj.clause if adj else clause, money(want), adj.interpretation if adj else None),)
            if adj is not None:
                ev += (Evidence("adjustment_basis", app.application_no,
                                f"{len(adj.basis)} {'lines' if kind.startswith('clause_31a') else 'earlier applications'}: {', '.join(adj.basis[:12])}{' ...' if len(adj.basis) > 12 else ''}"),)
            category = Category.ADJUSTMENT_MISSING if have == 0 else Category.ADJUSTMENT_INCORRECTLY_APPLIED
            out.append(RuleOutput(finding(category, app.application_no, f"adjustments.{kind}",
                                          f"{column} shows {money(have)}; the contract requires {money(want)} here as the {what}. "
                                          "This sum is settled outside the application total.",
                                          observed=money(have), expected=money(want), impact_cents=have - want,
                                          outside_total=True, citations=(ctx.cite(clause),), evidence=ev)))
    return out
