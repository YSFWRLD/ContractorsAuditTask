"""From recorded quantity to chargeable quantity: chargeability, the 21A rig-up hour, the 6-hour minimum, daily limits.

Only rules the contract states clearly remove a quantity here (Standby days for not-chargeable services,
Operating-day-only clauses, Appendix A's hole sizes, the term). Conditions whose consequence is an open
audit question (a missing record part, a blank signature, an unverified call-off) are carried as flags.
"""

from decimal import Decimal

from contractor_audit.domains.drilling.contract.models import ContractTerms, ServiceDefinition, StandbyTreatment
from contractor_audit.domains.drilling.interpretation.models import Quantity
from contractor_audit.domains.drilling.pricing.models import Step
from contractor_audit.domains.drilling.pricing.selection import Selection

MINIMUM_HOURS_CLAUSE = "21 / P10 / Schedule 3 Part 7"


def chargeability(terms: ContractTerms, q: Quantity, service: ServiceDefinition) -> tuple[str | None, tuple[str, ...]]:
    """(reason it is not chargeable, or None; flags left for the audit phase)."""
    if q.date and not (terms.commencement <= q.date <= terms.final_expiry):
        return f"service date {q.date} outside the term {terms.commencement}..{terms.final_expiry} (A1 1.1 / A2 2.1)", ()
    flags = []
    for c in q.conditions:
        if c.code == "OPERATING_DAY" and c.satisfied is False:
            return f"charged only for an Operating day (cl. {c.clause.removeprefix('cl. ')}); {c.note}", ()
        if c.code == "PERFORMANCE_SECTION_NOMINATED":
            if c.satisfied is False:
                return f"{c.note} (cl. 23 / Appendix A)", ()
            if c.satisfied is None:
                flags.append("ELIGIBILITY_UNVERIFIED_CALLOFF (AMB-13)")
        if c.code.startswith("RECORD_PART_") and c.satisfied is False:
            flags.append(f"{c.code}_ABSENT (cl. 37 / Schedule 5; consequence AMB-23)")
        if c.code == "REPORT_SIGNED" and c.satisfied is False:
            flags.append(f"REPORT_NOT_SIGNED (cl. 15; consequence AMB-23): {c.note}")
    if q.day_status == "Standby" and service.standby.treatment is StandbyTreatment.NOT_CHARGEABLE:
        return "not chargeable on a Standby day in any quantity (cl. 20 / Schedule 3 Part 3)", ()
    return None, tuple(flags)


def chargeable_quantity(terms: ContractTerms, q: Quantity, service: ServiceDefinition, selection: Selection,
                        first_in_run: bool) -> tuple[Decimal, tuple[Step, ...], list[tuple[str, str]]]:
    value = q.quantity
    steps: list[Step] = []
    used: list[tuple[str, str]] = []

    def note(name, clause, new, why):
        nonlocal value
        if new != value:
            steps.append(Step(name, clause, value, "", int(new), why))
            value = new

    if service.unit == "hour":
        reading = selection.value("rig_up_hour")
        used.append(("rig_up_hour", reading))
        minimum = Decimal(service.minimum_hours_operating_day) if service.minimum_hours_operating_day else None
        deduct = reading in ("PER_DAY_THEN_MINIMUM", "MINIMUM_THEN_PER_DAY") or (reading == "PER_BHA_RUN" and first_in_run)
        if reading == "MINIMUM_THEN_PER_DAY" and minimum is not None:
            note("minimum hours", MINIMUM_HOURS_CLAUSE, max(value, minimum), f"not less than {minimum} hours")
        if deduct:
            note("rig-up hour", "21A", max(value - 1, Decimal(0)), f"first hour of the period in the hole ({reading})")
        if reading != "MINIMUM_THEN_PER_DAY" and minimum is not None:
            note("minimum hours", MINIMUM_HOURS_CLAUSE, max(value, minimum), f"not less than {minimum} hours")
    if service.daily_limit and q.scope.value == "DAY":
        note("daily limit", "22 / Schedule 3 Part 5", min(value, Decimal(service.daily_limit.quantity)),
             f"limit {service.daily_limit.quantity} {service.daily_limit.unit} per day")
    return value, tuple(steps), used
