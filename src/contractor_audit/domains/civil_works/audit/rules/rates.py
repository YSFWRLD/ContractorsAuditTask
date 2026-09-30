"""Check 7 (and the rebate / discount part of check 8): billed rate against the contract rate.

The contract rate is the Phase 2 price of the billed quantity at the line's band position. When
the billed rate differs, the rule looks for a single deviation that reproduces it: each
counterfactual is priced by the same Phase 2 engine with one input, one contract term or one
reading changed. This explains the discrepancy; it never changes the expected value, which is
always the working-contract price.
"""

import dataclasses
from datetime import timedelta
from decimal import Decimal

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.models import RuleOutput
from contractor_audit.domains.civil_works.audit.rules.common import finding, money, trace_evidence
from contractor_audit.domains.civil_works.interpretation import (ConcurrentUplifts, ConversionRounding,
                                                                 DiscountInteraction, IndexedRateMethod,
                                                                 MonthlyRateTreatment, NightZoneCap,
                                                                 PostCompletionGround, UsdReading)
from contractor_audit.domains.civil_works.pricing import PricingEngine
from contractor_audit.domains.civil_works.rates import PricingError
from contractor_audit.domains.civil_works.rebates import BandAllocation, BandSlice
from contractor_audit.domains.civil_works.rounding import amount_to_cents
from contractor_audit.domains.civil_works.valuation import line_context
from contractor_audit.shared.findings import Evidence


class RateDiagnoser:
    def __init__(self, ctx):
        t, it = ctx.terms, ctx.interp
        self.ctx = ctx
        self.engine = PricingEngine(t, it)
        R = dataclasses.replace
        self._engines = {
            "discount_omitted": PricingEngine(R(t, instruments=tuple(R(i, discount=None) for i in t.instruments)), it),
            "discount_compounded": PricingEngine(t, it.with_(discount_interaction=DiscountInteraction.COMPOUND)),
            "zone_factor_omitted": PricingEngine(R(t, zone_factor_series=frozenset()), it),
            "ground_as_recorded_after_27A": PricingEngine(t, it.with_(post_completion_ground=PostCompletionGround.RECORDED_CLASS)),
            "night_uplift_despite_27A_zone_cap": PricingEngine(t, it.with_(night_zone_cap=NightZoneCap.NOT_APPLIED)),
            "rest_day_uplift_omitted": PricingEngine(R(t, rest_day_uplift_percent={}), it),
            "night_and_rest_day_uplifts_both": PricingEngine(t, it.with_(concurrent_uplifts=ConcurrentUplifts.BOTH_ASSUMED_INSTRUCTED)),
            "index_not_applied": PricingEngine(t, it.with_(indexed_rate_method=IndexedRateMethod.APPENDIX_B_UNINDEXED)),
            "usd_not_converted": PricingEngine(t, it.with_(usd_reading=UsdReading.SAR_AS_PRINTED)),
            "conversion_not_rounded": PricingEngine(t, it.with_(conversion_rounding=ConversionRounding.UNROUNDED_INTO_BUILD_UP)),
            "monthly_rate_taken_as_final": PricingEngine(t, it.with_(monthly_rate_treatment=MonthlyRateTreatment.FINAL_RATE)),
        }
        self._recorded_ground = PricingEngine(t, it.with_(post_completion_ground=PostCompletionGround.RECORDED_CLASS))

    def _rate(self, engine, lctx, quantity, alloc):
        """The figure being matched: the rate for a single-rate line, the amount for a band-split one."""
        try:
            price = engine.price(lctx, quantity, alloc)
        except PricingError:
            return None
        return price.amount_cents if self._by_amount else price.unit_rate

    def explain(self, line, lctx, alloc, target, by_amount: bool = False) -> list[tuple[str, Category]]:
        """Every single deviation that reproduces the billed figure exactly, with its category.

        `target` is the billed rate, or (with `by_amount`) the billed amount in halalas.
        """
        self._by_amount = by_amount
        t = self.ctx.terms
        q = line.quantity
        found: list[tuple[str, Category]] = []

        def test(name, value, category=Category.UNIT_RATE_MISMATCH):
            if value is not None and value == target and name not in [f[0] for f in found]:
                found.append((name, category))

        for name, eng in self._engines.items():
            cat = Category.DISCOUNT_INCORRECTLY_APPLIED if name.startswith("discount") else Category.UNIT_RATE_MISMATCH
            test(name, self._rate(eng, lctx, q, alloc), cat)
        # Rebate band omitted, or the whole line taken at the band it ends in.
        if alloc is not None:
            test("rebate_band_omitted", self._rate(self.engine, lctx, q, None), Category.REBATE_INCORRECTLY_APPLIED)
            last = alloc.slices[-1]
            whole = BandAllocation(alloc.item_code, alloc.period_key, q, alloc.volume_before, alloc.volume_after,
                                   (BandSlice(q, last.percent_of_rate, last.band_printed, alloc.volume_before, alloc.volume_after),))
            if alloc.crosses_band_edge:
                test("whole_line_at_final_band", self._rate(self.engine, lctx, q, whole), Category.REBATE_INCORRECTLY_APPLIED)
            for pct in sorted({b.percent_of_rate for b in t.bands[line.item_code]}):
                band = next(b for b in t.bands[line.item_code] if b.percent_of_rate == pct)
                other = BandAllocation(alloc.item_code, alloc.period_key, q, alloc.volume_before, alloc.volume_after,
                                       (BandSlice(q, pct, band.printed, alloc.volume_before, alloc.volume_after),))
                test(f"band_{band.printed}", self._rate(self.engine, lctx, q, other), Category.REBATE_INCORRECTLY_APPLIED)
        # A rate or discount from before an instrument that governs this work.
        for inst in t.instruments:
            if inst.effective > line.work_date or (lctx.known_at and inst.issued > lctx.known_at):
                continue
            touches_rate = line.item_code in {s.code for s in inst.rate_substitutions} | {m.code for m in inst.monthly_rates}
            touches_discount = bool(inst.discount and line.item_code in inst.discount.codes)
            if not (touches_rate or touches_discount):
                continue
            earlier = dataclasses.replace(lctx, known_at=inst.issued - timedelta(days=1))
            cat = Category.DISCOUNT_INCORRECTLY_APPLIED if touches_discount and not touches_rate else Category.UNIT_RATE_MISMATCH
            test(f"as_if_{inst.id}_not_in_force", self._rate(self.engine, earlier, q, alloc), cat)
        # Priced by the application date instead of the work date (guideline 1).
        app_date = self.ctx.apps[line.application_no].application_date
        if app_date != line.work_date:
            test("priced_at_application_date", self._rate(self.engine, dataclasses.replace(lctx, work_date=app_date), q, alloc))
        # Zone, ground and night inputs.
        for zone in t.zone_factors:
            if zone != lctx.zone:
                test(f"zone_{zone}", self._rate(self.engine, dataclasses.replace(lctx, zone=zone), q, alloc))
        if line.item_code in t.ground_factor_items:
            for ground in t.ground_factors:
                test(f"ground_{ground}", self._rate(self._recorded_ground, dataclasses.replace(lctx, ground_class=ground), q, alloc))
        test("night_flag_inverted", self._rate(self.engine, dataclasses.replace(lctx, night_work=not lctx.night_work), q, alloc))
        return found


