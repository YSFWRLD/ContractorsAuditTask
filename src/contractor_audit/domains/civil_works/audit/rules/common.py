"""Helpers every rule uses to build findings the same way."""

from decimal import Decimal

from contractor_audit.domains.civil_works.audit.categories import CATEGORY_INFO, Category
from contractor_audit.domains.civil_works.models import ApplicationLine
from contractor_audit.domains.civil_works.rounding import cents_to_decimal
from contractor_audit.domains.civil_works.trace import TraceStep
from contractor_audit.shared.findings import Citation, Evidence, Finding, Outcome


def money(cents: int | None) -> str | None:
    return None if cents is None else str(cents_to_decimal(cents))


def qty(q: Decimal) -> str:
    return format(q.normalize(), "f") if q == q.to_integral_value() else str(q)


def line_evidence(line: ApplicationLine) -> Evidence:
    return Evidence("billed_line", line.line_ref,
                    f"{line.item_code} {qty(line.quantity)} {line.unit} @ {line.rate_applied} = {money(line.amount_cents)}; "
                    f"work {line.work_date} in {line.site} / {line.site_zone}"
                    + (f"; ground {line.ground_class}" if line.ground_class else "") + ("; night" if line.night_work else "")
                    + (f"; record {line.record_ref}" if line.record_ref else "; no record reference"))


def trace_evidence(steps: tuple[TraceStep, ...], reference: str) -> tuple[Evidence, ...]:
    """Phase 2 pricing trace steps, carried into the finding unchanged in substance."""
    return tuple(Evidence("pricing_trace", f"{reference}:{s.rule}", s.calculation, s.source, s.result, s.interpretation) for s in steps)


def finding(category: Category, invoice_id: str, rule: str, message: str, *, line: ApplicationLine | None = None,
            observed: str | None = None, expected: str | None = None, impact_cents: int | None = None,
            citations: tuple[Citation, ...] = (), evidence: tuple[Evidence, ...] = (), affects_total: bool = False,
            outside_total: bool = False, outcome: Outcome | None = None) -> Finding:
    info = CATEGORY_INFO[category]
    ev = ((line_evidence(line),) if line is not None else ()) + tuple(evidence)
    if outcome is None:
        outcome = Outcome.PART_REJECT if affects_total else Outcome.QUERY
    return Finding(check=info.check, outcome=outcome, message=message, clause=citations[0].reference if citations else None,
                   line_ref=line.line_ref if line is not None else None, evidence=ev, invoice_id=invoice_id,
                   category=category.value, rule=rule, observed=observed, expected=expected, impact_cents=impact_cents,
                   citations=citations, affects_total=affects_total, outside_total=outside_total)
