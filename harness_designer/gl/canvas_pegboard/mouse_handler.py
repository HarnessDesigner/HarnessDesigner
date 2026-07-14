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
click-to-select behavior: a click hit-tests `Canvas.anchors` (the Phase 1
static layout built by `layout_graph.build_anchors`) and drives selection
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

from typing import TYPE_CHECKING

from PySide6 import QtCore

from ... import config as _config
from ...geometry import point as _point
from .. import events as _events


if TYPE_CHECKING:
    from . import canvas as _canvas
    from . import layout_graph as _layout_graph


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

    :param anchors: The canvas's current anchor list.
    :type anchors: list[:class:`_layout_graph.PegboardAnchor`]
    :param world_pos: Click position in world coordinates.
    :type world_pos: :class:`_point.Point`
    :returns: The topmost anchor whose axis-aligned XZ footprint contains
        *world_pos*, or ``None``.
    :rtype: :class:`_layout_graph.PegboardAnchor` | None
    """
    click_x = world_pos.x
    click_z = world_pos.y

    for anchor in reversed(anchors):
        if (
            anchor.x - anchor.half_width <= click_x <= anchor.x + anchor.half_width and
            anchor.z - anchor.half_depth <= click_z <= anchor.z + anchor.half_depth
        ):
            return anchor

    return None


def _find_selected_anchor(anchors: list):
    """Return whichever anchor's wrapped object is currently selected.

    Derived live from ``anchor.obj.is_selected`` on every call rather than
    tracked as a separate selected-anchor pointer on the canvas -- this
    keeps the peg board automatically in sync with selection changes made
    from the 2D/3D editors (see
    ``objects.object_base.ObjectBase.set_selected``), with no extra
    bookkeeping required when selection changes from elsewhere.

    :param anchors: The canvas's current anchor list.
    :type anchors: list[:class:`_layout_graph.PegboardAnchor`]
    :returns: The selected anchor, or ``None``.
    :rtype: :class:`_layout_graph.PegboardAnchor` | None
    """
    for anchor in anchors:
        if anchor.obj.is_selected:
            return anchor

    return None


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

        canvas.installEventFilter(self)

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

        Hit-tests the click against the peg board's anchor list and
        selection-only (no drag) mirrors
        ``gl.canvas2d.mouse_handler.MouseHandler2D.on_left_down``: the
        previously-selected anchor (if any) is deselected, the anchor hit
        by the click (if any) is selected, and the matching
        ``EVT_GL_OBJECT_SELECTED``/``EVT_GL_OBJECT_UNSELECTED`` events are
        emitted. Selection flows through
        ``objects.object_base.ObjectBase.set_selected()`` exactly like
        every other editor, so ``mainframe._set_selected()`` picks it up
        and syncs the 2D/3D editors automatically.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False
        refresh = False

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
            refresh = True

        # TODO: object drag hookup happens here once the peg board
        # supports dragging (a later phase, not this task's scope).
        # Reference: MouseHandler2D.on_left_down arms self._drag_obj when
        # ``hit is cur_selected`` so the next on_mouse_motion call drags
        # the object instead of panning the camera.

        self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_DOWN), evt)
        self.canvas.grabMouse()

        if refresh:
            self.canvas.update()

    def on_left_up(self, evt):
        """Handle the left up event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos

        # TODO: object drag-release hookup happens here once the peg
        # board supports dragging -- see on_left_down's TODO.

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

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_RIGHT_DOWN), evt)
        self.canvas.grabMouse()

    def on_right_up(self, evt):
        """Handle the right up event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos

        # TODO: object picking / right-click context-menu hookup happens
        # here once scene objects exist -- see MouseHandler2D.on_right_up
        # and _show_canvas_context_menu.

        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_RIGHT_UP), evt)
        self.canvas.releaseMouse()

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
        if btns != QtCore.Qt.MouseButton.NoButton:
            mouse_pos = _qt_pos(evt)

            if self._mouse_pos is None:
                self._mouse_pos = mouse_pos

            delta = mouse_pos - self._mouse_pos
            self._mouse_pos = mouse_pos

            with self.canvas:
                if btns & QtCore.Qt.MouseButton.LeftButton:
                    self._is_motion = True

                    # TODO: object drag hookup happens here once scene
                    # objects exist. Reference: MouseHandler2D.
                    # on_mouse_motion only pans when self._drag_obj is
                    # None; otherwise it moves the dragged object's
                    # position (with grid-snap / angle-lock applied) and
                    # emits EVT_GL_OBJECT_DRAG instead. Until then,
                    # left-drag always pans (matches the default
                    # Config.editor_pegboard.pan.mouse = MOUSE_LEFT).
                    self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])

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
            self.canvas.update()

    def on_mouse_wheel(self, evt):
        """Handle the mouse wheel event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        delta = 1.0 if evt.angleDelta().y() > 0 else -1.0
        self.canvas.camera.zoom_at_point(mouse_pos, delta)
        self.canvas.update()
