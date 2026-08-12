# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects_schematic import cover as _cover_schematic
from .objects_3d import cover as _cover_3d
from .objects_pegboard import cover as _cover_pegboard
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_cover as _pjt_cover


class Cover(_ObjectBase):
    """Represent a cover in :mod:`harness_designer.objects.cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: _cover_schematic.Cover = None
    obj3d: _cover_3d.Cover = None
    objpegboard: _cover_pegboard.Cover = None
    db_obj: "_pjt_cover.PJTCover" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_cover.PJTCover", project_load=False):
        """Initialise the :class:`Cover` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cover.PJTCover`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.objschematic = _cover_schematic.Cover(self, db_obj)
        self.obj3d = _cover_3d.Cover(self, db_obj)
        self.objpegboard = _cover_pegboard.Cover(self, db_obj)
        self.mainframe.add_object(self)

    @_check_types.do
    def delete(self):
        super().delete()
        self.mainframe.project.delete_cover(self.db_obj.db_id)
        self.db_obj.delete()
