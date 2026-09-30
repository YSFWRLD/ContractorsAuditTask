import pytest

from contractor_audit.shared.findings import InvoiceResult


def _result(**overrides):
    fields = dict(
        invoice_id="PA-00001",
        flagged=False,
        billed_total_cents=26512389,
        expected_total_cents=26512389,
        confidence=0.9,
    )
    fields.update(overrides)
    return InvoiceResult(**fields)


def test_unflagged_result_is_valid():
    assert _result().error_category == ""


def test_flagged_result_requires_category():
    with pytest.raises(ValueError):
        _result(flagged=True)
    assert _result(flagged=True, error_category="superseded_rate").flagged


def test_unflagged_result_must_not_carry_category():
    with pytest.raises(ValueError):
        _result(error_category="superseded_rate")


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_bounds(confidence):
    with pytest.raises(ValueError):
        _result(confidence=confidence)


def test_amounts_must_be_integer_minor_units():
    with pytest.raises(TypeError):
        _result(expected_total_cents=265123.89)
    assert _result(expected_total_cents=None).expected_total_cents is None
