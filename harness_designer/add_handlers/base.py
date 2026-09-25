# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared base for every per-add-session stateful handler, across every
editor.

Mirrors :class:`~harness_designer.drag_handlers.base.DragHandlerBase`'s
own construct/call/destroy lifecycle -- a concrete add handler is
constructed by the object's own ``start_add`` classmethod (see e.g.
``objects.objects_3d.wire.Wire.start_add``) the moment placement begins,
attached to that view instance's own ``_active_handler`` (the same slot
drag/rotation handlers use -- see ``objectsvar.base_var.BaseVar.
handle_interaction``), called once per relevant mouse event for the
session's duration, and torn down via :meth:`delete` once placement
finishes (committed or cancelled).

Unlike a drag handler's narrow ``__call__(delta, mouse_pos)``, an add
session is a genuine multi-step interaction (hover preview, click to
commit a point, right-click to finish early, Escape to cancel outright)
spanning many separate mouse gestures rather than one continuous drag --
so it receives the exact same arguments its owning view object's own
``handle_interaction`` was called with, unpacked instead of repackaged,
and returns the same True/False "did I consume this" contract.
"""

from typing import TYPE_CHECKING

from ..gl.canvas_base import interaction as _interaction
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..geometry import point as _point
    from ..gl.canvas_base import canvas_base as _canvas_base
    from .. import objects as _objects
    from ..gl import shaders as _shaders


class AddHandlerBase:
    """Base class for every per-add-session stateful handler.

    See the module docstring for the full lifecycle rationale.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas_base.CanvasBase", target: "_objects.ObjectBase"):
        """Initialise the :class:`AddHandlerBase` instance.

        :param canvas: The canvas this add session is happening on.
        :param target: The preview object being placed -- already a
            real, fully-constructed facade (all 3 views built together,
            per the usual pattern) by the time this runs; never deleted
            and recreated mid-session, only ever mutated in place.
        """
        self.canvas = canvas
        self.target = target

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        """Whether this session has completed (committed or cancelled) --
        checked by the owning view object's own ``handle_interaction``
        after a ``True``-returning call, to decide whether to clear its
        own ``_active_handler`` back to ``None``. Override to track real
        state; default assumes a single ``__call__`` always finishes it
        (fine for a one-shot placement, wrong for anything session-like).
        """
        return True

    @_check_types.do
    def __call__(
        self, last_pos, current_pos, had_motion: bool, interaction_type, clicked_object
    ) -> bool:
        """Handle one mouse event for this session. Must be overridden --
        see :meth:`objectsvar.base_var.BaseVar.handle_interaction` for
        what each argument means; this receives exactly what that
        received.
        """
        raise NotImplementedError

    @_check_types.do
    def delete(self) -> None:
        """End this add session -- release whatever this handler
        acquired (snap probes, an overlay, ...). Called exactly once,
        on both a normal finish and a cancel -- no distinction is made
        here. Default: no-op.
        """
        pass

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        """Render whatever visual aid this add session owns, called via
        ``BaseVar.render_handler()`` the same as a drag/rotation handler
        -- see :meth:`drag_handlers.base.DragHandlerBase.render`'s own
        docstring for the full calling contract. Default: no-op, for
        every add session with nothing of its own to draw (the
        in-progress preview object itself already renders through the
        normal per-object pipeline, not here). Override only where an
        add session needs its own extra overlay (a snap highlight, a
        placement guide, ...).
        """
        pass


@_check_types.do
def click_at(canvas: "_canvas_base.CanvasBase", view_obj: object, mouse_pos: "_point.Point") -> None:
    """Replay a mouse move + left click at *mouse_pos* into the add session
    just armed on *view_obj* (see each object's own ``start_add``), exactly
    as the canvas would have delivered them, then release the canvas's
    active-handler pointer if that click finished the session.

    Used by the empty-space right-click menus, where the position of the
    right click is where the new object goes: a one-click placement (a
    housing) finishes right here, a multi-click one (a wire) is left armed
    at its next step.
    """
    for interaction in (_interaction.MouseInteraction.MOVE, _interaction.MouseInteraction.LEFT_UP):
        view_obj.handle_interaction(mouse_pos, mouse_pos, False, interaction, None)

    if view_obj._active_handler is None and canvas.active_handler_obj is view_obj:  # NOQA
        canvas.active_handler_obj = None
