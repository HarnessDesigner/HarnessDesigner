from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import boot as _boot_2d
from .objects3d import boot as _boot_3d

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_boot as _pjt_boot


class Boot(_ObjectBase):
    obj2d: _boot_2d.Boot = None
    obj3d: _boot_3d.Boot = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_boot.PJTBoot"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        db_obj.set_object(self)

        self.obj2d = _boot_2d.Boot(self, db_obj)
        self.obj3d = _boot_3d.Boot(self, db_obj)


