"""The controlled civil works error-category vocabulary (one value per kind of error).

`error_category` in the submission uses these strings. Which category an application's row shows is
decided by `primary_tier` and then CATEGORY_PRECEDENCE (see `primary_key`); every finding is kept.
"""

from dataclasses import dataclass
from enum import Enum

from contractor_audit.shared.findings import Check


class Category(str, Enum):
    CONTRACT_REFERENCE_MISMATCH = "contract_reference_mismatch"
    WORK_OUTSIDE_CONTRACT_PERIOD = "work_outside_contract_period"
    WORK_AFTER_FINAL_COMPLETION = "work_after_final_completion"
    APPLICATION_TIMING = "application_timing"
    APPLICATION_PERIOD_MISSTATED = "application_period_misstated"
    LINE_OUTSIDE_APPLICATION_PERIOD = "line_outside_application_period"
    MISSING_RECORD = "missing_record"
    UNSIGNED_RECORD = "unsigned_record"
    RECORD_LINE_MISMATCH = "record_line_mismatch"
    ITEM_RECORD_MISMATCH = "item_record_mismatch"
    UNIT_MISMATCH = "unit_mismatch"
    ITEM_NOT_IN_CONTRACT = "item_not_in_contract"
    QUANTITY_EXCEEDS_RECORD = "quantity_exceeds_record"
    DUPLICATE_RECORD = "duplicate_record"
    DUPLICATE_LINE = "duplicate_line"
    DAILY_LIMIT_EXCEEDED = "daily_limit_exceeded"
    EXCLUSION_WINDOW_VIOLATION = "exclusion_window_violation"
    UNIT_RATE_MISMATCH = "unit_rate_mismatch"
    REBATE_INCORRECTLY_APPLIED = "rebate_incorrectly_applied"
    DISCOUNT_INCORRECTLY_APPLIED = "discount_incorrectly_applied"
    LINE_TOTAL_ARITHMETIC = "line_total_arithmetic"
    APPLICATION_TOTAL_MISMATCH = "application_total_mismatch"
    ADJUSTMENT_MISSING = "adjustment_missing"
    ADJUSTMENT_INCORRECTLY_APPLIED = "adjustment_incorrectly_applied"
    RETENTION_INCORRECT = "retention_incorrect"


@dataclass(frozen=True)
class CategoryInfo:
    check: Check
    meaning: str
    clauses: tuple[str, ...]


CATEGORY_INFO: dict[Category, CategoryInfo] = {
    Category.CONTRACT_REFERENCE_MISMATCH: CategoryInfo(Check.CONTRACT_MATCH, "application quotes another contract reference or issuer", ("Agreement p.1",)),
    Category.WORK_OUTSIDE_CONTRACT_PERIOD: CategoryInfo(Check.CONTRACT_LIVE, "work dated before the Commencement Date", ("Agreement p.1",)),
    Category.WORK_AFTER_FINAL_COMPLETION: CategoryInfo(Check.CONTRACT_LIVE, "work dated after the Date for Completion as extended; not measurable or payable", ("A2 2.1 p.42",)),
    Category.APPLICATION_TIMING: CategoryInfo(Check.INVOICE_WINDOW, "submitted before its period closed, or more than 21 days after it", ("41",)),
    Category.APPLICATION_PERIOD_MISSTATED: CategoryInfo(Check.INVOICE_WINDOW, "stated period is not the first and last day of the work it includes", ("40",)),
    Category.LINE_OUTSIDE_APPLICATION_PERIOD: CategoryInfo(Check.INVOICE_WINDOW, "line executed outside the application's stated period; may not be included", ("41",)),
    Category.MISSING_RECORD: CategoryInfo(Check.RECORD_PRESENT, "Schedule 5 item without its record (no reference, or the referenced record does not exist)", ("46", "Sch 5", "P23")),
    Category.UNSIGNED_RECORD: CategoryInfo(Check.RECORD_PRESENT, "record lacks the foreman signature or the Engineer's representative countersignature", ("47", "P22")),
    Category.RECORD_LINE_MISMATCH: CategoryInfo(Check.RECORD_PRESENT, "record's work area or date does not match the line it is quoted against", ("47", "47A")),
    Category.ITEM_RECORD_MISMATCH: CategoryInfo(Check.ITEM_IDENTIFIED, "record is of the wrong series, or describes a different item", ("47A", "Sch 5")),
    Category.ITEM_NOT_IN_CONTRACT: CategoryInfo(Check.ITEM_IDENTIFIED, "item code with no Schedule 1 rate; valued only at daywork or an agreed rate, neither of which is in the data", ("P24", "26")),
    Category.UNIT_MISMATCH: CategoryInfo(Check.ITEM_IDENTIFIED, "quantity presented in a unit other than the Schedule 1 unit; rejected in its entirety", ("26",)),
    Category.QUANTITY_EXCEEDS_RECORD: CategoryInfo(Check.RECORDED_QUANTITY, "billed more than the record supports (incl. chargeable hours, survey tolerance, five-day week)", ("47", "6A", "33A", "47A")),
    Category.DUPLICATE_RECORD: CategoryInfo(Check.NOT_DUPLICATED, "a record's quantity already billed on an earlier line or application", ("44", "47A")),
    Category.DUPLICATE_LINE: CategoryInfo(Check.NOT_DUPLICATED, "same item, work area and date measured more than once; later measurement disallowed", ("44",)),
    Category.DAILY_LIMIT_EXCEEDED: CategoryInfo(Check.LIMITS, "more than the Schedule 4 Part 4 daily quantity per work area", ("31", "Sch 4 Part 4", "19", "P6")),
    Category.EXCLUSION_WINDOW_VIOLATION: CategoryInfo(Check.LIMITS, "item measured inside the window excluded by another item's measurement", ("32", "Sch 4 Part 5", "P19", "P21")),
    Category.UNIT_RATE_MISMATCH: CategoryInfo(Check.RATE_IN_FORCE, "billed rate differs from the contract rate for the work date", ("27", "28")),
    Category.REBATE_INCORRECTLY_APPLIED: CategoryInfo(Check.ADJUSTMENTS, "rebate band applied wrongly or omitted", ("Sch 4 Part 3", "28")),
    Category.DISCOUNT_INCORRECTLY_APPLIED: CategoryInfo(Check.ADJUSTMENTS, "S2/A2 discount applied wrongly, early, late or omitted", ("S2 2.2", "A2 2.3")),
    Category.LINE_TOTAL_ARITHMETIC: CategoryInfo(Check.ARITHMETIC, "line amount does not equal quantity x rate (or its band parts)", ("28",)),
    Category.APPLICATION_TOTAL_MISMATCH: CategoryInfo(Check.ARITHMETIC, "header total (or net payable) does not reconcile with its lines", ("43", "45A")),
    Category.ADJUSTMENT_MISSING: CategoryInfo(Check.ADJUSTMENTS, "an adjustment or release the contract requires on this application is not shown", ("31A", "45A")),
    Category.ADJUSTMENT_INCORRECTLY_APPLIED: CategoryInfo(Check.ADJUSTMENTS, "an adjustment or release shown where, or in an amount, the contract does not support", ("31A", "45A")),
    Category.RETENTION_INCORRECT: CategoryInfo(Check.ADJUSTMENTS, "retention is not 5% of the application total rounded down", ("45",)),
}

