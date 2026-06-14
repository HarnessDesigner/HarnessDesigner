# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import tpa_lock as _tpa_lock_2d
from .objects3d import tpa_lock as _tpa_lock_3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_tpa_lock as _pjt_tpa_lock


class TPALock(_ObjectBase):
    """Represent a TPA lock in :mod:`harness_designer.objects.tpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _tpa_lock_2d.TPALock = None
    obj3d: _tpa_lock_3d.TPALock = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_tpa_lock.PJTTPALock"):
        """Initialise the :class:`TPALock` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_tpa_lock.PJTTPALock`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _tpa_lock_2d.TPALock(self, db_obj)
        self.obj3d = _tpa_lock_3d.TPALock(self, db_obj)
        self.mainframe.add_object(self)
