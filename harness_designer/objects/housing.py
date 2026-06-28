# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import housing as _housing_2d
from .objects3d import housing as _housing_3d

from . import cavity as _cavity


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_housing as _pjt_housing


class Housing(_ObjectBase):
    """Represent a housing in :mod:`harness_designer.objects.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _housing_2d.Housing = None
    obj3d: _housing_3d.Housing = None

    db_obj: "_pjt_housing.PJTHousing" = None

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


