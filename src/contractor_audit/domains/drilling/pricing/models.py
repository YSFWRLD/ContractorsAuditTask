"""Priced quantities with the whole chain: evidence -> quantity -> readings -> rate statement -> steps -> amount."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from contractor_audit.domains.drilling.interpretation.models import FieldRef


class PricingStatus(StrEnum):
    PRICED = "PRICED"
    NOT_CHARGEABLE = "NOT_CHARGEABLE"      # the contract says this evidence is not charged (e.g. a Standby day for a not-chargeable service)
    EVIDENCE_NOT_PROVIDED = "EVIDENCE_NOT_PROVIDED"  # the price needs evidence the data cannot establish (the call-off, AMB-13): a resolved outcome
    UNPRICEABLE = "UNPRICEABLE"            # the contract prices it, but another input it needs is missing (index month, section)


@dataclass(frozen=True)
class RateSource:
    """The rate statement relied on."""
    source: str                  # SCHEDULE_1, SCHEDULE_2, SCHEDULE_2D, SCHEDULE_6 or an instrument id
    kind: str
    rate_cents: int
    effective: date | None
    issued: date | None
    month: str | None
    page: int | None
    candidates: tuple[str, ...]  # every statement that spoke to the date, "source:kind:rate"


@dataclass(frozen=True)
class Step:
    """One step of the build-up: input -> factor -> rounded output, and why."""
    name: str
    clause: str
    input_cents: Decimal
    factor: str
    output_cents: int
    note: str = ""


@dataclass(frozen=True)
class PricedPart:
    """A priced slice of a quantity (PD-210 may split across volume tiers)."""
    quantity: Decimal
    rate: RateSource
    steps: tuple[Step, ...]
    rate_cents: int
    amount_cents: int
    detail: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class PricedQuantity:
    qid: str
    service_code: str
    well: str
    date: date | None
    report_ids: tuple[str, ...]
    unit: str
    recorded_quantity: Decimal
    chargeable_quantity: Decimal
    quantity_steps: tuple[Step, ...]
    status: PricingStatus
    reason: str
    parts: tuple[PricedPart, ...]
    amount_cents: int
    amount_without_retroactive_cents: int | None   # the same charge at rates known before a back-dated instrument was issued
    flags: tuple[str, ...]                         # conditions left for the audit phase (record parts, signatures, eligibility)
    readings_used: tuple[tuple[str, str, str], ...]  # (switch, value, source) that shaped this price
    evidence: tuple[FieldRef, ...]
    # EVIDENCE_NOT_PROVIDED only: what the calculated rate would come to if the missing evidence (eligibility) were
    # established. Conditional, never payable and never in a total; amount_cents stays 0.
    conditional_amount_cents: int | None = None
    # the per-unit rate at the rates known before a back-dated instrument was issued (Clause 36A); None when no
    # back-dated instrument changes this quantity's rate
    rate_without_retroactive_cents: int | None = None


@dataclass(frozen=True)
class PricingResult:
    priced: tuple[PricedQuantity, ...]
    canonical: bool
    hypothetical_switches: tuple[str, ...]
    selection: tuple[tuple[str, str, str], ...]

    def total_cents(self, services: set[str] | None = None) -> int:
        return sum(p.amount_cents for p in self.priced if services is None or p.service_code in services)
