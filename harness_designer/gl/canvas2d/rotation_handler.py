# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Base class for editor-specific rotate-drag mechanics.

Long-lived: one instance per :class:`~.mouse_handler.MouseHandler`,
constructed once in its ``__init__`` (see ``MouseHandler.
_get_rotate_handler``) and reused for the editor's entire lifetime -- NOT
one instance per drag the way
:class:`harness_designer.gl.canvas3d.rotation_rings.DragRotate` is. Same
rationale as :class:`~.drag_handler.DragHandler`: a subclass that needs
state that's expensive to rebuild can cache it once and keep it warm
across many separate rotate-drags instead of reconstructing it every
time one starts.

Lifecycle per drag: :meth:`can_rotate` (eligibility -- e.g. rejecting a
Wire outright, or a terminal that's currently seated in a cavity), then
:meth:`begin`, then this instance is called directly with each
mouse-move for the duration of the drag, then :meth:`end`.

Mirrors :class:`harness_designer.gl.canvas3d.rotation_rings.DragRotate`'s
per-frame screen-angle math, adapted for a permanently locked top-down
view where there is only ever one rotation axis (world Y -- "spin in the
schematic/board plane"), never a locked-at-drag-start choice of X/Y/Z the
way the 3D editor's gizmo needs -- so unlike ``DragRotate`` there is no
``axis`` parameter anywhere here.

Not the gizmo itself -- see
:class:`harness_designer.gl.canvas2d.rotation_ring.RotationRing` for
that. Not keyed to any specific object type -- *target* only needs to
duck-type ``.position`` (``.x``/``.z``) and ``.angle.y``, the same
contract ``RotationRing`` itself already requires of it.
"""

from typing import TYPE_CHECKING

import math

from ..canvas3d import rotation_rings as _rotation_rings
from ...geometry import point as _point
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import canvas as _canvas
    from . import rotation_ring as _rotation_ring


class RotationHandler:
    """Base class for editor-specific rotate-drag mechanics.

    See the module docstring for the full rationale.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas"):
        """Initialise the :class:`RotationHandler` instance.

        Constructed once (see the module docstring) -- a subclass adding
        its own long-lived, cross-drag caches should build them here,
        not in :meth:`begin`.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """
        self.canvas = canvas

        # Per-drag state -- reset in begin()/end().
        self.target = None
        self.rings = None
        self.start_value = None
        self._cx = None
        self._cy = None
        self._prev_phi = None
        self._total = 0.0

    @_check_types.do
    def can_rotate(self, target) -> bool:
        """Return whether *target* can be rotated via the ring gizmo at
        all by this handler.

        Must be overridden by the subclass -- e.g. rejecting a Wire
        outright, or a terminal currently seated in a cavity. Called by
        the ``MouseHandler`` before the gizmo is even shown.

        :param target: The view-object under the mouse -- already
            resolved via ``MouseHandler._get_view_object``.
        :rtype: bool
        """
        raise NotImplementedError

    @_check_types.do
    def begin(self, target, rings: "_rotation_ring.RotationRing") -> None:
        """Start a new rotate-drag on *target*'s grab handle -- resets
        this handler's per-drag state (not its long-lived, cross-drag
        caches).

        Base implementation seeds the screen-angle tracking state
        :meth:`__call__` needs; override to also seed whatever
        additional per-drag state the subclass needs, calling
        ``super().begin(target, rings)`` first.

        :param target: The object/anchor being rotated -- already
            resolved by the caller via ``MouseHandler._get_view_object``.
        :param rings: The active gizmo this drag is dragging the grab
            handle of.
        :type rings: :class:`~.rotation_ring.RotationRing`
        """
        self.target = target
        self.rings = rings

        self.start_value = float(target.angle.y)

        center_screen = self.canvas.camera.ProjectPoint(target.position)
        self._cx = float(center_screen.x)
        self._cy = float(center_screen.y)

        self._prev_phi = None
        self._total = 0.0

    @_check_types.do
    def _screen_phi(self, mouse_pos: _point.Point) -> float:
        """Return the math-orientation angle of the cursor around the
        gizmo's screen-space center.

        Screen Y grows downward, negated for counter-clockwise-positive
        math -- no camera-facing sign flip is needed here (unlike the 3D
        editor's ``DragRotate``), every 2D-plane editor only ever has one
        fixed top-down viewing direction.

        :param mouse_pos: Mouse position in screen coordinates.
        :type mouse_pos: :class:`~harness_designer.geometry.point.Point`
        :rtype: float
        """
        return math.atan2(-(float(mouse_pos.y) - self._cy),
                          float(mouse_pos.x) - self._cx)

    @_check_types.do
    def _snap_angle(self) -> float:
        """Return the rotation-drag snap increment in degrees, or ``0``
        for free rotation.

        Must be overridden by the subclass -- e.g. the schematic editor
        forces a hard 90-degree detent, the peg board editor's detent is
        optional/user-configurable. The drag mechanics that apply
        whatever this returns (:meth:`__call__`) are identical either
        way -- only the value differs.

        :rtype: float
        """
        raise NotImplementedError

    @_check_types.do
    def __call__(self, mouse_pos: _point.Point):
        """Update the live in-progress rotation from the current mouse
        position, and write it straight through to the target's live,
        DB-backed ``angle.y``.

        :param mouse_pos: Mouse position in screen coordinates.
        :type mouse_pos: :class:`~harness_designer.geometry.point.Point`
        """
        phi = self._screen_phi(mouse_pos)

        if self._prev_phi is None:
            self._prev_phi = phi
            return

        # Wrap-safe incremental step so crossing the atan2 seam doesn't jump.
        step = math.atan2(math.sin(phi - self._prev_phi),
                          math.cos(phi - self._prev_phi))
        self._prev_phi = phi
        self._total += step

        new_value = _rotation_rings.wrap_angle(
            self.start_value + math.degrees(self._total))

        snap = self._snap_angle()
        if snap:
            new_value = _rotation_rings.wrap_angle(
                round(round(new_value / snap) * snap, 2))

        self.target.angle.y = new_value

    @_check_types.do
    def end(self) -> None:
        """End the current rotate-drag -- clears this handler's per-drag
        state.

        The handler instance itself is not discarded -- it stays alive
        on the ``MouseHandler`` for the next drag (see the module
        docstring). Base implementation just clears :attr:`target`/
        :attr:`rings`; override to also release/undo whatever per-drag
        state the subclass's own :meth:`begin` acquired, calling
        ``super().end()`` too.
        """
        self.target = None
        self.rings = None
