from decimal import Decimal as _Decimal


class Decimal(_Decimal):
    """
    Wrapper class around decimal.Decimal

    This class converts any input value to a string so proper calculations
    are able to be done. How it works by default doesn't allow for proper
    calculations when the input is either an integer or a float.

    >>> import decimal
    >>> print(repr(decimal.Decimal(0.1))

    has the output of
    `Decimal('0.1000000000000000055511151231257827021181583404541015625')`

    This wrapper fixes that issue.
    """

    def __new__(cls, value, *args, **kwargs):
        value = str(float(value))

        return super().__new__(cls, value, *args, **kwargs)


del _Decimal
