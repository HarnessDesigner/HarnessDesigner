# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects_schematic import housing as _housing_schematic
from .objects_3d import housing as _housing_3d
from .objects_pegboard import housing as _housing_pegboard

from . import cavity as _cavity
from .. import debug as _debug
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_housing as _pjt_housing


class Housing(_ObjectBase):
    """Represent a housing in :mod:`harness_designer.objects.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: _housing_schematic.Housing = None
    obj3d: _housing_3d.Housing = None
    objpegboard: _housing_pegboard.Housing = None
    db_obj: "_pjt_housing.PJTHousing" = None

    @_debug.logfunc
    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_housing.PJTHousing", project_load=False):
        """Initialise the :class:`Housing` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_housing.PJTHousing`
        """

        # Pure DB-layer op -- doesn't touch/construct any Cavity/Terminal
        # object instances itself, just pre-seeds the PJTCavity/PJTTerminal
        # rows' own name/cross-reference caches -- so this runs unconditionally
        # here (project_load or not) rather than only from _construct_cavities,
        # regardless of whether this housing's cavities happen to already
        # exist as PJTCavity singletons by this point (project load) or not
        # (interactive add).
        db_obj.cache_names()

        if not project_load:
            # Deferred one Qt event-loop iteration past this housing's
            # own construction (see _construct_cavities) -- Cavity2D
            # looks up its owning Housing2D at its own construction time
            # (via db_obj.housing.get_object().objschematic, see
            # objects_schematic/cavity.py) to register for batched cavity/
            # terminal name updates, which needs this housing already
            # fully constructed and registered (db_obj.set_object/
            # mainframe.add_object, below) by the time it runs -- not
            # guaranteed yet at this point, this line included. Must be
            # CallLater, not CallAfter -- CallAfter runs immediately
            # (no deferral at all) when called from the main thread,
            # which this always is, defeating the purpose entirely.
            from .. import app as _app

            _app.CallLater(self._construct_cavities)

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.objschematic = _housing_schematic.Housing(self, db_obj)
        self.obj3d = _housing_3d.Housing(self, db_obj)
        self.objpegboard = _housing_pegboard.Housing(self, db_obj)

        self.seals = []
        self.tpa_locks = []
        self.cpa_locks = []

        self.mainframe.add_object(self)

    @_check_types.do
    def _construct_cavities(self) -> None:
        """Construct every ``Cavity`` wrapper for this housing's own
        existing cavity rows -- see the ``CallAfter`` call in
        :meth:`__init__` for why this is deferred rather than run
        directly there. ``__init__`` already called
        ``db_obj.cache_names()``, so ``self.db_obj.cavities`` below
        hits the pre-populated cache instead of querying per cavity.
        """
        for cavity in self.db_obj.cavities:
            if cavity is None:
                continue

            cavity_obj = _cavity.Cavity(self.mainframe, cavity)
            self.mainframe.project.add_cavity(cavity_obj)

    @property
    @_check_types.do
    def cavities(self) -> list[_cavity.Cavity]:
        res = []
        for cavity in self.db_obj.cavities:
            if cavity is None:
                continue

            res.append(cavity.get_object())

        return res

    @_check_types.do
    def delete(self):
        """Cascade-delete every part attached to this housing.

        Nothing else walks this ownership graph -- cavities (and any
        terminal seated in one), the seal, the CPA lock, both TPA locks,
        the cover, and the boot are all rows that only exist by virtue of
        this housing's db_id, but none of that is expressed as attributes
        Python holds onto (see the dead ``self.seals``/``self.tpa_locks``/
        ``self.cpa_locks`` lists above, never populated by any handler) --
        it is only queryable through the housing_id lookups on db_obj. Skip
        straight to ``super().delete()`` for a part with none of these.
        """

        # TODO: we should figure out how to hold references to the accessory
        #       objects that are attached in this class itself. This would be a
        #       cleaner approach to performing a proper taredown.

        @_check_types.do
        def _delete_child(db_row):
            if db_row is None:
                return

            obj = db_row.get_object()
            if obj is not None:
                obj.delete()

        for cavity in self.db_obj.cavities:
            if cavity is None:
                continue

            _delete_child(cavity.terminal)
            _delete_child(cavity.seal)
            _delete_child(cavity)

        _delete_child(self.db_obj.seal)
        _delete_child(self.db_obj.cpa_lock)

        for tpa_lock in self.db_obj.tpa_locks:
            _delete_child(tpa_lock)

        _delete_child(self.db_obj.cover)
        _delete_child(self.db_obj.boot)

        super().delete()

        self.mainframe.project.delete_housing(self.db_obj.db_id)
        self.db_obj.delete()
