# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Mouse pan/zoom/reset handling for the Peg Board Editor canvas.

Mirrors gl.canvas2d.mouse_handler.MouseHandler2D's button-mapping
(`_process_mouse`, reading config.pan.mouse / config.zoom.mouse /
config.reset.mouse bitmasks) and wheel-zoom handling (`on_mouse_wheel`)
verbatim -- that logic is generic mouse-button plumbing, not schematic-2D
specific.

Object hit-testing / selection (`_find_anchor_at_point`,
`_find_selected_anchor`, `on_left_down`) now mirrors MouseHandler2D's
click-to-select behavior: a click hit-tests `Canvas.anchors` (the
incrementally-maintained live list of `objects.objectspeg.
basepeg.BasePeg` anchors) and drives selection
through `objects.object_base.ObjectBase.set_selected()` exactly like every
other editor, so `mainframe._set_selected()` picks it up and syncs the
2D/3D editors automatically. Unlike MouseHandler2D, there is no separate
canvas-level `_selected` pointer here -- "which anchor is selected" is
derived live from `anchor.obj.is_selected` (`_find_selected_anchor`) so
this canvas stays in sync even when selection changes from the 2D/3D
editors, not just from clicks on this canvas.

What is deliberately NOT replicated here: MouseHandler2D's dragging
(`_drag_obj`) and its right-click context menu
(`_show_canvas_context_menu`). Dragging is a later phase's work, not this
task's scope. Every place that logic would plug in is marked below with
a "TODO: object drag hookup happens here..." comment for a later task to
fill in.

