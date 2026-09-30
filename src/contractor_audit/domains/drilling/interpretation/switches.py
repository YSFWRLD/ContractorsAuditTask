"""Every open contract reading as a named interpretation switch.

A switch names its Phase 1 ambiguity and maps each of its readings to a reading in the ambiguity register.
Its default is the register's preferred reading, when there is one; otherwise it has none. Nothing here
chooses a reading: Phase 3 derives quantities under *every* reading of the switches it uses, and later
phases take the readings the user approves.
"""

from dataclasses import dataclass
from enum import StrEnum

from contractor_audit.domains.drilling.contract.models import Ambiguity, AmbiguityStatus


class AppliesIn(StrEnum):
    PHASE_3_QUANTITIES = "PHASE_3_QUANTITIES"   # changes which evidence becomes a quantity (evaluated now)
    PHASE_4_PRICING = "PHASE_4_PRICING"         # defined now, used later in the pricing phase
    PHASE_5_AUDIT = "PHASE_5_AUDIT"             # defined now, used later when invoices are compared


@dataclass(frozen=True)
class SwitchReading:
    value: str
    ambiguity_reading: str      # reading id in contract_ambiguities.json
    description: str            # the register's own wording


@dataclass(frozen=True)
class Switch:
    name: str
    ambiguity_id: str
    applies_in: AppliesIn
    readings: tuple[SwitchReading, ...]
    default: str | None
    default_basis: str
    requires_approval: bool
    explanation: str

    def reading(self, value: str) -> SwitchReading:
        return next(r for r in self.readings if r.value == value)

    @property
    def values(self) -> tuple[str, ...]:
        return tuple(r.value for r in self.readings)


# name, ambiguity, applies in, {switch value: ambiguity reading}, explanation
_DEFINITIONS = (
    ("appendix_g_reading", "AMB-17", AppliesIn.PHASE_3_QUANTITIES, {"LITERAL": "A", "LWD_ROWS_SHIFTED": "B"},
     "Which LWD service a logging-tool word evidences. The shifted reading moves the three LWD 'logged' rows (and LH-714, which follows LW-410) up one row; the other surprising pairings have no alternative in the contract and stay literal."),
    ("appendix_g_duplicates", "AMB-16", AppliesIn.PHASE_3_QUANTITIES, {"CONTEXT_SELECTS": "A", "UNRESOLVED": "B"},
     "A term listed for a rental and a lost-in-hole code: the Appendix G footnote says Part E context selects the lost-in-hole row."),
    ("dd102_basis", "AMB-18", AppliesIn.PHASE_3_QUANTITIES, {"PER_COORDINATOR_RECORDED": "A", "PER_DAY_TOOL_IN_HOLE": "B"},
     "What evidences DD-102: the coordinator the report records (Appendix G 'night man'), or any day a tool is in the hole."),
    ("hc630_basis", "AMB-19", AppliesIn.PHASE_3_QUANTITIES, {"DAILY_COUNT": "A", "PER_BHA_RUN": "B"},
     "HC-630 from the daily clean-out-run count (cl. 30) or once per BHA run (Schedule 8)."),
    ("dd121_condition", "AMB-20", AppliesIn.PHASE_3_QUANTITIES, {"STANDBY_DAY_RSS_IN_HOLE": "A", "EVERY_STANDBY_DAY_OF_RSS_WELL": "B"},
     "Which Standby days evidence DD-121."),
    ("dd120_hours", "AMB-06", AppliesIn.PHASE_3_QUANTITIES, {"CIRCULATING_ONLY": "A", "CIRCULATING_PLUS_BACK_REAMING": "B"},
     "Which recorded hours evidence DD-120."),
    ("metre_source", "AMB-24", AppliesIn.PHASE_3_QUANTITIES, {"DAILY_DEPTH_ADVANCE": "A", "PART_B_RUN_METRES": "B"},
     "LW-410/411/412 and RM-510 metres from the day's depth advance, or once per run from Part B metres logged/reamed."),
    ("lih_hours", "AMB-22", AppliesIn.PHASE_3_QUANTITIES, {"PART_E_STATED": "A", "TOOL_ACCUMULATED": "B"},
     "Depreciation hours for a lost tool: the Part E figure or the tool's own daily hours on the well. Both values are carried; depreciation itself is Phase 4."),
    ("report_vocabulary", "AMB-15", AppliesIn.PHASE_5_AUDIT, {"RIG_WORDS_VALID": "A", "CODES_REQUIRED": "B"},
     "Whether a report written in rig words (not service codes) is compliant. Phase 3 reads the rig words either way."),
    ("rig_up_hour", "AMB-05", AppliesIn.PHASE_4_PRICING, {"PER_DAY_THEN_MINIMUM": "A", "PER_BHA_RUN": "B", "NO_DEDUCTION": "C", "MINIMUM_THEN_PER_DAY": "D"},
     "21A rig-up hour and the 6-hour minimum on DD-120 and RM-530. Used later in the pricing phase; Phase 3 carries recorded hours."),
    ("pd210_class_factor", "AMB-02", AppliesIn.PHASE_4_PRICING, {"APPLY": "A", "DO_NOT_APPLY": "B"}, "Used later in the pricing phase."),
    ("standby_section_factor", "AMB-03", AppliesIn.PHASE_4_PRICING, {"APPLY": "A", "OMIT": "B"}, "Used later in the pricing phase."),
    ("rig_services_index", "AMB-04", AppliesIn.PHASE_4_PRICING, {"APPLY_FROM_FIRST_MONTH": "A", "NOT_APPLIED": "B"}, "Used later in the pricing phase."),
    ("dd120_rate_from_feb_2026", "AMB-07", AppliesIn.PHASE_4_PRICING, {"LATER_ISSUED_GOVERNS": "A", "LATER_EFFECTIVE_GOVERNS": "B", "MONTHLY_TABLE_SEPARATE": "C"}, "Used later in the pricing phase."),
    ("monthly_rate_basis", "AMB-08", AppliesIn.PHASE_4_PRICING, {"BASE_RATE_THEN_BUILD_UP": "A", "FINAL_RATE": "B"}, "Used later in the pricing phase."),
    ("principal_discount_combination", "AMB-09", AppliesIn.PHASE_4_PRICING, {"LATER_REPLACES": "A", "CUMULATIVE": "B"}, "Used later in the pricing phase."),
    ("volume_tier_scope", "AMB-10", AppliesIn.PHASE_4_PRICING, {"PER_WELL": "A", "CONTRACT_WIDE": "B"}, "Used later in the pricing phase."),
    ("contract_year_2", "AMB-11", AppliesIn.PHASE_4_PRICING, {"STARTS_2026_01_01": "A", "YEAR_1_EXTENDED": "B"}, "Used later in the pricing phase."),
    ("lih_replacement_value", "AMB-21", AppliesIn.PHASE_4_PRICING, {"SCHEDULE_2D_CONVERTED": "A", "SCHEDULE_6_USD": "B"}, "Used later in the pricing phase."),
    ("ds900_threshold_basis", "AMB-26", AppliesIn.PHASE_4_PRICING, {"SERVICES_ONLY": "A", "ALL_CHARGES": "B"}, "Used later in the pricing phase."),
    ("unranked_precedence", "AMB-01", AppliesIn.PHASE_4_PRICING, {"NO_RANK_CASE_BY_CASE": "A", "RANK_BY_NAME": "B", "CLAUSE_2_EXHAUSTIVE": "C"},
     "Meta-switch: how conflicts involving unlisted documents are settled. Used later in the pricing phase."),
    ("backdated_adjustment", "AMB-12", AppliesIn.PHASE_5_AUDIT, {"CONTRACT_WIDE_ON_OR_AFTER": "A", "CONTRACT_WIDE_AFTER": "B", "PER_WELL": "C", "NO_REPRICING": "D"},
     "Used later when invoices are compared; no report evidence depends on it."),
    ("calloff_evidence", "AMB-13", AppliesIn.PHASE_5_AUDIT, {"INVOICE_STATEMENT_UNVERIFIED": "A", "UNVERIFIABLE_QUERY": "B"},
     "Well class and performance-section eligibility without call-offs. Phase 3 marks the condition as unknown."),
    ("record_signatories", "AMB-14", AppliesIn.PHASE_5_AUDIT, {"DDR_SIGNATURES_COVER_PARTS": "A", "FORM_SIGNATORIES_REQUIRED": "B"}, "Used later when invoices are compared."),
    ("missing_record_consequence", "AMB-23", AppliesIn.PHASE_5_AUDIT, {"PART_REJECT": "A", "QUERY": "B"}, "Used later when invoices are compared."),
    ("submission_date", "AMB-25", AppliesIn.PHASE_5_AUDIT, {"INVOICE_DATE_IS_SUBMISSION": "A", "UNKNOWN_QUERY": "B"}, "Used later when invoices are compared."),
)


