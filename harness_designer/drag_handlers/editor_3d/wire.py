# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Segment-local drag for a Wire in the 3D editor.

Thin, view-specific shell around
:class:`~harness_designer.handlers.wire_drag_base.WireDragMixin` -- the
whole planning/drag/live-snap-preview algorithm lives there exactly
once, shared with the peg-board editor's own drag handler (see that
module's docstring for the full behavioral rule and rationale,
including why the mixin is combined here via explicit, never-``super()``
dispatch in :meth:`Wire.__init__`/:meth:`Wire.delete` rather than
cooperative MRO chaining). Everything here beyond that is just the
small set of "which object/editor/column belongs to this view"
accessors :class:`~.WireDragMixin` requires every concrete subclass to
override, plus the one thing that's genuinely 3D-only: locking the raw
projected delta to whichever axis dominates once the drag settles
(:meth:`Wire._move_delta`, delegating to
:class:`~harness_designer.drag_handlers.editor_3d.DragHandler3D`'s own
``_axis_locked_delta3d`` -- the peg-board's locked top-down ortho camera
is never ambiguous the way 3D's free-orbit camera is, so it needs no
such lock at all and just uses :class:`~.WireDragMixin`'s own unlocked
default).

Ported from :class:`~harness_designer.gl.canvas_3d.dragging.wire.WireDragObject`
(proven, working code from before this package existed) -- only import
paths and the base class changed; the algorithm itself is unchanged.

The module-level :func:`is_anchor_point`/:func:`wire_end_anchors`/
:func:`plan_wire_drag`/:data:`WireDragPlan` names below are kept as
thin delegates to :class:`Wire`'s own (now-shared) classmethods, not
duplicated implementations -- :mod:`~harness_designer.handlers.
wire_snap` and :mod:`~harness_designer.handlers.wire_handler` both
import and call ``wire_end_anchors`` this way already, and that call
site's own documented semantics ("checked via the 3D endpoints
regardless of *view* -- a project-wide topology fact, not a per-view
rendering detail") is exactly what :class:`Wire`'s own 3D-specific
accessor overrides already produce, so nothing about that behavior
changes here.
"""

from typing import TYPE_CHECKING

from ...geometry import point as _point
from ...handlers import wire_drag_base as _wire_drag_base
from .. import editor_3d as _editor_3d
from ... import check_types as _check_types
from . import wire_snap as _wire_snap


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ...objects import project as _project
    from ...objects import wire as _wire_object


class Wire(_editor_3d.DragHandler3D, _wire_drag_base.WireDragMixin):
    """Segment-local drag for a Wire -- moves only the one or two path
    points (true end or interior waypoint) bounding the segment nearest
    the click, computed once at construction time by
    :meth:`WireDragMixin.plan_wire_drag`; see
    :mod:`~harness_designer.handlers.wire_drag_base`'s own module
    docstring for the full rule. Also builds an invisible snap-probe set
    when the plan's moving point is snap-eligible -- see that same
    module's docstring.
    """

    _SnapProbeSet = _wire_snap.SnapProbeSet

    @staticmethod
    def _get_view_object(obj: "_wire_object.Wire"):
        return obj.obj3d

    @staticmethod
    def _get_editor(mainframe):
        return mainframe.editor3d.editor._canvas  # NOQA

    @staticmethod
    def _points_table(project: "_project.Project"):
        return project.ptables.pjt_points3d_table

    @staticmethod
    def _waypoints(wire_db_obj):
        return wire_db_obj.waypoints3d

    @staticmethod
    def _wire_position_id_raw(obj) -> bytes | None:
        return obj.wire_position3d_id_raw

    @staticmethod
    def _attach_position_id_raw(obj) -> bytes | None:
        return obj.attach_position3d_id_raw

    @staticmethod
    def _get_start_position_id(wire_db_obj) -> bytes | None:
        return wire_db_obj.start_position3d_id

    @staticmethod
    def _set_start_position_id(wire_db_obj, value: bytes | None) -> None:
        wire_db_obj.start_position3d_id = value

    @staticmethod
    def _get_stop_position_id(wire_db_obj) -> bytes | None:
        return wire_db_obj.stop_position3d_id

    @staticmethod
    def _set_stop_position_id(wire_db_obj, value: bytes | None) -> None:
        wire_db_obj.stop_position3d_id = value

    @staticmethod
    def _layout_position_id(layout_db_obj) -> bytes | None:
        return layout_db_obj.position3d_id

    @staticmethod
    def _is_in_view(obj) -> bool:
        return obj.is_in_3dview

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_wire_object.Wire",
                 plan: _wire_drag_base.WireDragPlan):
        # Explicit, never super() -- see handlers.wire_drag_base's own
        # module docstring on why: a bare super() call here would only
        # stay correct for as long as DragHandler3D and WireDragMixin
        # never happen to gain a same-named method, and nothing
        # enforces that. Calling each one by its own name is correct
        # regardless of base-class order or any future change to
        # either class -- confirmed empirically, several ways,
        # 2026-09-13.
        _editor_3d.DragHandler3D.__init__(self, canvas, target)
        self._arm_drag(canvas, target, plan)

    @_check_types.do
    def delete(self) -> None:
        self._disarm_drag()
        _editor_3d.DragHandler3D.delete(self)

    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:
        # Explicit, never a bare inherited lookup -- DragHandler3D's own
        # ancestor DragHandlerBase also defines __call__ (as an
        # unconditional NotImplementedError, meant to be overridden per
        # concrete handler), and it sits before WireDragMixin in this
        # class's MRO since DragHandler3D is listed first in the class
        # statement. Relying on plain inheritance to find __call__ would
        # resolve to DragHandlerBase's NotImplementedError instead of
        # WireDragMixin's real logic -- confirmed live, 2026-09-13. Same
        # rule as __init__/delete above.
        _wire_drag_base.WireDragMixin.__call__(self, delta, mouse_pos)

    @_check_types.do
    def _move_delta(self, anchor: _point.Point, last_pos: _point.Point, delta, aabb):
        """3D's free-orbit camera makes a raw screen delta ambiguous
        (it could mean movement along any of X/Y/Z) -- lock to whichever
        axis dominates once the drag settles, same as every other 3D
        drag (see ``DragHandler3D._axis_locked_delta3d``). *aabb* sizes
        the move-arrows gizmo created the moment the axis locks in.
        """
        return self._axis_locked_delta3d(anchor, last_pos, delta, aabb)


# ----------------------------------------------------------------------
# Backward-compatible module-level names -- see the module docstring.
# ----------------------------------------------------------------------

WireDragPlan = _wire_drag_base.WireDragPlan
