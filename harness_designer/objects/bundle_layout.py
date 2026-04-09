from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import bundle_layout as _bundle_layout_2d
from .objects3d import bundle_layout as _bundle_layout_3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_bundle_layout as _pjt_bundle_layout


class BundleLayout(_ObjectBase):
    obj2d: _bundle_layout_2d.BundleLayout = None
    obj3d: _bundle_layout_3d.BundleLayout = None
    db_obj: "_pjt_bundle_layout.PJTBundleLayout" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_bundle_layout.PJTBundleLayout"):
        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _bundle_layout_2d.BundleLayout(self, db_obj)
        self.obj3d = _bundle_layout_3d.BundleLayout(self, db_obj)
