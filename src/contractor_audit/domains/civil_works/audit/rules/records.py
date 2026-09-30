"""Check 4: every Schedule 5 line has its record, signed as Clause 47 requires, for that work area and date.

`link_record` is the single place a line is joined to the record it quotes (direct reference
lookup only) and the record's fitness for that line is assessed; the quantity and item-identity
rules reuse it.
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.models import RuleOutput
from contractor_audit.domains.civil_works.audit.options import MissingRecordConsequence, UnsignedRecord
from contractor_audit.domains.civil_works.audit.rules.common import finding
from contractor_audit.domains.civil_works.models import ApplicationLine
from contractor_audit.domains.civil_works.record_quantities import RecordQuantity
from contractor_audit.domains.civil_works.records import SiteRecord
from contractor_audit.shared.findings import Evidence

EVIDENCE_PROBLEMS = ("record_not_found", "no_reference", "wrong_series", "item_not_indicated", "area_mismatch", "date_mismatch")


@dataclass(frozen=True)
class RecordLink:
    line_ref: str
    required_series: str | None
    reference: str | None
    record: SiteRecord | None
    quantity: RecordQuantity | None
    problems: tuple[str, ...]

    def usable(self, unsigned: UnsignedRecord) -> bool:
        """The record can be used to measure the line's quantity."""
        tolerated = {"unsigned"} if unsigned is UnsignedRecord.ACCEPTED_WITH_DEFECT else set()
        return self.record is not None and set(self.problems) <= tolerated


def link_record(ctx, line: ApplicationLine) -> RecordLink | None:
    """None when the item needs no Schedule 5 record and none is quoted."""
    req = ctx.terms.required_records.get(line.item_code)
    if req is None and not line.record_ref:
        return None
    series = req.reference_series if req else None
    if not line.record_ref:
        return RecordLink(line.line_ref, series, None, None, None, ("no_reference",))
    record = ctx.data.records.get(line.record_ref)
    if record is None:
        return RecordLink(line.line_ref, series, line.record_ref, None, None, ("record_not_found",))
    q = ctx.data.quantities.get(line.record_ref)
    problems = []
    if not (record.foreman.signed and record.engineer_rep.signed):
        problems.append("unsigned")
    if series is not None and record.record_type != series:
        problems.append("wrong_series")
    elif q is not None and q.resolved and line.item_code not in q.indicated_items:
        problems.append("item_not_indicated")
    if record.area != line.site:
        problems.append("area_mismatch")
    if record.date is not None:
        if record.date != line.work_date:
            problems.append("date_mismatch")
    elif record.week_beginning is not None and not record.week_beginning <= line.work_date <= record.week_beginning + timedelta(6):
        problems.append("date_mismatch")
    if q is None or not q.resolved:
        problems.append("quantity_unresolved")
    elif line.item_code in ctx.terms.boq and q.unit != ctx.terms.boq[line.item_code].unit:
        problems.append("unit_incomparable")
    return RecordLink(line.line_ref, series, line.record_ref, record, q, tuple(problems))


def record_evidence(link: RecordLink) -> tuple[Evidence, ...]:
    if link.record is None:
        return ()
    r, q = link.record, link.quantity
    when = str(r.date) if r.date else f"week beginning {r.week_beginning}, days on {', '.join(str(d) for d in r.days_on)}"
    ev = [Evidence("site_record", r.ticket, f"{r.title}; {r.area}; {when}; foreman {r.foreman.name or 'UNSIGNED'}; "
                                          f"Engineer's rep {r.engineer_rep.name or 'UNSIGNED'}; text: {r.description!r}", r.source_file)]
    if q is not None:
        ev.append(Evidence("record_quantity", r.ticket, f"rule {q.rule_id}: {q.quantity} {q.unit}; phrase indicates {', '.join(q.indicated_items) or '-'}"
                           if q.resolved else f"unresolved: {q.reason}"))
    return tuple(ev)


