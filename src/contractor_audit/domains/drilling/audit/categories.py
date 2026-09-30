"""The controlled drilling error-category vocabulary: one value per kind of contractual failure.

Each category names the guideline check it belongs to, the contract provisions it rests on, and whether it
flags the invoice. The vocabulary is drilling's own: a category is reused from civil works only where the
contractual issue is the same kind of failure.

`entitlement_unverified` is the one category that never flags: the call-offs are not in the data (AMB-13), so a
charge whose price is consistent with an entitlement the contractor claims is neither proven wrong nor proven
payable. It is a standing query recorded on the invoice; it blocks a canonical corrected total. A billed rate that
matches a class other than the one the invoice describes is also only this query: the invoice's well class is a
descriptive field outside the contractual billing basis (cl. 34, Appendix B; the class is the call-off's, P2, P3).
"""

from dataclasses import dataclass
from enum import Enum

from contractor_audit.shared.findings import Check, ConfidenceBand


class Category(str, Enum):
    CONTRACT_REFERENCE_MISMATCH = "contract_reference_mismatch"
    INVOICE_WELL_MISMATCH = "invoice_well_mismatch"
    INVOICE_DETAILS_MISSING = "invoice_details_missing"
    WORK_OUTSIDE_CONTRACT_TERM = "work_outside_contract_term"
    INVOICE_TIMING = "invoice_timing"
    LINE_OUTSIDE_INVOICE_PERIOD = "line_outside_invoice_period"
    MISSING_RECORD = "missing_record"
    RECORD_LINE_MISMATCH = "record_line_mismatch"
    UNSIGNED_RECORD = "unsigned_record"
    RECORD_PART_MISSING = "record_part_missing"
    RECORD_NOT_COMPLIANT = "record_not_compliant"
    QUANTITY_EXCEEDS_RECORD = "quantity_exceeds_record"
    SERVICE_NOT_IN_CONTRACT = "service_not_in_contract"
    UNIT_MISMATCH = "unit_mismatch"
    DESCRIPTION_MISMATCH = "description_mismatch"
    LINE_DETAILS_MISSING = "line_details_missing"
    UNSUPPORTED_SERVICE = "unsupported_service"
    RATE_MISMATCH = "rate_mismatch"
    SUPERSEDED_RATE = "superseded_rate"
    DEPTH_BAND_MISAPPLIED = "depth_band_misapplied"
    DISCOUNT_MISAPPLIED = "discount_misapplied"
    STANDBY_RATE_MISAPPLIED = "standby_rate_misapplied"
    FACTOR_MISAPPLIED = "factor_misapplied"
    INDEX_MISAPPLIED = "index_misapplied"
    LOST_IN_HOLE_VALUATION = "lost_in_hole_valuation"
    BACKDATED_ADJUSTMENT_MISSING = "backdated_adjustment_missing"
    BACKDATED_ADJUSTMENT_INCORRECT = "backdated_adjustment_incorrect"
    NOT_CHARGEABLE_ON_STANDBY = "not_chargeable_on_standby"
    SECTION_NOT_ELIGIBLE = "section_not_eligible"
    DAILY_LIMIT_EXCEEDED = "daily_limit_exceeded"
    ONCE_ONLY_EXCEEDED = "once_only_exceeded"
    DUPLICATE_CHARGE = "duplicate_charge"
    LINE_ARITHMETIC = "line_arithmetic"
    INVOICE_ARITHMETIC = "invoice_arithmetic"
    VAT_ERROR = "vat_error"
    INVOICE_DISCOUNT_ERROR = "invoice_discount_error"
    ENTITLEMENT_UNVERIFIED = "entitlement_unverified"


@dataclass(frozen=True)
class CategoryInfo:
    check: Check
    meaning: str
    clauses: tuple[str, ...]
    flags: bool = True


