"""Money parsing and the submission's integer minor-unit representation.

Both contracts print money with two decimal places (SAR / USD) and the
submission takes integer minor units (README: 265123.89 -> 26512389).
Contract-specific rounding rules do not belong here.
"""

from decimal import Decimal, InvalidOperation


def parse_amount(text: str) -> Decimal:
    """Parse a money string exactly as printed in the task CSVs."""
    try:
        value = Decimal(text.strip())
    except InvalidOperation as exc:
        raise ValueError(f"not a money amount: {text!r}") from exc
    if not value.is_finite():
        raise ValueError(f"not a money amount: {text!r}")
    return value


def to_minor_units(amount: Decimal) -> int:
    """Convert a two-decimal amount to integer minor units, refusing to round silently."""
    scaled = amount * 100
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{amount} has fractional minor units; round it explicitly first")
    return int(scaled)
