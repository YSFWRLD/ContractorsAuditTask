"""PD-210 Contract-Year volume tiers (Schedule 2 Part 2), under the selected scope and Contract Year readings.

"The rate for item PD-210 is taken at the percentage below according to the metres already drilled on the
well in the Contract Year (Clause 3A). Metres are counted from zero at the start of each Contract Year, and an
interval that crosses a band is divided at the band."

    volume_tier_scope   PER_WELL (the operative sentence) | CONTRACT_WIDE (the heading and column)
    contract_year_2     STARTS_2026_01_01 | YEAR_1_EXTENDED

"Metres already drilled" counts every metre drilled (each day's depth advance), not only PD-210 metres; within
a day, metres before the charged interval count. For the contract-wide reading, wells drilled on the same day
are taken in well order (the reports carry no time of day): a stated, deterministic tie-break.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from contractor_audit.domains.drilling.contract.models import ContractTerms


@dataclass(frozen=True)
class DrillingDay:
    well: str
    day: date
    depth_start: int
    depth_end: int


def contract_year(terms: ContractTerms, day: date, reading: str) -> int:
    if reading == "YEAR_1_EXTENDED":
        return 1
    return next((y.year for y in terms.contract_years if y.start <= day <= y.end), 0)


class MetreCounter:
    """Metres already drilled before a given (well, day, depth), by scope and Contract Year."""

    def __init__(self, terms: ContractTerms, days: list[DrillingDay], scope: str, year_reading: str):
        self.scope, self.year_reading, self.terms = scope, year_reading, terms
        self._before: dict[tuple[str, date], int] = {}
        running: dict[tuple, int] = defaultdict(int)
        for d in sorted(days, key=lambda d: (d.day, d.well)):
            key = self._key(d.well, d.day)
            self._before[(d.well, d.day)] = running[key]
            running[key] += max(d.depth_end - d.depth_start, 0)
        self._starts = {(d.well, d.day): d.depth_start for d in days}

    def _key(self, well: str, day: date) -> tuple:
        year = contract_year(self.terms, day, self.year_reading)
        return (year, well) if self.scope == "PER_WELL" else (year,)

    def before(self, well: str, day: date, from_m: int) -> int:
        return self._before[(well, day)] + (from_m - self._starts[(well, day)])


def split_by_tiers(terms: ContractTerms, already: int, metres: int) -> list[tuple[int, Decimal, int]]:
    """[(metres, percent of rate, tier)] for metres numbered already+1 .. already+metres."""
    out = []
    first = already + 1
    last = already + metres
    for tier in terms.volume_tiers:
        lo, hi = max(first, tier.from_m), min(last, tier.to_m if tier.to_m is not None else last)
        if hi >= lo:
            out.append((hi - lo + 1, tier.percent_of_rate, tier.band))
    return out
