# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Decimal helpers for geometry calculations."""

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
        """Create a :class:`Decimal` from a value coerced through ``float``.

        :param value: Source value to convert.
        :type value: object
        :param args: Additional positional arguments forwarded to :class:`decimal.Decimal`.
        :type args: tuple
        :param kwargs: Additional keyword arguments forwarded to :class:`decimal.Decimal`.
        :type kwargs: dict
        :returns: New wrapped decimal value.
        :rtype: :class:`Decimal`
        """
        value = str(float(value))

        return super().__new__(cls, value, *args, **kwargs)

    def __ipow__(self, power, modulo=None):
        """Return ``self`` raised to ``power`` as :class:`Decimal`.

        :param power: Exponent value.
        :type power: object
        :param modulo: Optional modulo passed to :meth:`decimal.Decimal.__pow__`.
        :type modulo: object | None
        :returns: Wrapped power result.
        :rtype: :class:`Decimal`
        """
        power = Decimal(power)
        return Decimal(_Decimal.__pow__(self, power, modulo))

    def __pow__(self, power, modulo=None):
        """Return ``self`` raised to ``power``.

        :param power: Exponent value.
        :type power: object
        :param modulo: Optional modulo passed to :meth:`decimal.Decimal.__pow__`.
        :type modulo: object | None
        :returns: Wrapped power result.
        :rtype: :class:`Decimal`
        """
        power = Decimal(power)
        return Decimal(_Decimal.__pow__(self, power, modulo))

    def __rpow__(self, other):
        """Return ``other`` raised to ``self``.

        :param other: Base value.
        :type other: object
        :returns: Wrapped power result.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__rpow__(self, other))

    def __iadd__(self, other):
        """Return the sum of ``self`` and ``other``.

        :param other: Value to add.
        :type other: object
        :returns: Wrapped sum.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__add__(self, other))

    def __add__(self, other):
        """Return the sum of ``self`` and ``other``.

        :param other: Value to add.
        :type other: object
        :returns: Wrapped sum.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__add__(self, other))

    def __radd__(self, other):
        """Return the sum of ``other`` and ``self``.

        :param other: Value to add.
        :type other: object
        :returns: Wrapped sum.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__radd__(self, other))

    def __isub__(self, other):
        """Return the difference of ``self`` and ``other``.

        :param other: Value to subtract.
        :type other: object
        :returns: Wrapped difference.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__sub__(self, other))

    def __sub__(self, other):
        """Return the difference of ``self`` and ``other``.

        :param other: Value to subtract.
        :type other: object
        :returns: Wrapped difference.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__sub__(self, other))

    def __rsub__(self, other):
        """Return the difference of ``other`` and ``self``.

        :param other: Value to subtract from.
        :type other: object
        :returns: Wrapped difference.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__rsub__(self, other))

    def __imul__(self, other):
        """Return the product of ``self`` and ``other``.

        :param other: Value to multiply by.
        :type other: object
        :returns: Wrapped product.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__mul__(self, other))

    def __mul__(self, other):
        """Return the product of ``self`` and ``other``.

        :param other: Value to multiply by.
        :type other: object
        :returns: Wrapped product.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__mul__(self, other))

    def __rmul__(self, other):
        """Return the product of ``other`` and ``self``.

        :param other: Value to multiply by.
        :type other: object
        :returns: Wrapped product.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__rmul__(self, other))

    def __itruediv__(self, other):
        """Return the quotient of ``self`` and ``other``.

        :param other: Divisor value.
        :type other: object
        :returns: Wrapped quotient.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__truediv__(self, other))

    def __truediv__(self, other):
        """Return the quotient of ``self`` and ``other``.

        :param other: Divisor value.
        :type other: object
        :returns: Wrapped quotient.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__truediv__(self, other))

    def __rtruediv__(self, other):
        """Return the quotient of ``other`` and ``self``.

        :param other: Dividend value.
        :type other: object
        :returns: Wrapped quotient.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__rtruediv__(self, other))

    def __ifloordiv__(self, other):
        """Return the floor-division result of ``self`` and ``other``.

        :param other: Divisor value.
        :type other: object
        :returns: Wrapped floor-division result.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__floordiv__(self, other))

    def __floordiv__(self, other):
        """Return the floor-division result of ``self`` and ``other``.

        :param other: Divisor value.
        :type other: object
        :returns: Wrapped floor-division result.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__floordiv__(self, other))

    def __rfloordiv__(self, other):
        """Return the floor-division result of ``other`` and ``self``.

        :param other: Dividend value.
        :type other: object
        :returns: Wrapped floor-division result.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__rfloordiv__(self, other))

    def __imod__(self, other):
        """Return ``self`` modulo ``other``.

        :param other: Divisor value.
        :type other: object
        :returns: Wrapped modulo result.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__mod__(self, other))

    def __mod__(self, other):
        """Return ``self`` modulo ``other``.

        :param other: Divisor value.
        :type other: object
        :returns: Wrapped modulo result.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__mod__(self, other))

    def __rmod__(self, other):
        """Return ``other`` modulo ``self``.

        :param other: Dividend value.
        :type other: object
        :returns: Wrapped modulo result.
        :rtype: :class:`Decimal`
        """
        other = Decimal(other)
        return Decimal(_Decimal.__rmod__(self, other))
