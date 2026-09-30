"""Price each line's billed and payable quantity with the Phase 2 engine.

Rebate bands need one extra idea the Phase 2 valuation (which priced billed quantities) did not:
the band position a line is priced at, and how far the line advances the counter, can differ
once some of its quantity is disallowed (`rebate_progression`). Both allocations are taken from
the counter as it stands before the line; the counter then advances by the progression quantity.
"""

from decimal import Decimal

from contractor_audit.domains.civil_works.audit.models import LineValuation, Unresolved
from contractor_audit.domains.civil_works.pricing import PricingEngine
from contractor_audit.domains.civil_works.rates import PricingError
from contractor_audit.domains.civil_works.rebates import BandAllocation, RebateLedger, band_order_key
from contractor_audit.domains.civil_works.valuation import line_context


class AuditBandLedger(RebateLedger):
    """A RebateLedger that can allocate from the current counter without moving it."""

    def peek(self, item_code, work_date, quantity) -> BandAllocation:
        key, _ = self.period_key(work_date)
        before = self.volume(item_code, key)
        allocation = self.allocate(item_code, work_date, quantity)
        self._volumes[(item_code, key)] = before
        return allocation


def value_lines(ctx, payable: dict[str, Decimal], progression: dict[str, Decimal], binding: dict[str, tuple]) -> tuple[dict, list]:
    engine = PricingEngine(ctx.terms, ctx.interp)
    ledger = AuditBandLedger(ctx.terms, ctx.interp.rebate_counting, ctx.period)
    out: dict[str, LineValuation] = {}
    unresolved: list[Unresolved] = []
    for line in sorted(ctx.lines, key=lambda l: band_order_key(l.work_date, l.application_no, l.line_no)):
        app = ctx.apps[line.application_no]
        lctx = line_context(line, app, ctx.interp)
        pay = payable[line.line_ref]
        billed_alloc = payable_alloc = None
        if ledger.is_banded(line.item_code):
            billed_alloc = ledger.peek(line.item_code, line.work_date, line.quantity)
            payable_alloc = ledger.peek(line.item_code, line.work_date, pay)
            ledger.allocate(line.item_code, line.work_date, progression[line.line_ref])
        try:
            billed_price = engine.price(lctx, line.quantity, billed_alloc)
            payable_price = engine.price(lctx, pay, payable_alloc)
        except PricingError as exc:
            billed_price = payable_price = None
            if pay != 0:     # nothing payable needs no rate (e.g. work before commencement)
                unresolved.append(Unresolved(line.application_no, line.line_ref, "rate_not_established", str(exc)))
        payable_cents = payable_price.amount_cents if payable_price is not None else (0 if pay == 0 else None)
        out[line.line_ref] = LineValuation(line.line_ref, line.application_no, line.quantity, pay, progression[line.line_ref],
                                           line.amount_cents, billed_price, payable_price, binding.get(line.line_ref, ()), payable_cents)
    return out, unresolved
