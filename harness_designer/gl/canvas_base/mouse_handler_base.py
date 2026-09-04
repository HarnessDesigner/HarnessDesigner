# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Editor-agnostic mouse dispatch.

Every add/drag/rotation handler lives directly on a view object instance
(``obj.obj3d`` / ``obj.objschematic`` / ``obj.objpegboard`` -- see
``objectsvar.base_var.BaseVar.handle_interaction``), not as a separate
listener object reacting to Qt signals. This module tracks, per canvas,
which view object (if any) is currently armed -- ``CanvasBase.
active_handler_obj`` -- and routes every relevant mouse event there first
via :meth:`MouseHandlerBase._dispatch_to_active_handler`, called at the top
of each button/motion handler below before any of that handler's own
default click/drag/selection behavior runs. A `True` return means the
event was consumed and this module's own default logic for that event is
skipped entirely; `False` (nothing armed, and the freshly picked object
declined to arm one) falls through unchanged to the existing behavior.
"""

import math
from typing import TYPE_CHECKING

from PySide6 import QtCore
from PySide6 import QtGui

from .. import object_picker as _object_picker
from ...geometry import point as _point
from ... import config as _config
from .. import events as _events
from . import interaction as _interaction
from ...objects import housing as _housing
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import canvas_base as _canvas_base


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

_EPSILON = 1e-6

# Mouse-wheel easing (see on_mouse_wheel/_on_wheel_tick): a physical wheel
# notch is one discrete hardware event with nothing to interpolate between
# notches on its own, so applying its full step instantly always reads as
# a visible "hard step" no matter how small the per-notch step is -- the
# fix is to ease each notch's contribution in over several frames instead
# of applying it in one shot, the same way a trackpad/smooth-scroll wheel
# already feels continuous.
_WHEEL_TICK_MS = 16          # ~60Hz easing tick rate
_WHEEL_EASE_RATIO = 0.35     # fraction of the still-pending distance applied per tick
_WHEEL_STOP_THRESHOLD = 0.01  # pending distance below which the ease-out is done

# Caps how much distance can ever sit in the pending buffer at once --
# without this, a long/fast scroll burst keeps adding to the same pending
# total (see on_mouse_wheel) and the ease-out then keeps "coasting" for
# proportionally longer the more you scrolled, so the camera visibly
# keeps moving well after you've actually stopped turning the wheel.
# Capping it bounds the coast-after-stop tail to a short, fixed length
# (roughly the time to ease out this many notches) regardless of how
# long or fast the scroll burst was -- it still smooths out a notch (or
# a couple of notches landing close together), it just can never build
# into an open-ended glide.
_WHEEL_MAX_PENDING = 2.0

# Hard stop, tied directly to wheel input specifically (not whatever
# movement type the wheel happens to be bound to -- a mouse-button+drag
# rebound onto the same movement doesn't have this discrete-notch problem
# at all, so it gets none of this wheel-only machinery): reset on every
# wheel event, and if this much time passes with no new wheel event, the
# easing timer is stopped outright and any still-pending distance is
# dropped, rather than left to keep decaying on its own. _WHEEL_MAX_PENDING
# already keeps the natural decay short, but this guarantees motion never
# continues past a point genuinely tied to "the user stopped scrolling",
# not just "the buffer happened to empty out around when they stopped".
_WHEEL_IDLE_MS = 500


@_check_types.do
def _qt_pos(qt_event) -> _point.Point:
    """Execute the qt pos operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param qt_event: Value for ``qt_event``.
    :type qt_event: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: :class:`_point.Point`
    """
    p = qt_event.position().toPoint()
    return _point.Point(p.x(), p.y())


@_check_types.do
def _qt_buttons_flag(qt_event) -> int:
    """Convert Qt mouse buttons bitmask to our internal BTN_* flags."""
    btns = qt_event.buttons()
    flags = 0
    if btns & QtCore.Qt.MouseButton.LeftButton:
        flags |= _events.BTN_LEFT
    if btns & QtCore.Qt.MouseButton.MiddleButton:
        flags |= _events.BTN_MIDDLE
    if btns & QtCore.Qt.MouseButton.RightButton:
        flags |= _events.BTN_RIGHT
    if btns & QtCore.Qt.MouseButton.XButton1:
        flags |= _events.BTN_AUX1
    if btns & QtCore.Qt.MouseButton.XButton2:
        flags |= _events.BTN_AUX2
    return flags


class MouseHandlerBase:
    """Represent a mouse handler in :mod:`harness_designer.gl.canvas3d.mouse_handler`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas_base.CanvasBase"):
        """Initialise the :class:`MouseHandler` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas_base.CanvasBase`
        """
        self.canvas = canvas
        self.config = self.canvas.config.input

        self._is_motion = False
        self._mouse_pos = None
        self._active_cavity_housing = None

        self._gl_mouse_event: _events.GLEvent | _events.GLObjectEvent | None = None

        # Last position handed to an active/newly-armed handler via
        # _dispatch_to_active_handler -- independent of _mouse_pos (which
        # is cleared on button-up and serves the older click/drag-distance
        # bookkeeping below), so a handler always gets a real previous
        # position even across a plain hover with no button held.
        self._last_dispatch_pos: _point.Point | None = None

        # Wheel easing state -- see on_mouse_wheel/_on_wheel_tick.
        self._wheel_pending = 0.0
        self._wheel_timer = QtCore.QTimer()
        self._wheel_timer.setInterval(_WHEEL_TICK_MS)
        self._wheel_timer.timeout.connect(self._on_wheel_tick)

        # Idle-stop watchdog -- restarted on every wheel event, fires
        # (once, see _WHEEL_IDLE_MS's own comment) only once that much
        # time has passed with no further wheel input.
        self._wheel_idle_timer = QtCore.QTimer()
        self._wheel_idle_timer.setInterval(_WHEEL_IDLE_MS)
        self._wheel_idle_timer.setSingleShot(True)
        self._wheel_idle_timer.timeout.connect(self._on_wheel_idle)

    # ------------------------------------------------------------------
    # Qt event filter dispatcher
    # ------------------------------------------------------------------

    @_check_types.do
    def handle_event(self, event):
        """Handle the event.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        t = event.type()

        if t == QtCore.QEvent.Type.MouseButtonPress:
            btn = event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_down(event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_down(event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_down(event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_down(event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_down(event)

            return False

        if t == QtCore.QEvent.Type.MouseButtonRelease:
            btn = event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_up(event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_up(event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_up(event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_up(event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_up(event)
            return False

        if t == QtCore.QEvent.Type.MouseButtonDblClick:
            btn = event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_dclick(event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_dclick(event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_dclick(event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_dclick(event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_dclick(event)
            return False

        if t == QtCore.QEvent.Type.MouseMove:
            self.on_mouse_motion(event)
            return False

        if t == QtCore.QEvent.Type.Wheel:
            self.on_mouse_wheel(event)
            return False

        # Mouse capture lost: Qt sends QEvent.Type.MouseButtonRelease with no
        # button held when the grab is broken externally.  For explicit
        # capture-lost notification we use QWidget.mouseGrabber() == None
        # after a grab was active.  The canvas calls this directly when
        # needed — see Canvas.changeEvent override (not required here).
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @_check_types.do
    def _pick_exclusions(self) -> tuple:
        """Objects that must never be pick-eligible -- gizmo overlays drawn
        on top of the scene (the 3D canvas's focal-target indicator, the
        active rotation-rings gizmo). Checked generically (``getattr``
        with a ``None`` default) rather than via a per-canvas override,
        since not every canvas has these -- schematic/pegboard just fall
        through to the empty tuple.

        The rotation rings themselves are excluded here, but their grab
        handles are not affected -- handle-grabbing goes through
        RotationRings.pick_handle(), a separate code path that never
        consults this method.
        """
        exclusions = []

        focal_target = getattr(self.canvas, '_focal_target', None)
        if focal_target is not None:
            exclusions.append(focal_target)

        rotation_rings = getattr(self.canvas, '_rotation_rings', None)
        if rotation_rings is not None:
            exclusions.append(rotation_rings)

        return tuple(exclusions)

    @_check_types.do
    def _blocks_deselection(self, obj) -> bool:
        """Whether *obj* currently has its rotation gizmo up -- if so, a
        click that misses everything (or lands back on the object
        itself, which would normally toggle selection off) shouldn't
        also drop the selection out from under it. Closing the gizmo
        itself is still entirely ``_handle_rotation_interaction``'s own
        call (see its own docstring) -- this only stops that same click
        from *additionally* deselecting.
        """
        from ...rotation_handlers import rotation_rings as _rotation_rings

        view_obj = self._get_view_object(obj)
        return isinstance(
            getattr(view_obj, '_active_handler', None), _rotation_rings.RotationRings)

    @_check_types.do
    def _pick_object(self, mouse_pos, current_selection=None):
        """Pick a scene object, ignoring anything :meth:`_pick_exclusions`
        reports (e.g. an active rotation gizmo overlay)."""
        objects = self.canvas.objects_in_view

        exclusions = self._pick_exclusions()
        if exclusions:
            objects = [o for o in objects if o not in exclusions]

        return _object_picker.find_object(
            mouse_pos, objects, self.canvas.camera,
            self._get_view_object, current_selection=current_selection)

    @_check_types.do
    def _dispatch_to_active_handler(
        self, mouse_pos: _point.Point, interaction_type: _interaction.MouseInteraction,
        had_motion: bool, clicked_object=None,
    ) -> bool:
        """Route one mouse event to whatever's armed on this canvas, or to
        a freshly picked object so it gets a chance to arm.

        Called first, before any of this handler's own default click/drag/
        selection logic -- see ``objectsvar.base_var.BaseVar.
        handle_interaction`` for the object side of this contract. Returns
        True when the event was consumed, in which case the caller must
        return immediately without running its own default behavior for
        this event (including its own ``_send_event`` call).

        *clicked_object* (from :meth:`_pick_object`) is the facade
        (``ObjectBase``) -- ``handle_interaction``/``is_handler_active``
        live on the view-level object (``obj.obj3d`` etc., what
        :attr:`CanvasBase.active_handler_obj` actually stores), so a freshly
        picked facade is resolved to its view object here via
        :meth:`_get_view_object` before use; *clicked_object* itself is
        still forwarded to the handler as-is (the facade), matching what
        every other picking call site in this module already hands out.
        """
        target = self.canvas.active_handler_obj
        if target is None and clicked_object is not None:
            target = self._get_view_object(clicked_object)

        if target is None:
            return False

        last_pos = self._last_dispatch_pos
        self._last_dispatch_pos = mouse_pos

        if not target.handle_interaction(
            last_pos, mouse_pos, had_motion, interaction_type, clicked_object
        ):
            return False

        if self.canvas.active_handler_obj is not target:
            self.canvas.active_handler_obj = target

        if not target.is_handler_active:
            self.canvas.active_handler_obj = None

        return True

    @_check_types.do
    def _process_mouse(self, code):
        """Execute the process mouse operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param code: Value for ``code``.
        :type code: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        if (
            self.config.truck_pedestal.mouse is not None and
            self.config.truck_pedestal.mouse & code
        ):

            def _wrapper(dx, dy):

                if self.config.truck_pedestal.mouse & MOUSE_SWAP_AXIS:
                    dy, dx = dx, dy

                if self.config.truck_pedestal.mouse & MOUSE_REVERSE_X_AXIS:
                    dx = -dx

                if self.config.truck_pedestal.mouse & MOUSE_REVERSE_Y_AXIS:
                    dy = -dy

                sens = self.config.truck_pedestal.sensitivity
                self.canvas.camera.TruckPedestal(
                    dx * sens, dy * sens, self.config.truck_pedestal.speed)

            return _wrapper

        if (
            self.config.rotate.mouse is not None and
            self.config.rotate.mouse & code
        ):

            def _wrapper(dx, dy):

                if self.config.rotate.mouse & MOUSE_SWAP_AXIS:
                    dy, dx = dx, dy

                if self.config.rotate.mouse & MOUSE_REVERSE_X_AXIS:
                    dx = -dx

                if self.config.rotate.mouse & MOUSE_REVERSE_Y_AXIS:
                    dy = -dy

                sens = self.config.rotate.sensitivity
                self.canvas.camera.Rotate(dx * sens, dy * sens)

            return _wrapper

        if (
            self.config.pan_tilt.mouse is not None and
            self.config.pan_tilt.mouse & code
        ):

            def _wrapper(dx, dy):

                if self.config.pan_tilt.mouse & MOUSE_SWAP_AXIS:
                    dy, dx = dx, dy

                if self.config.pan_tilt.mouse & MOUSE_REVERSE_X_AXIS:
                    dx = -dx

                if self.config.pan_tilt.mouse & MOUSE_REVERSE_Y_AXIS:
                    dy = -dy

                sens = self.config.pan_tilt.sensitivity
                self.canvas.camera.PanTilt(dx * sens, dy * sens)

            return _wrapper

        if (
            self.config.dolly.mouse is not None and
            self.config.dolly.mouse & code
        ):

            if (
                self.config.walk.mouse is not None and
                self.config.walk.mouse & code
            ):
                def _wrapper(dx, dy):

                    if dy == 0.0:
                        # dy == 0.0 here means this call came from the
                        # wheel (see on_mouse_wheel/_on_wheel_tick, which
                        # only ever pass (step, 0.0)) -- dolly and walk
                        # are BOTH bound to MOUSE_WHEEL in editor_3d's
                        # config, dolly claims the code first (checked
                        # above walk in this if/elif chain), so this is
                        # where that overlap has to be handled explicitly:
                        # dolly the camera AND turn it, together, on the
                        # same wheel tick.
                        #
                        # Edge-relative turn: driven by where the cursor
                        # CURRENTLY sits relative to the viewport's own
                        # center, not by dx (the wheel's own eased delta,
                        # which only drives the dolly amount below) --
                        # scaled by walk.sensitivity, same as every other
                        # movement type in this file. No smoothing/timer
                        # of its own needed here either: since this
                        # branch is reached once per already-eased wheel
                        # tick (see _on_wheel_tick), the turn naturally
                        # arcs in smoothly right along with the dolly
                        # instead of jumping to the full deflection in
                        # one step.
                        global_pos = QtGui.QCursor.pos()  # QPoint, screen coordinates
                        local_pos = self.canvas.mapFromGlobal(global_pos)  # QPoint, widget-local coordinates

                        vx, vy, vw, vh = self.canvas.camera.viewport
                        center_x = vx + (vw / 2.0)
                        center_y = vy + (vh / 2.0)

                        lx = local_pos.x()
                        ly = local_pos.y()

                        if self.config.walk.mouse & MOUSE_SWAP_AXIS:
                            lx, ly = ly, lx

                        walk_sens = self.config.walk.sensitivity * 0.005
                        yaw = (lx - center_x) * walk_sens
                        pitch = (ly - center_y) * walk_sens

                        if self.config.walk.mouse & MOUSE_REVERSE_X_AXIS:
                            yaw = -yaw

                        if self.config.walk.mouse & MOUSE_REVERSE_Y_AXIS:
                            pitch = -pitch

                        self.canvas.PanTilt(yaw, pitch)

                        if self.config.dolly.mouse & MOUSE_SWAP_AXIS:
                            dy, dx = dx, dy

                        sens = self.config.dolly.sensitivity
                        self.canvas.camera.Dolly(dx * sens)

                        return

                    if self.config.walk.mouse & MOUSE_SWAP_AXIS:
                        dy, dx = dx, dy

                    look_dx = dx
                    if self.config.walk.mouse & MOUSE_REVERSE_X_AXIS:
                        dx = -dx

                    if self.config.walk.mouse & MOUSE_REVERSE_Y_AXIS:
                        dy = -dy

                    sens = self.config.walk.sensitivity
                    self.canvas.camera.Walk(
                        dx * sens, dy * sens, self.config.walk.speed
                    )

                    self.canvas.PanTilt(look_dx * 2.0, 0.0)

                return _wrapper

            else:
                def _wrapper(dx, dy):

                    if self.config.dolly.mouse & MOUSE_SWAP_AXIS:
                        dy, dx = dx, dy

                    sens = self.config.dolly.sensitivity
                    self.canvas.camera.Dolly(dx * sens)

            return _wrapper

        if (
            self.config.reset.mouse is not None and
            self.config.reset.mouse & code
        ):

            def _wrapper(_, __):
                self.canvas.camera.Reset()

            return _wrapper

        if (
            self.config.walk.mouse is not None and
            self.config.walk.mouse & code
        ):
            def _wrapper(dx, dy):
                if dy == 0.0:
                    self.canvas.PanTilt(dx * 6.0, 0.0)
                    return

                if self.config.walk.mouse & MOUSE_SWAP_AXIS:
                    dy, dx = dx, dy

                look_dx = dx
                if self.config.walk.mouse & MOUSE_REVERSE_X_AXIS:
                    dx = -dx

                if self.config.walk.mouse & MOUSE_REVERSE_Y_AXIS:
                    dy = -dy

                sens = self.config.walk.sensitivity
                self.canvas.camera.Walk(
                    dx * sens, dy * sens, self.config.walk.speed)

                self.canvas.PanTilt(look_dx * 2.0, 0.0)

            return _wrapper

        if (
            self.config.zoom.mouse is not None and
            self.config.zoom.mouse & code
        ):
            def _wrapper(dx, dy):

                if self.config.zoom.mouse & MOUSE_SWAP_AXIS:
                    dy, dx = dx, dy

                sens = self.config.zoom.sensitivity
                self.canvas.camera.Zoom(dx * sens)

            return _wrapper

        def _do_nothing_func(_, __):
            pass

        return _do_nothing_func

    @property
    @_check_types.do
    def active_event(self) -> _events.GLEvent | _events.GLObjectEvent | None:
        """
        Return the active event.

        :rtype: _events.GLEvent | _events.GLObjectEvent | None
        """

        return self._gl_mouse_event

    @_check_types.do
    def _send_event(self, new_event: _events.GLEvent | _events.GLObjectEvent,
                    qt_event) -> bool:
        """
        Execute the send event operation.

        :param new_event: Value for ``new_event``.
        :type new_event: _events.GLEvent | _events.GLObjectEvent

        :param qt_event: Value for ``qt_event``.
        :type qt_event: UNKNOWN

        :rtype: bool
        """

        position = _qt_pos(qt_event)
        world_position = self.canvas.camera.UnprojectPoint(position)

        flags = _qt_buttons_flag(qt_event)

        new_event.SetId(id(self.canvas))
        new_event.SetEventObject(self.canvas)
        new_event.SetPosition(position)
        new_event.SetWorldPosition(world_position)
        new_event.SetMouseButtons(flags)

        if flags:
            self._gl_mouse_event = new_event
        else:
            self._gl_mouse_event = None

        getattr(self.canvas, new_event.GetType()).emit(new_event)

        return new_event.ShouldPropagate()

    @_check_types.do
    def _send_capture_lost(self):
        """
        Execute the send capture lost operation.

        Unconditional -- every listener (including any active drag or
        rotation handler, via their own ``gl_capture_lost`` connection)
        is expected to hard-reset itself here regardless of whether
        anything calls ``StopPropagation``.
        """

        event = _events.GLCaptureLostEvent(_events.EVT_GL_CAPTURE_LOST)
        event.SetId(id(self.canvas))
        event.SetEventObject(self.canvas)
        self.canvas.gl_capture_lost.emit(event)

        self._is_motion = False

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    @_check_types.do
    def on_left_down(self, evt):
        """
        Handle the left down event.
        """

        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False

        clicked_object = self._pick_object(mouse_pos)
        if self._dispatch_to_active_handler(
            mouse_pos, _interaction.MouseInteraction.LEFT_DOWN, False, clicked_object
        ):
            self.canvas.grabMouse()
            # A consumed click can change visible state on its own (e.g.
            # RotationRing.activate()'s newly-shown protractor, or an
            # outer-tick click snapping the object's angle) with no
            # button-drag delta of its own to fall through to the
            # refresh below -- repaint now so that shows up immediately
            # rather than waiting on some unrelated later event.
            self.canvas.repaint()
            return

        event = _events.GLEvent(_events.EVT_GL_LEFT_DOWN)
        if self._send_event(event, evt):
            return

        self.canvas.grabMouse()

    @_check_types.do
    def on_left_up(self, evt):
        """
        Handle the left up event.
        """

        refresh = False

        mouse_pos = _qt_pos(evt)
        clicked_object = self._pick_object(mouse_pos)
        if self._dispatch_to_active_handler(
            mouse_pos, _interaction.MouseInteraction.LEFT_UP, self._is_motion, clicked_object
        ):
            self.canvas.releaseMouse()
            self._mouse_pos = None
            self._is_motion = False
            # See on_left_down's own repaint -- a consumed release (e.g.
            # ending an inner-ring free-rotation drag) needs to show its
            # final state immediately too.
            self.canvas.repaint()
            return

        event = _events.GLEvent(_events.EVT_GL_LEFT_UP)

        if self._send_event(event, evt):
            mouse_pos = _qt_pos(evt)
            self._mouse_pos = mouse_pos

            cur_selected = self.canvas.get_selected()
            selected = self._pick_object(mouse_pos, current_selection=cur_selected)

            if not self._is_motion:
                # Read by MainFrame._set_selected: this click is what's about
                # to trigger the selection change below, so the 3D view
                # shouldn't re-center on it -- it's already right where the
                # user clicked.
                self.canvas.mainframe._selection_source_editor = 'editor3d'  # NOQA

                if self._active_cavity_housing is not None:
                    self._active_cavity_housing.clear_cavity_overlay()
                    self._active_cavity_housing = None

                # If the clicked object is a Housing, check whether the click
                # landed on a cavity face and highlight it.  Cavity interaction
                # is intentionally separate from normal object selection: the
                # housing itself gets selected; right-click on it (while a
                # cavity is highlighted) opens the cavity context menu.
                if isinstance(selected, _housing.Housing):
                    view_obj = self._get_view_object(selected)
                    if hasattr(view_obj, 'try_pick_cavity'):
                        cavity = view_obj.try_pick_cavity(
                            int(mouse_pos.x), int(mouse_pos.y))

                        if cavity is not None:
                            self._active_cavity_housing = view_obj
                            selected = cavity.parent

                if cur_selected is None and selected is not None:
                    selected.set_selected(True)

                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_SELECTED)
                    event.SetGLObject(selected)
                    if not self._send_event(event, evt):
                        selected.set_selected(False)

                elif (
                    selected is None and cur_selected is not None and
                    not self._blocks_deselection(cur_selected)
                ):
                    cur_selected.set_selected(False)

                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                    event.SetGLObject(selected)

                    if not self._send_event(event, evt):
                        cur_selected.set_selected(True)

                elif (
                    selected is not None and
                    cur_selected is not None and
                    selected == cur_selected and
                    not self._blocks_deselection(cur_selected)
                ):
                    selected.set_selected(False)
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                    event.SetGLObject(selected)

                    if not self._send_event(event, evt):
                        selected.set_selected(True)

                elif (
                    selected is not None and
                    cur_selected is not None and
                    selected != cur_selected
                ):
                    cur_selected.set_selected(False)

                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                    event.SetGLObject(cur_selected)

                    if not self._send_event(event, evt):
                        cur_selected.set_selected(True)

                    else:
                        selected.set_selected(True)

                        event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_SELECTED)
                        event.SetGLObject(selected)

                        if not self._send_event(event, evt):
                            selected.set_selected(False)

                refresh = True

        self._mouse_pos = None
        self._is_motion = False

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.repaint()

    @_check_types.do
    def on_left_dclick(self, evt):
        """
        Handle the left dclick event.
        """

        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_LEFT_DCLICK)
        if self._send_event(event, evt):
            selected = _object_picker.find_object(
                mouse_pos, self.canvas.objects_in_view,
                self.canvas.camera, self._get_view_object)

            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_ACTIVATED)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    @_check_types.do
    def on_middle_up(self, evt):
        """
        Handle the middle up event.
        """

        refresh = False

        mouse_pos = _qt_pos(evt)
        clicked_object = self._pick_object(mouse_pos)
        if self._dispatch_to_active_handler(
            mouse_pos, _interaction.MouseInteraction.MIDDLE_UP, self._is_motion, clicked_object
        ):
            self.canvas.releaseMouse()
            return

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_UP)
        if self._send_event(event, evt):
            if not self._is_motion:
                with self.canvas:
                    mouse_pos = _qt_pos(evt)
                    selected = _object_picker.find_object(
                        mouse_pos, self.canvas.objects_in_view,
                        self.canvas.camera, self._get_view_object)

                    if selected:
                        event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_MIDDLE_CLICK)
                        event.SetGLObject(selected)
                        self._send_event(event, evt)

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.repaint()

    @_check_types.do
    def on_middle_down(self, evt):
        """
        Handle the middle down event.
        """

        self._is_motion = False

        mouse_pos = _qt_pos(evt)
        clicked_object = self._pick_object(mouse_pos)
        if self._dispatch_to_active_handler(
            mouse_pos, _interaction.MouseInteraction.MIDDLE_DOWN, False, clicked_object
        ):
            self.canvas.grabMouse()
            self._mouse_pos = mouse_pos
            return

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_DOWN)
        self._send_event(event, evt)

        self.canvas.grabMouse()

        self._mouse_pos = _qt_pos(evt)

    @_check_types.do
    def on_middle_dclick(self, evt):
        """
        Handle the middle dclick event.
        """

        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(
                mouse_pos, self.canvas.objects_in_view,
                self.canvas.camera, self._get_view_object)

            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_MIDDLE_DCLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    @_check_types.do
    def on_right_up(self, evt):
        """
        Handle the right up event.
        """

        refresh = False

        mouse_pos = _qt_pos(evt)
        clicked_object = self._pick_object(mouse_pos)
        if self._dispatch_to_active_handler(
            mouse_pos, _interaction.MouseInteraction.RIGHT_UP, self._is_motion, clicked_object
        ):
            self.canvas.releaseMouse()
            return

        event = _events.GLEvent(_events.EVT_GL_RIGHT_UP)
        if self._send_event(event, evt):

            with self.canvas:
                if not self._is_motion:
                    mouse_pos = _qt_pos(evt)

                    selected = self._pick_object(mouse_pos)
                    cur_selected = self.canvas.get_selected()

                    # A fresh pick at this exact position may not resolve
                    # to the same cavity that's actually selected (or to a
                    # cavity at all) -- try_pick_cavity re-derives it
                    # directly, gated on the click having landed on the
                    # housing that has an active cavity highlight in the
                    # first place.
                    cavity = None
                    if (
                        self._active_cavity_housing is not None and
                        self._active_cavity_housing.parent is selected
                    ):
                        view_obj = self._get_view_object(selected)
                        if hasattr(view_obj, 'try_pick_cavity'):
                            cavity = view_obj.try_pick_cavity(
                                int(mouse_pos.x), int(mouse_pos.y))

                    is_cavity_menu_target = cavity is not None and cavity.parent is cur_selected

                    if is_cavity_menu_target or (selected and selected != cur_selected):
                        # Cavity3D.get_context_menu() owns the cavity-aware
                        # menu now, so the event target is the cavity
                        # itself (cavity.parent, the wrapper) rather than
                        # the housing when this was a cavity hit.
                        target = cavity.parent if is_cavity_menu_target else selected

                        event = _events.GLObjectEvent(
                            _events.EVT_GL_OBJECT_RIGHT_CLICK)
                        event.SetGLObject(target)
                        self._send_event(event, evt)
                    else:
                        refresh = True

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.repaint()

    @_check_types.do
    def on_right_down(self, evt):
        """
        Handle the right down event.

        Entering angle mode for the selected object (if this editor's
        rotation handler decides to) is driven entirely by the picked
        object's own ``handle_interaction`` override -- see
        ``objectsvar.base_var.BaseVar.handle_interaction`` and
        ``_dispatch_to_active_handler``. This method's only remaining job
        is emitting the event and establishing the mouse grab when nothing
        claims the interaction.
        """

        self._is_motion = False

        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos

        clicked_object = self._pick_object(mouse_pos)
        if self._dispatch_to_active_handler(
            mouse_pos, _interaction.MouseInteraction.RIGHT_DOWN, False, clicked_object
        ):
            self.canvas.grabMouse()
            return

        event = _events.GLEvent(_events.EVT_GL_RIGHT_DOWN)
        self._send_event(event, evt)

        self.canvas.grabMouse()

    @_check_types.do
    def on_right_dclick(self, evt):
        """
        Handle the right dclick event.
        """

        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_RIGHT_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(
                mouse_pos, self.canvas.objects_in_view,
                self.canvas.camera, self._get_view_object)

            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_RIGHT_DCLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    @_check_types.do
    def on_mouse_wheel(self, evt):
        """
        Handle the mouse wheel event.
        """

        delta = 1.0 if evt.angleDelta().y() > 0 else -1.0

        if self.config.walk.mouse is not None and self.config.walk.mouse & MOUSE_WHEEL:
            self._orient_to_mouse_on_focal_plane(_qt_pos(evt), delta)

        # Accumulate rather than apply instantly -- _on_wheel_tick eases
        # this notch's contribution in over several frames instead of
        # moving the camera the full step in one shot (see the module-
        # level comment on _WHEEL_TICK_MS/_WHEEL_EASE_RATIO for why).
        # Clamped to _WHEEL_MAX_PENDING (see its own comment) so a long
        # scroll burst can't build up an ever-growing tail that keeps
        # the camera coasting well after the wheel itself stops moving.
        if (
            (delta < 0 < self._wheel_pending) or
            (delta > 0 > self._wheel_pending)
        ):
            self._wheel_pending = delta
        else:
            self._wheel_pending += delta

        if not self._wheel_timer.isActive():
            self._wheel_timer.start()

        # (Re)start the idle watchdog on every wheel event -- calling
        # start() on an already-running QTimer resets its countdown, so
        # this only actually fires _WHEEL_IDLE_MS after the LAST wheel
        # event, not the first.
        self._wheel_idle_timer.start()

    @_check_types.do
    def _on_wheel_idle(self) -> None:
        """Stop the wheel-easing timer outright once no new wheel event
        has arrived for `_WHEEL_IDLE_MS` -- see that constant's own
        comment for why this exists alongside `_WHEEL_MAX_PENDING`.
        """
        self._wheel_pending = 0.0
        self._wheel_timer.stop()

    @_check_types.do
    def _on_wheel_tick(self) -> None:
        """Apply one eased-out slice of the accumulated wheel movement.

        Ease-out: each tick consumes a fixed fraction of whatever's still
        pending, so motion starts at roughly the speed a plain instant
        apply would have and decays smoothly to a stop instead of
        cutting off abruptly the moment the wheel itself stops moving.
        """
        if abs(self._wheel_pending) < _WHEEL_STOP_THRESHOLD:
            self._wheel_pending = 0.0
            self._wheel_timer.stop()
            return

        step = self._wheel_pending * _WHEEL_EASE_RATIO
        self._wheel_pending -= step

        self._process_mouse(MOUSE_WHEEL)(step, 0.0)
        self.canvas.repaint()

    @_check_types.do
    def _orient_to_mouse_on_focal_plane(self, mouse_pos: _point.Point, wheel_delta: float) -> None:
        @_check_types.do
        def _norm(values) -> float:
            return math.sqrt(sum(v * v for v in values))

        camera = self.canvas.camera
        target = camera.get_position_on_focal_plane(mouse_pos)
        camera_pos = camera.position
        focal_pos = camera.focal_position

        current_forward = (
            focal_pos.x - camera_pos.x,
            focal_pos.y - camera_pos.y,
            focal_pos.z - camera_pos.z
        )
        desired_forward = (
            target.x - camera_pos.x,
            target.y - camera_pos.y,
            target.z - camera_pos.z
        )

        current_norm = _norm(current_forward)
        desired_norm = _norm(desired_forward)

        if current_norm < _EPSILON or desired_norm < _EPSILON:
            return

        current_forward = tuple(v / current_norm for v in current_forward)
        desired_forward = tuple(v / desired_norm for v in desired_forward)

        current_xz = (current_forward[0], current_forward[2])
        desired_xz = (desired_forward[0], desired_forward[2])

        current_xz_norm = _norm(current_xz)
        desired_xz_norm = _norm(desired_xz)

        yaw_delta = 0.0
        if current_xz_norm > _EPSILON and desired_xz_norm > _EPSILON:
            current_xz = tuple(v / current_xz_norm for v in current_xz)
            desired_xz = tuple(v / desired_xz_norm for v in desired_xz)
            dot = max(-1.0, min(1.0, (current_xz[0] * desired_xz[0]) + (current_xz[1] * desired_xz[1])))
            cross = (current_xz[0] * desired_xz[1]) - (current_xz[1] * desired_xz[0])
            yaw_delta = -math.degrees(math.atan2(cross, dot))

        current_pitch = math.degrees(math.atan2(current_forward[1], current_xz_norm))
        desired_pitch = math.degrees(math.atan2(desired_forward[1], desired_xz_norm))
        pitch_delta = desired_pitch - current_pitch

        if abs(yaw_delta) < _EPSILON and abs(pitch_delta) < _EPSILON:
            return

        walk_cfg = self.config.walk
        step_distance = abs(wheel_delta) * walk_cfg.sensitivity * walk_cfg.speed
        if step_distance < _EPSILON:
            return

        angular_step_size = math.degrees(math.atan2(step_distance, current_norm))
        largest_rotation_component = max(abs(yaw_delta), abs(pitch_delta))

        if largest_rotation_component > angular_step_size > _EPSILON:
            scale = angular_step_size / largest_rotation_component
            yaw_delta *= scale
            pitch_delta *= scale

        camera.PanTilt(yaw_delta / 6, pitch_delta / 6)

    @_check_types.do
    def on_mouse_motion(self, evt):
        """
        Handle the mouse motion event.

        Per-button behavior below is always the *default*: whatever's
        armed on ``canvas.active_handler_obj`` gets first refusal via
        ``_dispatch_to_active_handler`` -- no picking is done here (unlike
        the click-type handlers) since this fires on every pixel of
        movement and an unarmed hover never arms anything new on its own.
        """

        mouse_pos = _qt_pos(evt)

        if self._dispatch_to_active_handler(
            mouse_pos, _interaction.MouseInteraction.MOVE, self._is_motion
        ):
            # A consumed MOVE means a handler is actively armed and just
            # did something with this motion (advanced a drag, updated a
            # rotation gizmo) -- exactly what _is_motion exists to track,
            # so it must be set here too, not just in the raw
            # button-delta fallback below. Without this, _is_motion stays
            # False for a handler's entire drag (every one of its MOVE
            # events returns early right here), so the eventual LEFT_UP
            # reports had_motion=False for a drag that very much had
            # motion -- see Base3D.handle_interaction's own LEFT_UP
            # branch, which returns that had_motion value straight
            # through: a False there both lets the default click-toggle
            # deselect the object that was just dragged, AND (returning
            # False from handle_interaction) stops _dispatch_to_active_
            # handler from ever reaching its own active_handler_obj=None
            # cleanup, leaving the canvas permanently stuck routing every
            # future click back to this now-dead handler instead of
            # whatever gets freshly picked.
            self._is_motion = True

            # A consumed MOVE (e.g. the inner ring's own free-rotation
            # drag advancing) has no button-drag delta of its own to
            # reach the refresh below -- repaint now so the drag's
            # in-progress motion is actually visible, not just its final
            # state once the mouse eventually stops.
            self.canvas.repaint()
            return

        # A handler can still be armed (e.g. the rotation gizmo's outer-
        # ring tick hover) even when it declines to consume this MOVE --
        # that's deliberate, so camera controls keep working while it's
        # up (see BaseVar.handle_interaction's own docstring) -- but a
        # hover highlight change like that still needs a repaint of its
        # own, since with no mouse button held the button-driven refresh
        # below never runs at all.
        refresh = self.canvas.active_handler_obj is not None

        event = _events.GLEvent(_events.EVT_GL_MOUSE_MOVE)
        if not self._send_event(event, evt):
            return

        btns = evt.buttons()
        if btns != QtCore.Qt.MouseButton.NoButton:
            if self._mouse_pos is None:
                self._mouse_pos = mouse_pos

            delta = mouse_pos - self._mouse_pos
            self._mouse_pos = mouse_pos

            with self.canvas:
                if btns & QtCore.Qt.MouseButton.LeftButton:
                    self._is_motion = True
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

        if refresh:
            self.canvas.repaint()

    @_check_types.do
    def on_aux1_up(self, evt):
        """
        Handle the aux 1 up event.
        """

        if not self._is_motion:
            with self.canvas:
                mouse_pos = _qt_pos(evt)
                selected = _object_picker.find_object(
                    mouse_pos, self.canvas.objects_in_view,
                    self.canvas.camera, self._get_view_object)

                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX1_CLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        self.canvas.releaseMouse()

    @_check_types.do
    def on_aux1_down(self, evt):
        """
        Handle the aux 1 down event.
        """

        self._is_motion = False
        self.canvas.grabMouse()
        self._mouse_pos = _qt_pos(evt)

    @_check_types.do
    def on_aux1_dclick(self, evt):
        """
        Handle the aux 1 dclick event.
        """

        mouse_pos = _qt_pos(evt)
        selected = _object_picker.find_object(
            mouse_pos, self.canvas.objects_in_view,
            self.canvas.camera, self._get_view_object)

        with self.canvas:
            if selected:
                event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX1_DCLICK)
                event.SetGLObject(selected)
                self._send_event(event, evt)

    @_check_types.do
    def on_aux2_up(self, evt):
        """
        Handle the aux 2 up event.
        """

        if not self._is_motion:
            with self.canvas:
                mouse_pos = _qt_pos(evt)
                selected = _object_picker.find_object(
                    mouse_pos, self.canvas.objects_in_view,
                    self.canvas.camera, self._get_view_object)

                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX2_CLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        self.canvas.releaseMouse()

    @_check_types.do
    def on_aux2_down(self, evt):
        """
        Handle the aux 2 down event.
        """

        self._is_motion = False
        self.canvas.grabMouse()
        self._mouse_pos = _qt_pos(evt)

    @_check_types.do
    def on_aux2_dclick(self, evt):
        """
        Handle the aux 2 dclick event.
        """

        mouse_pos = _qt_pos(evt)
        selected = _object_picker.find_object(
            mouse_pos, self.canvas.objects_in_view,
            self.canvas.camera, self._get_view_object)

        with self.canvas:
            if selected:
                event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX2_DCLICK)
                event.SetGLObject(selected)
                self._send_event(event, evt)

    @staticmethod
    def _get_view_object(obj):  # NOQA
        # this function needs to be overridden to return the correct view object
        raise NotImplementedError
