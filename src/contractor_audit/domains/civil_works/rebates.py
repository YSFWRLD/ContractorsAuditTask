"""Stateful rebate-band ledger (Schedule 4 Part 3, pp.24-25; Clause 30 p.6; Clause 28 p.6).

Bands are printed as whole-unit ranges ('1 to 4,000', '4,001 to 16,000', 'above 16,000').
They are read as cumulative intervals (0, 4000], (4000, 16000], (16000, inf): the 4,000th unit
is the last at 100%, the 4,001st the first at 96%. A measurement that crosses a band edge is
divided at the edge (Sch 4 Part 3) and each part is priced at its own rounded rate (Clause 28).

What the counter restarts on is an interpretation switch (RebateCounting). Measurements must be
fed in the order the contract prescribes; the caller owns that order (see `band_order_key`).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from contractor_audit.domains.civil_works.contract import Band, ContractTerms
from contractor_audit.domains.civil_works.contract_period import ContractPeriod
from contractor_audit.domains.civil_works.interpretation import RebateCounting


@dataclass(frozen=True)
class BandEdge:
    printed: str
    lower: Decimal            # cumulative quantity already counted when this band starts
    upper: Decimal | None     # None = open-ended
    percent_of_rate: Decimal


@dataclass(frozen=True)
class BandSlice:
    quantity: Decimal
    percent_of_rate: Decimal
    band_printed: str
    cumulative_from: Decimal  # counter before this slice
    cumulative_to: Decimal    # counter after this slice


@dataclass(frozen=True)
class BandAllocation:
    item_code: str
    period_key: str
    quantity: Decimal
    volume_before: Decimal
    volume_after: Decimal
    slices: tuple[BandSlice, ...]
    notes: tuple[str, ...] = ()

    @property
    def crosses_band_edge(self) -> bool:
        return len(self.slices) > 1


def band_edges(code: str, bands: tuple[Band, ...]) -> tuple[BandEdge, ...]:
    edges = []
    lower = Decimal(0)
    for i, band in enumerate(bands):
        if band.above is not None:
            if band.above != lower:
                raise ValueError(f"{code}: 'above {band.above}' does not continue from {lower}")
            edges.append(BandEdge(band.printed, lower, None, band.percent_of_rate))
            if i != len(bands) - 1:
                raise ValueError(f"{code}: open-ended band is not last")
            continue
        if Decimal(band.start) != lower + 1:
            raise ValueError(f"{code}: band {band.printed!r} does not start at {lower + 1}")
        upper = Decimal(band.end)
        edges.append(BandEdge(band.printed, lower, upper, band.percent_of_rate))
        lower = upper
    return tuple(edges)


def band_order_key(work_date: date, application_no: str, line_no: int) -> tuple:
    """Clause 30's ordering: date of execution, then application number, then line number.

    Schedule 4 Part 3 substitutes Clause 30 without restating an order; this is the only order
    the contract gives anywhere, so it is used under both counting readings.
    """
    return (work_date, application_no, line_no)


@dataclass
class RebateLedger:
    terms: ContractTerms
    counting: RebateCounting
    period: ContractPeriod
    _volumes: dict[tuple[str, str], Decimal] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.edges = {code: band_edges(code, bands) for code, bands in self.terms.bands.items()}

    def is_banded(self, item_code: str) -> bool:
        return item_code in self.edges

    def period_key(self, work_date: date) -> tuple[str, tuple[str, ...]]:
        if self.counting is RebateCounting.WHOLE_WORKS:
            return "whole_works", ()
        year = self.period.contract_year(work_date)
        if year is not None:
            return f"contract_year_{year.year}", ()
        last, first = self.period.years[-1], self.period.years[0]
        if work_date > last.end:
            return f"contract_year_{last.year}", (f"{work_date} is after the final Contract Year ({last.end}); counted in it for illustration only (not measurable).",)
        return f"contract_year_{first.year}", (f"{work_date} is before the first Contract Year; counted in it.",)

    def volume(self, item_code: str, key: str) -> Decimal:
        return self._volumes.get((item_code, key), Decimal(0))

    def allocate(self, item_code: str, work_date: date, quantity: Decimal) -> BandAllocation:
        """Split `quantity` across bands from the current counter, then advance the counter."""
        if quantity < 0:
            raise ValueError("negative quantity")
        key, notes = self.period_key(work_date)
        before = self.volume(item_code, key)
        remaining, cursor, slices = quantity, before, []
        for edge in self.edges[item_code]:
            if remaining == 0:
                break
            if edge.upper is not None and cursor >= edge.upper:
                continue
            room = remaining if edge.upper is None else min(remaining, edge.upper - cursor)
            slices.append(BandSlice(room, edge.percent_of_rate, edge.printed, cursor, cursor + room))
            cursor += room
            remaining -= room
        if quantity == 0:
            first = next(e for e in self.edges[item_code] if e.upper is None or before < e.upper)
            slices.append(BandSlice(Decimal(0), first.percent_of_rate, first.printed, before, before))
        self._volumes[(item_code, key)] = cursor
        return BandAllocation(item_code, key, quantity, before, cursor, tuple(slices), notes)
