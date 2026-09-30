"""Shared helpers: building a Quantity with a deterministic id, and the conditions evaluated from reports."""

from datetime import date
from decimal import Decimal

from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DailyReport
from contractor_audit.domains.drilling.interpretation.ambiguity import later_dependencies
from contractor_audit.domains.drilling.interpretation.models import (
    Basis, Condition, FieldRef, MappingStatus, Quantity, Scope,
)

# Appendix A: a performance-drilled section is a 12-1/4 inch or 8-1/2 inch section the call-off nominates.
PERFORMANCE_SECTION_SIZES = ('12-1/4"', '8-1/2"')


def make_quantity(terms: ContractTerms, code: str, quantity, basis: Basis, scope: Scope, *, well: str, day: date | None,
                  reports: tuple[DailyReport, ...], derivation: str, clauses: tuple[str, ...], evidence: tuple[FieldRef, ...],
                  status: MappingStatus, run: int | None = None, conditions: tuple[Condition, ...] = (),
                  readings: tuple[tuple[str, str], ...] = (), ambiguity_ids: tuple[str, ...] = (),
                  detail: tuple[tuple[str, str], ...] = ()) -> Quantity:
    service = terms.services[code]
    day_report = reports[0] if len(reports) == 1 else None
    # a day's status belongs to day-scope quantities only; a run or well charge is not a Standby-day charge
    status_of_day = day_report.operations.status if scope is Scope.DAY and day_report and day_report.operations else None
    sections = {r.operations.hole_section for r in reports if r.operations}
    section = sections.pop() if len(sections) == 1 else None
    key = "|".join([code, scope.value, well, str(run or ""), str(day or ""), derivation,
                    ",".join(f"{s}={v}" for s, v in readings), ",".join(f"{k}={v}" for k, v in detail)])
    return Quantity(
        qid=key, service_code=code, quantity=Decimal(quantity), unit=service.unit, basis=basis, scope=scope, well=well,
        date=day, report_ids=tuple(r.report_id for r in reports), run=run, derivation=derivation, clauses=clauses,
        evidence=evidence, mapping_status=status, day_status=status_of_day, hole_section=section, conditions=conditions,
        readings=readings, depends_on=later_dependencies(service, status_of_day), ambiguity_ids=ambiguity_ids, detail=detail)


def operating_day(report: DailyReport, clause: str) -> Condition:
    return Condition("OPERATING_DAY", clause, report.operations.status == "Operating", f"status {report.operations.status}")


def standby_day(report: DailyReport, clause: str) -> Condition:
    return Condition("STANDBY_DAY", clause, report.operations.status == "Standby", f"status {report.operations.status}")


def record_part(report: DailyReport, part: str) -> Condition:
    present = part in report.parts
    return Condition(f"RECORD_PART_{part}", "Schedule 5 / cl. 37", present, f"Part {part} {'present' if present else 'absent'}")


def signed(report: DailyReport) -> Condition:
    blank = [s.role for s in report.signatures if s.blank]
    return Condition("REPORT_SIGNED", "cl. 15", not blank and len(report.signatures) >= 2,
                     "blank: " + ", ".join(blank) if blank else "both signatories named")


def performance_section(report: DailyReport) -> Condition:
    section = report.operations.hole_section
    if section in PERFORMANCE_SECTION_SIZES:
        return Condition("PERFORMANCE_SECTION_NOMINATED", "cl. 23 / Appendix A", None,
                         f"{section} may be performance-drilled; the call-off nominating it is not in the data (AMB-13)")
    return Condition("PERFORMANCE_SECTION_NOMINATED", "cl. 23 / Appendix A", False,
                     f"{section} is not a size Appendix A allows for a performance-drilled section")