def evidence_cap(ctx) -> tuple[Decimal | None, bool]:
    """Payable-quantity cap for a line whose record does not evidence it, per the consequence reading."""
    if ctx.audit_interp.missing_record_consequence is MissingRecordConsequence.NOT_PAYABLE_IN_THIS_APPLICATION:
        return Decimal(0), True        # Clause 46: 'not payable' (still measured)
    return None, True                  # P23: payable now, deducted from the next valuation


def _consequence_note(ctx) -> str:
    if ctx.audit_interp.missing_record_consequence is MissingRecordConsequence.NOT_PAYABLE_IN_THIS_APPLICATION:
        return "not payable in this valuation (Clause 46)"
    return "to be deducted from the next valuation (P23)"


def check(ctx, payable) -> list:
    out = []
    cap, measurable = evidence_cap(ctx)
    c46, c47 = ctx.cite("46"), ctx.cite("47")
    sch5 = ctx.data.raw_extraction["schedule_5"]
    sch5_cite = ctx.cite_text("Schedule 5", sch5["source_page"], "The items listed below are not payable in any valuation until the record named against them has been delivered to the Engineer.")
    for line in ctx.lines:
        link = link_record(ctx, line)
        if link is None or link.required_series is None:
            continue
        note = _consequence_note(ctx)
        ev = record_evidence(link)
        if "no_reference" in link.problems or "record_not_found" in link.problems:
            what = "quotes no record reference" if "no_reference" in link.problems else f"quotes {link.reference}, which does not exist in the site records"
            out.append(RuleOutput(finding(Category.MISSING_RECORD, line.application_no,
                                          "records.missing_reference" if "no_reference" in link.problems else "records.record_not_found",
                                          f"{line.item_code} requires a {link.required_series} record (Schedule 5); the line {what}; {note}.",
                                          line=line, observed=link.reference or "none", expected=f"a {link.required_series} record",
                                          citations=(sch5_cite, c46, ctx.cite("P23")), affects_total=cap is not None, evidence=ev),
                                  cap=cap, cap_measurable=measurable))
            continue
        if "unsigned" in link.problems:
            invalid = ctx.audit_interp.unsigned_record is UnsignedRecord.NOT_A_VALID_RECORD
            missing = [n for n, s in (("foreman", link.record.foreman), ("Engineer's representative", link.record.engineer_rep)) if not s.signed]
            out.append(RuleOutput(finding(Category.UNSIGNED_RECORD, line.application_no, "records.unsigned",
                                          f"{link.reference} lacks the {' and '.join(missing)} signature required by Clause 47"
                                          + (f"; not a Schedule 5 record, so {note}." if invalid else "; accepted as evidence with a defect."),
                                          line=line, observed="unsigned: " + ", ".join(missing), expected="signed and countersigned",
                                          citations=(c47, ctx.cite("P22")), affects_total=invalid and cap is not None, evidence=ev),
                                  cap=cap if invalid else None, cap_measurable=measurable))
        # A record of the wrong series or describing another item is not this line's record at all; that single
        # defect is reported once (item_record_mismatch), not again as an area/date mismatch.
        wrong_record = "wrong_series" in link.problems or "item_not_indicated" in link.problems
        mism = [] if wrong_record else [p for p in ("area_mismatch", "date_mismatch") if p in link.problems]
        if mism:
            r = link.record
            detail = []
            if "area_mismatch" in mism:
                detail.append(f"record area {r.area} vs line {line.site}")
            if "date_mismatch" in mism:
                detail.append(f"record {'date ' + str(r.date) if r.date else 'week beginning ' + str(r.week_beginning)} vs work date {line.work_date}")
            out.append(RuleOutput(finding(Category.RECORD_LINE_MISMATCH, line.application_no, "records.area_or_date",
                                          f"{link.reference} does not evidence this line ({'; '.join(detail)}); {note}.",
                                          line=line, observed="; ".join(detail), expected="record for the line's work area and date",
                                          citations=(c47, ctx.cite("47A")), affects_total=cap is not None, evidence=ev),
                                  cap=cap, cap_measurable=measurable))
    return out
