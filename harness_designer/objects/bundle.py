from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import bundle as _bundle


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_bundle as _pjt_bundle


class Bundle(_ObjectBase):
    obj_3d: _bundle.Bundle = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_bundle.PJTBundle"):
        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_3d = _bundle.Bundle(mainframe.editor3d, db_obj)
