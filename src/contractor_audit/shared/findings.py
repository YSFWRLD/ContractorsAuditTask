"""Audit result representation shared by every contract domain.

The twelve checks and the pass / query / part-reject outcomes come from
INVOICE_AUDIT_GUIDELINES.md, which is identical for both contracts apart from
its title. `Finding` is the one canonical finding record; each domain supplies its
own category vocabulary (as strings) and its own rules. InvoiceResult mirrors one
row of submission_template.csv.
"""

from dataclasses import dataclass, field
from enum import Enum, IntEnum


class Check(IntEnum):
    CONTRACT_MATCH = 1
    CONTRACT_LIVE = 2
    INVOICE_WINDOW = 3
    RECORD_PRESENT = 4
    RECORDED_QUANTITY = 5
    ITEM_IDENTIFIED = 6
    RATE_IN_FORCE = 7
    ADJUSTMENTS = 8
    LIMITS = 9
    NOT_DUPLICATED = 10
    ARITHMETIC = 11
    OUTCOME_RECORDED = 12


class Outcome(str, Enum):
    PASS = "pass"
    QUERY = "query"
    PART_REJECT = "part-reject"


class ConfidenceBand(str, Enum):
    """Evidence quality, not a statistical probability.

    HIGH: a direct, deterministic contract/data violation (or, for an unflagged invoice, no
    reading of the contract would flag it). MEDIUM: depends on a defensible but unresolved
    reading. LOW: depends on one of the least certain readings. `score` is the fixed number
    written to the submission for each band.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def score(self) -> float:
        return {ConfidenceBand.HIGH: 0.95, ConfidenceBand.MEDIUM: 0.75, ConfidenceBand.LOW: 0.55}[self]

    @property
    def rank(self) -> int:
        return {ConfidenceBand.LOW: 0, ConfidenceBand.MEDIUM: 1, ConfidenceBand.HIGH: 2}[self]

    @staticmethod
    def weakest(bands) -> "ConfidenceBand":
        bands = list(bands)
        return min(bands, key=lambda b: b.rank) if bands else ConfidenceBand.HIGH

    @staticmethod
    def strongest(bands) -> "ConfidenceBand":
        bands = list(bands)
        return max(bands, key=lambda b: b.rank) if bands else ConfidenceBand.HIGH


@dataclass(frozen=True)
class Citation:
    """A contract provision relied on, as recorded in the domain's reviewed extraction."""

    reference: str          # e.g. "Clause 46", "Sch 4 Part 4"
    page: int | None
    text: str


@dataclass(frozen=True)
class Evidence:
    """One step of the path from billed line to finding (a billed value, a record, a pricing step)."""

    kind: str               # e.g. "billed_line", "site_record", "pricing_trace", "application"
    reference: str          # line ref, record id, trace rule ...
    detail: str
    source: str | None = None           # clause/page for contract-derived steps
    result: str | None = None
    interpretation: str | None = None   # "switch=value" when a reading decided the step


@dataclass(frozen=True)
class Dependency:
    """A reading the finding (or an expected total) relies on: under `alternative` it changes."""

    switch: str
    working: str
    alternative: str
    effect: str             # "finding_absent" | "value_changes" | "total_changes" | "would_flag"
    band: ConfidenceBand


@dataclass(frozen=True)
class Finding:
    """One check's outcome on an invoice, or on one of its lines."""

    check: Check
    outcome: Outcome
    message: str
    clause: str | None = None
    line_ref: str | None = None
    evidence: tuple[Evidence, ...] = ()
    invoice_id: str = ""
    category: str = ""
    rule: str = ""                      # stable rule identifier, e.g. "records.missing_reference"
    observed: str | None = None
    expected: str | None = None
    impact_cents: int | None = None     # billed minus contract for this component; None if not determinable
    citations: tuple[Citation, ...] = ()
    affects_total: bool = False         # changes the corrected invoice total
    outside_total: bool = False         # a sum the contract settles outside the invoice total
    blocks_total: bool = False          # makes the corrected total non-reconstructable
    dependencies: tuple[Dependency, ...] = ()
    confidence: ConfidenceBand = ConfidenceBand.HIGH

    @property
    def key(self) -> tuple[str, str, str, str]:
        """Identity used to compare findings across interpretation runs (amounts excluded)."""
        return (self.invoice_id, self.line_ref or "", self.category, self.rule)


@dataclass(frozen=True)
class InvoiceResult:
    """The audit verdict for one invoice; one submission row."""

    invoice_id: str
    flagged: bool
    billed_total_cents: int
    expected_total_cents: int | None
    confidence: float
    error_category: str = ""
    findings: tuple[Finding, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.invoice_id:
            raise ValueError("invoice_id is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"{self.invoice_id}: confidence {self.confidence} outside [0, 1]")
        for name in ("billed_total_cents", "expected_total_cents"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                raise TypeError(f"{self.invoice_id}: {name} must be integer minor units")
        if not self.flagged and self.error_category:
            raise ValueError(f"{self.invoice_id}: error_category must be blank when not flagged")
        if self.flagged and not self.error_category:
            raise ValueError(f"{self.invoice_id}: a flagged invoice needs an error_category")
