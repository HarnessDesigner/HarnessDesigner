from typing import TYPE_CHECKING

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from .. import bundle_layout as _bundle_layout


class BundleLayout(_base2d.Base2D):
    _parent: "_bundle_layout.BundleLayout" = None

    def __init__(self, parent: "_bundle_layout.BundleLayout",
                 db_obj: "_pjt_bundle_layout.PJTBundleLayout"):

        _base2d.Base2D.__init__(self, parent)
        self._db_obj: "_pjt_bundle_layout.PJTBundleLayout" = db_obj
