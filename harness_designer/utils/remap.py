# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ..geometry.decimal import Decimal as _d


def remap(
    value: int | float | _d,
    old_min: int | float | _d, old_max: int | float | _d,
    new_min: int | float | _d, new_max: int | float | _d,
    type_=_d
) -> int | float | _d:

    """
    Remaps/Reranges a value from one range to another range.

    Lets say you have a value of 25 and that value fits into a range of 1-100.
    You need that value to fit into the 1-250 range but still be 25% of the range
    like it is in the 0-100 range. This is the function to use to do that.

    :param value: input value

    :param old_min: input value's minimum

    :param old_max: input values maximum
    :param new_min: new minimum
    :param new_max: new maximum
    :param type_: what type to return the value as; `int`, `float` or `Decimal`
    :return: The new value mapped to the new range
    """

    value = _d(value)
    old_min = _d(old_min)
    old_max = _d(old_max)
    new_min = _d(new_min)
    new_max = _d(new_max)

    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min

    return type_(new_value)
