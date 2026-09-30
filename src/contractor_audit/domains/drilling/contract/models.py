"""Typed view of the reviewed DDS-2025-118 terms (artifacts/drilling/contract_terms.json).

These classes state what the contract says. They never price a charge: where the contract supports more
than one reading, the model returns every candidate and leaves the choice to a later phase.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum


class FactStatus(StrEnum):
    STATED = "STATED"
    INTERPRETED = "INTERPRETED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_PROVIDED = "NOT_PROVIDED"


class RateBasis(StrEnum):
    SCHEDULE_1 = "SCHEDULE_1"   # a USD rate printed in Schedule 1
    SCHEDULE_2 = "SCHEDULE_2"   # PD-210: depth bands
    CLAUSE_31 = "CLAUSE_31"     # lost in hole: replacement value less depreciation


class StandbyTreatment(StrEnum):
    PERCENT = "PERCENT"
    NOT_CHARGEABLE = "NOT_CHARGEABLE"
    STANDBY_ONLY = "STANDBY_ONLY"
    FULL_WHATEVER_STATUS = "FULL_WHATEVER_STATUS"


class StatementKind(StrEnum):
    SCHEDULE_1 = "SCHEDULE_1"
    SUBSTITUTION = "SUBSTITUTION"
    MONTHLY = "MONTHLY"


class AmbiguityStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED_BY_TEXT = "RESOLVED_BY_TEXT"
    EVIDENCE_NOT_PROVIDED = "EVIDENCE_NOT_PROVIDED"
    NOTED = "NOTED"


@dataclass(frozen=True)
class Provenance:
    source_file: str
    page: int | None
    printed_page: int | None
    section: str
    source_text: str


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    kind: str
    first_page: int
    last_page: int
    in_contents: bool
    listed_in_clause_2: bool
    reference: str | None = None
    issued: date | None = None
    effective: date | None = None


@dataclass(frozen=True)
class PrecedenceRule:
    id: str
    rule: str
    status: FactStatus
    ambiguities: tuple[str, ...]


@dataclass(frozen=True)
class Standby:
    treatment: StandbyTreatment
    percent: Decimal | None


@dataclass(frozen=True)
class DailyLimit:
    quantity: int
    unit: str


@dataclass(frozen=True)
class ServiceDefinition:
    code: str
    series: int
    description: str
    unit: str
    rate_basis: RateBasis
    base_rate_cents: int | None
    section_rated: bool
    class_rated: bool           # as printed in Schedule 3 Part 2 (PD-210 is contested, AMB-02)
    standby: Standby
    daily_limit: DailyLimit | None
    once_per_well: bool
    minimum_hours_operating_day: int | None
    record_part_required: str | None
    indexed: bool
    monthly_republished_by: str | None
    rate_amended_by: tuple[str, ...]
    rate_discounted_by: tuple[str, ...]
    appendix_g_terms: tuple[str, ...]
    charged_for: str
    charge_timing: str | None
    governing_clauses: tuple[str, ...]
    provenance: tuple[Provenance, ...]
    personnel_normally_on_rig: str | None = None   # Schedule 4 wording, for personnel services


@dataclass(frozen=True)
class RateSubstitution:
    instrument_id: str
    code: str
    unit: str
    previous_rate_cents: int
    rate_cents: int
    effective: date


@dataclass(frozen=True)
class MonthlyRates:
    instrument_id: str
    code: str
    index_reference: str
    months: dict[str, int]      # "YYYY-MM" -> cents; later months carry the last published rate forward

    @property
    def first_month(self) -> str:
        return min(self.months)

    @property
    def last_month(self) -> str:
        return max(self.months)


@dataclass(frozen=True)
class RateDiscount:
    instrument_id: str
    percent: Decimal
    codes: tuple[str, ...]
    effective: date


@dataclass(frozen=True)
class TermExtension:
    instrument_id: str
    new_expiry: date
    extension_days: int


@dataclass(frozen=True)
class Instrument:
    id: str
    title: str
    reference: str
    issued: date
    effective: date
    page: int
    cited_clauses: tuple[str, ...]
    substitutions: tuple[RateSubstitution, ...]
    monthly_rates: tuple[MonthlyRates, ...]
    discounts: tuple[RateDiscount, ...]
    extensions: tuple[TermExtension, ...]
    added_services: tuple[str, ...]
    removed_services: tuple[str, ...]

    @property
    def retroactive(self) -> bool:
        """Takes effect before it was issued (Amendment No. 3; see Clause 36A)."""
        return self.effective < self.issued


@dataclass(frozen=True)
class RateStatement:
    """One statement of a rate for a service, as the contract makes it; not a decision about which one applies."""
    code: str
    kind: StatementKind
    source: str                 # "SCHEDULE_1" or an instrument id
    rate_cents: int
    effective: date
    issued: date | None         # None for the base contract
    month: str | None = None    # for monthly re-publications
    carried_forward: bool = False


@dataclass(frozen=True)
class DepthBand:
    band: int
    over_m: int
    to_m: int | None            # None: open-ended; a boundary depth belongs to the shallower band
    rate_cents: int


@dataclass(frozen=True)
class VolumeTier:
    band: int
    from_m: int
    to_m: int | None
    percent_of_rate: Decimal


@dataclass(frozen=True)
class PriceIndex:
    name: str
    base_index: Decimal
    base_rates_cents: dict[str, int]
    monthly: dict[str, Decimal]


@dataclass(frozen=True)
class LostInHoleTerms:
    services: tuple[str, ...]
    replacement_sar_halalas: dict[str, int]
    replacement_usd_cents_as_let: dict[str, int]
    fx_halalas_per_usd: dict[str, Decimal]
    depreciation_percent_per_block: Decimal
    depreciation_block_hours: int
    depreciation_cap_percent: Decimal


@dataclass(frozen=True)
class InvoiceDiscount:
    code: str
    threshold_cents: int
    comparison: str             # GREATER_THAN ("exceeds")
    percent: Decimal


@dataclass(frozen=True)
class FieldTermMapping:
    """One Appendix G row, exactly as printed."""
    row: int
    code: str
    schedule_1_description: str
    report_term: str


@dataclass(frozen=True)
class ContractYear:
    year: int
    start: date
    end: date
    status: FactStatus
    ambiguities: tuple[str, ...]


@dataclass(frozen=True)
class Reading:
    id: str
    reading: str
    evidence: tuple[Provenance, ...]


@dataclass(frozen=True)
class Ambiguity:
    id: str
    topic: str
    title: str
    issue: str
    readings: tuple[Reading, ...]
    preferred_reading: str | None
    confidence: str | None
    affects_totals: str
    services: tuple[str, ...]
    resolve_in_phase: str
    status: AmbiguityStatus
    pages: tuple[int, ...]


@dataclass(frozen=True)
class ContractTerms:
    contract_ref: str
    currency: str
    vat_percent: Decimal
    commencement: date
    original_expiry: date
    source_sha256: str
    documents: tuple[Document, ...]
    precedence: tuple[PrecedenceRule, ...]
    unranked_documents: tuple[str, ...]
    services: dict[str, ServiceDefinition]
    instruments: tuple[Instrument, ...]
    section_factors: dict[str, Decimal]
    class_factors: dict[str, Decimal]
    depth_bands: tuple[DepthBand, ...]
    volume_tiers: tuple[VolumeTier, ...]
    price_index: PriceIndex
    lost_in_hole: LostInHoleTerms
    invoice_discount: InvoiceDiscount
    appendix_g: tuple[FieldTermMapping, ...]
    contract_years: tuple[ContractYear, ...]
    evidence_not_provided: tuple[str, ...]
    ambiguity_refs: frozenset[str] = field(default_factory=frozenset)

    # ------------------------------------------------------------------ term
    @property
    def extensions(self) -> tuple[TermExtension, ...]:
        return tuple(e for i in self.instruments for e in i.extensions)

    @property
    def final_expiry(self) -> date:
        return max((e.new_expiry for e in self.extensions), default=self.original_expiry)

    def instrument(self, instrument_id: str) -> Instrument:
        return next(i for i in self.instruments if i.id == instrument_id)

    # ------------------------------------------------------------------ rates over time
    def rate_statements(self, code: str) -> tuple[RateStatement, ...]:
        """Every rate the contract states for `code`, base contract first, then instruments in the order issued."""
        service = self.services[code]
        out: list[RateStatement] = []
        if service.base_rate_cents is not None:
            out.append(RateStatement(code, StatementKind.SCHEDULE_1, "SCHEDULE_1", service.base_rate_cents, self.commencement, None))
        for ins in sorted(self.instruments, key=lambda i: i.issued):
            out += [RateStatement(code, StatementKind.SUBSTITUTION, ins.id, s.rate_cents, s.effective, ins.issued)
                    for s in ins.substitutions if s.code == code]
            for m in ins.monthly_rates:
                if m.code == code:
                    out += [RateStatement(code, StatementKind.MONTHLY, ins.id, cents, _month_start(month), ins.issued, month)
                            for month, cents in sorted(m.months.items())]
        return tuple(out)

    def rate_statements_on(self, code: str, service_date: date) -> tuple[RateStatement, ...]:
        """The statements that speak to a service performed on `service_date`, in the order issued.

        Includes the Schedule 1 rate and every substitution already effective, and the monthly rate for the
        month (or the last one published, marked carried_forward). Where more than one instrument speaks, this
        method does not choose: that is a pricing decision (AMB-07, AMB-08).
        """
        month = service_date.strftime("%Y-%m")
        out: list[RateStatement] = []
        for st in self.rate_statements(code):
            if st.kind is StatementKind.MONTHLY:
                continue
            if st.effective <= service_date:
                out.append(st)
        for ins in sorted(self.instruments, key=lambda i: i.issued):
            for m in ins.monthly_rates:
                if m.code != code or month < m.first_month:
                    continue
                if month in m.months:
                    out.append(RateStatement(code, StatementKind.MONTHLY, ins.id, m.months[month], _month_start(month), ins.issued, month))
                else:
                    last = m.last_month
                    out.append(RateStatement(code, StatementKind.MONTHLY, ins.id, m.months[last], _month_start(last), ins.issued, last, True))
        return tuple(out)

    def discounts_on(self, code: str, service_date: date) -> tuple[RateDiscount, ...]:
        """Principal-services discounts already effective for `code`, in the order issued (AMB-09 decides how they combine)."""
        return tuple(d for ins in sorted(self.instruments, key=lambda i: i.issued) for d in ins.discounts
                     if code in d.codes and d.effective <= service_date)

    def contract_year_of(self, service_date: date) -> ContractYear | None:
        return next((y for y in self.contract_years if y.start <= service_date <= y.end), None)

    # ------------------------------------------------------------------ Appendix G
    def codes_for_report_term(self, term: str) -> tuple[str, ...]:
        """Every code Appendix G pairs with a report term, as printed (a term may map to more than one code)."""
        return tuple(m.code for m in self.appendix_g if m.report_term == term)


def _month_start(month: str) -> date:
    year, mon = month.split("-")
    return date(int(year), int(mon), 1)


def day_before(d: date) -> date:
    return d - timedelta(days=1)
