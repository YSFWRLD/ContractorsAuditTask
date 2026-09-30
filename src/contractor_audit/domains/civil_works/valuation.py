"""Contract-side valuation of every line and application under one interpretation.

Measured work (Clause 27/28 pricing of each line) is kept apart from the sums Clause 45A says
sit outside the measured total: the Clause 31A retroactive-rate adjustment and the Clause 45A
retention release. Nothing here reads a billed rate, amount or total, and nothing is judged.

The measured quantity priced is the quantity stated on the line; which part of it is payable
(records, limits, exclusions) is decided by quantity_rules.py and, later, the audit rules.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping

from contractor_audit.domains.civil_works.contract import ContractTerms, Instrument
from contractor_audit.domains.civil_works.contract_period import ContractPeriod, ContractPeriodStatus
from contractor_audit.domains.civil_works.interpretation import (WORKING_INTERPRETATION, CivilWorksInterpretation,
                                                                 RetroAdjustmentTrigger)
from contractor_audit.domains.civil_works.models import Application, ApplicationLine
from contractor_audit.domains.civil_works.pricing import LineContext, LinePrice, PricingEngine
from contractor_audit.domains.civil_works.rebates import RebateLedger, band_order_key
from contractor_audit.domains.civil_works.rounding import round_down_to_halala


@dataclass(frozen=True)
class PricedLine:
    line_ref: str
    application_no: str
    price: LinePrice
    period: ContractPeriodStatus


@dataclass(frozen=True)
class OutsideMeasuredAdjustment:
    kind: str                         # "clause_31a_retroactive_rate" | "clause_45a_retention_release"
    application_no: str
    amount_cents: int
    clause: str
    basis: tuple[str, ...]            # line refs / application numbers the amount is computed from
    interpretation: str | None
    note: str


@dataclass(frozen=True)
class ApplicationValuation:
    application_no: str
    measured_work_total_cents: int
    retention_cents: int
    outside_measured_adjustments: tuple[OutsideMeasuredAdjustment, ...]


@dataclass(frozen=True)
class DatasetValuation:
    interpretation: CivilWorksInterpretation
    lines: dict[str, PricedLine]
    applications: dict[str, ApplicationValuation]
    adjustments: tuple[OutsideMeasuredAdjustment, ...]


def retention_cents(measured_total_cents: int, percent: Decimal) -> int:
    """Clause 45 p.8: percent of the application total, rounded down to the halala."""
    return int(round_down_to_halala(Decimal(measured_total_cents) / 100 * percent / 100) * 100)


def on_post_issue_side(application_date: date, issued: date, trigger: RetroAdjustmentTrigger) -> bool:
    """Whether an application is priced with an instrument issued on `issued` (Clause 31A / A3 recital)."""
    if trigger is RetroAdjustmentTrigger.ON_OR_AFTER_ISSUE:
        return application_date >= issued
    return application_date > issued


def line_context(line: ApplicationLine, app: Application, interp: CivilWorksInterpretation) -> LineContext:
    return LineContext(item_code=line.item_code, work_date=line.work_date, zone=line.site_zone, work_area=line.site,
                       ground_class=line.ground_class, night_work=line.night_work, known_at=app.application_date,
                       include_issued_on_known_at=interp.retro_adjustment_trigger is RetroAdjustmentTrigger.ON_OR_AFTER_ISSUE)


def retention_release(applications: list[Application], retention_held: Mapping[str, int], completion: date,
                      percent_released: Decimal = Decimal(50)) -> OutsideMeasuredAdjustment | None:
    """Clause 45A p.32: on the first application submitted after the Date for Completion as extended,
    one half of the retention held on all earlier applications, rounded down to the halala.

    'Earlier' is taken as submitted on an earlier date; `retention_held` says what was held on each.
    """
    after = sorted((a for a in applications if a.application_date > completion), key=lambda a: (a.application_date, a.application_no))
    if not after:
        return None
    first = after[0]
    earlier = [a for a in applications if a.application_date < first.application_date]
    held = sum(retention_held[a.application_no] for a in earlier)
    released = int(round_down_to_halala(Decimal(held) / 100 * percent_released / 100) * 100)
    return OutsideMeasuredAdjustment(
        "clause_45a_retention_release", first.application_no, released, "45A p.32", tuple(sorted(a.application_no for a in earlier)), None,
        f"first application submitted after {completion} ({first.application_date}); {len(earlier)} earlier applications held {held} halalas")


class Valuer:
    def __init__(self, terms: ContractTerms, interpretation: CivilWorksInterpretation = WORKING_INTERPRETATION):
        self.terms = terms
        self.interp = interpretation
        self.engine = PricingEngine(terms, interpretation)
        self.period = ContractPeriod(terms)

    def value(self, applications: list[Application], lines: list[ApplicationLine]) -> DatasetValuation:
        apps = {a.application_no: a for a in applications}
        ledger = RebateLedger(self.terms, self.interp.rebate_counting, self.period)
        ordered = sorted(lines, key=lambda l: band_order_key(l.work_date, l.application_no, l.line_no))
        priced: dict[str, PricedLine] = {}
        allocations = {}
        for line in ordered:
            app = apps[line.application_no]
            ctx = line_context(line, app, self.interp)
            alloc = ledger.allocate(line.item_code, line.work_date, line.quantity) if ledger.is_banded(line.item_code) else None
            allocations[line.line_ref] = alloc
            priced[line.line_ref] = PricedLine(line.line_ref, line.application_no, self.engine.price(ctx, line.quantity, alloc),
                                               self.period.status(line.work_date))

        adjustments: list[OutsideMeasuredAdjustment] = []
        for inst in self.terms.instruments:
            if inst.retroactive:
                adj = self._retro_adjustment(inst, applications, lines, apps, allocations)
                if adj:
                    adjustments.append(adj)

        totals: dict[str, int] = {a: 0 for a in apps}
        for pl in priced.values():
            totals[pl.application_no] += pl.price.amount_cents
        retention = {a: retention_cents(t, self.terms.retention_percent) for a, t in totals.items()}
        release = retention_release(applications, retention, self.period.final_completion)
        if release:
            adjustments.append(release)
        by_app: dict[str, list] = {a: [] for a in apps}
        for adj in adjustments:
            by_app[adj.application_no].append(adj)
        valuations = {a: ApplicationValuation(a, totals[a], retention[a], tuple(by_app[a])) for a in sorted(apps)}
        return DatasetValuation(self.interp, priced, valuations, tuple(adjustments))

    def _retro_adjustment(self, inst: Instrument, applications, lines, apps, allocations) -> OutsideMeasuredAdjustment | None:
        """Clause 31A: the difference on work already valued, as one adjustment on the first post-issue application."""
        trigger = self.interp.retro_adjustment_trigger
        post = sorted((a for a in applications if on_post_issue_side(a.application_date, inst.issued, trigger)),
                      key=lambda a: (a.application_date, a.application_no))
        codes = {s.code for s in inst.rate_substitutions}
        affected = [l for l in lines if l.item_code in codes and l.work_date >= inst.effective
                    and not on_post_issue_side(apps[l.application_no].application_date, inst.issued, trigger)]
        if not post:
            return None
        diff, basis = 0, []
        for line in sorted(affected, key=lambda l: l.line_ref):
            app = apps[line.application_no]
            before = self.engine.price(line_context(line, app, self.interp), line.quantity, allocations[line.line_ref])
            known = LineContext(**{**line_context(line, app, self.interp).__dict__, "known_at": None})
            after = self.engine.price(known, line.quantity, allocations[line.line_ref])
            if after.amount_cents != before.amount_cents:
                diff += after.amount_cents - before.amount_cents
                basis.append(line.line_ref)
        first = post[0]
        same_day = [a.application_no for a in post if a.application_date == first.application_date]
        note = (f"{inst.id} issued {inst.issued}, effective {inst.effective}; {len(basis)} lines valued before issue at the superseded rate; "
                f"first application on the post-issue side: {first.application_no} ({first.application_date})")
        if len(same_day) > 1:
            note += f"; {len(same_day)} applications share that date ({', '.join(same_day)}), taken in application-number order"
        return OutsideMeasuredAdjustment("clause_31a_retroactive_rate", first.application_no, diff, "31A p.32; A3 p.43", tuple(basis),
                                         f"retro_adjustment_trigger={trigger.value}", note)
