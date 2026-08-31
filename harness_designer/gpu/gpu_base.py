# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared attribute-value holder for :mod:`harness_designer.gpu`."""
from .. import check_types as _check_types


class GPUAttribute:
    """Store a labeled GPU attribute value for display purposes.

    :param label: Prefix used when rendering the attribute as text.
    :type label: str
    """

    @_check_types.do
    def __init__(self, label):
        """Initialize the attribute with a display label.

        :param label: Prefix used when the value is converted to text.
        :type label: str
        """
        self.label = label
        self.value = 'Unknown'

    @_check_types.do
    def __str__(self):
        """Return the label and current value as a single string.

        :returns: Human-readable label/value text.
        :rtype: str
        """
        return self.label + str(self.value)
