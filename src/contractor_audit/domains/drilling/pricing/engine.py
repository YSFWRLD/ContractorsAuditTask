"""`price`: interpreted quantities -> priced quantities under an explicit selection. No invoice is read.

Chain kept on every priced quantity: report evidence (FieldRefs) -> the Phase 3 quantity (qid) -> the
readings used (switch, value, source) -> the rate statement relied on -> quantity and rate steps -> the
rounded amount. The caller supplies well classes when calloff_evidence allows them; pricing never looks them up.
"""

from collections.abc import Mapping
from decimal import Decimal
from functools import lru_cache

from contractor_audit.domains.drilling.contract.models import ContractTerms, RateBasis
from contractor_audit.domains.drilling.interpretation.models import InterpretationResult, Quantity
from contractor_audit.domains.drilling.interpretation.switches import Switch
from contractor_audit.domains.drilling.pricing.build_up import DayContext, EvidenceNotProvided, Unpriceable, build_up
from contractor_audit.domains.drilling.pricing.lost_in_hole import value_lost_tool
from contractor_audit.domains.drilling.pricing.models import PricedPart, PricedQuantity, PricingResult, PricingStatus, RateSource, Step
from contractor_audit.domains.drilling.pricing.quantity_rules import chargeability, chargeable_quantity
from contractor_audit.domains.drilling.pricing.rates import resolve, retroactive_instruments
from contractor_audit.domains.drilling.pricing.rounding import half_even_cents
from contractor_audit.domains.drilling.pricing.selection import Selection, require
from contractor_audit.domains.drilling.pricing.tiers import DrillingDay, MetreCounter, split_by_tiers

RATE_READINGS = ("LATER_ISSUED_GOVERNS", "LATER_EFFECTIVE_GOVERNS", "MONTHLY_TABLE_SEPARATE")
PD210 = "PD-210"


def selected(q: Quantity, selection: Selection) -> bool:
    return all(selection.value(s) == v for s, v in q.readings)


def price(result: InterpretationResult, terms: ContractTerms, switches: dict[str, Switch], selection: Selection,
          well_classes: Mapping[str, str] | None = None, services: set[str] | None = None) -> PricingResult:
    require(selection, switches)
    calloff = selection.value("calloff_evidence")
    if calloff == "INVOICE_STATEMENT_UNVERIFIED" and well_classes is None:
        raise ValueError("calloff_evidence = INVOICE_STATEMENT_UNVERIFIED needs the stated well classes to be supplied")
    classes = well_classes if calloff == "INVOICE_STATEMENT_UNVERIFIED" else {}
    included = [q for q in result.quantities if selected(q, selection)]
    retro = retroactive_instruments(terms)
    rate_reading = selection.value("dd120_rate_from_feb_2026")

    @lru_cache(maxsize=None)
    def rate_for(code, day, reading, exclude):
        return resolve(terms, code, day, reading, exclude)

    first_in_run = set()
    seen = set()
    for q in sorted(included, key=lambda q: (q.service_code, q.well, q.run or 0, q.date or q.qid)):
        if terms.services[q.service_code].unit == "hour" and q.scope.value == "DAY":
            key = (q.service_code, q.well, q.run)
            if key not in seen:
                seen.add(key)
                first_in_run.add(q.qid)
    counter = None
    if any(q.service_code == PD210 for q in included) and (services is None or PD210 in services):
        days = {}
        for q in (x for x in result.quantities if x.service_code == PD210):
            d = dict(q.detail)
            lo, hi = int(d["from_m"]), int(d["to_m"])
            cur = days.get((q.well, q.date))
            days[(q.well, q.date)] = (min(lo, cur[0]), max(hi, cur[1])) if cur else (lo, hi)
        counter = MetreCounter(terms, [DrillingDay(w, day, lo, hi) for (w, day), (lo, hi) in days.items()],
                               selection.value("volume_tier_scope"), selection.value("contract_year_2"))

    priced = []
    for q in included:
        if services is not None and q.service_code not in services:
            continue
        priced.append(_price_one(terms, q, selection, classes, rate_for, rate_reading, retro, q.qid in first_in_run, counter))
    return PricingResult(tuple(priced), selection.canonical, selection.hypothetical(),
                         tuple((n, c.value, c.source.value) for n, c in sorted(selection.choices.items())))


