# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Camera for the Peg Board Editor.

Re-exports :class:`Camera2D` from :mod:`harness_designer.gl.canvas2d.camera`
unchanged. It is a generic top-down orthographic camera (focal position +
distance-based zoom, screen/world conversion via a fixed distance/1000.0
world-per-pixel convention) with nothing schematic-2D specific -- the peg
board canvas reuses it directly instead of subclassing or copying it, so
that other ``canvas_pegboard`` modules can ``from . import camera`` without
caring that the implementation actually lives in ``canvas2d``.
"""

from ..canvas2d import camera as _camera2d


Camera2D = _camera2d.Camera2D


del _camera2d
