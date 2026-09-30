"""Civil works audit models. The finding itself is the shared canonical `Finding`."""

from dataclasses import dataclass, field
from decimal import Decimal

from contractor_audit.domains.civil_works.pricing import LinePrice
from contractor_audit.shared.findings import ConfidenceBand, Dependency, Finding


@dataclass(frozen=True)
class RuleOutput:
    """A finding, and the ceiling it puts on the line's payable quantity (if any).

    `cap_measurable` records the contract's own wording: True where the quantity above the cap is
    still 'measured' but 'not payable' (Clause 46); False where the contract makes it 'not
    measurable' / disallowed / rejected. It matters only for rebate-band progression.
    """
    finding: Finding
    cap: Decimal | None = None
    cap_measurable: bool = False


@dataclass(frozen=True)
class Unresolved:
    application_no: str
    line_ref: str | None
    reason: str          # BlankReason value
    detail: str


@dataclass(frozen=True)
class LineValuation:
    line_ref: str
    application_no: str
    billed_quantity: Decimal
    payable_quantity: Decimal
    progression_quantity: Decimal
    billed_cents: int
    contract_billed: LinePrice | None      # contract price of the billed quantity
    contract_payable: LinePrice | None     # contract price of the payable quantity
    binding_rules: tuple[str, ...]         # rules whose cap decided the payable quantity
    payable_cents: int | None = None       # contract amount of the payable quantity (0 when nothing is payable, even without a rate)


@dataclass(frozen=True)
class AuditRun:
    """One audit pass under one set of readings (no confidence yet)."""
    label: dict
    findings: tuple[Finding, ...]
    lines: dict[str, LineValuation]
    contract_totals: dict[str, int | None]     # working reconstruction of each application total
    unresolved: tuple[Unresolved, ...]
    outside_total: dict[str, tuple]            # application_no -> ((kind, amount_cents, clause, note), ...)


@dataclass(frozen=True)
class ApplicationAssessment:
    application_no: str
    billed_total_cents: int
    flagged: bool
    categories: tuple[str, ...]
    primary_category: str
    expected_total_cents: int | None           # under the total policy; None = blank
    contract_total_cents: int | None           # working reconstruction, before the blank policy
    graded_total_cents: int | None             # what the GRADED policy would publish
    blank_reasons: tuple[str, ...]
    confidence: ConfidenceBand
    findings: tuple[Finding, ...]
    total_dependencies: tuple[Dependency, ...]
    would_flag_under: tuple[Dependency, ...]   # alternative readings under which an unflagged application is flagged
    outside_total: tuple = field(default=())
    primary_blank_reason: str = ""             # single, mutually exclusive reason (see assessment.blank_reason_key)
    outcome: str = "pass"                      # guideline check 12: pass | query | part-reject
    total_status: str = "correct"              # correct | unchanged | corrected | undetermined (is application_total itself wrong?)

    @property
    def confidence_score(self) -> float:
        return self.confidence.score