(For what it's worth: MouseHandler2D's own `_show_canvas_context_menu`
references `self.canvas.grid_enabled` / `set_snap_to_grid` / `set_grid` /
`self.canvas.camera.reset()`, none of which exist on
gl.canvas2d.canvas.Canvas or gl.canvas2d.camera.Camera2D -- only
`config.grid.enabled` / `set_grid_snap` / `set_grid_display` /
`camera.Reset()` do. That path is only reachable via a right-click hit on
a selected object, which doesn't happen for the peg board yet, so it's
not something this file needs to work around -- just noting it wasn't
copied forward.)
"""

import math
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtWidgets

from ... import config as _config
from ...geometry import point as _point
from .. import events as _events
from ..canvas3d.rotation_rings import (
    HANDLE_PICK_TOLERANCE, wrap_angle, validate_snap_angle)


if TYPE_CHECKING:
    from . import canvas as _canvas
    from . import layout_graph as _layout_graph
    from ...objects.objectspeg import basepeg as _basepeg


MOUSE_NONE = _config.MOUSE_NONE
MOUSE_LEFT = _config.MOUSE_LEFT
MOUSE_MIDDLE = _config.MOUSE_MIDDLE
MOUSE_RIGHT = _config.MOUSE_RIGHT
MOUSE_AUX1 = _config.MOUSE_AUX1
MOUSE_AUX2 = _config.MOUSE_AUX2
MOUSE_WHEEL = _config.MOUSE_WHEEL

MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS
MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS
MOUSE_REVERSE_WHEEL_AXIS = _config.MOUSE_REVERSE_WHEEL_AXIS
MOUSE_SWAP_AXIS = _config.MOUSE_SWAP_AXIS


def _qt_pos(qt_event) -> _point.Point:
    """Convert a Qt mouse event's position to a :class:`_point.Point`.

    :param qt_event: Qt mouse event.
    :type qt_event: UNKNOWN
    :returns: Screen-space position.
    :rtype: :class:`_point.Point`
    """
    p = qt_event.position().toPoint()
    return _point.Point(p.x(), p.y())


def _qt_buttons_flag(qt_event) -> int:
    """Convert Qt button flags to our BTN_* bitmask."""
    btns = qt_event.buttons()
    flags = _events.BTN_NONE
    if btns & QtCore.Qt.MouseButton.LeftButton:
        flags |= _events.BTN_LEFT
    if btns & QtCore.Qt.MouseButton.RightButton:
        flags |= _events.BTN_RIGHT
    if btns & QtCore.Qt.MouseButton.MiddleButton:
        flags |= _events.BTN_MIDDLE
    if btns & QtCore.Qt.MouseButton.XButton1:
        flags |= _events.BTN_AUX1
    if btns & QtCore.Qt.MouseButton.XButton2:
        flags |= _events.BTN_AUX2
    return flags


def _find_anchor_at_point(anchors: list, world_pos: _point.Point):
    """Hit-test *world_pos* against *anchors*, topmost-drawn-first.

    ``Camera2D.screen_to_world`` is a generic 2D (x, y) conversion -- on
    this canvas ``world_pos.y`` stands in for world Z (see
    ``Canvas._pegboard_projection_matrix``/``_render_objects``, which feed
    ``camera.y`` into the shader as the object's Z position). Anchors are
    tested in reverse build order (last-built == last-drawn == topmost),
    mirroring ``gl.canvas2d.mouse_handler.MouseHandler2D._get_object_at_point``'s
    ``reversed(self.canvas.objects)`` iteration.

    Hit-tests against ``anchor.aabb`` (the live world-space AABB
    ``BasePeg._compute_aabb`` maintains -- recomputed on every position/
    angle/scale mutation, and once a real mesh replaces an anchor's
    placeholder-box VBO via ``BasePeg._set_model``) rather than a
    separately cached half-width/half-depth pair, so hit-testing is never
    stale relative to what's actually rendered.

    :param anchors: The canvas's current anchor list.
    :type anchors: list[:class:`_basepeg.BasePeg`]
    :param world_pos: Click position in world coordinates.
    :type world_pos: :class:`_point.Point`
    :returns: The topmost anchor whose axis-aligned XZ footprint contains
        *world_pos*, or ``None``.
    :rtype: :class:`_basepeg.BasePeg` | None
    """
    click_x = world_pos.x
    click_z = world_pos.y

    for anchor in reversed(anchors):
        aabb = anchor.aabb
        if (
            aabb[0][0] <= click_x <= aabb[1][0] and
            aabb[0][2] <= click_z <= aabb[1][2]
        ):
            return anchor

    return None


# Fixed world-space (mm) hit-test radius for waypoints. Waypoints have no
# rendered mesh/footprint of their own (unlike anchors, which hit-test
# against a real axis-aligned XZ footprint derived from their mesh's live
# AABB -- see objects.objectspeg.basepeg.BasePeg.aabb) -- they are purely
# peg-board-only bend points, so a small fixed radius stands in for
# "footprint". World-space (not screen-space/pixels) was chosen to match
# how anchor hit-testing already works (_find_anchor_at_point's aabb is
# also world units): it keeps grabbability consistent with zoom level, whereas
# a fixed pixel radius would make waypoints effectively impossible to
# grab when zoomed out (shrinking below a pixel in world terms) and
# oddly huge relative to nearby geometry when zoomed way in.
_WAYPOINT_HIT_RADIUS_MM = 5.0


def _find_waypoint_at_point(nodes: list, world_pos: _point.Point,
                             radius: float = _WAYPOINT_HIT_RADIUS_MM):
    """Hit-test *world_pos* against every waypoint node in *nodes*.

    Only considers nodes with ``waypoint_id is not None`` (anchor nodes
    are hit-tested separately, by :func:`_find_anchor_at_point`, against
    their own real mesh footprint). Returns the *closest* waypoint within
    *radius*, not merely the first one found within it, since waypoints
    have no draw order to prioritize by (unlike anchors' "topmost drawn"
    convention).

    :param nodes: The canvas's current live node list (``Canvas.nodes``).
    :type nodes: list[:class:`_layout_graph.PegboardNode`]
    :param world_pos: Click position in world coordinates (``.y`` stands
        in for world Z, same convention as :func:`_find_anchor_at_point`).
    :type world_pos: :class:`_point.Point`
    :param radius: Hit-test radius, world units (mm).
    :type radius: float
    :returns: The closest waypoint node within *radius*, or ``None``.
    :rtype: :class:`_layout_graph.PegboardNode` | None
    """
    click_x = world_pos.x
    click_z = world_pos.y

    best = None
    best_dist_sq = radius * radius

    for node in nodes:
        if node.waypoint_id is None:
            continue

        dx = node.x - click_x
        dz = node.z - click_z
        dist_sq = dx * dx + dz * dz

        if dist_sq <= best_dist_sq:
            best_dist_sq = dist_sq
            best = node

    return best


def _find_selected_anchor(anchors: list):
    """Return whichever anchor's wrapped object is currently selected.

    Derived live from ``anchor.obj.is_selected`` on every call rather than
    tracked as a separate selected-anchor pointer on the canvas -- this
    keeps the peg board automatically in sync with selection changes made
    from the 2D/3D editors (see
    ``objects.object_base.ObjectBase.set_selected``), with no extra
    bookkeeping required when selection changes from elsewhere.

    :param anchors: The canvas's current anchor list.
    :type anchors: list[:class:`_basepeg.BasePeg`]
    :returns: The selected anchor, or ``None``.
    :rtype: :class:`_basepeg.BasePeg` | None
    """
    for anchor in anchors:
        if anchor.obj.is_selected:
            return anchor

    return None


def _find_table_point_at(anchors: list, world_pos: _point.Point):
    """Return whichever data-table anchor point is under *world_pos*, if any.

    Hit-tests against ``anchor.aabb`` first (same as
    :func:`_find_anchor_at_point`) to find which anchor's mesh was
    clicked, then -- since most anchor types have exactly one table point
    but a :class:`~harness_designer.objects.objectspeg.transition.Transition`
    has one per populated branch -- picks whichever of that anchor's own
    ``table_anchor_points`` lands nearest the click.

    :param anchors: The canvas's current anchor list.
    :type anchors: list[:class:`_basepeg.BasePeg`]
    :param world_pos: Click position in world coordinates.
    :type world_pos: :class:`_point.Point`
    :returns: ``(point3d_id, world_x, world_z, label)`` for the closest
        table point on the clicked anchor, or ``None``.
    :rtype: tuple[int, float, float, str] | None
    """
    anchor = _find_anchor_at_point(anchors, world_pos)
    if anchor is None:
        return None

    points = anchor.table_anchor_points
    if not points:
        return None

    if len(points) == 1:
        return points[0]

    best = None
    best_dist_sq = None
    for point3d_id, px, pz, label in points:
        dist_sq = (px - world_pos.x) ** 2 + (pz - world_pos.y) ** 2
        if best_dist_sq is None or dist_sq < best_dist_sq:
            best_dist_sq = dist_sq
            best = (point3d_id, px, pz, label)

    return best


class MouseHandlerPegBoard(QtCore.QObject):
    """Pan/zoom/reset mouse handling for the peg board canvas.

    See module docstring for what is/isn't replicated from
    :class:`harness_designer.gl.canvas2d.mouse_handler.MouseHandler2D`.
    """

    def __init__(self, canvas: "_canvas.Canvas"):
        """Initialise the :class:`MouseHandlerPegBoard` instance.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """
        super().__init__()
        self.canvas = canvas

        self._mouse_pos: _point.Point = None
        self._is_motion = False
        self._click_threshold = 3

        # Phase 3: "currently selected waypoint" -- waypoints have no
        # ObjectBase/is_selected of their own (unlike anchors, whose
        # selection is derived live via _find_selected_anchor()), so this
        # canvas-level id is the whole of that bookkeeping. Mutually
        # exclusive with anchor selection: selecting/arming either one
        # clears the other (see on_left_down).
        self._selected_waypoint_id: int = None

        # Phase 3: continuous drag state. _drag_kind is None when no drag
        # is armed, else 'anchor' or 'waypoint'. _drag_touching is the
        # dragged node's touching-edges list from
        # Canvas.edges_touching_node(), precomputed once at drag-arm time
        # (on_left_down/arm_waypoint_drag) -- never recomputed per
        # mouse-move.
        self._drag_kind: str = None
        self._drag_anchor = None
        self._drag_node = None
        self._drag_touching: list = None

        # Phase 3: set by Canvas.arm_waypoint_drag()/start_add_waypoint()
        # once a "click on a bundle strand to add a waypoint" action is
        # active -- see handlers.pegboard_handler.AddWaypointHandler.
        self._add_waypoint_handler = None

        # Rotate-gizmo drag state. Mirrors gl.canvas3d.rotation_rings's
        # DragRotate, minus the camera-facing sign flip (the peg board only
        # ever has one fixed top-down viewing direction, so there is only
        # ever one consistent rotation direction). Entering/exiting
        # "rotation mode" itself lives on Canvas (rotation_gizmo_anchor is
        # the single source of truth for whether it's active) -- this is
        # just the continuous-drag bookkeeping for while the handle is
        # being dragged.
        self._rotate_drag_active = False
        self._rotate_start_value = 0.0
        self._rotate_center = None
        self._rotate_prev_phi = None
        self._rotate_total = 0.0

        # Set by on_right_down() when that exact press entered rotation
        # mode -- on_right_up() checks this to avoid also popping the
        # Show/Hide Data Table context menu for the same click.
        self._right_down_entered_rotation = False

        canvas.installEventFilter(self)

    # ------------------------------------------------------------------
    # Phase 3: drag arming / add-waypoint mode
    # ------------------------------------------------------------------

    def arm_waypoint_drag(self, node) -> None:
        """Arm a continuous drag for *node* (a waypoint), without
        requiring a prior "click once to select, click again to arm"
        pair of clicks.

        Used two ways: (1) internally, by :meth:`on_left_down` when a
        click lands on an already-selected waypoint (mirrors
        ``gl.canvas2d.mouse_handler.MouseHandler2D``'s "click again on the
        already-selected object arms drag" gate); (2) by
        ``handlers.pegboard_handler.AddWaypointHandler`` (via
        ``Canvas.arm_waypoint_drag``) immediately after it creates a
        brand-new waypoint from a click on a bundle strand, so the same
        mouse-down that created the waypoint can carry straight into
        dragging it.

        :param node: The waypoint node to arm a drag for.
        :type node: :class:`_layout_graph.PegboardNode`
        """
        self.canvas.begin_drag()

        self._drag_kind = 'waypoint'
        self._drag_anchor = None
        self._drag_node = node
        self._selected_waypoint_id = node.waypoint_id
        self._drag_touching = self.canvas.edges_touching_node(
            waypoint_id=node.waypoint_id)

    def start_add_waypoint(self) -> None:
        """Activate "click on a bundle strand to add a new waypoint"
        mode for the next left-click.

        No peg-board toolbar/menu exists yet to wire this to (the dock is
        called out as later-task scope throughout this feature's plan) --
        this is the concrete entry point a future toolbar action calls,
        mirroring how ``mainframe._on_tool_mode_change`` instantiates
        every other ``Add*Handler`` on a toolbar id. Until that wiring
        exists, call this directly (e.g. from a test or a temporary menu
        action) to exercise the interaction.
        """
        from ...handlers import pegboard_handler as _pegboard_handler

        self._add_waypoint_handler = _pegboard_handler.AddWaypointHandler(
            self.canvas.mainframe, self.canvas)

    # ------------------------------------------------------------------
    # Rotate-gizmo hit-testing / drag
    # ------------------------------------------------------------------

    def _rotation_handle_hit(self, mouse_pos: _point.Point) -> bool:
        """Return whether *mouse_pos* (screen coordinates) hits the active
        rotate gizmo's grab handle.

        Mirrors ``gl.canvas3d.rotation_rings.RotationRings.pick_handle``'s
        screen-space distance test (same ``HANDLE_PICK_TOLERANCE``), but
        against the peg board's single handle position instead of picking
        among 3 candidate axes.

        :param mouse_pos: Mouse position, screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        :returns: ``True`` if the handle was hit.
        :rtype: bool
        """
        handle_world = self.canvas.rotation_gizmo_handle_world_pos()
        if handle_world is None:
            return False

        # Camera2D.world_to_screen is a generic 2-component screen/world
        # helper (shared with editor2d, unaware of a "z" axis) -- the one
        # necessary boundary conversion from handle_world's real 3D
        # (.x/.y=0/.z) position.
        screen = self.canvas.camera.world_to_screen(
            _point.Point(handle_world.x, handle_world.z))
        dx = float(screen.x) - float(mouse_pos.x)
        dz = float(screen.y) - float(mouse_pos.y)

        return math.hypot(dx, dz) <= HANDLE_PICK_TOLERANCE

    def _rotate_center_screen(self, anchor) -> tuple:
        """Return the active gizmo's target *anchor*'s screen-space center.

        :param anchor: The anchor currently in rotation mode.
        :type anchor: :class:`_basepeg.BasePeg`
        :returns: ``(screen_x, screen_y)``.
        :rtype: tuple[float, float]
        """
        world = _point.Point(anchor.position.x, anchor.position.z)
        screen = self.canvas.camera.world_to_screen(world)
        return float(screen.x), float(screen.y)

    @staticmethod
    def _rotate_screen_phi(mouse_pos: _point.Point, center_x: float,
                            center_z: float) -> float:
        """Return the math-orientation angle of the cursor around
        ``(center_x, center_z)``.

        Mirrors ``gl.canvas3d.rotation_rings.DragRotate._screen_phi``
        exactly -- screen Y grows downward, negated for
        counter-clockwise-positive math. Unlike ``DragRotate``, there is no
        camera-facing sign flip here: the peg board only ever has one
        fixed top-down viewing direction.

        :param mouse_pos: Mouse position, screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        :param center_x: Rotation center, screen X.
        :type center_x: float
        :param center_z: Rotation center, screen Y.
        :type center_z: float
        :returns: Polar angle, radians.
        :rtype: float
        """
        return math.atan2(-(float(mouse_pos.y) - center_z),
                          float(mouse_pos.x) - center_x)

    def _arm_rotate_drag(self, mouse_pos: _point.Point) -> None:
        """Arm a continuous rotate-drag starting at *mouse_pos*.

        :param mouse_pos: Mouse position, screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        """
        self._rotate_drag_active = True
        self._rotate_start_value = self.canvas.rotation_gizmo_degrees
        self._rotate_center = self._rotate_center_screen(
            self.canvas.rotation_gizmo_anchor)
        self._rotate_prev_phi = self._rotate_screen_phi(
            mouse_pos, *self._rotate_center)
        self._rotate_total = 0.0

    def _update_rotate_drag(self, mouse_pos: _point.Point) -> None:
        """Update the in-progress rotate-drag from the current mouse
        position -- writes immediately through the anchor's bound
        ``Angle`` (see ``Canvas.update_rotation_drag``).

        Mirrors ``gl.canvas3d.rotation_rings.DragRotate.__call__``'s
        wrap-safe accumulation and live snap-angle read exactly.

        :param mouse_pos: Mouse position, screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        """
        phi = self._rotate_screen_phi(mouse_pos, *self._rotate_center)

        step = math.atan2(math.sin(phi - self._rotate_prev_phi),
                          math.cos(phi - self._rotate_prev_phi))
        self._rotate_prev_phi = phi
        self._rotate_total += step

        new_value = wrap_angle(
            self._rotate_start_value + math.degrees(self._rotate_total))

        ring_config = _config.Config.editor_pegboard.rotation_ring

        if ring_config.snap_enable:
            snap = validate_snap_angle(ring_config.snap_angle)
        else:
            snap = 0.0

        if snap:
            new_value = wrap_angle(round(round(new_value / snap) * snap, 2))

        self.canvas.update_rotation_drag(new_value)

    # ------------------------------------------------------------------
    # Signal dispatch helper
    # ------------------------------------------------------------------

    def _send_event(self, event, qt_event):
        """Populate event fields and emit the named canvas signal."""
        mouse_pos = _qt_pos(qt_event)
        world_pos = self.canvas.camera.screen_to_world(mouse_pos)
        flags = _qt_buttons_flag(qt_event)

        event.SetId(id(self.canvas))
        event.SetEventObject(self.canvas)
        event.SetPosition(mouse_pos)
        event.SetWorldPosition(world_pos)
        event.SetMouseButtons(flags)

        getattr(self.canvas, event.GetType()).emit(event)

        return event

    # ------------------------------------------------------------------
    # Qt event filter dispatcher
    # ------------------------------------------------------------------

    def eventFilter(self, obj, qt_event):
        """Execute the event filter operation.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        :param qt_event: Value for ``qt_event``.
        :type qt_event: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if obj is not self.canvas:
            return False

        try:
            t = qt_event.type()
        except:  # NOQA
            return False

        if t == QtCore.QEvent.Type.MouseButtonPress:
            btn = qt_event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_down(qt_event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_down(qt_event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_down(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_down(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_down(qt_event)
            return False

        if t == QtCore.QEvent.Type.MouseButtonRelease:
            btn = qt_event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_up(qt_event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_up(qt_event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_up(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_up(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_up(qt_event)
            return False

        if t == QtCore.QEvent.Type.MouseButtonDblClick:
            btn = qt_event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_dclick(qt_event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_dclick(qt_event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_dclick(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_dclick(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_dclick(qt_event)
            return False

        if t == QtCore.QEvent.Type.MouseMove:
            self.on_mouse_motion(qt_event)
            return False

        if t == QtCore.QEvent.Type.Wheel:
            self.on_mouse_wheel(qt_event)
            return False

        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_mouse(self, code):
        """Return a pan/zoom/reset wrapper bound to whichever of
        config.pan/config.zoom/config.reset claims ``code``, or a no-op.

        :param code: One of the MOUSE_* button bitmask values.
        :type code: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        for config, func in (
            (self.canvas.config.pan, self.canvas.Pan),
            (self.canvas.config.zoom, self.canvas.Zoom),
            (self.canvas.config.reset, self.canvas.camera.Reset),
        ):
            if not config.mouse:
                continue

            if config.mouse & code:
                def _wrapper_func(c):
                    """Bind ``func`` with axis-swap applied per ``c.mouse``.

                    :param c: Value for ``c``.
                    :type c: UNKNOWN
                    :returns: Return value. UNKNOWN details.
                    :rtype: UNKNOWN
                    """
                    def _wrapper(dx, dy):
                        """Execute the wrapper operation.

                        :param dx: Value for ``dx``.
                        :type dx: UNKNOWN
                        :param dy: Value for ``dy``.
                        :type dy: UNKNOWN
                        """
                        if c.mouse & MOUSE_SWAP_AXIS:
                            func(dy, dx)
                        else:
                            func(dx, dy)
                    return _wrapper
                return _wrapper_func(config)

        def _do_nothing_func(_, __):
            """No binding claimed this button -- do nothing.

            :param _: Value for ``_``.
            :type _: UNKNOWN
            :param __: Value for ``__``.
            :type __: UNKNOWN
            """
            pass

        return _do_nothing_func

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def on_left_down(self, evt):
        """Handle the left down event.

        Hit-tests the click against the peg board's anchor list --
        selection mirrors ``gl.canvas2d.mouse_handler.MouseHandler2D.
        on_left_down`` exactly as before: the previously-selected anchor
        (if any) is deselected, the anchor hit by the click (if any) is
        selected, and the matching
        ``EVT_GL_OBJECT_SELECTED``/``EVT_GL_OBJECT_UNSELECTED`` events are
        emitted, flowing through ``objects.object_base.ObjectBase.
        set_selected()`` exactly like every other editor. Unchanged from
        Phase 2.

        Added on top of that, unchanged behavior:

        - Clicking an anchor that is *already* selected arms a continuous
          drag for it instead (mirrors ``MouseHandler2D``'s own "click
          again on the already-selected object" drag-arm gate).
        - If no anchor was hit, a waypoint is hit-tested next
          (:func:`_find_waypoint_at_point`) -- clicking a new waypoint
          selects it (canvas-level ``self._selected_waypoint_id``, since
          waypoints have no ``ObjectBase``/``is_selected``), clicking an
          already-selected waypoint arms its drag.
        - If "add waypoint" mode is active (``self._add_waypoint_handler``
          -- see :meth:`start_add_waypoint`), the click is instead routed
          straight to ``handlers.pegboard_handler.AddWaypointHandler``,
          which hit-tests the click against a bundle strand, creates a new
          waypoint there, and hands off directly into the same drag
          mechanism (:meth:`arm_waypoint_drag`) so the same mouse-down can
          carry straight into fine-tuning its position.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False
        refresh = False

        if self.canvas.rotation_gizmo_anchor is not None:
            # Rotation mode consumes left clicks entirely -- mirrors
            # gl.canvas3d.mouse_handler.py's on_left_down angle-mode gate:
            # hitting the handle arms a drag, missing it just consumes the
            # click (exit-on-miss happens on release, see on_left_up).
            if self._rotation_handle_hit(mouse_pos):
                self._arm_rotate_drag(mouse_pos)

            self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_DOWN), evt)
            self.canvas.grabMouse()
            return

        if self._add_waypoint_handler is not None:
            handler = self._add_waypoint_handler
            self._add_waypoint_handler = None  # one-shot per click

            handler.hover(mouse_pos)
            handler.capture_position(mouse_pos)
            handler.release_capture()

            self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_DOWN), evt)
            self.canvas.grabMouse()
            self.canvas.update()
            return

        # Read by MainFrame._set_selected: this click is what's about to
        # trigger the selection change below, so the peg board view
        # shouldn't re-center on it -- it's already right where the user
        # clicked.
        self.canvas.mainframe._selection_source_editor = 'editor_pegboard'  # NOQA

        world_pos = self.canvas.camera.screen_to_world(mouse_pos)
        anchors = self.canvas.anchors

        hit = _find_anchor_at_point(anchors, world_pos)
        cur_selected = _find_selected_anchor(anchors)

        if hit is None:
            if cur_selected is not None:
                cur_selected.obj.set_selected(False)
                unsel_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                unsel_event.SetGLObject(cur_selected.obj)
                self._send_event(unsel_event, evt)
                refresh = True

            waypoint_hit = _find_waypoint_at_point(self.canvas.nodes, world_pos)
            if waypoint_hit is None:
                self._selected_waypoint_id = None
            elif waypoint_hit.waypoint_id == self._selected_waypoint_id:
                self.arm_waypoint_drag(waypoint_hit)
            else:
                self._selected_waypoint_id = waypoint_hit.waypoint_id
                refresh = True
        elif hit is not cur_selected:
            if cur_selected is not None:
                cur_selected.obj.set_selected(False)
                unsel_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                unsel_event.SetGLObject(cur_selected.obj)
                self._send_event(unsel_event, evt)

            hit.obj.set_selected(True)
            sel_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_SELECTED)
            sel_event.SetGLObject(hit.obj)
            self._send_event(sel_event, evt)
            self._selected_waypoint_id = None
            refresh = True
        else:
            # Clicked the already-selected anchor -- arm a continuous
            # drag instead of re-selecting (mirrors MouseHandler2D).
            self.canvas.begin_drag()

            self._drag_kind = 'anchor'
            self._drag_anchor = hit
            self._drag_node = None
            self._drag_touching = self.canvas.edges_touching_node(anchor=hit)

        self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_DOWN), evt)
        self.canvas.grabMouse()

        if refresh:
            self.canvas.update()

    def on_left_up(self, evt):
        """Handle the left up event.

        If a drag was in progress (armed by :meth:`on_left_down`/
        :meth:`arm_waypoint_drag`), this is the single point where the
        final position(s) are written to the database -- exactly once per
        moved entity, never during the drag itself (see
        ``Canvas.commit_drag``). In "clamp" mode that is always just the
        one directly-dragged anchor/waypoint; in "pull" mode it may also
        include every neighbor the pull propagated to.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos

        if self.canvas.rotation_gizmo_anchor is not None:
            # Mirrors gl.canvas3d.mouse_handler.py's angle-mode on_left_up:
            # ending a handle drag keeps the gizmo up (so the user can keep
            # adjusting); a click (no motion) anywhere that isn't the grab
            # handle exits rotation mode. No commit needed here anymore --
            # Canvas.update_rotation_drag() already wrote every intermediate
            # value straight to the live, DB-backed anchor.angle.y (same
            # "no batching" discipline angle3d/angle2d already use), so the
            # database is already fully up to date by the time this fires.
            if self._rotate_drag_active:
                self._rotate_drag_active = False
                self._rotate_prev_phi = None
                self._rotate_total = 0.0
                self._rotate_center = None
            elif not self._is_motion:
                if not self._rotation_handle_hit(mouse_pos):
                    self.canvas.exit_rotation_mode()

            self._is_motion = False
            self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_UP), evt)
            self.canvas.releaseMouse()
            return

        if self._drag_kind == 'anchor':
            self.canvas.commit_drag(primary_anchor=self._drag_anchor)
        elif self._drag_kind == 'waypoint':
            self.canvas.commit_drag(primary_node=self._drag_node)

        self._drag_kind = None
        self._drag_anchor = None
        self._drag_node = None
        self._drag_touching = None

        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_UP), evt)
        self.canvas.releaseMouse()

    def on_left_dclick(self, evt):
        """Handle the left dclick event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        # TODO: object activation (EVT_GL_OBJECT_ACTIVATED) happens here
        # once scene objects exist -- see MouseHandler2D.on_left_dclick.

        self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_DCLICK), evt)

    def on_right_down(self, evt):
        """Handle the right down event.

        Right-clicking the currently-selected anchor enters rotation mode
        (mirrors ``gl.canvas3d.mouse_handler.py``'s on_right_down: a
        right-click on an already-selected object shows the rotate
        gizmo). No-op if rotation mode is already active for some anchor,
        or if the click doesn't land on the selected anchor.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False
        self._right_down_entered_rotation = False

        if self.canvas.rotation_gizmo_anchor is None:
            world_pos = self.canvas.camera.screen_to_world(mouse_pos)
            anchors = self.canvas.anchors

            hit = _find_anchor_at_point(anchors, world_pos)
            cur_selected = _find_selected_anchor(anchors)

            if hit is not None and hit is cur_selected:
                self.canvas.enter_rotation_mode(hit)
                self.canvas.update()
                self._right_down_entered_rotation = True

        self._send_event(_events.GLEvent(_events.EVT_GL_RIGHT_DOWN), evt)
        self.canvas.grabMouse()

    def on_right_up(self, evt):
        """Handle the right up event.

        A plain right-click (no drag, and this press didn't just enter
        rotation mode -- see :meth:`on_right_down`) shows the Show/Hide
        Data Table context menu for whichever anchor (or, for a
        transition, whichever of its branch table-points is nearest the
        click) is under the cursor.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos

        if not self._is_motion and not self._right_down_entered_rotation:
            self._show_table_context_menu(mouse_pos)

        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_RIGHT_UP), evt)
        self.canvas.releaseMouse()

    def _show_table_context_menu(self, mouse_pos: _point.Point) -> None:
        """Show the Show/Hide Data Table context menu for whichever
        table-point is under *mouse_pos*, if any.

        :param mouse_pos: Mouse position, screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        """
        world_pos = self.canvas.camera.screen_to_world(mouse_pos)
        hit = _find_table_point_at(self.canvas.anchors, world_pos)
        if hit is None:
            return

        point3d_id, _world_x, _world_z, label = hit
        is_visible = self.canvas.tables_overlay.is_visible(point3d_id)
        action_text = 'Hide Data Table' if is_visible else 'Show Data Table'

        menu = QtWidgets.QMenu(self.canvas)
        action = menu.addAction(f'{action_text} ({label})')
        action.triggered.connect(
            lambda: self.canvas.tables_overlay.toggle_visibility(point3d_id))

        menu.exec(self.canvas.mapToGlobal(
            QtCore.QPoint(int(mouse_pos.x), int(mouse_pos.y))))

    def on_right_dclick(self, evt):
        """Handle the right dclick event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_RIGHT_DCLICK), evt)

    def on_middle_down(self, evt):
        """Handle the middle down event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_MIDDLE_DOWN), evt)
        self.canvas.grabMouse()

    def on_middle_up(self, evt):
        """Handle the middle up event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._mouse_pos = _qt_pos(evt)
        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_MIDDLE_UP), evt)
        self.canvas.releaseMouse()

    def on_middle_dclick(self, evt):
        """Handle the middle dclick event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_MIDDLE_DCLICK), evt)

    def on_aux1_up(self, evt):
        """Handle the aux 1 up event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX1_UP), evt)

    def on_aux1_down(self, evt):
        """Handle the aux 1 down event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX1_DOWN), evt)

    def on_aux1_dclick(self, evt):
        """Handle the aux 1 dclick event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX1_DCLICK), evt)

    def on_aux2_up(self, evt):
        """Handle the aux 2 up event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX2_UP), evt)

    def on_aux2_down(self, evt):
        """Handle the aux 2 down event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX2_DOWN), evt)

    def on_aux2_dclick(self, evt):
        """Handle the aux 2 dclick event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX2_DCLICK), evt)

    def on_mouse_motion(self, evt):
        """Handle the mouse motion event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        refresh = False

        btns = evt.buttons()
        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_MOUSE_MOVE)
        if not self._send_event(event, evt):
            return

        if btns != QtCore.Qt.MouseButton.NoButton:
            if self._mouse_pos is None:
                self._mouse_pos = mouse_pos

            delta = mouse_pos - self._mouse_pos
            self._mouse_pos = mouse_pos

            with self.canvas:
                if btns & QtCore.Qt.MouseButton.LeftButton:
                    self._is_motion = True

                    if self._rotate_drag_active:
                        self._update_rotate_drag(mouse_pos)
                    elif self.canvas.rotation_gizmo_anchor is not None:
                        # Rotation mode active but this drag isn't on the
                        # grab handle -- mirrors gl.canvas3d.mouse_handler
                        # .py's rule that a drag not on a grab handle moves
                        # the camera instead.
                        self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])
                    elif self._drag_kind is None:
                        # No drag armed -- left-drag pans (matches the
                        # default Config.editor_pegboard.pan.mouse =
                        # MOUSE_LEFT), same as Phase 1/2.
                        self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])
                    else:
                        # Mirrors MouseHandler2D.on_mouse_motion's drag
                        # branch: convert to world, grid-snap if enabled,
                        # then hand off to Canvas for the local-clamp +
                        # in-memory position update (no DB write here --
                        # see Canvas.drag_update_anchor/
                        # drag_update_waypoint and on_left_up's commit).
                        world_pos = self.canvas.camera.screen_to_world(mouse_pos)

                        if self.canvas.config.grid.snap:
                            world_pos = self.canvas.snap_to_grid(world_pos)

                        cand_x, cand_z = float(world_pos.x), float(world_pos.y)

                        if self._drag_kind == 'anchor':
                            self.canvas.drag_update_anchor(
                                self._drag_anchor, cand_x, cand_z,
                                self._drag_touching)
                        else:
                            self.canvas.drag_update_waypoint(
                                self._drag_node, cand_x, cand_z,
                                self._drag_touching)

                    refresh = True

                if btns & QtCore.Qt.MouseButton.MiddleButton:
                    self._is_motion = True
                    self._process_mouse(MOUSE_MIDDLE)(*list(delta)[:-1])
                    refresh = True

                if btns & QtCore.Qt.MouseButton.RightButton:
                    self._is_motion = True
                    self._process_mouse(MOUSE_RIGHT)(*list(delta)[:-1])
                    refresh = True

                if btns & QtCore.Qt.MouseButton.XButton1:
                    self._is_motion = True
                    self._process_mouse(MOUSE_AUX1)(*list(delta)[:-1])
                    refresh = True

                if btns & QtCore.Qt.MouseButton.XButton2:
                    self._is_motion = True
                    self._process_mouse(MOUSE_AUX2)(*list(delta)[:-1])
                    refresh = True

        self._send_event(_events.GLEvent(_events.EVT_GL_MOUSE_MOVE), evt)

        if refresh:
            # Refresh(), not update() -- the pan/zoom/drag above ran inside
            # `with self.canvas:`, so any camera-change-triggered Refresh()
            # during it was suppressed by the batching ref-count (see
            # Canvas.Refresh's guard). A plain update() only repaints the
            # GL grid/pegs (recomputed fresh from live camera state every
            # frame); it skips reposition_all(), so the table overlays
            # would only catch up on some later, unbatched Refresh() (e.g.
            # the next zoom) instead of tracking the pan live.
            self.canvas.Refresh()

    def on_mouse_wheel(self, evt):
        """Handle the mouse wheel event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        delta = 1.0 if evt.angleDelta().y() > 0 else -1.0
        self.canvas.camera.zoom_at_point(mouse_pos, delta)
        self.canvas.update()