CATEGORIES: tuple[Category, ...] = tuple(Category)


# Findings the contract attaches no consequence to: the breach is certain, but the contract prices
# nothing off it and does not say the application is rejected for it. Their confidence is capped at
# MEDIUM because whether such a breach makes the invoice "wrong" is itself not settled by the text.
NO_CONSEQUENCE_CATEGORIES = frozenset({Category.APPLICATION_TIMING, Category.APPLICATION_PERIOD_MISSTATED})

# Fixed order used to break ties inside a primary tier. Loss of the whole entitlement first, then
# evidence, then quantity, then price, then arithmetic, then sums outside the total, then paperwork.
CATEGORY_PRECEDENCE: tuple[Category, ...] = (
    Category.WORK_AFTER_FINAL_COMPLETION,
    Category.WORK_OUTSIDE_CONTRACT_PERIOD,
    Category.DUPLICATE_LINE,
    Category.DUPLICATE_RECORD,
    Category.MISSING_RECORD,
    Category.ITEM_RECORD_MISMATCH,
    Category.RECORD_LINE_MISMATCH,
    Category.UNSIGNED_RECORD,
    Category.ITEM_NOT_IN_CONTRACT,
    Category.UNIT_MISMATCH,
    Category.LINE_OUTSIDE_APPLICATION_PERIOD,
    Category.QUANTITY_EXCEEDS_RECORD,
    Category.DAILY_LIMIT_EXCEEDED,
    Category.EXCLUSION_WINDOW_VIOLATION,
    Category.UNIT_RATE_MISMATCH,
    Category.REBATE_INCORRECTLY_APPLIED,
    Category.DISCOUNT_INCORRECTLY_APPLIED,
    Category.LINE_TOTAL_ARITHMETIC,
    Category.APPLICATION_TOTAL_MISMATCH,
    Category.ADJUSTMENT_MISSING,
    Category.ADJUSTMENT_INCORRECTLY_APPLIED,
    Category.RETENTION_INCORRECT,
    Category.CONTRACT_REFERENCE_MISMATCH,
    Category.APPLICATION_PERIOD_MISSTATED,
    Category.APPLICATION_TIMING,
)
_PRECEDENCE = {c.value: i for i, c in enumerate(CATEGORY_PRECEDENCE)}
STRUCTURAL_CATEGORIES = frozenset({Category.CONTRACT_REFERENCE_MISMATCH, Category.ITEM_NOT_IN_CONTRACT})

PRIMARY_TIERS = {
    1: "explicit contractual violation, HIGH confidence, that changes the application total",
    2: "any other finding that changes the application total",
    3: "determinable sum settled outside the total (adjustment, release, retention)",
    4: "structural / data-integrity issue without a monetary effect",
    5: "timing or documentation only",
}


def primary_tier(finding) -> int:
    """Tier 1-5 of PRIMARY_TIERS. Monetary size never decides the tier."""
    from contractor_audit.shared.findings import ConfidenceBand
    if finding.category in {c.value for c in NO_CONSEQUENCE_CATEGORIES}:
        return 5
    if finding.affects_total:
        return 1 if finding.confidence is ConfidenceBand.HIGH else 2
    if finding.outside_total and finding.impact_cents:
        return 3
    return 4


def primary_key(finding) -> tuple:
    """Sort key: lowest is the application's primary finding. Deterministic; no amounts involved."""
    return (primary_tier(finding), _PRECEDENCE[finding.category], finding.line_ref or "", finding.rule)
