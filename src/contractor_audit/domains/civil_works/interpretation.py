"""Readings of the civil works contract that the pricing engine can be switched between.

Every choice the contract leaves open (or that a reviewer might contest) is one field
of `CivilWorksInterpretation`. `WORKING_INTERPRETATION` is the currently selected
reading: it is chosen from the contract text alone and is **not** a claim of proof.
Billed data is never used to pick a value here; see `docs/civil_works/decision_log.md`.
"""

from dataclasses import dataclass, fields, replace
from enum import Enum


class RebateCounting(str, Enum):
    CONTRACT_YEAR = "contract_year"          # Sch 4 Part 3: bands restart each Contract Year (3A)
    WHOLE_WORKS = "whole_works"              # Clause 30 as printed: cumulative from Commencement


class IndexedRateMethod(str, Enum):
    CLAUSE_29A = "clause_29a"                # base x SMI(month) / 100, rounded half-even
    APPENDIX_B_UNINDEXED = "appendix_b_unindexed"   # the Appendix B worked example: base rate, no index


class UsdReading(str, Enum):
    CONVERT_FROM_USD = "convert_from_usd"    # Sch 2B + 26A: Schedule 1 figure is USD
    SAR_AS_PRINTED = "sar_as_printed"        # Clause 38 / Sch 1 heading: figure is SAR


class ConversionRounding(str, Enum):
    ROUND_BEFORE_BUILD_UP = "round_before_build_up"      # 26A / 29A: converted or indexed figure rounded half-even first
    UNROUNDED_INTO_BUILD_UP = "unrounded_into_build_up"  # Clause 28 read literally: no rounding before the final one


class PostCompletionGround(str, Enum):
    DATUM_G2_ALL_WORK = "datum_g2_all_work"              # 27A: every line executed after 2025-09-27 priced at G2
    DATUM_G2_EOT_AREAS_ONLY = "datum_g2_eot_areas_only"  # only the work areas named in the A1 recital
    RECORDED_CLASS = "recorded_class"                    # 27A disregarded: the stated ground class applies


class NightZoneCap(str, Enum):
    NO_NIGHT_UPLIFT_ABOVE_1_1 = "no_night_uplift_above_1_1"  # 27A applied
    NOT_APPLIED = "not_applied"


class ConcurrentUplifts(str, Enum):
    REST_DAY_ONLY_UNLESS_INSTRUCTED = "rest_day_only_unless_instructed"  # P11; instruction must be evidenced
    BOTH_ASSUMED_INSTRUCTED = "both_assumed_instructed"                  # theoretical branch only


class MonthlyRateTreatment(str, Enum):
    BASE_RATE_IN_BUILD_UP = "base_rate_in_build_up"  # the published monthly figure replaces the base rate, then Clause 27
    FINAL_RATE = "final_rate"                        # the published monthly figure is the rate paid, no further build-up


class DiscountInteraction(str, Enum):
    LATER_REPLACES_EARLIER = "later_replaces_earlier"  # instruments' closing words: the later discount governs
    COMPOUND = "compound"                              # 5% and 8% both applied


class ChargeableHourScope(str, Enum):
    PER_RECORD = "per_record"          # 6A: one hour fewer than the hours a record states
    PER_LINE = "per_line"              # one hour fewer per billed line
    PER_WORK_AREA_DAY = "per_work_area_day"


class SurveyQuantityRule(str, Enum):
    TOLERANCE_33A = "tolerance_33a"    # up to 2% over the surveyed quantity payable as measured
    EXACT_33 = "exact_33"              # the surveyed quantity exactly


class ExclusionWindow(str, Enum):
    SAME_DAY_INCLUDED = "same_day_included"   # excluded on day 0, 1 and 2
    SAME_DAY_EXCLUDED = "same_day_excluded"   # excluded on day 1 and 2 only


class RetroAdjustmentTrigger(str, Enum):
    ON_OR_AFTER_ISSUE = "on_or_after_issue"   # Clause 31A
    AFTER_ISSUE = "after_issue"               # Amendment No. 3 recital


