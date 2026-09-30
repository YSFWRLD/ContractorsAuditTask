"""The Clause 27 build-up: what a measured quantity is worth under the contract.

Order, from the contract text:

1. rate in force (Schedule 1, or a substituted / monthly rate from an instrument)   rates.py
2. Schedule 2B USD conversion, rounded half-even, before any factor              26A p.32
   Schedule 2A indexation, rounded half-even, then 'treated as the rate'         29A p.32
3. site zone factor (Series A-D only)                                            27, 29, Sch 2
4. ground classification factor (15 listed items only; G2 after 2025-09-27)      27, Sch 3, 27A, S4
5. night uplift (Sch 4 Part 1 items; not above zone factor 1.1)                  7, 27, 27A, P11
6. rest-day uplift (Sch 4 Part 2 items, Friday/Saturday)                         8, 27, P11
7. rebate band percentage (Sch 4 Part 3, band-by-band)                           27, 30, Sch 4 Part 3
8. discount (S2 2.2 / A2 2.3: 'final factor ... after any rebate ... before the rounding')
9. one rounding, half-up to the halala                                           28
amount = quantity x rounded rate, summed over band parts                         28

The engine prices; it does not judge. It never reads billed rates or amounts.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from contractor_audit.domains.civil_works.contract import ContractTerms
from contractor_audit.domains.civil_works.contract_period import ContractPeriod
from contractor_audit.domains.civil_works.interpretation import (WORKING_INTERPRETATION, CivilWorksInterpretation,
                                                                 ConcurrentUplifts, ConversionRounding,
                                                                 DiscountInteraction, IndexedRateMethod,
                                                                 MonthlyRateTreatment, NightZoneCap,
                                                                 PostCompletionGround, UsdReading)
from contractor_audit.domains.civil_works.rates import PricingError, RateKind, RateResolution, RateResolver
from contractor_audit.domains.civil_works.rebates import BandAllocation
from contractor_audit.domains.civil_works.rounding import (amount_to_cents, cents_to_decimal, round_built_up_rate,
                                                           round_converted_rate)
from contractor_audit.domains.civil_works.trace import TraceStep

DATUM_GROUND = "G2 Firm Sabkha"
NIGHT_ZONE_FACTOR_CEILING = Decimal("1.1")             # Clause 27A
EOT_RECITAL_WORK_AREAS = frozenset({"S-04 Drainage Corridor", "S-05 Compound Extension"})  # A1 recital p.40
_WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class LineContext:
    """What the contract needs to know about one measurement. Nothing here is a billed price."""
    item_code: str
    work_date: date
    zone: str
    work_area: str
    ground_class: str | None = None
    night_work: bool = False
    known_at: date | None = None                  # submission date of the application pricing it
    include_issued_on_known_at: bool = True       # see RetroAdjustmentTrigger
    engineer_instruction_both_uplifts: bool = False   # Clause 9 instruction; never evidenced in the task data


@dataclass(frozen=True)
class PreBandRate:
    """Everything up to (not including) the band percentage, discount and final rounding."""
    context: LineContext
    resolution: RateResolution
    value: Decimal
    discount_factors: tuple[tuple[str, Decimal], ...]
    final_rate_only: bool           # MonthlyRateTreatment.FINAL_RATE applied: no further factors
    trace: tuple[TraceStep, ...]


@dataclass(frozen=True)
class PricedPart:
    quantity: Decimal
    band_percent: Decimal | None
    band_printed: str | None
    unrounded_rate: Decimal
    rate: Decimal                   # rounded (Clause 28)
    amount_cents: int


@dataclass(frozen=True)
class LinePrice:
    context: LineContext
    quantity: Decimal
    resolution: RateResolution
    parts: tuple[PricedPart, ...]
    amount_cents: int
    band_allocation: BandAllocation | None
    trace: tuple[TraceStep, ...]

    @property
    def unit_rate(self) -> Decimal:
        """The rounded rate of the first part (the rate a single-rate line would show)."""
        return self.parts[0].rate

    @property
    def is_split(self) -> bool:
        return len(self.parts) > 1


def _d(x: Decimal) -> str:
    return format(x.normalize(), "f") if x == x.to_integral_value() else str(x)


class PricingEngine:
    def __init__(self, terms: ContractTerms, interpretation: CivilWorksInterpretation = WORKING_INTERPRETATION):
        self.terms = terms
        self.interp = interpretation
        self.resolver = RateResolver(terms)
        self.period = ContractPeriod(terms)

    # ------------------------------------------------------------------ steps 1-6

    def pre_band_rate(self, ctx: LineContext) -> PreBandRate:
        t, it = self.terms, self.interp
        if ctx.item_code not in t.boq:
            raise PricingError(f"{ctx.item_code} is not a Schedule 1 item")
        res = self.resolver.resolve(ctx.item_code, ctx.work_date, ctx.known_at,
                                    include_issued_on_known_at=ctx.include_issued_on_known_at)
        trace = list(res.trace)
        month = f"{ctx.work_date.year:04d}-{ctx.work_date.month:02d}"
        rate = res.rate_in_force
        round_conv = it.conversion_rounding is ConversionRounding.ROUND_BEFORE_BUILD_UP

        # Step 2: Schedule 2B (26A) and Schedule 2A (29A) apply to the Schedule 1 figure only.
        if ctx.item_code in t.usd_items and res.kind is RateKind.BILL_OF_QUANTITIES:
            if it.usd_reading is UsdReading.CONVERT_FROM_USD:
                if month not in t.fx_halalas_per_usd:
                    raise PricingError(f"no Schedule 2B exchange rate for {month}")
                fx = t.fx_halalas_per_usd[month]
                raw = rate * fx / 100
                rate = round_converted_rate(raw) if round_conv else raw
                trace.append(TraceStep("usd_conversion", "Sch 2B p.22; Clause 26A p.32",
                                       f"{_d(res.rate_in_force)} USD x {fx} halalas/USD / 100 = {raw}" + (" -> half-even to halala" if round_conv else " (unrounded)"),
                                       str(rate), {"month": month}, f"usd_reading={it.usd_reading.value}; conversion_rounding={it.conversion_rounding.value}"))
            else:
                trace.append(TraceStep("usd_conversion", "Clause 38 p.7; Sch 1 heading 'Rate (SAR)'", "figure read as SAR; not converted",
                                       str(rate), interpretation=f"usd_reading={it.usd_reading.value}"))
        if ctx.item_code in t.indexed_items and res.kind is RateKind.BILL_OF_QUANTITIES:
            if it.indexed_rate_method is IndexedRateMethod.CLAUSE_29A:
                if month not in t.site_materials_index:
                    raise PricingError(f"no Site Materials Index for {month}")
                smi = t.site_materials_index[month]
                raw = rate * smi / t.index_base
                rate = round_converted_rate(raw) if round_conv else raw
                trace.append(TraceStep("indexation", "Sch 2A p.21; Clause 29A p.32",
                                       f"{_d(res.rate_in_force)} x SMI {smi} / {t.index_base} = {raw}" + (" -> half-even to halala" if round_conv else " (unrounded)"),
                                       str(rate), {"month": month}, f"indexed_rate_method={it.indexed_rate_method.value}; conversion_rounding={it.conversion_rounding.value}"))
            else:
                trace.append(TraceStep("indexation", "Appendix B p.36 worked example", "Schedule 1 rate used unindexed, as in the Appendix B example",
                                       str(rate), interpretation=f"indexed_rate_method={it.indexed_rate_method.value}"))

        if res.kind is RateKind.MONTHLY and it.monthly_rate_treatment is MonthlyRateTreatment.FINAL_RATE:
            trace.append(TraceStep("monthly_rate_final", f"{res.source_instrument} monthly re-measurement p.{res.governing.page}",
                                   "published monthly rate taken as the rate paid; no zone, ground, uplift, band or discount applied",
                                   str(rate), interpretation=f"monthly_rate_treatment={it.monthly_rate_treatment.value}"))
            return PreBandRate(ctx, res, rate, (), True, tuple(trace))
        if res.kind is RateKind.MONTHLY:
            trace.append(TraceStep("monthly_rate_as_base", f"{res.source_instrument} monthly re-measurement p.{res.governing.page}; S2 2.1-2.2 p.41",
                                   "published monthly rate replaces the base rate and enters the Clause 27 build-up",
                                   str(rate), interpretation=f"monthly_rate_treatment={it.monthly_rate_treatment.value}"))

        series = ctx.item_code[0]
        # Step 3: zone factor.
        zone_factor = Decimal(1)
        if series in t.zone_factor_series:
            if ctx.zone not in t.zone_factors:
                raise PricingError(f"unknown zone {ctx.zone!r}")
            zone_factor = t.zone_factors[ctx.zone]
            rate = rate * zone_factor
            trace.append(TraceStep("zone_factor", "Sch 2 p.20; Clauses 4, 27, 29", f"x {zone_factor} ({ctx.zone})", str(rate)))
        else:
            trace.append(TraceStep("zone_factor", "Sch 2 p.20: 'They do not apply to Series E'", f"Series {series}: no zone factor", str(rate)))

        # Step 4: ground factor.
        if ctx.item_code in t.ground_factor_items:
            ground, why, interp_note = ctx.ground_class, "ground class stated for the measurement", None
            if ground is None:
                ground, why = DATUM_GROUND, "no classification stated: taken as G2 (S4 p.10; G2 is the datum, Sch 3)"
            after = ctx.work_date > t.original_completion_date
            rule = it.post_completion_ground
            if after and (rule is PostCompletionGround.DATUM_G2_ALL_WORK or
                          (rule is PostCompletionGround.DATUM_G2_EOT_AREAS_ONLY and ctx.work_area in EOT_RECITAL_WORK_AREAS)):
                ground, why = DATUM_GROUND, f"work executed after {t.original_completion_date}: taken as G2 whatever was recorded (27A p.32)"
                interp_note = f"post_completion_ground={rule.value}"
            elif after:
                interp_note = f"post_completion_ground={rule.value}"
            if ground not in t.ground_factors:
                raise PricingError(f"unknown ground class {ground!r}")
            factor = t.ground_factors[ground]
            rate = rate * factor
            trace.append(TraceStep("ground_factor", "Sch 3 p.23; Clause 27", f"x {factor} ({ground}; {why})", str(rate),
                                   {"stated_ground": ctx.ground_class or ""}, interp_note))
        else:
            trace.append(TraceStep("ground_factor", "Sch 3 p.23: 'apply only to the items listed'", "item not listed in Schedule 3: no ground factor", str(rate)))

        # Steps 5-6: uplifts.
        night_pct = t.night_uplift_percent.get(ctx.item_code)
        rest_pct = t.rest_day_uplift_percent.get(ctx.item_code)
        is_rest_day = _WEEKDAY_NAMES[ctx.work_date.weekday()] in t.rest_days
        apply_night = bool(night_pct is not None and ctx.night_work)
        night_note = None
        if apply_night and series in t.zone_factor_series and zone_factor > NIGHT_ZONE_FACTOR_CEILING:
            night_note = f"night_zone_cap={it.night_zone_cap.value}"
            if it.night_zone_cap is NightZoneCap.NO_NIGHT_UPLIFT_ABOVE_1_1:
                apply_night = False
                trace.append(TraceStep("night_uplift", "Clause 27A p.32", f"zone factor {zone_factor} exceeds 1.1: night uplift not payable",
                                       str(rate), interpretation=night_note))
        apply_rest = bool(rest_pct is not None and is_rest_day)
        if apply_night and apply_rest:
            both = (it.concurrent_uplifts is ConcurrentUplifts.BOTH_ASSUMED_INSTRUCTED or ctx.engineer_instruction_both_uplifts)
            if not both:
                apply_night = False
                trace.append(TraceStep("night_uplift", "Clauses 8, 9 p.3; P11 p.13",
                                       "night work on a rest day without an evidenced Clause 9 instruction: rest-day uplift alone applies",
                                       str(rate), interpretation=f"concurrent_uplifts={it.concurrent_uplifts.value}"))
            else:
                night_note = f"concurrent_uplifts={it.concurrent_uplifts.value}"
        if apply_night:
            rate = rate * (1 + night_pct / 100)
            trace.append(TraceStep("night_uplift", "Sch 4 Part 1 p.24; Clauses 7, 27", f"x (1 + {night_pct}%)", str(rate), interpretation=night_note))
        elif night_pct is not None and not ctx.night_work:
            trace.append(TraceStep("night_uplift", "Clause 7 p.3", "not night work: no night uplift", str(rate)))
        if apply_rest:
            rate = rate * (1 + rest_pct / 100)
            trace.append(TraceStep("rest_day_uplift", "Sch 4 Part 2 p.24; Clauses 8, 27",
                                   f"x (1 + {rest_pct}%) ({_WEEKDAY_NAMES[ctx.work_date.weekday()]})", str(rate)))

        # Step 8 inputs: discounts in effect (applied after the band percentage).
        discounts = self._discounts(ctx, trace)
        return PreBandRate(ctx, res, rate, discounts, False, tuple(trace))

    def _discounts(self, ctx: LineContext, trace: list) -> tuple[tuple[str, Decimal], ...]:
        def known(issued: date) -> bool:
            if ctx.known_at is None:
                return True
            return issued < ctx.known_at or (ctx.include_issued_on_known_at and issued == ctx.known_at)

        live = [i for i in self.terms.instruments
                if i.discount and ctx.item_code in i.discount.codes and i.discount.effective <= ctx.work_date and known(i.issued)]
        if not live:
            return ()
        live.sort(key=lambda i: i.issued)
        chosen = [live[-1]] if self.interp.discount_interaction is DiscountInteraction.LATER_REPLACES_EARLIER else live
        if len(live) > 1:
            trace.append(TraceStep("discount_selection", "instrument closing words pp.39-43",
                                   f"discounts in effect: {', '.join(f'{i.id} {i.discount.percent}%' for i in live)}; applying {', '.join(i.id for i in chosen)}",
                                   "", interpretation=f"discount_interaction={self.interp.discount_interaction.value}"))
        return tuple((i.id, i.discount.percent) for i in chosen)

    # ------------------------------------------------------------------ steps 7-9

    def finish_rate(self, pre: PreBandRate, band_percent: Decimal | None) -> tuple[Decimal, Decimal, list[TraceStep]]:
        steps, rate = [], pre.value
        if not pre.final_rate_only:
            if band_percent is not None:
                rate = rate * band_percent / 100
                steps.append(TraceStep("rebate_band", "Sch 4 Part 3 pp.24-25; Clause 27", f"x {band_percent}% of rate", str(rate),
                                       interpretation=f"rebate_counting={self.interp.rebate_counting.value}"))
            for iid, pct in pre.discount_factors:
                rate = rate * (1 - pct / 100)
                steps.append(TraceStep("discount", f"{iid} discount (final factor, after rebate, before rounding)", f"x (1 - {pct}%)", str(rate)))
        rounded = round_built_up_rate(rate)
        steps.append(TraceStep("rounding", "Clause 28 p.6", f"{rate} -> nearest halala, half up", str(rounded)))
        return rate, rounded, steps

    def price(self, ctx: LineContext, quantity: Decimal, band_allocation: BandAllocation | None = None) -> LinePrice:
        pre = self.pre_band_rate(ctx)
        trace = list(pre.trace)
        slices = [(s.quantity, s.percent_of_rate, s.band_printed) for s in band_allocation.slices] if band_allocation else [(quantity, None, None)]
        if band_allocation is not None:
            if band_allocation.quantity != quantity:
                raise ValueError("band allocation does not cover the priced quantity")
            trace.append(TraceStep("band_allocation", "Sch 4 Part 3 pp.24-25",
                                   f"{band_allocation.period_key}: volume before {band_allocation.volume_before}, after {band_allocation.volume_after}; "
                                   + "; ".join(f"{s.quantity} in '{s.band_printed}' at {s.percent_of_rate}%" for s in band_allocation.slices)
                                   + ("".join(f" [{n}]" for n in band_allocation.notes)),
                                   str(len(band_allocation.slices)) + " part(s)", interpretation=f"rebate_counting={self.interp.rebate_counting.value}"))
        parts = []
        for qty, pct, printed in slices:
            unrounded, rounded, steps = self.finish_rate(pre, pct)
            trace.extend(steps)
            cents = amount_to_cents(qty * rounded)
            parts.append(PricedPart(qty, pct, printed, unrounded, rounded, cents))
        total = sum(p.amount_cents for p in parts)
        trace.append(TraceStep("amount", "Clause 28 p.6: quantity x rounded rate; parts summed",
                               " + ".join(f"{p.quantity} x {p.rate}" for p in parts), str(cents_to_decimal(total))))
        return LinePrice(ctx, quantity, pre.resolution, tuple(parts), total, band_allocation, tuple(trace))
