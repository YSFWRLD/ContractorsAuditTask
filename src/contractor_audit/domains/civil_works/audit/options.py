"""Audit-level readings of the contract, alongside the Phase 2 pricing switches.

These questions only arise once quantities can be disallowed, so they live here rather than in
`interpretation.py`. The working value of each is chosen from the contract text; billed data is
never used to choose it.
"""

from dataclasses import dataclass, fields, replace
from enum import Enum

from contractor_audit.domains.civil_works.interpretation import SwitchInfo, SwitchStatus


class RebateProgression(str, Enum):
    MEASURABLE_ONLY = "measurable_only"   # quantities the contract says are 'not measurable' do not count; 'not payable' ones do
    ALL_BILLED = "all_billed"             # every billed quantity counts (what Phase 2 valued)
    PAYABLE_ONLY = "payable_only"         # only the payable quantity counts


class MissingRecordConsequence(str, Enum):
    NOT_PAYABLE_IN_THIS_APPLICATION = "not_payable_in_this_application"   # Clause 46 / 13
    DEDUCT_FROM_NEXT_VALUATION = "deduct_from_next_valuation"             # Clause P23


class UnsignedRecord(str, Enum):
    NOT_A_VALID_RECORD = "not_a_valid_record"          # Clause 47 / P22: both signatures are part of the required form
    ACCEPTED_WITH_DEFECT = "accepted_with_defect"


class MeasurementOrder(str, Enum):
    SUBMISSION_DATE = "submission_date"          # the later-submitted application holds the 'later measurement'
    APPLICATION_NUMBER = "application_number"


class TotalPolicy(str, Enum):
    STRICT = "strict"      # blank the corrected total if any unresolved reading changes it
    GRADED = "graded"      # blank only if a LOW-grade reading changes it


@dataclass(frozen=True)
class AuditInterpretation:
    rebate_progression: RebateProgression = RebateProgression.MEASURABLE_ONLY
    missing_record_consequence: MissingRecordConsequence = MissingRecordConsequence.NOT_PAYABLE_IN_THIS_APPLICATION
    unsigned_record: UnsignedRecord = UnsignedRecord.NOT_A_VALID_RECORD
    measurement_order: MeasurementOrder = MeasurementOrder.SUBMISSION_DATE

    def with_(self, **changes) -> "AuditInterpretation":
        return replace(self, **changes)

    def label(self) -> dict[str, str]:
        return {f.name: getattr(self, f.name).value for f in fields(self)}


WORKING_AUDIT_INTERPRETATION = AuditInterpretation()

AUDIT_SWITCHES: tuple[SwitchInfo, ...] = (
    SwitchInfo("rebate_progression", None, ("Sch 4 Part 3", "31", "32", "44", "46", "A2 2.1", "26"), (24, 6, 8, 42, 7), SwitchStatus.UNRESOLVED,
               "Which quantities advance the Schedule 4 Part 3 band counter once some billed quantity is disallowed?",
               {"measurable_only": "Sch 4 Part 3 counts 'the quantity measured'. The contract separates 'not measurable' (31 excess, 32, 44, 26, 41, A2 2.1, "
                                   "quantities above the record, 6A, 33A) from 'not payable' (46 missing record); only measurable quantity counts.",
                "all_billed": "Every billed quantity counts, as the Phase 2 valuation of billed quantities did.",
                "payable_only": "Only the quantity actually payable counts."},
               "The band text counts 'the quantity measured', and the contract uses 'measurable' and 'payable' as distinct words; a quantity it declares not "
               "measurable is not 'quantity measured', while a measured quantity awaiting its record still is."),
    SwitchInfo("missing_record_consequence", "AMB-MISSING-RECORD", ("13", "46", "P23", "P1"), (4, 8, 14, 12), SwitchStatus.UNRESOLVED,
               "When a Schedule 5 record is missing (or invalid), is the line not payable in this application, or deducted from the next valuation?",
               {"not_payable_in_this_application": "46: 'not payable in any valuation until that record has been delivered'; 13 likewise for certificates.",
                "deduct_from_next_valuation": "P23 (Part V, which prevails over Parts I-III): 'the amount shall be deducted from the next valuation'."},
               "P23 speaks of an item that 'has been included in a valuation', i.e. after valuation; the audit is the valuation of this application, "
               "which Clause 46 governs. Retained as unresolved because P23 prevails in any genuine conflict."),
    SwitchInfo("unsigned_record", "AMB-MISSING-RECORD", ("47", "P22", "46"), (8, 14), SwitchStatus.UNRESOLVED,
               "Does a record without the Engineer's countersignature count as the required record?",
               {"not_a_valid_record": "47: a Schedule 5 record 'shall be signed ... and countersigned'; P22 accepts a record only if it 'bears both signatures'.",
                "accepted_with_defect": "The record exists; the missing countersignature is a defect but the work is evidenced."},
               "Clause 47 makes both signatures part of what a Schedule 5 record is."),
    SwitchInfo("measurement_order", None, ("44", "guideline 10"), (8,), SwitchStatus.UNRESOLVED,
               "When the same work is billed twice, which is the 'later measurement' that is disallowed?",
               {"submission_date": "The application submitted later (guideline 10: 'billed twice ... against an earlier one').",
                "application_number": "The application with the higher number."},
               "44 disallows 'the later measurement'; a measurement is made when it is submitted for valuation."),
)
AUDIT_SWITCHES_BY_FIELD = {s.field: s for s in AUDIT_SWITCHES}
