# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import cavity as _cavity_2d
from .objects3d import cavity as _cavity_3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_cavity as _pjt_cavity
    from . import housing as _housing
    from . import terminal as _terminal
    from . import seal as _seal


class Cavity(_ObjectBase):
    """Represent a cavity in :mod:`harness_designer.objects.cavity`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _cavity_2d.Cavity = None
    obj3d: _cavity_3d.Cavity = None
    db_obj: "_pjt_cavity.PJTCavity" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_cavity.PJTCavity"):
        """Initialise the :class:`Cavity` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cavity.PJTCavity`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _cavity_2d.Cavity(self, db_obj)
        self.obj3d = _cavity_3d.Cavity(self, db_obj)
        self.mainframe.add_object(self)
