from decimal import Decimal

import pytest

from apps.platform.money import quantize_money


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("10.005", "10.01"),
        ("10.004", "10.00"),
        ("0.999", "1.00"),
    ],
)
def test_quantize_money_rounds_half_up(raw, expected):
    assert quantize_money(Decimal(raw)) == Decimal(expected)


def test_quantize_money_rejects_float_input():
    with pytest.raises(TypeError):
        quantize_money(1.0)
