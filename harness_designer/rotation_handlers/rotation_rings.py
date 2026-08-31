# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Protractor-style rotation gizmo for mouse-driven angle changes.

Right-clicking a selected object shows three always-on activation rings
(one per Euler axis, :class:`~.rotation_ring.torus_ring.
TorusRing`). Clicking anywhere on one shows that axis's protractor -- an
object-space :class:`~.rotation_ring.inner_ring.InnerRing`
(spins with the object, grab-and-drag anywhere on its band free-rotates
about this axis) and a world-space :class:`~.rotation_ring.
outer_ring.OuterRing` (own spin fixed, hover a tick to highlight it,
click to snap the object's local zero to that exact angle) -- and dims
the other two axes' torus rings. The Euler value is the only thing ever
written -- the quaternion is rebuilt from it by :class:`_angle.Angle`
(see the Euler rule in CODEBASE_MAP.md).

Ring planes follow the nested Euler order used by
``Quaternion.from_euler`` (effective matrix ``Ry·Rx·Rz``, i.e. Z
innermost, X middle, Y outermost -- verified numerically), exactly like
the old single-ring-per-axis gizmo this replaces:

- y ring: fixed in world space (normal = world Y)
- x ring: normal = Ry @ X
- z ring: normal = Ry·Rx @ Z (full rotation applied to Z)

Each axis's outer (world-space) ring holds its OWN Euler slot at zero
while still nesting under the other two, so its own tick-zero never
moves even while the object (and the inner ring) spin past it -- see
:meth:`.rotation_ring.outer_ring.OuterRing._disc_rotation`.

This module is just the facade -- ``RotationRings`` -- that ties one
view-specific implementation per view together (mirrors the same
facade/view-package split every ``objects.*`` type already uses, e.g.
``objects.wire.Wire`` holding ``obj3d``/``objschematic``): the real 3D
gizmo lives in :mod:`.editor_3d.generic`, the (currently dummy)
schematic one in :mod:`.editor_schematic.generic`.
"""

from typing import TYPE_CHECKING

from .editor_3d import generic as _editor_3d_generic
from .editor_schematic import generic as _editor_schematic_generic
from .editor_pegboard import generic as _editor_pegboard_generic
from ..objects import object_base as _object_base
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..gl.canvas_3d import canvas as _canvas
    from .. import objects as _objects
    from ..gl import shaders as _shaders


class RotationRings(_object_base.ObjectBase):
    """Rotation gizmo shown around a selected object in angle mode.

    Deliberately NOT registered via ``mainframe.add_object`` -- rendered
    instead through ``BaseVar.render_handler()``, called directly by
    ``canvas_base.py`` at the same point as the selected object's own
    special rendering, not through the ordinary per-object scene
    pipeline. Registering it there mixed its own translucent-washer
    draws into the arbitrary per-object bucket order, ahead of the
    selected object's own deferred translucent-shell/depth-only passes
    -- since neither this gizmo's own draws nor those passes agreed on
    who owned the depth buffer at that point in the frame, both ended up
    with visibly wrong compositing.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", selected: "_objects.ObjectBase"):
        """Initialise the :class:`RotationRings` instance.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        :param selected: The selected object the rings surround.
        :type selected: :class:`_objects.ObjectBase`
        """
        mainframe = canvas.mainframe

        _object_base.ObjectBase.__init__(self, mainframe, None)
        self.selected = selected
        self.objschematic = _editor_schematic_generic.Rings2D(self, selected, mainframe)
        self.objpegboard = _editor_pegboard_generic.RingsPegboard(self, selected, mainframe)
        self.obj3d = _editor_3d_generic.Rings3D(self, selected, mainframe)
        self._treeitem = None

        # Which one of the 3 view-specific gizmos above actually gets
        # drawn by :meth:`render` -- resolved once, here, from *canvas*
        # (whichever one of editor3d/editor2d/editor_pegboard's own
        # canvas armed this instance -- see the 3 call sites in
        # objects_3d/objects_schematic/objects_pegboard's own
        # ``base_*.py``), rather than every call site reaching into a
        # RotationRings-specific attribute (.obj3d/.objschematic/
        # .objpegboard) itself. That reach-in is exactly what made a
        # plain drag handler's own render() call site (which has no such
        # attributes) crash -- see BaseVar.render_handler's own
        # docstring: every handler type exposes the same render(shaders)
        # entry point so the caller never needs to know which kind of
        # handler is actually armed.
        if canvas is mainframe.editor2d.editor:
            self._render_target = self.objschematic
        elif canvas is mainframe.editor_pegboard.editor:
            self._render_target = self.objpegboard
        else:
            self._render_target = self.obj3d

        # Some object types track a user-settable "is my angle locked,
        # or does something else keep computing it for me" flag --
        # currently only Note (see objects.note.Note's own
        # is_angle_locked/lock_angle/unlock_angle, which delegate to
        # objects_3d.note.Note's real camera-tracking logic), duck-typed
        # here rather than checked by isinstance -- this class has no
        # business knowing Note exists, and any future object type
        # gaining the same three members picks up the same behavior for
        # free.
        #
        # Opening the rings on one of these while it's still unlocked
        # locks it immediately -- the angle it's about to be dragged
        # from must be a real, persisted value, not whatever
        # placeholder/computed value it happened to be showing -- and
        # remembers what that angle was AT the moment of locking, so
        # :meth:`delete` (the one method every close path actually
        # calls, regardless of how the session ends) can undo the lock
        # again if it turns out to have ended without the angle ever
        # actually changing. An accidental open/close click must not
        # leave the object stuck non-following for no reason. An object
        # that was already locked before this session ever started is
        # never touched by any of this -- the lock/snapshot only happen
        # together, right here, so there's nothing to undo otherwise.
        self._angle_lock_snapshot: tuple | None = None
        if (
            hasattr(selected, 'is_angle_locked') and hasattr(selected, 'lock_angle') and
            hasattr(selected, 'unlock_angle') and not selected.is_angle_locked
        ):
            selected.lock_angle()
            self._angle_lock_snapshot = tuple(selected.db_obj.angle3d.as_euler_float)

    @_check_types.do
    def set_treeitem(self, treeitem):
        """Set the treeitem.

        :param treeitem: Value for ``treeitem``.
        :type treeitem: UNKNOWN
        """
        self._treeitem = treeitem

    @_check_types.do
    def get_treeitem(self):
        """Return the treeitem.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._treeitem

    @_check_types.do
    def __del__(self):
        """Execute the del operation."""

        # we need to avoid an error that can occur when the application closes
        # and the rings have not yet been removed. Deleting the rings after
        # the application closes tried to update the canvas after it has already
        # been deleted and this causes a runtime error to occur
        try:
            self.delete()
        except RuntimeError:
            pass

    @_check_types.do
    def delete(self):
        """Unbind from the tracked object and free each view's GL buffers
        -- never registered via ``add_object`` (see this class's own
        docstring), so there's nothing in the mainframe/tree/render loop
        to unregister.

        The sole method every close path (a plain right-click toggle-off
        or a miss-click that dismisses the gizmo -- see
        ``objects_3d.base_3d.Base3D._handle_rotation_interaction``'s own
        two branches, and its schematic/pegboard siblings) actually
        calls -- which is exactly why the angle-lock revert check
        belongs here rather than duplicated at each of those call sites
        (or worse, inferred indirectly from before/after state around
        them): see :meth:`__init__`'s own docstring for the full
        reasoning.
        """
        if self._angle_lock_snapshot is not None:
            db_obj = self.selected.db_obj
            if tuple(db_obj.angle3d.as_euler_float) == self._angle_lock_snapshot:
                self.selected.unlock_angle()

        self.obj3d.detach()
        self.objschematic.detach()
        self.objpegboard.detach()

    @_check_types.do
    def close(self):
        """Execute the close operation.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        """Render this gizmo -- called via ``BaseVar.render_handler()``,
        same uniform entry point every handler type exposes (see
        :meth:`drag_handlers.base.DragHandlerBase.render` and
        :meth:`add_handlers.base.AddHandlerBase.render`). Delegates to
        whichever one of :attr:`obj3d`/:attr:`objschematic`/
        :attr:`objpegboard` matches the view that armed this instance
        (see :attr:`_render_target`, resolved once in :meth:`__init__`).
        """
        self._render_target.render(shaders)

    @_check_types.do
    def set_selected(self, flag):
        """Set the selected.

        :param flag: Value for ``flag``.
        :type flag: UNKNOWN
        """
        pass

    @property
    @_check_types.do
    def is_selected(self) -> bool:
        """Return the is selected.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return False

    @is_selected.setter
    @_check_types.do
    def is_selected(self, value: bool):
        """Set the is selected.

        :param value: Value to store or process.
        :type value: bool
        """
        pass
