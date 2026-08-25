# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Protractor-style rotation gizmo for mouse-driven angle changes.

Right-clicking a selected object shows three always-on activation rings
(one per Euler axis, :class:`~.editor_3d.rotation_ring.torus_ring.
TorusRing`). Clicking anywhere on one shows that axis's protractor -- an
object-space :class:`~.editor_3d.rotation_ring.inner_ring.InnerRing`
(spins with the object, grab-and-drag anywhere on its band free-rotates
about this axis) and a world-space :class:`~.editor_3d.rotation_ring.
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
:meth:`.editor_3d.rotation_ring.outer_ring.OuterRing._disc_rotation`.

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


class RotationRings(_object_base.ObjectBase):
    """Rotation gizmo shown around a selected object in angle mode."""

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
        self.mainframe.add_object(self)

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
        """Remove the gizmo from all 3 editors and unbind from the object."""
        self.obj3d.detach()
        self.objschematic.detach()
        self.objpegboard.detach()
        self.mainframe.remove_object(self)

    @_check_types.do
    def close(self):
        """Execute the close operation.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

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
