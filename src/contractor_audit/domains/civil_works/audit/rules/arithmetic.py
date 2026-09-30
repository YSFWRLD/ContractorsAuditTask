"""Check 11: the billed arithmetic, independently of whether the rates are right.

* line: amount = quantity x billed rate. A line the contract divides at a band edge (Clause 28)
  has no single rate and its amount is the sum of its parts, so the product identity does not
  apply; the rates rule compares such a line's amount with the contract's split instead.
* header: application_total = sum of its line amounts (Clause 43).
* net payable and retention (Clauses 45, 45A): outside the invoice total.
"""

from decimal import ROUND_FLOOR, Decimal

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.models import RuleOutput
from contractor_audit.domains.civil_works.audit.rules.common import finding, money
from contractor_audit.domains.civil_works.rounding import amount_to_cents
from contractor_audit.shared.findings import Evidence


def check(ctx, valuations) -> list:
    out = []
    by_ref = {l.line_ref: l for l in ctx.lines}
    c28, c43 = ctx.cite("28"), ctx.cite("43")
    for ref in sorted(valuations):
        v, line = valuations[ref], by_ref[ref]
        product = line.quantity * line.rate_applied
        contract = v.contract_billed
        split = contract is not None and contract.is_split
        if not split:
            expected = amount_to_cents(product)
            if line.amount_cents != expected or product * 100 != (product * 100).to_integral_value():
                out.append(RuleOutput(finding(Category.LINE_TOTAL_ARITHMETIC, line.application_no, "arithmetic.line_product",
                                              f"Amount {money(line.amount_cents)} is not quantity x billed rate = {money(expected)}.",
                                              line=line, observed=money(line.amount_cents), expected=money(expected),
                                              impact_cents=line.amount_cents - expected, affects_total=True, citations=(c28,))))

    for app in ctx.data.applications:
        lines = ctx.lines_by_app[app.application_no]
        s = sum(l.amount_cents for l in lines)
        ev = (Evidence("application", app.application_no,
                       f"application_total {money(app.application_total_cents)}; {len(lines)} lines summing to {money(s)}; retention {money(app.retention_cents)}; "
                       f"adjustment {money(app.adjustment_cents)}; retention released {money(app.retention_released_cents)}; net {money(app.net_payable_cents)}"),)
        if app.application_total_cents != s:
            out.append(RuleOutput(finding(Category.APPLICATION_TOTAL_MISMATCH, app.application_no, "arithmetic.header_total",
                                          f"Application total {money(app.application_total_cents)} does not equal the sum of its lines {money(s)}; "
                                          "an application whose total does not agree is returned unpaid.",
                                          observed=money(app.application_total_cents), expected=money(s),
                                          impact_cents=app.application_total_cents - s, affects_total=True, citations=(c43,), evidence=ev)))
        ret = int((Decimal(app.application_total_cents) * ctx.terms.retention_percent / 100).to_integral_value(rounding=ROUND_FLOOR))
        if app.retention_cents != ret:
            out.append(RuleOutput(finding(Category.RETENTION_INCORRECT, app.application_no, "arithmetic.retention",
                                          f"Retention {money(app.retention_cents)}; 5% of the application total rounded down is {money(ret)}.",
                                          observed=money(app.retention_cents), expected=money(ret), impact_cents=app.retention_cents - ret,
                                          outside_total=True, citations=(ctx.cite("45"),), evidence=ev)))
        net = app.application_total_cents + app.adjustment_cents - app.retention_cents + app.retention_released_cents
        if app.net_payable_cents != net:
            out.append(RuleOutput(finding(Category.APPLICATION_TOTAL_MISMATCH, app.application_no, "arithmetic.net_payable",
                                          f"Net payable {money(app.net_payable_cents)} is not total + adjustment - retention + released = {money(net)}.",
                                          observed=money(app.net_payable_cents), expected=money(net), impact_cents=app.net_payable_cents - net,
                                          outside_total=True, citations=(ctx.cite("45A"),), evidence=ev)))
    return out
