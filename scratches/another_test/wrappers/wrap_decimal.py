

from decimal import Decimal as _Decimal


class Decimal(_Decimal):
    """
    Wrapper around `decimal.Decimal` that allows me to pass floats
    to the constructor instead if having to pass strings
    """

    def __new__(cls, value, *args, **kwargs):
        value = str(float(value))

        return super().__new__(cls, value, *args, **kwargs)


_decimal = Decimal

TEN_0 = _decimal(10.0)
ZERO_1 = _decimal(0.1)
