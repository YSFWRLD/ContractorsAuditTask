"""Contract rules that decide how much of a measured quantity is payable.

These evaluators return what the contract allows, with the clause and reading used.
They do not compare against an invoice or decide that anything is wrong.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Hashable, Iterable

from contractor_audit.domains.civil_works.contract import ContractTerms
from contractor_audit.domains.civil_works.interpretation import (ChargeableHourScope, ExclusionWindow,
                                                                 SurveyQuantityRule)

SURVEY_TOLERANCE = Decimal("0.02")   # Clause 33A


# --------------------------------------------------------------------------- 33 / 33A surveyed items

@dataclass(frozen=True)
class QuantityAllowance:
    rule: str
    clause: str
    measured: Decimal
    reference: Decimal
    payable_quantity: Decimal
    payable_as_measured_up_to: Decimal
    note: str = ""


def surveyed_payable(measured: Decimal, surveyed: Decimal, rule: SurveyQuantityRule) -> QuantityAllowance:
    """Payable quantity of a surveyed item (Sch 4 Part 6) measured against a joint survey sheet.

    A measured quantity below the survey is payable as measured under both readings: the contract
    cannot pay more than is claimed.
    """
    if rule is SurveyQuantityRule.TOLERANCE_33A:
        ceiling = surveyed * (1 + SURVEY_TOLERANCE)
        payable = measured if measured <= ceiling else surveyed
        return QuantityAllowance(rule.value, "33A p.32", measured, surveyed, payable, ceiling,
                                 "within 2% of the survey: as measured" if measured <= ceiling else "more than 2% over: surveyed quantity only")
    payable = min(measured, surveyed)
    return QuantityAllowance(rule.value, "33 p.7", measured, surveyed, payable, surveyed, "the surveyed quantity exactly")


def recorded_payable(measured: Decimal, recorded: Decimal) -> QuantityAllowance:
    """A non-surveyed Schedule 5 item: payable up to the quantity its record states (Clauses 46-47; guideline 5)."""
    return QuantityAllowance("record_cap", "46-47 p.8; guideline check 5", measured, recorded, min(measured, recorded), recorded)


# --------------------------------------------------------------------------- 6A chargeable hour

def chargeable_hours(hours_attended: Decimal) -> Decimal:
    """Clause 6A: every hour of an attendance except the first. Fractions are kept exact."""
    return max(Decimal(0), hours_attended - 1)


def chargeable_hours_by_scope(entries: Iterable[tuple[Hashable, Hashable, Hashable, Decimal]],
                              scope: ChargeableHourScope) -> dict[Hashable, Decimal]:
    """Chargeable hours per group, grouping (line_key, record_key, area_day_key, hours) entries by `scope`.

    PER_RECORD and PER_WORK_AREA_DAY sum the hours of a group before deducting the first hour once;
    PER_LINE deducts it from each entry.
    """
    groups: dict[Hashable, Decimal] = defaultdict(Decimal)
    for line_key, record_key, area_day_key, hours in entries:
        key = {ChargeableHourScope.PER_LINE: line_key, ChargeableHourScope.PER_RECORD: record_key,
               ChargeableHourScope.PER_WORK_AREA_DAY: area_day_key}[scope]
        groups[key] += hours
    return {k: chargeable_hours(v) for k, v in groups.items()}


# --------------------------------------------------------------------------- 47A week

def week_measurable(days_worked: int, minimum: int = 5) -> bool:
    """Clause 47A / Sch 5 note: a week is measurable only where the record shows >= 5 days worked."""
    return days_worked >= minimum


# --------------------------------------------------------------------------- exclusions (32, Sch 4 Part 5, P19, P21)

@dataclass(frozen=True)
class ExclusionRule:
    excluded_item: str
    excluding_items: frozenset[str]
    days_following: int              # 0 = same day only
    clause: str
    window_switch_applies: bool      # whether ExclusionWindow decides the same-day question


def exclusion_rules(terms: ContractTerms) -> tuple[ExclusionRule, ...]:
    rules = [ExclusionRule(e.excluded_item, frozenset({e.excluded_by}), e.period_days, "32 p.6; Sch 4 Part 5 p.26; P19 p.13", True)
             for e in terms.exclusions]
    # P21 p.13: E.51.020 is not measurable on a day any surfacing item is measured for the same work area.
    rules.append(ExclusionRule("E.51.020", frozenset({"D.41.020", "D.41.030", "D.41.050", "D.43.010", "D.43.020"}), 0, "P21 p.13", False))
    return tuple(rules)


@dataclass(frozen=True)
class Measurement:
    key: str                  # e.g. line_ref
    item_code: str
    work_area: str
    work_date: date


@dataclass(frozen=True)
class ExclusionHit:
    excluded: Measurement
    excluded_by: Measurement
    days_after: int
    rule: ExclusionRule
    window: str


class ExclusionEvaluator:
    def __init__(self, rules: tuple[ExclusionRule, ...], window: ExclusionWindow):
        self.rules = rules
        self.window = window

    def _days(self, rule: ExclusionRule) -> range:
        if rule.days_following == 0:
            return range(0, 1)
        start = 0 if (not rule.window_switch_applies or self.window is ExclusionWindow.SAME_DAY_INCLUDED) else 1
        return range(start, rule.days_following + 1)

    def evaluate(self, measurements: Iterable[Measurement]) -> list[ExclusionHit]:
        """Every measurement falling inside an exclusion window opened by an excluding measurement."""
        ms = list(measurements)
        index: dict[tuple[str, str, date], list[Measurement]] = defaultdict(list)
        for m in ms:
            index[(m.item_code, m.work_area, m.work_date)].append(m)
        hits = []
        for rule in self.rules:
            for m in ms:
                if m.item_code != rule.excluded_item:
                    continue
                for d in self._days(rule):
                    day = m.work_date - timedelta(days=d)
                    blockers = [b for code in sorted(rule.excluding_items) for b in index.get((code, m.work_area, day), [])]
                    if blockers:
                        hits.append(ExclusionHit(m, blockers[0], d, rule, self.window.value if rule.window_switch_applies else "same_day_rule"))
                        break
        return hits


# --------------------------------------------------------------------------- daily limitations (31, Sch 4 Part 4)

@dataclass(frozen=True)
class DailyLimitUse:
    item_code: str
    work_area: str
    work_date: date
    measured: Decimal
    limit: Decimal
    excess: Decimal
    measurement_keys: tuple[str, ...]


def daily_limit_use(terms: ContractTerms, measurements: Iterable[tuple[Measurement, Decimal]]) -> list[DailyLimitUse]:
    """Total measured per item, work area and day against the Schedule 4 Part 4 limit.

    Clause 31: the excess 'is not payable and shall not be carried forward'. Which measurement
    within a day bears the excess is not stated; only the day's excess is reported.
    """
    totals: dict[tuple[str, str, date], list] = defaultdict(lambda: [Decimal(0), []])
    for m, qty in measurements:
        if m.item_code in terms.daily_limits:
            slot = totals[(m.item_code, m.work_area, m.work_date)]
            slot[0] += qty
            slot[1].append(m.key)
    out = []
    for (code, area, day), (qty, keys) in sorted(totals.items()):
        limit = terms.daily_limits[code].limit
        out.append(DailyLimitUse(code, area, day, qty, limit, max(Decimal(0), qty - limit), tuple(keys)))
    return out
