# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import seal as _seal_2d
from .objects3d import seal as _seal_3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_seal as _pjt_seal


class Seal(_ObjectBase):
    """Represent a seal in :mod:`harness_designer.objects.seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _seal_2d.Seal = None
    obj3d: _seal_3d.Seal = None
    db_obj: "_pjt_seal.PJTSeal" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_seal.PJTSeal"):
        """Initialise the :class:`Seal` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_seal.PJTSeal`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _seal_2d.Seal(self, db_obj)
        self.obj3d = _seal_3d.Seal(self, db_obj)
        self.mainframe.add_object(self)
