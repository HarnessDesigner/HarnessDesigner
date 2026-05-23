# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import splice as _splice_2d
from .objects3d import splice as _splice_3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_splice as _pjt_splice


class Splice(_ObjectBase):
    """Represent a splice in :mod:`harness_designer.objects.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _splice_2d.Splice = None
    obj3d: _splice_3d.Splice = None
    db_obj: "_pjt_splice.PJTSplice" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_splice.PJTSplice"):
        """Initialise the :class:`Splice` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_splice.PJTSplice`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _splice_2d.Splice(self, db_obj)
        self.obj3d = _splice_3d.Splice(self, db_obj)
