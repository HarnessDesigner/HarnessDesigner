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
    db_obj: "_pjt_boot.PJTBoot" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_boot.PJTBoot"):

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _boot_2d.Boot(self, db_obj)
        self.obj3d = _boot_3d.Boot(self, db_obj)




