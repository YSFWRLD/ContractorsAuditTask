"""Typed results of the interpretation layer."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum


class MappingStatus(StrEnum):
    IDENTIFIED = "IDENTIFIED"                                # one contract candidate, no open reading involved
    IDENTIFIED_BY_CONTEXT = "IDENTIFIED_BY_CONTEXT"          # several candidates; the contract text says which the context selects
    AMBIGUOUS = "AMBIGUOUS"                                  # several candidates and nothing selects one
    UNRESOLVED_INTERPRETATION = "UNRESOLVED_INTERPRETATION"  # the candidate depends on an open switch
    UNSUPPORTED = "UNSUPPORTED"                              # no contract candidate
    NOT_APPLICABLE = "NOT_APPLICABLE"                        # the field is not service evidence

    @property
    def deterministic(self) -> bool:
        return self in (MappingStatus.IDENTIFIED, MappingStatus.IDENTIFIED_BY_CONTEXT)


class Basis(StrEnum):
    PERSON_DAY = "PERSON_DAY"
    RENTAL_DAY = "RENTAL_DAY"
    HOUR = "HOUR"
    COUNT = "COUNT"
    METRE = "METRE"
    RUN = "RUN"
    WELL = "WELL"
    LOST_IN_HOLE = "LOST_IN_HOLE"
    STANDBY_DAY = "STANDBY_DAY"


class Scope(StrEnum):
    DAY = "DAY"
    RUN = "RUN"
    WELL = "WELL"


@dataclass(frozen=True)
class FieldRef:
    """One report field used as evidence, exactly as written."""
    report_id: str
    source_file: str
    section: str        # HEADER, A..E
    label: str
    raw_value: str
    line: int


@dataclass(frozen=True)
class Condition:
    """A contractual condition on a quantity, evaluated from report evidence; None when the data cannot tell."""
    code: str
    clause: str
    satisfied: bool | None
    note: str = ""


@dataclass(frozen=True)
class ServiceCandidate:
    service_code: str
    source_term: str
    report_id: str
    source_field: FieldRef
    status: MappingStatus
    ambiguity_ids: tuple[str, ...] = ()
    readings: tuple[tuple[str, str], ...] = ()  # (switch, reading) pairs this candidate belongs to
    note: str = ""


@dataclass(frozen=True)
class MappingResult:
    """How one report term maps, for one report."""
    term: str
    report_id: str
    source_field: FieldRef
    status: MappingStatus
    candidates: tuple[ServiceCandidate, ...]
    unresolved_reason: str = ""

    @property
    def deterministic(self) -> bool:
        return self.status.deterministic


@dataclass(frozen=True)
class Quantity:
    """An evidence-backed quantity for one service. Not a price, not a finding."""
    qid: str
    service_code: str
    quantity: Decimal
    unit: str                        # the contract unit of the service (Schedule 1)
    basis: Basis
    scope: Scope
    well: str
    date: date | None
    report_ids: tuple[str, ...]
    run: int | None
    derivation: str
    clauses: tuple[str, ...]
    evidence: tuple[FieldRef, ...]
    mapping_status: MappingStatus
    day_status: str | None
    hole_section: str | None
    conditions: tuple[Condition, ...] = ()
    readings: tuple[tuple[str, str], ...] = ()  # (switch, reading) pairs; the quantity exists only under all of them
    depends_on: tuple[str, ...] = ()            # later-phase switches that affect how it is used (not its value)
    ambiguity_ids: tuple[str, ...] = ()
    detail: tuple[tuple[str, str], ...] = ()

    @property
    def report_id(self) -> str | None:
        return self.report_ids[0] if len(self.report_ids) == 1 else None


@dataclass(frozen=True)
class InterpretationResult:
    mappings: tuple[MappingResult, ...]
    quantities: tuple[Quantity, ...]
    reports_interpreted: int
    evidence_facts: tuple[dict, ...] = field(default_factory=tuple)
