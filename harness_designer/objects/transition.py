# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING
import weakref

from . import ObjectBase as _ObjectBase
from .objects_schematic import transition as _transition_schematic
from .objects3d import transition as _transition_3d
from .objectspeg import transition as _transition_peg
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_transition as _pjt_transition
    from . import bundle as _bundle_obj


class Transition(_ObjectBase):
    """Represent a transition in :mod:`harness_designer.objects.transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: _transition_schematic.Transition = None
    obj3d: _transition_3d.Transition = None
    objpeg: _transition_peg.Transition = None
    db_obj: "_pjt_transition.PJTTransition" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_transition.PJTTransition", project_load=False):
        """Initialise the :class:`Transition` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_transition.PJTTransition`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.objschematic = _transition_schematic.Transition(self, db_obj)
        self.obj3d = _transition_3d.Transition(self, db_obj)
        self.objpeg = _transition_peg.Transition(self, db_obj)

        # Sibling graph: at most one Bundle per branch slot (1-6), keyed by
        # branch_id -- mirrors PJTTransitionBranch.bundle's own point-id
        # match (start_point3d_id/stop_point3d_id landing on the branch's
        # own position3d_id), just as a live weakref instead of a fresh SQL
        # lookup every time. A Transition never forks a bundle's own row
        # (unlike Splice for wires) -- it's just a waypoint/branch marker
        # the bundle's trunk terminates at, so there's nothing to fork here;
        # this dict only records which bundle (if any) sits at each branch.
        self._bundle_refs: dict[int, weakref.ref] = {}

        self.mainframe.add_object(self)

    @_check_types.do
    def bundle_at(self, branch_id: int) -> "_bundle_obj.Bundle | None":
        """Return the Bundle attached at *branch_id* (1-6), or None."""
        ref = self._bundle_refs.get(branch_id)
        return None if ref is None else ref()

    @_check_types.do
    def branch_id_of(self, bundle: "_bundle_obj.Bundle") -> int | None:
        """Return which branch slot (1-6) *bundle* is attached at, or
        None if it isn't attached to this transition at all."""
        for branch_id, ref in self._bundle_refs.items():
            if ref() is bundle:
                return branch_id
        return None

    @property
    @_check_types.do
    def bundles(self) -> list["_bundle_obj.Bundle"]:
        """Every Bundle currently attached to any branch of this transition."""
        res = []
        for ref in self._bundle_refs.values():
            bundle = ref()
            if bundle is not None:
                res.append(bundle)
        return res

    @_check_types.do
    def add_bundle(self, bundle: "_bundle_obj.Bundle", end: str, branch_id: int) -> None:
        """Attach *bundle* to this transition at *branch_id* (1-6).

        Records the link on both sides: this transition's own
        ``_bundle_refs`` slot for *branch_id*, and a call to
        ``bundle.set_sibling(self, end)`` so the bundle knows what its own
        *end* ('start' or 'stop') attaches to.

        :param bundle: The bundle being attached.
        :param end: Which of the bundle's own ends is attaching -- 'start'
            or 'stop'.
        :param branch_id: Which branch slot (1-6) the bundle attaches at.
        """
        self._bundle_refs[branch_id] = weakref.ref(bundle)
        bundle.set_sibling(self, end)

    @_check_types.do
    def replace_bundle(self, old: "_bundle_obj.Bundle", new: "_bundle_obj.Bundle") -> None:
        """Re-home whichever branch slot(s) reference *old* to *new*
        instead -- used when two bundles merge into one row (see
        handlers.bundle_topology.merge_bundles) and *old* is about to be
        discarded.
        """
        for branch_id, ref in list(self._bundle_refs.items()):
            if ref() is old:
                self._bundle_refs[branch_id] = weakref.ref(new)

    @_check_types.do
    def delete(self):
        # TODO: Branches should be left dangling. layouts at each branch should
        #       be removed. Wires should be left alone.
        super().delete()
        self.mainframe.project.delete_transition(self.db_obj.db_id)
        self.db_obj.delete()
