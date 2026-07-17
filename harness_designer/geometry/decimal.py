# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Decimal helpers for geometry calculations."""
from typing import Union

from decimal import Decimal as _Decimal, Context as _Context


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

    def __new__(cls, value: Union["Decimal", int, float, str], *args, **kwargs):
        """
        Create a :class:`Decimal` from a value coerced through ``float``.

        :param value: Source value to convert.
        :type value: int | float | str | :class:`Decimal`
        :param args: Additional positional arguments forwarded to :class:`decimal.Decimal`.
        :type args: tuple
        :param kwargs: Additional keyword arguments forwarded to :class:`decimal.Decimal`.
        :type kwargs: dict
        :returns: New wrapped decimal value.
        :rtype: :class:`Decimal`
        """

        value = str(float(value))

        return super().__new__(cls, value, *args, **kwargs)

    def __ipow__(self, power: Union["Decimal", int, float], modulo=None):
        """
        Return ``self`` raised to ``power`` as :class:`Decimal`.

        :param power: Exponent value.
        :type power: int | float | :class:`Decimal`
        :param modulo: Optional modulo passed to :meth:`decimal.Decimal.__pow__`.
        :type modulo: object | None
        :returns: Wrapped power result.
        :rtype: :class:`Decimal`
        """

        power = Decimal(power)
        return Decimal(_Decimal.__pow__(self, power, modulo))

    def __pow__(self, power: Union["Decimal", int, float], modulo=None):
        """
        Return ``self`` raised to ``power``.

        :param power: Exponent value.
        :type power: int | float | :class:`Decimal`
        :param modulo: Optional modulo passed to :meth:`decimal.Decimal.__pow__`.
        :type modulo: object | None
        :returns: Wrapped power result.
        :rtype: :class:`Decimal`
        """

        power = Decimal(power)
        return Decimal(_Decimal.__pow__(self, power, modulo))

    def __rpow__(self, __value: Union["Decimal", int, float],
                 __mod: _Context | None = None) -> "Decimal":

        """
        Return ``other`` raised to ``self``.

        :param __value: Base value.
        :type __value: int | float | :class:`Decimal`
        :param __mod: UNKNOWN
        :type __mod: :class:`_Context` | None
        :returns: Wrapped power result.
        :rtype: :class:`Decimal`
        """

        other = Decimal(__value)
        return Decimal(_Decimal.__rpow__(self, other, __mod))

    def __neg__(self):
        """
        Return the negation of ``self``.

        :returns: Wrapped negation.
        :rtype: :class:`Decimal`
        """

        return Decimal(_Decimal.__neg__(self))

    def __pos__(self):
        """
        Return ``self`` unary-plussed (normalized per :class:`decimal.Decimal` rules).

        :returns: Wrapped result.
        :rtype: :class:`Decimal`
        """

        return Decimal(_Decimal.__pos__(self))

    def __abs__(self):
        """
        Return the absolute value of ``self``.

        :returns: Wrapped absolute value.
        :rtype: :class:`Decimal`
        """

        return Decimal(_Decimal.__abs__(self))

    def __iadd__(self, other: Union["Decimal", int, float]):
        """
        Return the sum of ``self`` and ``other``.

        :param other: Value to add.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped sum.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__add__(self, other))

    def __add__(self, other: Union["Decimal", int, float]):
        """
        Return the sum of ``self`` and ``other``.

        :param other: Value to add.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped sum.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__add__(self, other))

    def __radd__(self, other: Union["Decimal", int, float]):
        """
        Return the sum of ``other`` and ``self``.

        :param other: Value to add.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped sum.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__radd__(self, other))

    def __isub__(self, other: Union["Decimal", int, float]):
        """
        Return the difference of ``self`` and ``other``.

        :param other: Value to subtract.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped difference.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__sub__(self, other))

    def __sub__(self, other: Union["Decimal", int, float]):
        """
        Return the difference of ``self`` and ``other``.

        :param other: Value to subtract.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped difference.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__sub__(self, other))

    def __rsub__(self, other: Union["Decimal", int, float]):
        """
        Return the difference of ``other`` and ``self``.

        :param other: Value to subtract from.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped difference.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__rsub__(self, other))

    def __imul__(self, other: Union["Decimal", int, float]):
        """
        Return the product of ``self`` and ``other``.

        :param other: Value to multiply by.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped product.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__mul__(self, other))

    def __mul__(self, other: Union["Decimal", int, float]):
        """
        Return the product of ``self`` and ``other``.

        :param other: Value to multiply by.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped product.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__mul__(self, other))

    def __rmul__(self, other: Union["Decimal", int, float]):
        """
        Return the product of ``other`` and ``self``.

        :param other: Value to multiply by.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped product.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__rmul__(self, other))

    def __itruediv__(self, other: Union["Decimal", int, float]):
        """
        Return the quotient of ``self`` and ``other``.

        :param other: Divisor value.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped quotient.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__truediv__(self, other))

    def __truediv__(self, other: Union["Decimal", int, float]):
        """
        Return the quotient of ``self`` and ``other``.

        :param other: Divisor value.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped quotient.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__truediv__(self, other))

    def __rtruediv__(self, other: Union["Decimal", int, float]):
        """
        Return the quotient of ``other`` and ``self``.

        :param other: Dividend value.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped quotient.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__rtruediv__(self, other))

    def __ifloordiv__(self, other: Union["Decimal", int, float]):
        """
        Return the floor-division result of ``self`` and ``other``.

        :param other: Divisor value.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped floor-division result.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__floordiv__(self, other))

    def __floordiv__(self, other: Union["Decimal", int, float]):
        """
        eturn the floor-division result of ``self`` and ``other``.

        :param other: Divisor value.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped floor-division result.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__floordiv__(self, other))

    def __rfloordiv__(self, other: Union["Decimal", int, float]):
        """
        Return the floor-division result of ``other`` and ``self``.

        :param other: Dividend value.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped floor-division result.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__rfloordiv__(self, other))

    def __imod__(self, other: Union["Decimal", int, float]):
        """
        Return ``self`` modulo ``other``.

        :param other: Divisor value.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped modulo result.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__mod__(self, other))

    def __mod__(self, other: Union["Decimal", int, float]):
        """
        Return ``self`` modulo ``other``.

        :param other: Divisor value.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped modulo result.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__mod__(self, other))

    def __rmod__(self, other: Union["Decimal", int, float]):
        """
        Return ``other`` modulo ``self``.

        :param other: Dividend value.
        :type other: int | float | :class:`Decimal`
        :returns: Wrapped modulo result.
        :rtype: :class:`Decimal`
        """

        other = Decimal(other)
        return Decimal(_Decimal.__rmod__(self, other))