def check(ctx, valuations) -> list:
    """Compare each payable line with its contract price.

    A line the contract divides at a band edge has no single rate (Clause 28: each part at its own
    rate, the amount their sum), so only its amount is compared; the printed rate of such a line is
    not judged. Every other line is compared on its rate.
    """
    diag = RateDiagnoser(ctx)
    out = []
    by_ref = {l.line_ref: l for l in ctx.lines}
    c27, c28 = ctx.cite("27"), ctx.cite("28")
    for ref in sorted(valuations):
        v = valuations[ref]
        line = by_ref[ref]
        if v.contract_billed is None or v.payable_quantity == 0:
            continue
        contract = v.contract_billed
        lctx = line_context(line, ctx.apps[line.application_no], ctx.interp)
        if contract.is_split:
            if line.amount_cents == contract.amount_cents:
                continue
            explanations = diag.explain(line, lctx, contract.band_allocation, line.amount_cents, by_amount=True)
            default = Category.LINE_TOTAL_ARITHMETIC if not explanations else Category.UNIT_RATE_MISMATCH
            rule = "rates.band_split_amount"
            observed, expected = money(line.amount_cents), money(contract.amount_cents)
            parts = " + ".join(f"{p.quantity} x {p.rate}" for p in contract.parts)
            what = f"Billed amount {observed}; the contract divides the line at a band edge: {parts} = {expected}"
            impact = line.amount_cents - contract.amount_cents
            cites = (c28, ctx.cite("30"))
        else:
            if line.rate_applied == contract.unit_rate:
                continue
            explanations = diag.explain(line, lctx, contract.band_allocation, line.rate_applied)
            default = Category.UNIT_RATE_MISMATCH
            rule = "rates.unit_rate"
            observed, expected = str(line.rate_applied), str(contract.unit_rate)
            what = f"Billed rate {observed}; the contract rate for {line.item_code} executed {line.work_date} is {expected}"
            impact = amount_to_cents(line.quantity * line.rate_applied) - contract.amount_cents
            cites = (c27, c28)
        # The more specific rebate / discount category wins when any explanation points to it.
        category = next((c for _, c in explanations if c is not Category.UNIT_RATE_MISMATCH), default)
        why = ("; reproduced by: " + ", ".join(n for n, _ in explanations)) if explanations else "; no single deviation reproduces it"
        out.append(RuleOutput(finding(category, line.application_no, rule, f"{what}{why}.",
                                      line=line, observed=observed, expected=expected, impact_cents=impact,
                                      affects_total=True, citations=cites,
                                      evidence=trace_evidence(contract.trace, ref)
                                      + tuple(Evidence("diagnosis", ref, n) for n, _ in explanations))))
    return out
