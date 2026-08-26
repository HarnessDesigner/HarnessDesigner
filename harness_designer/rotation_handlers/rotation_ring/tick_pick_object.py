# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A single outer-protractor tick mark, wrapped just enough to be handed
to :func:`~harness_designer.gl.object_picker.find_object` -- reuses
:class:`~harness_designer.objects.objectsvar.base_var.BaseVar`'s own
obb/aabb math instead of a hand-rolled screen-space hit-test.

Deliberately NOT a real scene object: ``ObjectBase.__init__`` never gets
a ``self.mainframe.add_object(self)`` call the way
``drag_handlers/move_arrows.py``'s ``MoveArrows`` gets one, so a tick
never joins the object browser tree, the per-frame generic render loop,
or ``canvas.objects_in_view`` -- there can be up to
:data:`~.rotation_ring._protractor_base.TICK_COUNT` (360) of these alive
per active axis, rendered explicitly by
:class:`~._protractor_base.ProtractorRingBase`'s own ``render()``, never
through the generic per-object path. :class:`.outer_ring.OuterRing`
keeps its own plain list of these and hands it straight to
``find_object`` -- there's no global registry to avoid touching in the
first place, only ``add_object`` itself.

Still a genuine :class:`~...objects.object_base.ObjectBase` subclass
(not just a duck-typed lookalike) -- ``BaseVar.__init__``'s own ``parent``
type hint is enforced by ``_check_types.do`` at runtime the same way
Cython enforces it at compile time, so the object handed in as a tick's
``parent`` has to really be one.
"""

from typing import TYPE_CHECKING

from ...objects import object_base as _object_base
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ... import ui as _ui
    from ...objects.objectsvar import base_var as _base_var


class TickPickObject(_object_base.ObjectBase):
    """Facade for one tick mark.

    ``obj3d``/``objschematic``/``objpegboard`` all alias the SAME
    underlying view instance (see :meth:`set_view`) -- a tick only ever
    belongs to exactly one view (whichever :class:`.outer_ring.OuterRing`
    built it), so there's no reason to build 3 instances, 2 of them
    meaningless, just to satisfy generic code that expects an
    ``ObjectBase`` with the usual 3-view shape. Whichever of the three
    accessors a caller happens to use resolves to the one real object
    either way.
    """

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame"):
        _object_base.ObjectBase.__init__(self, mainframe, None)

    @_check_types.do
    def set_view(self, view_obj: "_base_var.BaseVar") -> None:
        self.obj3d = view_obj
        self.objschematic = view_obj
        self.objpegboard = view_obj

    @_check_types.do
    def delete(self) -> None:
        """No-op -- never registered via ``add_object``, so there's
        nothing in the mainframe/tree/render loop to unregister; the
        owning :class:`.outer_ring.OuterRing` just drops its reference.
        """

    @_check_types.do
    def close(self) -> None:
        raise NotImplementedError

    @_check_types.do
    def set_selected(self, flag: bool) -> None:
        pass

    @property
    @_check_types.do
    def is_selected(self) -> bool:
        return False

    @is_selected.setter
    @_check_types.do
    def is_selected(self, value: bool):
        pass
