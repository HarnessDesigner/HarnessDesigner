from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase

from .objects2d import splice as _splice2d
from .objects3d import splice as _splice3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_splice as _pjt_splice


class Splice(_ObjectBase):
    obj_2d: _splice2d.Splice = None
    obj_3d: _splice3d.Splice = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_splice.PJTSplice"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_2d = _splice2d.Splice(mainframe.editor2d, db_obj)
        self.obj_3d = _splice3d.Splice(mainframe.editor3d, db_obj)
