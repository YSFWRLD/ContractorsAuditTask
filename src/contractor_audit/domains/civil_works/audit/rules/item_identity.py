"""Check 6: the billed item is the priced item — in its Schedule 1 unit, and as its record describes it.

Compatibility is principled, not case-specific: a record must be of the Schedule 5 series for the
item, and its phrase (record_quantities.RULES) must describe that item.
"""

from decimal import Decimal

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.models import RuleOutput
from contractor_audit.domains.civil_works.audit.rules.common import finding
from contractor_audit.domains.civil_works.audit.rules.records import evidence_cap, link_record, record_evidence


def check(ctx, payable) -> list:
    out = []
    cap, measurable = evidence_cap(ctx)
    c26 = ctx.cite("26")
    p24 = ctx.cite("P24")
    for line in ctx.lines:
        boq = ctx.terms.boq.get(line.item_code)
        if boq is None:
            # Check 6: not identified against a priced item. P24 values such work at daywork or an agreed rate;
            # neither daywork sheets nor an agreed rate are in the data, so the line cannot be priced (total blank).
            out.append(RuleOutput(finding(Category.ITEM_NOT_IN_CONTRACT, line.application_no, "item.not_in_schedule_1",
                                          f"{line.item_code} has no rate in Schedule 1; it could only be valued at daywork rates or a rate agreed "
                                          "in writing before the work (P24), and neither is evidenced.",
                                          line=line, observed=line.item_code, expected="a Schedule 1 item code", citations=(p24, c26))))
            continue
        if line.unit != boq.unit:
            out.append(RuleOutput(finding(Category.UNIT_MISMATCH, line.application_no, "item.unit",
                                          f"{line.item_code} is measured in {boq.unit} (Schedule 1 p.{boq.provenance.page}); the line presents {line.unit}. "
                                          "A quantity in another unit is rejected in its entirety rather than converted.",
                                          line=line, observed=line.unit, expected=boq.unit, citations=(c26,), affects_total=True),
                                  cap=Decimal(0), cap_measurable=False))
        link = link_record(ctx, line)
        if link is None or link.record is None:
            continue
        if "wrong_series" in link.problems or "item_not_indicated" in link.problems:
            q = link.quantity
            if "wrong_series" in link.problems:
                why = f"{link.reference} is a {link.record.title} ({link.record.record_type}); Schedule 5 requires a {link.required_series} record for {line.item_code}"
            else:
                why = f"{link.reference} describes {', '.join(q.indicated_items)} ('{q.raw_text}'), not {line.item_code}"
            out.append(RuleOutput(finding(Category.ITEM_RECORD_MISMATCH, line.application_no, "item.record_describes_other_item",
                                          f"{why}; the record does not evidence this item.",
                                          line=line, observed=f"{link.record.record_type}: {', '.join(q.indicated_items) if q and q.resolved else '?'}",
                                          expected=f"{link.required_series or 'matching'} record describing {line.item_code}",
                                          citations=(ctx.cite("47A"), ctx.cite("46")), affects_total=cap is not None,
                                          evidence=record_evidence(link)),
                                  cap=cap, cap_measurable=measurable))
    return out