@dataclass(frozen=True)
class CivilWorksInterpretation:
    rebate_counting: RebateCounting = RebateCounting.CONTRACT_YEAR
    indexed_rate_method: IndexedRateMethod = IndexedRateMethod.CLAUSE_29A
    usd_reading: UsdReading = UsdReading.CONVERT_FROM_USD
    conversion_rounding: ConversionRounding = ConversionRounding.ROUND_BEFORE_BUILD_UP
    post_completion_ground: PostCompletionGround = PostCompletionGround.DATUM_G2_ALL_WORK
    night_zone_cap: NightZoneCap = NightZoneCap.NO_NIGHT_UPLIFT_ABOVE_1_1
    concurrent_uplifts: ConcurrentUplifts = ConcurrentUplifts.REST_DAY_ONLY_UNLESS_INSTRUCTED
    monthly_rate_treatment: MonthlyRateTreatment = MonthlyRateTreatment.BASE_RATE_IN_BUILD_UP
    discount_interaction: DiscountInteraction = DiscountInteraction.LATER_REPLACES_EARLIER
    chargeable_hour_scope: ChargeableHourScope = ChargeableHourScope.PER_RECORD
    survey_quantity_rule: SurveyQuantityRule = SurveyQuantityRule.TOLERANCE_33A
    exclusion_window: ExclusionWindow = ExclusionWindow.SAME_DAY_INCLUDED
    retro_adjustment_trigger: RetroAdjustmentTrigger = RetroAdjustmentTrigger.ON_OR_AFTER_ISSUE

    def with_(self, **changes) -> "CivilWorksInterpretation":
        return replace(self, **changes)

    def label(self) -> dict[str, str]:
        return {f.name: getattr(self, f.name).value for f in fields(self)}


WORKING_INTERPRETATION = CivilWorksInterpretation()


class SwitchStatus(str, Enum):
    TEXT_RESOLVED = "text_resolved"              # the contract text settles it; alternative kept only for sensitivity
    UNRESOLVED = "unresolved"                    # the text genuinely supports more than one reading
    EVIDENCE_NOT_PROVIDED = "evidence_not_provided"  # the rule is clear; the data needed to apply it is absent


@dataclass(frozen=True)
class SwitchInfo:
    field: str
    ambiguity_id: str | None
    clauses: tuple[str, ...]
    pages: tuple[int, ...]
    status: SwitchStatus
    question: str
    readings: dict[str, str]
    default_rationale: str


