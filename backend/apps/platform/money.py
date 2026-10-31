from decimal import Decimal, ROUND_HALF_UP

MONEY_QUANTUM = Decimal("0.01")


def quantize_money(value):
    if isinstance(value, float):
        raise TypeError("Money values must not be floats.")
    if not isinstance(value, Decimal):
        value = Decimal(value)
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