def _price_one(terms, q: Quantity, selection: Selection, classes, rate_for, rate_reading, retro, first_in_run, counter) -> PricedQuantity:
    service = terms.services[q.service_code]
    used = [(s, v) for s, v in q.readings]
    reason, flags = chargeability(terms, q, service)
    common = dict(qid=q.qid, service_code=q.service_code, well=q.well, date=q.date, report_ids=q.report_ids, unit=q.unit,
                  recorded_quantity=q.quantity, evidence=q.evidence)

    def finish(status, why, chargeable, qsteps, parts, amount, amount_without, flag_list, rate_without=None):
        sources = {n: c.source.value for n, c in selection.choices.items()}
        readings = tuple(dict.fromkeys((s, v, sources.get(s, "?")) for s, v in used))
        conditional = None
        if status is PricingStatus.PRICED and eligibility_not_established:
            # the rate is known, but whether the service was chargeable at all needs the call-off (AMB-13): the
            # calculation is kept as a conditional amount only, never payable
            status, why, conditional, amount, amount_without = (
                PricingStatus.EVIDENCE_NOT_PROVIDED,
                f"{q.service_code} eligibility not established: the call-off is not provided, and {q.service_code} is chargeable only for "
                "a performance-drilled section the call-off nominates (cl. 23) (AMB-13: UNKNOWN / UNVERIFIED); the rate is calculated "
                "and kept as a conditional amount only", amount, 0, None)
        return PricedQuantity(**common, chargeable_quantity=chargeable, quantity_steps=qsteps, status=status, reason=why,
                              parts=tuple(parts), amount_cents=amount, amount_without_retroactive_cents=amount_without,
                              flags=tuple(flag_list), readings_used=readings, conditional_amount_cents=conditional,
                              rate_without_retroactive_cents=rate_without)

    eligibility_not_established = False
    if reason:
        return finish(PricingStatus.NOT_CHARGEABLE, reason, Decimal(0), (), (), 0, None, ())
    chargeable, qsteps, qused = chargeable_quantity(terms, q, service, selection, first_in_run)
    used += qused
    flags = list(flags)
    unverified_eligibility = any(f.startswith("ELIGIBILITY_UNVERIFIED_CALLOFF") for f in flags)
    if unverified_eligibility and service.rate_basis is not RateBasis.SCHEDULE_2:
        used.append(("calloff_evidence", selection.value("calloff_evidence")))
        eligibility_not_established = selection.value("calloff_evidence") == "UNVERIFIABLE_QUERY"
    try:
        if service.rate_basis is RateBasis.SCHEDULE_2 and unverified_eligibility:
            used.append(("calloff_evidence", selection.value("calloff_evidence")))
            if selection.value("calloff_evidence") == "UNVERIFIABLE_QUERY":
                raise EvidenceNotProvided("performance-drilled section not established: PD-210 is charged only on sections the call-off "
                                          "nominates (cl. 23), and the call-off is not provided (AMB-13: UNKNOWN / UNVERIFIED)")
        if q.date is None:
            raise Unpriceable("quantity has no service date")
        well_class = classes.get(q.well)
        day = DayContext(q.date, q.day_status, q.hole_section, well_class)
        if service.class_rated and (service.rate_basis is not RateBasis.SCHEDULE_2 or selection.value("pd210_class_factor") == "APPLY"):
            used.append(("calloff_evidence", selection.value("calloff_evidence")))
            if well_class is not None:
                flags.append("WELL_CLASS_FROM_INVOICE_STATEMENT_UNVERIFIED (AMB-13)")
        if service.rate_basis is RateBasis.CLAUSE_31:
            rate, steps, rate_cents, lused = value_lost_tool(terms, q, selection)
            used += lused
            parts = [PricedPart(chargeable, rate, steps, rate_cents, half_even_cents(chargeable * rate_cents))]
            return finish(PricingStatus.PRICED, "", chargeable, qsteps, parts, sum(p.amount_cents for p in parts), None, flags)
        if service.rate_basis is RateBasis.SCHEDULE_2:
            parts, bused = _price_pd210(terms, service, q, chargeable, day, selection, counter)
            used += bused
            return finish(PricingStatus.PRICED, "", chargeable, qsteps, parts, sum(p.amount_cents for p in parts), None, flags)
        rate = rate_for(q.service_code, q.date, rate_reading, frozenset())
        if rate is None:
            raise Unpriceable("Schedule 1 prints no rate for this service")
        if len({rate_for(q.service_code, q.date, r, frozenset()).rate_cents for r in RATE_READINGS}) > 1:
            used.append(("dd120_rate_from_feb_2026", rate_reading))
        steps, rate_cents, bused = build_up(terms, service, rate, day, selection)
        used += bused
        parts = [PricedPart(chargeable, rate, steps, rate_cents, half_even_cents(chargeable * rate_cents))]
        amount = parts[0].amount_cents
        without = earlier_cents = None
        if rate.source in retro:
            earlier = rate_for(q.service_code, q.date, rate_reading, retro)
            _, earlier_cents, _ = build_up(terms, service, earlier, day, selection)
            without = half_even_cents(chargeable * earlier_cents)
        return finish(PricingStatus.PRICED, "", chargeable, qsteps, parts, amount, without, flags, earlier_cents)
    except EvidenceNotProvided as exc:
        return finish(PricingStatus.EVIDENCE_NOT_PROVIDED, str(exc), chargeable, qsteps, (), 0, None, flags)
    except Unpriceable as exc:
        return finish(PricingStatus.UNPRICEABLE, str(exc), chargeable, qsteps, (), 0, None, flags)


def _price_pd210(terms: ContractTerms, service, q: Quantity, chargeable: Decimal, day: DayContext, selection: Selection, counter):
    d = dict(q.detail)
    band = next(b for b in terms.depth_bands if b.band == int(d["band"]))
    rate = RateSource("SCHEDULE_2", "DEPTH_BAND", band.rate_cents, None, None, None, 17, (f"SCHEDULE_2:band {band.band}:{band.rate_cents}",))
    used = [("volume_tier_scope", selection.value("volume_tier_scope")), ("contract_year_2", selection.value("contract_year_2"))]
    already = counter.before(q.well, q.date, int(d["from_m"]))
    parts = []
    for metres, percent, tier in split_by_tiers(terms, already, int(chargeable)):
        tier_rate = half_even_cents(Decimal(band.rate_cents) * percent / 100)
        start = (Step("volume tier", "Schedule 2 Part 2", Decimal(band.rate_cents), str(percent / 100), tier_rate,
                      f"tier {tier}: metres {already + 1}.. already drilled in the Contract Year ({used[0][1]}, {used[1][1]})"),)
        steps, rate_cents, bused = build_up(terms, service, rate, day, selection, start_steps=start)
        used += bused
        parts.append(PricedPart(Decimal(metres), rate, steps, rate_cents, half_even_cents(metres * Decimal(rate_cents)),
                                (("band", str(band.band)), ("tier", str(tier)), ("metres_already_drilled", str(already)))))
        already += metres
    return parts, used
