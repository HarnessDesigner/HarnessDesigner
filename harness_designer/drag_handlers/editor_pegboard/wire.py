# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Segment-local drag for a Wire in the peg-board editor.

Thin, view-specific shell around
:class:`~harness_designer.handlers.wire_drag_base.WireDragMixin` -- the
whole planning/drag/live-snap-preview algorithm lives there exactly
once, shared with the 3D editor's own drag handler (see that module's
docstring for the full behavioral rule and rationale, including why
the mixin is combined here via explicit, never-``super()`` dispatch in
:meth:`Wire.__init__`/:meth:`Wire.delete` rather than cooperative MRO
chaining). Everything here beyond that is just the small set of "which
object/editor/column belongs to this view" accessors
:class:`~.WireDragMixin` requires every concrete subclass to override
-- never ``getattr``/duck-typing, so IDE navigation and static type-
checking still work.

**Known gap (2026-09-13, narrowed):** finalizing a live in-drag snap
into a real connection on mouse-up works here now for a snap onto
another wire's own dangling end (``handlers.wire_snap.commit_snap``'s
wire-end case reaches ``WireDragMixin.merge_wire_into``, which merges
peg-board geometry too) -- but a snap onto a TERMINAL or SPLICE still
is not: ``Terminal.add_wire``/``Splice.add_wire`` and ``commit_snap``'s
own splice branch remain 3D/2D-only -- see
:mod:`~harness_designer.handlers.wire_drag_base`'s own module docstring.
The live teleport-onto-a-probe this class drives during the drag itself
already works for every snap kind (:class:`~.wire_snap.SnapProbeSet`
builds probes at ``*_position_pegboard``); only committing a
terminal/splice snap on release does not yet.
"""

from typing import TYPE_CHECKING

from ...handlers import wire_drag_base as _wire_drag_base
from .. import editor_pegboard as _editor_pegboard
from ... import check_types as _check_types
from . import wire_snap as _wire_snap


if TYPE_CHECKING:
    from ...objects import project as _project
    from ...objects import wire as _wire_object
    from ...geometry import point as _point
    from ...database.project_db import pjt_wire as _pjt_wire
    from ...gl.canvas_pegboard import canvas as _canvas
    from ... import ui as _ui


class Wire(_editor_pegboard.DragHandlerPegboard, _wire_drag_base.WireDragMixin):
    """Segment-local drag for a Wire in the peg-board editor -- see the
    module docstring. All planning/drag/snap mechanics come from
    :class:`~harness_designer.handlers.wire_drag_base.WireDragMixin`;
    this class only supplies the peg-board-specific accessors it
    requires plus its own explicit ``__init__``/``delete``.
    """

    _SnapProbeSet = _wire_snap.SnapProbeSet

    @staticmethod
    def _get_view_object(obj: "_wire_object.Wire"):
        return obj.objpegboard

    @staticmethod
    def _get_editor(mainframe: "_ui.MainFrame"):
        return mainframe.editor_pegboard.editor._canvas  # NOQA

    @staticmethod
    def _points_table(project: "_project.Project"):
        return project.ptables.pjt_points_pegboard_table

    @staticmethod
    def _waypoints(wire_db_obj: "_pjt_wire.PJTWire"):
        return wire_db_obj.waypoints_pegboard

    @staticmethod
    def _wire_position_id_raw(obj: "_wire_object.Wire") -> bytes | None:
        return obj.wire_position_pegboard_id_raw

    @staticmethod
    def _attach_position_id_raw(obj: "_wire_object.Wire") -> bytes | None:
        return obj.attach_position_pegboard_id_raw

    @staticmethod
    def _get_start_position_id(wire_db_obj: "_pjt_wire.PJTWire") -> bytes | None:
        return wire_db_obj.start_position_pegboard_id

    @staticmethod
    def _set_start_position_id(wire_db_obj: "_pjt_wire.PJTWire", value: bytes | None) -> None:
        wire_db_obj.start_position_pegboard_id = value

    @staticmethod
    def _get_stop_position_id(wire_db_obj: "_pjt_wire.PJTWire") -> bytes | None:
        return wire_db_obj.stop_position_pegboard_id

    @staticmethod
    def _set_stop_position_id(wire_db_obj: "_pjt_wire.PJTWire", value: bytes | None) -> None:
        wire_db_obj.stop_position_pegboard_id = value

    @staticmethod
    def _layout_position_id(layout_db_obj: object) -> bytes | None:
        return layout_db_obj.position_pegboard_id

    @staticmethod
    def _is_in_view(obj: "_wire_object.Wire") -> bool:
        return obj.is_in_pegboardview

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_wire_object.Wire",
                 plan: _wire_drag_base.WireDragPlan) -> None:
        # Explicit, never super() -- see handlers.wire_drag_base's own
        # module docstring on why: a bare super() call here would only
        # stay correct for as long as DragHandlerPegboard and
        # WireDragMixin never happen to gain a same-named method, and
        # nothing enforces that. Calling each one by its own name is
        # correct regardless of base-class order or any future change
        # to either class -- confirmed empirically, several ways,
        # 2026-09-13.
        #
        # DragHandlerPegboard.__init__ caches target.objpegboard.
        # touching_budgets() -- meaningful for a single-point anchor
        # drag, a harmless no-op here (a Wire has no single point3d_id
        # of its own, see objects_pegboard.wire.Wire's own docstring,
        # so that always returns []), not worth skipping.
        _editor_pegboard.DragHandlerPegboard.__init__(self, canvas, target)
        self._arm_drag(canvas, target, plan)

    @_check_types.do
    def delete(self) -> None:
        self._disarm_drag()
        _editor_pegboard.DragHandlerPegboard.delete(self)

    @_check_types.do
    def __call__(self, delta: object, mouse_pos: "_point.Point") -> None:
        # Explicit, never a bare inherited lookup -- DragHandlerPegboard's
        # own ancestor DragHandlerBase also defines __call__ (as an
        # unconditional NotImplementedError, meant to be overridden per
        # concrete handler), and it sits before WireDragMixin in this
        # class's MRO since DragHandlerPegboard is listed first in the
        # class statement. Relying on plain inheritance to find __call__
        # would resolve to DragHandlerBase's NotImplementedError instead
        # of WireDragMixin's real logic -- confirmed live (the 3D
        # editor's identical Wire class hit exactly this), 2026-09-13.
        # Same rule as __init__/delete above.
        _wire_drag_base.WireDragMixin.__call__(self, delta, mouse_pos)

    @_check_types.do
    def _move_delta(self, anchor: "_point.Point", last_pos: "_point.Point",
                     delta: object, aabb: object) -> "_point.Point":
        """Hard-lock Y to exactly 0, every frame -- do NOT rely on the
        peg-board's locked top-down ortho camera to keep it there on its
        own via :meth:`WireDragMixin._raw_move_delta`'s round trip
        through ``CameraBase.ProjectPoint``/``UnprojectPoint``: those
        share the same screen-space depth channel 3D's perspective
        camera uses, and X/Z (screen-plane) and Y (this camera's own
        viewing axis) are only decoupled there for a mathematically
        perfect top-down camera -- any float32 imprecision in that
        shared depth channel bleeds into world-space Y specifically, and
        because ``WireDragMixin.__call__`` accumulates ``move_delta``
        into ``self._anchor`` every frame (re-deriving depth fresh from
        THAT anchor next frame), an un-clamped Y drift compounds across
        a drag instead of staying a one-frame rounding error -- confirmed
        2026-09-13 as the actual mechanism behind a live bug report
        ("portions of the wire drop below the floor... extending to the
        opposite side of the layout, following the dragged point")—not a
        wrong-points-moved bug. This was the original, explicit design
        requirement for this view from the very start of this feature
        ("the Y axis will be locked to zero") -- the module docstring's
        claim that peg-board "needs no axis lock at all" undersold this:
        no *choice-of-axis* lock the way 3D needs, but Y still needs a
        hard floor against precision drift.
        """
        raw_delta = self._raw_move_delta(anchor, last_pos, delta)
        raw_delta.y = 0.0
        return raw_delta
