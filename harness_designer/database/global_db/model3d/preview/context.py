# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

# QOpenGLWidget manages its own GL context automatically.
# This module is kept as a no-op shim so existing imports don't break.

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Preview as _Preview


class GLContext:
    """Compatibility shim - QOpenGLWidget manages context internally."""

    def __init__(self, canvas: "_Preview"):
        self.canvas = canvas

    @property
    def is_locked(self):
        return False

    def __enter__(self):
        self.canvas.makeCurrent()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.canvas.doneCurrent()