_I = CategoryInfo
CATEGORY_INFO: dict[Category, CategoryInfo] = {
    Category.CONTRACT_REFERENCE_MISMATCH: _I(Check.CONTRACT_MATCH, "invoice quotes another contract reference, or another issuer", ("Form of Agreement",)),
    Category.INVOICE_WELL_MISMATCH: _I(Check.CONTRACT_MATCH, "invoice charges a well other than the one it is for (each well is invoiced separately)", ("32",)),
    Category.INVOICE_DETAILS_MISSING: _I(Check.CONTRACT_MATCH, "an invoice field needed to audit it is blank or malformed", ("32", "33", "36", "40")),
    Category.WORK_OUTSIDE_CONTRACT_TERM: _I(Check.CONTRACT_LIVE, "service dated outside the term as extended by every instrument; not chargeable", ("5", "A1 1.1", "A2 2.1")),
    Category.INVOICE_TIMING: _I(Check.INVOICE_WINDOW, "invoice dated before its period closed, or more than 30 days after it", ("33", "Form of Agreement")),
    Category.LINE_OUTSIDE_INVOICE_PERIOD: _I(Check.INVOICE_WINDOW, "charge for a day outside the period the invoice states", ("32",)),
    Category.MISSING_RECORD: _I(Check.RECORD_PRESENT, "no Daily Drilling Report is quoted, or the quoted report does not exist", ("15", "19A", "37")),
    Category.RECORD_LINE_MISMATCH: _I(Check.RECORD_PRESENT, "the quoted report is of another day or well than the charge", ("19", "19A")),
    Category.UNSIGNED_RECORD: _I(Check.RECORD_PRESENT, "the report lacks a signature the contract requires", ("15",)),
    Category.RECORD_PART_MISSING: _I(Check.RECORD_PRESENT, "the Schedule 5 part the charge needs is absent from the report", ("37", "Schedule 5")),
    Category.RECORD_NOT_COMPLIANT: _I(Check.RECORD_PRESENT, "the report does not take the form the contract requires (only under an unapproved alternative reading)", ("R5", "R6")),
    Category.QUANTITY_EXCEEDS_RECORD: _I(Check.RECORDED_QUANTITY, "billed above what the report supports; payable up to the record", ("21", "21A", "22", "23", "24", "25", "25A", "30")),
    Category.SERVICE_NOT_IN_CONTRACT: _I(Check.ITEM_IDENTIFIED, "service code with no Schedule 1 item", ("Form of Agreement", "34")),
    Category.UNIT_MISMATCH: _I(Check.ITEM_IDENTIFIED, "charge stated in a unit other than the Schedule 1 unit", ("35",)),
    Category.DESCRIPTION_MISMATCH: _I(Check.ITEM_IDENTIFIED, "description does not match the service code's Schedule 1 description", ("34",)),
    Category.LINE_DETAILS_MISSING: _I(Check.ITEM_IDENTIFIED, "a charge detail the contract requires (date, quantity, rate, amount, depths) is blank", ("34",)),
    Category.UNSUPPORTED_SERVICE: _I(Check.ITEM_IDENTIFIED, "the quoted report records no tool, person or event the charged item is for", ("19A", "22", "28", "Appendix G")),
    Category.RATE_MISMATCH: _I(Check.RATE_IN_FORCE, "billed rate is not the contract rate for the work date (no single cause identified)", ("17", "18", "Schedule 1")),
    Category.SUPERSEDED_RATE: _I(Check.RATE_IN_FORCE, "billed at a rate statement that is not the one in force on the work date", ("Schedule of Variations", "36A")),
    Category.DEPTH_BAND_MISAPPLIED: _I(Check.RATE_IN_FORCE, "PD-210 metres billed at another Schedule 2 depth band or tier", ("23", "Schedule 2")),
    Category.DISCOUNT_MISAPPLIED: _I(Check.ADJUSTMENTS, "S2/A2 principal-services discount omitted, applied early, or at the wrong percentage", ("S2 2.2", "A2 2.3")),
    Category.STANDBY_RATE_MISAPPLIED: _I(Check.ADJUSTMENTS, "Standby percentage not applied on a Standby day, or applied on an Operating day", ("18", "20", "Schedule 3 Part 3")),
    Category.FACTOR_MISAPPLIED: _I(Check.ADJUSTMENTS, "hole-section or well-class factor applied where it does not belong, or omitted", ("17B", "18", "Schedule 3 Parts 1-2")),
    Category.INDEX_MISAPPLIED: _I(Check.ADJUSTMENTS, "Rig Services Index omitted or taken for the wrong month", ("17A", "Schedule 2C")),
    Category.LOST_IN_HOLE_VALUATION: _I(Check.ADJUSTMENTS, "lost-in-hole value not the Schedule 2D value converted and depreciated", ("31", "31A", "P12", "Schedule 2D")),
    Category.BACKDATED_ADJUSTMENT_MISSING: _I(Check.ADJUSTMENTS, "the Clause 36A adjustment for a back-dated rate is not shown where the contract puts it", ("36A", "A3")),
    Category.BACKDATED_ADJUSTMENT_INCORRECT: _I(Check.ADJUSTMENTS, "an adjustment shown where, or in an amount, Clause 36A does not support", ("36A", "A3")),
    Category.NOT_CHARGEABLE_ON_STANDBY: _I(Check.LIMITS, "service charged on a Standby day although the contract excludes it on Standby", ("20", "21", "Schedule 3 Part 3")),
    Category.SECTION_NOT_ELIGIBLE: _I(Check.LIMITS, "PD-210 charged in a hole section Appendix A does not allow for performance drilling", ("23", "Appendix A")),
    Category.DAILY_LIMIT_EXCEEDED: _I(Check.LIMITS, "more than the Schedule 3 Part 5 daily limit", ("22", "Schedule 3 Part 5")),
    Category.ONCE_ONLY_EXCEEDED: _I(Check.LIMITS, "a once-per-well or once-per-run item charged again", ("26", "27")),
    Category.DUPLICATE_CHARGE: _I(Check.NOT_DUPLICATED, "the same service, well and day (the same report evidence) already charged on this or an earlier invoice", ("29",)),
    Category.LINE_ARITHMETIC: _I(Check.ARITHMETIC, "line amount is not quantity x rate rounded to the cent", ("17", "34")),
    Category.INVOICE_ARITHMETIC: _I(Check.ARITHMETIC, "net amount is not the sum of the charges, or the total is not net plus VAT", ("36", "40")),
    Category.VAT_ERROR: _I(Check.ARITHMETIC, "VAT is not 15 per cent of the net amount rounded to the cent", ("39",)),
    Category.INVOICE_DISCOUNT_ERROR: _I(Check.ARITHMETIC, "the Clause 38 volume discount (DS-900) omitted or miscalculated", ("38",)),
    Category.ENTITLEMENT_UNVERIFIED: _I(Check.ITEM_IDENTIFIED, "entitlement depends on a call-off the data does not contain (well class, nominated section); consistent with the contractor's claim, not proven", ("23", "Appendix A", "NP-01"), flags=False),
}

