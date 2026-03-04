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

    def __ipow__(self, power, modulo=None):
        power = Decimal(power)
        return Decimal(_Decimal.__pow__(self, power, modulo))

    def __pow__(self, power, modulo=None):
        power = Decimal(power)
        return Decimal(_Decimal.__pow__(self, power, modulo))

    def __rpow__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__rpow__(self, other))

    def __iadd__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__add__(self, other))

    def __add__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__add__(self, other))

    def __radd__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__radd__(self, other))

    def __isub__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__sub__(self, other))

    def __sub__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__sub__(self, other))

    def __rsub__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__rsub__(self, other))

    def __imul__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__mul__(self, other))

    def __mul__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__mul__(self, other))

    def __rmul__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__rmul__(self, other))

    def __itruediv__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__truediv__(self, other))

    def __truediv__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__truediv__(self, other))

    def __rtruediv__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__rtruediv__(self, other))

    def __ifloordiv__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__floordiv__(self, other))

    def __floordiv__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__floordiv__(self, other))

    def __rfloordiv__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__rfloordiv__(self, other))

    def __imod__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__mod__(self, other))

    def __mod__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__mod__(self, other))

    def __rmod__(self, other):
        other = Decimal(other)
        return Decimal(_Decimal.__rmod__(self, other))
