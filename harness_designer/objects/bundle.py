from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import bundle as _bundle_2d
from .objects3d import bundle as _bundle_3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_bundle as _pjt_bundle


class Bundle(_ObjectBase):
    obj2d: _bundle_2d.Bundle = None
    obj3d: _bundle_3d.Bundle = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_bundle.PJTBundle"):
        super().__init__(mainframe)

        self.db_obj = db_obj
        db_obj.set_object(self)

        self.obj2d = _bundle_2d.Bundle(self, db_obj)
        self.obj3d = _bundle_3d.Bundle(self, db_obj)

