# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base2d as _base2d


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from .. import bundle_layout as _bundle_layout


class BundleLayout(_base2d.Base2D):
    """Represent a bundle layout in :mod:`harness_designer.objects.objects2d.bundle_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_bundle_layout.BundleLayout" = None
    db_obj: "_pjt_bundle_layout.PJTBundleLayout"

    def __init__(self, parent: "_bundle_layout.BundleLayout",
                 db_obj: "_pjt_bundle_layout.PJTBundleLayout"):
        """Initialise the :class:`BundleLayout` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_bundle_layout.BundleLayout`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_bundle_layout.PJTBundleLayout`
        """

        _base2d.Base2D.__init__(self, parent, db_obj)
