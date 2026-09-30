"""The contract's rounding: every amount in cents; each step rounded to the nearest cent, half to even (cl. 17)."""

from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, Decimal


def half_even_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def floor_int(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_FLOOR))
