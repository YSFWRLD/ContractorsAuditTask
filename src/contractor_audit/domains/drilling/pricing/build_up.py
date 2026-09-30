"""The rate build-up of Clause 18, with the index of Clause 17A before it and the principal discount after it.

    17A    Rig Services Index (Schedule 2C services)                     switch rig_services_index
    18.1   hole-section factor, where section-rated                      switch standby_section_factor (Standby days, 17B)
    18.2   well-class factor, where class-rated                          switch pd210_class_factor (PD-210, 17B)
    18.3   standby percentage, on a Standby day (Schedule 3 Part 3)
    S2/A2  principal-services discount, the last factor before rounding  switch principal_discount_combination
                                                                         (monthly rates: switch monthly_rate_basis)
Each step is rounded to the nearest cent, half to even (cl. 17).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from contractor_audit.domains.drilling.contract.models import ContractTerms, ServiceDefinition, StandbyTreatment
from contractor_audit.domains.drilling.pricing.models import RateSource, Step
from contractor_audit.domains.drilling.pricing.rounding import half_even_cents
from contractor_audit.domains.drilling.pricing.selection import Selection


class Unpriceable(ValueError):
    pass


class EvidenceNotProvided(Unpriceable):
    """The price needs a fact the supplied evidence cannot establish (e.g. the well class a missing call-off states)."""


@dataclass(frozen=True)
class DayContext:
    service_date: date
    day_status: str | None
    hole_section: str | None
    well_class: str | None


def _step(steps: list, name: str, clause: str, value: int, factor: Decimal, note: str = "") -> int:
    out = half_even_cents(Decimal(value) * factor)
    steps.append(Step(name, clause, Decimal(value), str(factor), out, note))
    return out


def build_up(terms: ContractTerms, service: ServiceDefinition, rate: RateSource, day: DayContext, selection: Selection,
             start_steps: tuple[Step, ...] = ()) -> tuple[tuple[Step, ...], int, list[tuple[str, str]]]:
    """(steps, final rate in cents, switches consulted). Raises Unpriceable when an input is missing."""
    steps: list[Step] = [Step("rate", _rate_clause(rate), Decimal(rate.rate_cents), "1", rate.rate_cents, f"{rate.source} {rate.kind}")] + list(start_steps)
    value = steps[-1].output_cents
    used: list[tuple[str, str]] = []
    standby = day.day_status == "Standby"

    if service.indexed and rate.source == "SCHEDULE_1":
        reading = selection.value("rig_services_index")
        used.append(("rig_services_index", reading))
        if reading == "APPLY_FROM_FIRST_MONTH":
            month = day.service_date.strftime("%Y-%m")
            index = terms.price_index.monthly.get(month)
            if index is None:
                raise Unpriceable(f"no Rig Services Index published for {month}")
            value = _step(steps, "index", "17A / Schedule 2C", value, index / terms.price_index.base_index, f"index {index} / {terms.price_index.base_index}")

    skip_schedule_3 = False
    if rate.kind == "MONTHLY":
        reading = selection.value("monthly_rate_basis")
        used.append(("monthly_rate_basis", reading))
        skip_schedule_3 = reading == "FINAL_RATE"

    if service.section_rated and not skip_schedule_3:
        apply = True
        if standby:
            reading = selection.value("standby_section_factor")
            used.append(("standby_section_factor", reading))
            apply = reading == "APPLY"
        if apply:
            factor = terms.section_factors.get(day.hole_section or "")
            if factor is None:
                raise Unpriceable(f"no hole-section factor for section {day.hole_section!r}")
            value = _step(steps, "section factor", "18 / Schedule 3 Part 1", value, factor, day.hole_section)

    if service.class_rated and not skip_schedule_3:
        apply = True
        if service.code == "PD-210":
            reading = selection.value("pd210_class_factor")
            used.append(("pd210_class_factor", reading))
            apply = reading == "APPLY"
        if apply:
            if day.well_class is None:
                raise EvidenceNotProvided("well class not established: the call-off is not provided (AMB-13: UNKNOWN / UNVERIFIED)")
            factor = terms.class_factors.get(day.well_class)
            if factor is None:
                raise Unpriceable(f"no well-class factor for {day.well_class!r}")
            value = _step(steps, "class factor", "18 / Schedule 3 Part 2", value, factor, day.well_class)

    if standby and not skip_schedule_3 and service.standby.treatment is StandbyTreatment.PERCENT:
        value = _step(steps, "standby percentage", "18 / 20 / Schedule 3 Part 3", value, service.standby.percent / 100,
                      f"{service.standby.percent}% on a Standby day")

    discounts = terms.discounts_on(service.code, day.service_date)
    if discounts:
        reading = selection.value("principal_discount_combination")
        used.append(("principal_discount_combination", reading))
        for d in (discounts[-1:] if reading == "LATER_REPLACES" else discounts):
            value = _step(steps, "principal discount", f"{d.instrument_id} (the last factor of the build-up)", value,
                          1 - d.percent / 100, f"{d.percent}% from {d.effective}")
    return tuple(steps), value, used


def _rate_clause(rate: RateSource) -> str:
    return {"SCHEDULE_1": "Schedule 1", "SCHEDULE_2": "Schedule 2 / cl. 23"}.get(rate.source, f"{rate.source} ({rate.kind.lower()})")
