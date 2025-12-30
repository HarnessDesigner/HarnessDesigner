from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import bundle_layout as _bundle_layout


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_bundle_layout as _pjt_bundle_layout


class BundleLayout(_ObjectBase):
    obj_3d: _bundle_layout.BundleLayout = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_bundle_layout.PJTBundleLayout"):
        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_3d = _bundle_layout.BundleLayout(mainframe.editor3d, db_obj)
