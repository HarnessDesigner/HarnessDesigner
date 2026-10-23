# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Intel GPU metrics backend for :mod:`harness_designer.gpu`.

No vendor SDK exists for Intel in this codebase (unlike NVIDIA/AMD, there
is no equivalent of ``nvapi``/``pyamd_adl`` to wrap) -- everything Intel
gets comes from :mod:`..gl_meminfo`'s GL/table-based fallback instead (see
:mod:`..gpu`, which uses that path as Intel's *primary* source, not a
fallback of one). This class exists only as a placeholder should a real
Intel SDK get integrated later; every attribute currently stays at
:class:`..backend_base.GPUBackend`'s default.
"""

from ..backend_base import GPUBackend
from ... import check_types as _check_types


class IntelBackend(GPUBackend):
    """Reserved for a future Intel-specific SDK. Currently a no-op."""

    @_check_types.do
    def __init__(self):
        pass