# The breach is certain but the contract prices nothing off it: never changes the total, confidence capped at MEDIUM.
NO_CONSEQUENCE_CATEGORIES = frozenset({Category.INVOICE_TIMING})
NO_CONSEQUENCE_CAP = ConfidenceBand.MEDIUM

# Fixed order used to break ties inside a primary tier: loss of the whole charge first, then evidence, quantity,
# price, adjustments, arithmetic, then identity and paperwork. Amounts never decide the order.
CATEGORY_PRECEDENCE: tuple[Category, ...] = (
    Category.WORK_OUTSIDE_CONTRACT_TERM,
    Category.DUPLICATE_CHARGE,
    Category.ONCE_ONLY_EXCEEDED,
    Category.UNSUPPORTED_SERVICE,
    Category.NOT_CHARGEABLE_ON_STANDBY,
    Category.SECTION_NOT_ELIGIBLE,
    Category.MISSING_RECORD,
    Category.RECORD_LINE_MISMATCH,
    Category.UNSIGNED_RECORD,
    Category.RECORD_PART_MISSING,
    Category.RECORD_NOT_COMPLIANT,
    Category.SERVICE_NOT_IN_CONTRACT,
    Category.UNIT_MISMATCH,
    Category.LINE_OUTSIDE_INVOICE_PERIOD,
    Category.QUANTITY_EXCEEDS_RECORD,
    Category.DAILY_LIMIT_EXCEEDED,
    Category.SUPERSEDED_RATE,
    Category.DEPTH_BAND_MISAPPLIED,
    Category.DISCOUNT_MISAPPLIED,
    Category.STANDBY_RATE_MISAPPLIED,
    Category.FACTOR_MISAPPLIED,
    Category.INDEX_MISAPPLIED,
    Category.LOST_IN_HOLE_VALUATION,
    Category.RATE_MISMATCH,
    Category.LINE_ARITHMETIC,
    Category.INVOICE_DISCOUNT_ERROR,
    Category.VAT_ERROR,
    Category.INVOICE_ARITHMETIC,
    Category.BACKDATED_ADJUSTMENT_MISSING,
    Category.BACKDATED_ADJUSTMENT_INCORRECT,
    Category.DESCRIPTION_MISMATCH,
    Category.LINE_DETAILS_MISSING,
    Category.INVOICE_DETAILS_MISSING,
    Category.INVOICE_WELL_MISMATCH,
    Category.CONTRACT_REFERENCE_MISMATCH,
    Category.INVOICE_TIMING,
    Category.ENTITLEMENT_UNVERIFIED,
)
_PRECEDENCE = {c.value: i for i, c in enumerate(CATEGORY_PRECEDENCE)}

PRIMARY_TIERS = {
    1: "contractual violation with HIGH confidence that changes the invoice total",
    2: "any other finding that changes the invoice total",
    3: "a finding that makes the total impossible to reconstruct",
    4: "identity, structure or record finding without a determinable monetary effect",
    5: "timing only",
    6: "entitlement query (does not flag)",
}


def info(category: str) -> CategoryInfo:
    return CATEGORY_INFO[Category(category)]


def flags(category: str) -> bool:
    return info(category).flags


def primary_tier(finding) -> int:
    """Tier of PRIMARY_TIERS. Monetary size never decides the tier."""
    if not flags(finding.category):
        return 6
    if Category(finding.category) in NO_CONSEQUENCE_CATEGORIES:
        return 5
    if finding.affects_total:
        return 1 if finding.confidence is ConfidenceBand.HIGH else 2
    if finding.blocks_total:
        return 3
    return 4


def primary_key(finding) -> tuple:
    """Sort key: the lowest is the invoice's primary finding. Deterministic; no amounts involved."""
    return (primary_tier(finding), _PRECEDENCE[finding.category], finding.line_ref or "", finding.rule)
