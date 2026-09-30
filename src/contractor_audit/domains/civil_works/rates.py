"""Rate in force for an item on a work date, across the Bill of Quantities and every instrument.

Precedence (Schedule of Variations p.38 and every instrument's closing words): instruments are
read in the order issued; each governs work executed on or after its own effective date (the
effective date stated against each rate where one is stated); where two instruments state a
rate for the same item, the later-issued governs work on or after its effective date.

`known_at` lets a caller price as an application submitted on a given date would have been:
an instrument issued after that date is not yet part of the Subcontract (Clause 31A). Which
side of the issue date an application falls on is decided by the caller (see adjustments.py).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from contractor_audit.domains.civil_works.contract import ContractTerms, Instrument
from contractor_audit.domains.civil_works.trace import TraceStep

BOQ_ID = "BOQ"


class RateKind(str, Enum):
    BILL_OF_QUANTITIES = "bill_of_quantities"   # Schedule 1 base rate
    SUBSTITUTED = "substituted"                 # instrument 'Substituted rates' table
    MONTHLY = "monthly"                         # instrument 'Monthly re-measurement' table


class PricingError(ValueError):
    """The contract data needed to price a case is absent; the engine refuses rather than guesses."""


@dataclass(frozen=True)
class RateProvision:
    item_code: str
    instrument_id: str            # "BOQ" for Schedule 1
    instrument_name: str
    issued: date | None           # None for the Bill of Quantities itself
    effective_from: date
    kind: RateKind
    rate: Decimal | None          # BOQ / SUBSTITUTED
    monthly: tuple[tuple[str, Decimal], ...] = ()   # MONTHLY: ((YYYY-MM, rate), ...) in month order
    page: int = 0

    def rate_for(self, work_date: date) -> tuple[Decimal, str]:
        if self.kind is not RateKind.MONTHLY:
            return self.rate, "fixed rate"
        month = f"{work_date.year:04d}-{work_date.month:02d}"
        table = dict(self.monthly)
        if month in table:
            return table[month], f"published rate for {month}"
        last_month, last_rate = self.monthly[-1]
        if month > last_month:
            return last_rate, f"month {month} is after the last published month {last_month}: 'the rate last published applies until it is superseded'"
        raise PricingError(f"{self.item_code}: no monthly rate for {month} under {self.instrument_id}")


@dataclass(frozen=True)
class RateResolution:
    item_code: str
    work_date: date
    known_at: date | None
    governing: RateProvision
    rate_in_force: Decimal        # before any Schedule 2A index or Schedule 2B conversion
    rate_note: str
    considered: tuple[RateProvision, ...]   # every provision in effect on the date, oldest first
    trace: tuple[TraceStep, ...]

    @property
    def kind(self) -> RateKind:
        return self.governing.kind

    @property
    def source_instrument(self) -> str:
        return self.governing.instrument_id

    @property
    def effective_from(self) -> date:
        return self.governing.effective_from


def _provisions_from_instrument(inst: Instrument) -> list[RateProvision]:
    out = [RateProvision(s.code, inst.id, inst.name, inst.issued, s.effective, RateKind.SUBSTITUTED, s.rate_payable, page=inst.page)
           for s in inst.rate_substitutions]
    by_code: dict[str, list] = {}
    for m in inst.monthly_rates:
        by_code.setdefault(m.code, []).append((m.month, m.rate_payable))
    for code, months in by_code.items():
        months.sort()
        first = date.fromisoformat(months[0][0] + "-01")
        out.append(RateProvision(code, inst.id, inst.name, inst.issued, max(first, inst.effective), RateKind.MONTHLY, None,
                                 tuple(months), page=inst.page))
    return out


class RateResolver:
    def __init__(self, terms: ContractTerms):
        self.terms = terms
        self._by_item: dict[str, list[RateProvision]] = {}
        for code, item in terms.boq.items():
            self._by_item[code] = [RateProvision(code, BOQ_ID, "Schedule 1 Bill of Quantities", None, terms.commencement_date,
                                                 RateKind.BILL_OF_QUANTITIES, item.base_rate, page=item.provenance.page)]
        for inst in terms.instruments:
            for prov in _provisions_from_instrument(inst):
                if prov.item_code not in self._by_item:
                    raise PricingError(f"{inst.id} states a rate for {prov.item_code}, which is not in Schedule 1")
                self._by_item[prov.item_code].append(prov)

    def provisions(self, item_code: str) -> list[RateProvision]:
        try:
            return list(self._by_item[item_code])
        except KeyError:
            raise PricingError(f"{item_code} is not a Schedule 1 item") from None

    @staticmethod
    def _issue_order(p: RateProvision) -> tuple:
        return (p.issued or date.min, p.instrument_id)

    def resolve(self, item_code: str, work_date: date, known_at: date | None = None, *,
                include_issued_on_known_at: bool = True) -> RateResolution:
        """Rate in force for `item_code` executed on `work_date`.

        With `known_at`, instruments issued after it are ignored; an instrument issued exactly on
        `known_at` counts only when `include_issued_on_known_at` is true.
        """
        def known(p: RateProvision) -> bool:
            if known_at is None or p.issued is None:
                return True
            return p.issued < known_at or (include_issued_on_known_at and p.issued == known_at)

        candidates = [p for p in self.provisions(item_code) if p.effective_from <= work_date]
        in_effect = sorted((p for p in candidates if known(p)), key=self._issue_order)
        if not in_effect:
            raise PricingError(f"{item_code}: no rate in force on {work_date} (before the Commencement Date?)")
        governing = in_effect[-1]
        rate, note = governing.rate_for(work_date)
        trace = [TraceStep(
            "rate_in_force", "Schedule of Variations p.38; instrument closing words",
            f"provisions in effect on {work_date}: " + ", ".join(f"{p.instrument_id} (issued {p.issued or 'n/a'}, from {p.effective_from})" for p in in_effect)
            + f"; later-issued governs -> {governing.instrument_id}; {note}",
            str(rate), {"item": item_code, "work_date": work_date.isoformat(), "known_at": known_at.isoformat() if known_at else "any"})]
        ignored = [p for p in candidates if not known(p)]
        if ignored:
            trace.append(TraceStep("instrument_not_yet_issued", "Clause 31A p.32",
                                   "ignored: " + ", ".join(f"{p.instrument_id} issued {p.issued}" for p in ignored), str(rate)))
        return RateResolution(item_code, work_date, known_at, governing, rate, note, tuple(in_effect), tuple(trace))

    def timeline(self, item_code: str) -> list[RateProvision]:
        """Every rate provision for the item in the order it takes effect (ties: order issued)."""
        return sorted(self.provisions(item_code), key=lambda p: (p.effective_from, self._issue_order(p)))
