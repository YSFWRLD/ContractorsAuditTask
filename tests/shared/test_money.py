from decimal import Decimal

import pytest

from contractor_audit.shared.money import parse_amount, to_minor_units


def test_readme_example_converts_to_minor_units():
    assert to_minor_units(parse_amount("265123.89")) == 26512389


def test_zero_and_whole_amounts():
    assert to_minor_units(parse_amount("0.00")) == 0
    assert to_minor_units(Decimal("420000")) == 42000000


def test_fractional_minor_units_are_refused():
    with pytest.raises(ValueError):
        to_minor_units(Decimal("1.005"))


@pytest.mark.parametrize("text", ["", "abc", "NaN", "Infinity"])
def test_parse_amount_rejects_non_amounts(text):
    with pytest.raises(ValueError):
        parse_amount(text)
