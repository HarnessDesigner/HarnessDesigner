# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Intel GPU memory collection helpers for :mod:`harness_designer.gpu_mem`."""
from .. import check_types as _check_types


@_check_types.do
def collect():
    """Collect Intel GPU metrics.

    The current implementation does not populate any values.

    :returns: ``None``.
    :rtype: None
    """
    pass
