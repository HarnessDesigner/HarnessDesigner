# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared base for every per-drag stateful handler, across every editor.

A concrete drag handler is constructed fresh at the moment a drag is
armed (one instance per drag, never reused across drags), called once
per mouse-move for the drag's duration, and torn down via :meth:`delete`
the moment the drag ends (commit or abort) -- same construct/call/
destroy lifecycle already proven by
:class:`~harness_designer.gl.canvas_3d.dragging.base.DragObjectBase`.

This class only holds what's genuinely identical no matter which editor
or object type is being dragged: a reference to the canvas and the
object being dragged. Everything that actually differs by *view*
(screen<->world projection math, axis locking, whether a move-arrows
gizmo exists at all) belongs on that editor's own intermediate base --
see :mod:`~.editor_3d`, :mod:`~.editor_schematic`,
:mod:`~.editor_pegboard` -- not here.
"""

from typing import TYPE_CHECKING

from ..geometry import point as _point
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..gl.canvas_base import canvas_base as _canvas_base
    from .. import objects as _objects
    from ..gl import shaders as _shaders


class DragHandlerBase:
    """Base class for every per-drag stateful handler.

    See the module docstring for the full lifecycle rationale.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas_base.CanvasBase", target: "_objects.ObjectBase"):
        """Initialise the :class:`DragHandlerBase` instance.

        :param canvas: The canvas this drag is happening on.
        :param target: The object being dragged.
        """
        self.canvas = canvas
        self.target = target

    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:
        """Apply one mouse-move event's worth of movement.

        *mouse_pos* is the real, absolute current screen-space cursor
        position -- always the caller's actual mouse position, never
        reconstructed/approximated from an object's own (possibly axis-
        locked, possibly snapped) tracked position. Anything that needs
        to know "where is the cursor right now" (e.g. hit-testing a snap
        probe) must use *mouse_pos* directly, not derive it from *delta*
        plus a stored anchor -- an axis-locked object's own screen
        position drifts away from the real cursor trail over the course
        of a drag, so reconstructing from it accumulates error the real
        position never has.

        Must be overridden -- what *delta* even means (a raw screen-space
        pixel delta vs. an already-resolved world position) is left to
        each editor's own intermediate base, since that's exactly where
        the projection math differs by view.
        """
        raise NotImplementedError

    @_check_types.do
    def delete(self) -> None:
        """End this drag -- release whatever this handler acquired
        (a gizmo, snap probes, an overlay, a cached collision-candidate
        list, ...).

        Called exactly once, on both a normal commit and an abort -- no
        distinction is made here. Default: no-op.
        """
        pass

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        """Render whatever visual aid this drag owns (a gizmo, an
        overlay, ...), called via ``BaseVar.render_handler()`` -- see
        that method's own docstring. Default: no-op, for every drag that
        has nothing of its own to draw (every 2D-editor drag -- a locked
        top-down projection has no ambiguous axis to lock, so there's no
        move-arrows-equivalent gizmo to show -- see
        :mod:`~.editor_schematic`/:mod:`~.editor_pegboard`'s own module
        docstrings). :class:`~.editor_3d.DragHandler3D` overrides this
        with real logic (the move-arrows axis-lock gizmo).
        """
        pass
