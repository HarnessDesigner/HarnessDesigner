# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Public entry points for the ray-tracing subsystem.

The package currently re-exports
:class:`harness_designer.ray_tracing.dialog.RayTracingDialog`.
"""

from . import dialog as _dialog


RayTracingDialog = _dialog.RayTracingDialog


del _dialog
