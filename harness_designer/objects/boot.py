from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import boot as _boot


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_boot as _pjt_boot


class Boot(_ObjectBase):
    obj_3d: _boot.Boot = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_boot.PJTBoot"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_3d = _boot.Boot(mainframe.editor3d, db_obj)

