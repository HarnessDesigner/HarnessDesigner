# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING
import weakref

from . import ObjectBase as _ObjectBase
from .objects_schematic import bundle as _bundle_schematic
from .objects_3d import bundle as _bundle_3d
from .objects_pegboard import bundle as _bundle_pegboard
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_bundle as _pjt_bundle
    from . import transition as _transition_obj


class Bundle(_ObjectBase):
    """Represent a bundle in :mod:`harness_designer.objects.bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: _bundle_schematic.Bundle = None
    obj3d: _bundle_3d.Bundle = None
    objpegboard: _bundle_pegboard.Bundle = None
    db_obj: "_pjt_bundle.PJTBundle" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_bundle.PJTBundle", project_load=False):
        """Initialise the :class:`Bundle` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_bundle.PJTBundle`
        """
        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.objschematic = _bundle_schematic.Bundle(self, db_obj)
        self.obj3d = _bundle_3d.Bundle(self, db_obj)
        self.objpegboard = _bundle_pegboard.Bundle(self, db_obj)

        # Sibling graph: whatever this bundle's own start/stop end attaches
        # to -- always a Transition (a bundle's trunk end can only ever
        # attach to a Transition, never directly to a Housing), or None for
        # a dangling/free-space end. Two bundles touching merge into one
        # row instead (see handlers.bundle_topology's bundle-to-bundle
        # join), same as two wires touching -- never a persistent sibling
        # link between two Bundles.
        self._start_sibling_ref = None
        self._stop_sibling_ref = None

        self.mainframe.add_object(self)

    @property
    @_check_types.do
    def start_sibling(self) -> "_transition_obj.Transition | None":
        """Whatever this bundle's start end attaches to (a Transition), or
        None for a dangling/free-space end."""
        return None if self._start_sibling_ref is None else self._start_sibling_ref()

    @property
    @_check_types.do
    def stop_sibling(self) -> "_transition_obj.Transition | None":
        """Whatever this bundle's stop end attaches to (a Transition), or
        None for a dangling/free-space end."""
        return None if self._stop_sibling_ref is None else self._stop_sibling_ref()

    @_check_types.do
    def set_sibling(self, other: "_transition_obj.Transition | None", end: str) -> None:
        """Record *other* as what this bundle's *end* ('start' or 'stop')
        attaches to.

        One-sided: this only stores this bundle's own side of the link.
        The reverse direction (Transition.add_bundle) is a separate,
        explicit call made by whichever handler is wiring the two objects
        together -- see handlers.transition_handler.

        :param other: The Transition attached at *end*, or None to clear it.
        :param end: 'start' or 'stop'.
        """
        ref = None if other is None else weakref.ref(other)

        if end == 'start':
            self._start_sibling_ref = ref
        elif end == 'stop':
            self._stop_sibling_ref = ref
        else:
            raise ValueError(f"end must be 'start' or 'stop', got {end!r}")

    @_check_types.do
    def delete(self):
        super().delete()
        self.mainframe.project.delete_bundle(self.db_obj.db_id)
        self.db_obj.delete()

    # TODO: We need to move things like wires so they are held here.
    #       anything that is held in any of the obj* class instances should
    #       only hold objects that areof the same instance type

    @_check_types.do
    def _delete(self):
        """Override delete to restore wire visibility."""
        # Restore visibility of all wires before deleting
        for ref in self._wires[:]:
            wire = ref()
            if wire is not None:
                wire.is_visible = True

        self._wires.clear()
        super()._delete()
