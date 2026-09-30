"""The one place civil works money is rounded. Every rounding cites the clause that orders it.

Python's default `round()` is never used for contract money.
"""

from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

HALALA = Decimal("0.01")


def round_built_up_rate(rate: Decimal) -> Decimal:
    """Clause 28: once, after the whole Clause 27 build-up, to the nearest halala, a half rounded upward."""
    return rate.quantize(HALALA, rounding=ROUND_HALF_UP)


def round_converted_rate(rate: Decimal) -> Decimal:
    """Clauses 26A and 29A: to the nearest halala, a half rounded to the nearer even halala."""
    return rate.quantize(HALALA, rounding=ROUND_HALF_EVEN)


def round_down_to_halala(amount: Decimal) -> Decimal:
    """Clauses 45 and 45A: retention and its release are rounded down to the halala."""
    return amount.quantize(HALALA, rounding=ROUND_FLOOR)


def amount_to_cents(amount: Decimal) -> int:
    """quantity x rounded rate, as whole halalas.

    With integer quantities (every billed line) the product is already exact. The contract does
    not say how to round a product with a fraction of a halala, which could only arise from a
    fractional quantity (e.g. a Clause 6A chargeable half-hour); Clause 28's half-up rule is used.
    """
    return int((amount * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def cents_to_decimal(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(HALALA)