# Readings that exist in the register but are deliberately not derived, with the reason.
NOT_DERIVED = {
    ("dd121_condition", "EVERY_STANDBY_DAY_OF_RSS_WELL"):
        "Its only concrete definition (Phase 3 Assumption 3: any report on the well with the rotary steerable in the hole) "
        "was rejected by the user on 2026-09-30; reading A was approved.",
}


def build_switches(ambiguities: dict[str, Ambiguity]) -> dict[str, Switch]:
    """The registry, with readings, defaults and approval flags taken from the Phase 1 register."""
    out = {}
    for name, amb_id, applies, mapping, explanation in _DEFINITIONS:
        amb = ambiguities[amb_id]
        by_id = {r.id: r for r in amb.readings}
        if set(mapping.values()) != set(by_id):
            raise ValueError(f"{name}: readings {sorted(mapping.values())} do not match {amb_id} {sorted(by_id)}")
        readings = tuple(SwitchReading(value, rid, by_id[rid].reading) for value, rid in mapping.items())
        default = next((r.value for r in readings if r.ambiguity_reading == amb.preferred_reading), None)
        basis = (f"Phase 1 preferred reading {amb.preferred_reading} ({amb.confidence}, {amb.status.value})" if default
                 else "no reading preferred in Phase 1")
        requires = amb.status in (AmbiguityStatus.OPEN, AmbiguityStatus.EVIDENCE_NOT_PROVIDED)
        out[name] = Switch(name, amb_id, applies, readings, default, basis, requires, explanation)
    return out


def phase3_switches(switches: dict[str, Switch]) -> dict[str, Switch]:
    return {k: v for k, v in switches.items() if v.applies_in is AppliesIn.PHASE_3_QUANTITIES}
