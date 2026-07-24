# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import housing as _housing_2d
from .objects3d import housing as _housing_3d
from .objectspeg import housing as _housing_peg

from . import cavity as _cavity
from .. import debug as _debug


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_housing as _pjt_housing


class Housing(_ObjectBase):
    """Represent a housing in :mod:`harness_designer.objects.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _housing_2d.Housing = None
    obj3d: _housing_3d.Housing = None
    objpeg: _housing_peg.Housing = None
    db_obj: "_pjt_housing.PJTHousing" = None

    @_debug.logfunc
    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_housing.PJTHousing", project_load=False):
        """Initialise the :class:`Housing` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_housing.PJTHousing`
        """

        if not project_load:
            for cavity in db_obj.cavities:
                if cavity is None:
                    continue

                cavity = _cavity.Cavity(mainframe, cavity)
                mainframe.project.add_cavity(cavity)

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _housing_2d.Housing(self, db_obj)
        self.obj3d = _housing_3d.Housing(self, db_obj)
        self.objpeg = _housing_peg.Housing(self, db_obj)

        self.seals = []
        self.tpa_locks = []
        self.cpa_locks = []

        self.mainframe.add_object(self)

    @property
    def cavities(self) -> list[_cavity.Cavity]:
        res = []
        for cavity in self.db_obj.cavities:
            if cavity is None:
                continue

            res.append(cavity.get_object())

        return res

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
