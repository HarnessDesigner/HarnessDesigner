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

from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..gl.canvas_base import canvas_base as _canvas_base
    from .. import objects as _objects


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
