"""Checks 2 and 3: the contract was live on the work date; the application's period and timing.

Work date governs (guideline 1); the application date matters only for Clause 41's window.
"""

from datetime import timedelta
from decimal import Decimal

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.models import RuleOutput
from contractor_audit.domains.civil_works.audit.rules.common import finding
from contractor_audit.shared.findings import Evidence

SUBMISSION_WINDOW_DAYS = 21   # Clause 41


def check(ctx, payable) -> list:
    out = []
    period = ctx.period
    a2 = next(i for i in ctx.terms.instruments if i.new_completion_date == period.final_completion)
    completion_cite = ctx.cite_text(f"{a2.name} 2.1", a2.page, "Work executed on or before the extended Date for Completion is measurable and payable under this Subcontract; work executed after it is not.")
    ag = ctx.data.raw_extraction["agreement"]["commencement_date"]
    commence_cite = ctx.cite_text("Agreement", ag["source_page"], ag["source_text"])
    c41 = ctx.cite("41")

    for line in ctx.lines:
        status = period.status(line.work_date)
        if status.measurable:
            continue
        if line.work_date > period.final_completion:
            out.append(RuleOutput(finding(Category.WORK_AFTER_FINAL_COMPLETION, line.application_no, "period.after_final_completion",
                                          f"Work executed {line.work_date}, after the Date for Completion as extended ({period.final_completion}); not measurable or payable.",
                                          line=line, observed=str(line.work_date), expected=f"on or before {period.final_completion}",
                                          citations=(completion_cite,), affects_total=True,
                                          evidence=(Evidence("contract_period", line.line_ref, status.reason),)),
                                  cap=Decimal(0)))
        else:
            out.append(RuleOutput(finding(Category.WORK_OUTSIDE_CONTRACT_PERIOD, line.application_no, "period.before_commencement",
                                          f"Work executed {line.work_date}, before the Commencement Date {period.commencement}.",
                                          line=line, observed=str(line.work_date), expected=f"on or after {period.commencement}",
                                          citations=(commence_cite,), affects_total=True), cap=Decimal(0)))

    for app in ctx.data.applications:
        lines = ctx.lines_by_app[app.application_no]
        ev = Evidence("application", app.application_no, f"period {app.period_from} to {app.period_to}; submitted {app.application_date}")
        if app.application_date < app.period_to:
            out.append(RuleOutput(finding(Category.APPLICATION_TIMING, app.application_no, "period.submitted_before_period_closed",
                                          f"Submitted {app.application_date}, before the last day of the period it states ({app.period_to}).",
                                          observed=str(app.application_date), expected=f"on or after {app.period_to}", citations=(c41,), evidence=(ev,))))
        latest = app.period_to + timedelta(days=SUBMISSION_WINDOW_DAYS)
        if app.application_date > latest:
            out.append(RuleOutput(finding(Category.APPLICATION_TIMING, app.application_no, "period.submitted_late",
                                          f"Submitted {app.application_date}, {(app.application_date - app.period_to).days} days after its period ended (limit 21).",
                                          observed=str(app.application_date), expected=f"on or before {latest}", citations=(c41,), evidence=(ev,))))
        outside = [l for l in lines if not app.period_from <= l.work_date <= app.period_to]
        for line in outside:
            out.append(RuleOutput(finding(Category.LINE_OUTSIDE_APPLICATION_PERIOD, app.application_no, "period.line_outside_stated_period",
                                          f"Line executed {line.work_date}, outside the stated period {app.period_from} to {app.period_to}; "
                                          "no item may be included in an application whose period does not include its day of execution.",
                                          line=line, observed=str(line.work_date), expected=f"{app.period_from} to {app.period_to}",
                                          citations=(c41,), affects_total=True, evidence=(ev,)), cap=Decimal(0)))
        if lines and not outside:
            first, last = min(l.work_date for l in lines), max(l.work_date for l in lines)
            if (first, last) != (app.period_from, app.period_to):
                out.append(RuleOutput(finding(Category.APPLICATION_PERIOD_MISSTATED, app.application_no, "period.misstated",
                                              f"Stated period {app.period_from} to {app.period_to}; its items were executed {first} to {last}.",
                                              observed=f"{app.period_from} to {app.period_to}", expected=f"{first} to {last}",
                                              citations=(ctx.cite("40"),), evidence=(ev,))))
    return out
