# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

# QOpenGLWidget manages its own GL context automatically.
# This module is kept as a no-op shim so existing imports don't break.

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Preview as _Preview


class GLContext:
    """Compatibility shim - QOpenGLWidget manages context internally."""

    def __init__(self, canvas: "_Preview"):
        """Initialise the :class:`GLContext` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: _Preview
        """
        self.canvas = canvas

    @property
    def is_locked(self):
        """Return the is locked.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return False

    def __enter__(self):
        """Enter the managed context.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.canvas.makeCurrent()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the managed context.

        UNKNOWN details are inferred from the callable name and signature.

        :param exc_type: Value for ``exc_type``.
        :type exc_type: UNKNOWN
        :param exc_val: Value for ``exc_val``.
        :type exc_val: UNKNOWN
        :param exc_tb: Value for ``exc_tb``.
        :type exc_tb: UNKNOWN
        """
        self.canvas.doneCurrent()
