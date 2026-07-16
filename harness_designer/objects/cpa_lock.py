# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import cpa_lock as _cpa_lock_2d
from .objects3d import cpa_lock as _cpa_lock_3d
from .objectspeg import cpa_lock as _cpa_lock_peg


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_cpa_lock as _pjt_cpa_lock


class CPALock(_ObjectBase):
    """Represent a CPA lock in :mod:`harness_designer.objects.cpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _cpa_lock_2d.CPALock = None
    obj3d: _cpa_lock_3d.CPALock = None
    objpeg: _cpa_lock_peg.CPALock = None
    db_obj: "_pjt_cpa_lock.PJTCPALock" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_cpa_lock.PJTCPALock", project_load=False):
        """Initialise the :class:`CPALock` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cpa_lock.PJTCPALock`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _cpa_lock_2d.CPALock(self, db_obj)
        self.obj3d = _cpa_lock_3d.CPALock(self, db_obj)
        self.objpeg = _cpa_lock_peg.CPALock(self, db_obj)

        self.mainframe.add_object(self)