SWITCHES: tuple[SwitchInfo, ...] = (
    SwitchInfo("rebate_counting", "AMB-BANDS", ("30", "Sch 4 Part 3", "3A", "2"), (6, 24, 32, 3), SwitchStatus.TEXT_RESOLVED,
               "Do rebate bands count per Contract Year or cumulatively over the whole Works?",
               {"contract_year": "Sch 4 Part 3: 'Clause 30 is substituted ... counted from zero at the start of each Contract Year (Clause 3A)'.",
                "whole_works": "Clause 30 as printed: cumulative across the whole of the Works from the Commencement Date."},
               "Schedule 4 Part 3 expressly substitutes Clause 30, and Clause 2 makes a Schedule prevail over the General Conditions."),
    SwitchInfo("indexed_rate_method", "AMB-INDEX-APPENDIX-B", ("29A", "Sch 2A", "App B", "2"), (3, 21, 32, 36), SwitchStatus.TEXT_RESOLVED,
               "Are C.31.010 and D.41.030 priced at the Schedule 2A index, or at the Schedule 1 rate as the Appendix B example does?",
               {"clause_29a": "29A: base x SMI(month of execution) / 100, rounded half-even; Sch 2A: the Schedule 1 rate 'is not payable as it stands'.",
                "appendix_b_unindexed": "Appendix B prices C.31.010 on 13/05/2025 at 86.20 x 1.06 = 91.37, i.e. with no index."},
               "Clause 2 defines the whole agreement as the Agreement, the General Conditions, Schedules 1 to 5 and Appendix A, and makes a "
               "Schedule prevail. Schedule 2A is inside that set and says the Schedule 1 rate 'is not payable as it stands', priced under 29A. "
               "Appendix B is an illustrative form outside the whole agreement, so its unindexed example cannot override an operative "
               "Schedule. Settled by the text (targeted correctness patch); the Appendix B reading is kept for sensitivity only."),
    SwitchInfo("usd_reading", "AMB-USD-CURRENCY", ("2", "26A", "38", "Sch 1", "Sch 2B"), (3, 7, 17, 22, 32), SwitchStatus.TEXT_RESOLVED,
               "Are the Schedule 1 figures for B.23.020, B.25.010 and C.32.040 USD or SAR?",
               {"convert_from_usd": "Sch 2B: 'The rate stated in Schedule 1 for the items below is in USD'; converted under 26A.",
                "sar_as_printed": "Clause 38 'All rates are in SAR' and the Schedule 1 column heading 'Rate (SAR)'."},
               "Clause 2: a Schedule prevails over the General Conditions (Clause 38) and a later-numbered Schedule (2B) over an earlier one (1)."),
    SwitchInfo("conversion_rounding", None, ("26A", "28", "29A"), (6, 32), SwitchStatus.TEXT_RESOLVED,
               "Is the USD-converted or indexed figure rounded before it enters the Clause 27 build-up?",
               {"round_before_build_up": "26A/29A: 'rounded to the nearest halala with a half rounded to the nearer even halala. That figure is then treated as the rate'.",
                "unrounded_into_build_up": "Clause 28: 'Rounding shall be applied once only ... Rates shall not be rounded at intermediate steps.'"},
               "26A and 29A are specific and state their own rounding and that Clause 28 then applies 'as usual'; the rounded figure is the input to Clause 27, not an intermediate step of it."),
    SwitchInfo("post_completion_ground", "AMB-G2-EOT", ("27A", "A1 recital"), (32, 40), SwitchStatus.TEXT_RESOLVED,
               "Which ground class prices work executed after 27 September 2025?",
               {"datum_g2_all_work": "27A: 'that is to say for work executed after 27 September 2025, the ground classification is taken as G2 Firm Sabkha whatever the Engineer recorded'.",
                "datum_g2_eot_areas_only": "Only S-04 Drainage Corridor and S-05 Compound Extension, the areas named in the Amendment No. 1 recital.",
                "recorded_class": "27A disregarded; the ground class stated on the line applies."},
               "27A defines the period itself ('that is to say ...') without limiting it to work areas."),
    SwitchInfo("night_zone_cap", "AMB-NIGHT-ZONE", ("27A", "7", "Sch 4 Part 1"), (3, 24, 32), SwitchStatus.TEXT_RESOLVED,
               "Is the night uplift withheld where the zone factor exceeds 1.1 (Z3, Z4)?",
               {"no_night_uplift_above_1_1": "27A: 'The night-working uplift is not payable on an item priced at a zone factor exceeding 1.1'.",
                "not_applied": "27A disregarded; any Schedule 4 Part 1 item worked at night takes the uplift."},
               "27A is an express condition; only its precedence is formally unstated."),
    SwitchInfo("concurrent_uplifts", "AMB-UPLIFT-EVIDENCE", ("8", "9", "P11", "Sch 4"), (3, 13, 26), SwitchStatus.EVIDENCE_NOT_PROVIDED,
               "Night work on a rest day for an item in both uplift lists: one uplift or both?",
               {"rest_day_only_unless_instructed": "P11: both only where the Engineer instructed in writing under Clause 9; otherwise the rest-day uplift alone.",
                "both_assumed_instructed": "Theoretical branch: both uplifts, as if an instruction existed."},
               "The rule is clear. No Clause 9 instruction exists anywhere in the data, so authorisation is never evidenced."),
    SwitchInfo("monthly_rate_treatment", "AMB-MONTHLY-RATE-BUILDUP", ("27", "S1 1.2", "A2 2.2", "S2 2.1"), (6, 39, 41, 42), SwitchStatus.UNRESOLVED,
               "Is a published monthly rate (D.41.020 under S1, E.54.010 under A2) a base rate for the Clause 27 build-up, or the final rate?",
               {"base_rate_in_build_up": "The monthly figure replaces the Schedule 1 base rate; zone factor and night uplift then apply. "
                                         "S2 2.1 treats 220.50 as a Bill of Quantities rate 'previously payable', and S2 2.2 applies its discount within the Clause 27 build-up for D.41.020.",
                "final_rate": "S1 1.2 / A2 2.2: 'The rate payable for a measured quantity is the rate published' reads as the amount per unit actually paid."},
               "The instruments use 'rate payable' for Bill of Quantities substitutions too, which are base rates; the default follows that usage. "
               "For E.54.010 (Series E, no uplift, no band, no discount) both readings give the same price."),
    SwitchInfo("discount_interaction", "AMB-DISCOUNT-STACK", ("S2 2.2", "A2 2.3", "closing words"), (41, 42), SwitchStatus.TEXT_RESOLVED,
               "From 2026-04-01, does the 8% discount replace the 5% or compound with it?",
               {"later_replaces_earlier": "Closing words of every instrument: 'Where this instrument and an earlier instrument both state ... a discount for the same item, the later governs'.",
                "compound": "0.95 x 0.92 applied together."},
               "The closing words address exactly this case; the A2 recital calls it a 'deepening' of the S2 discount."),
    SwitchInfo("chargeable_hour_scope", "AMB-CHARGEABLE-HOUR", ("6A",), (32,), SwitchStatus.UNRESOLVED,
               "The first hour of 'that attendance' is not chargeable: per record, per billed line, or per work area and day?",
               {"per_record": "The site record states the hours attended; the quantity measured is one hour fewer than the record.",
                "per_line": "One hour fewer on each billed line.",
                "per_work_area_day": "One hour fewer per work area per day, however many lines or records."},
               "6A ties the deduction to 'the site record [that] states the hours attended'."),
    SwitchInfo("survey_quantity_rule", "AMB-SURVEY-TOLERANCE", ("33", "33A"), (7, 32), SwitchStatus.UNRESOLVED,
               "For surveyed items, is the payable quantity the survey figure exactly, or measured quantity within 2% of it?",
               {"tolerance_33a": "33A: up to 2% over the surveyed quantity is payable as measured; more than that is payable at the surveyed quantity.",
                "exact_33": "33: 'The quantity measured shall be the quantity on the survey sheet exactly.'"},
               "33A is later and specific, but Part VII has no stated precedence over Part II."),
    SwitchInfo("exclusion_window", "AMB-EXCLUSION-WINDOW", ("32", "P19", "Sch 4 Part 5"), (6, 13, 26), SwitchStatus.UNRESOLVED,
               "Does 'within two days of/following the measurement of A.14.010' include the same day?",
               {"same_day_included": "Excluded on the day of the A.14.010 measurement and the two days after.",
                "same_day_excluded": "Excluded only on the two days following."},
               "P19 says 'within two days of', which on its natural reading covers the day itself; Clause 32 says 'following'."),
    SwitchInfo("retro_adjustment_trigger", "AMB-A3-ADJUSTMENT", ("31A", "A3 recital"), (32, 43), SwitchStatus.UNRESOLVED,
               "Which application carries the single Amendment No. 3 adjustment, and is an application submitted on the issue date priced at the new rates?",
               {"on_or_after_issue": "31A: 'the first Application for Payment submitted on or after the date of issue'.",
                "after_issue": "A3 recital: 'the first Application for Payment submitted after the date of issue'."},
               "A3 cites Clause 31A for the mechanism, so 31A's wording is taken as the operative rule."),
)
SWITCHES_BY_FIELD = {s.field: s for s in SWITCHES}


def alternatives(field_name: str) -> list[Enum]:
    """Every non-default value of one switch."""
    current = getattr(WORKING_INTERPRETATION, field_name)
    return [v for v in type(current) if v != current]
