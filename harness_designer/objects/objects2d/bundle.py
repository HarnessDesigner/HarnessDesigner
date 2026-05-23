# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base2d as _base2d


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle as _pjt_bundle
    from .. import bundle as _bundle


class Bundle(_base2d.Base2D):
    """Represent a bundle in :mod:`harness_designer.objects.objects2d.bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_bundle.Bundle" = None
    db_obj: "_pjt_bundle.PJTBundle"

    def __init__(self, parent: "_bundle.Bundle",
                 db_obj: "_pjt_bundle.PJTBundle"):
        """Initialise the :class:`Bundle` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_bundle.Bundle`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_bundle.PJTBundle`
        """

        _base2d.Base2D.__init__(self, parent, db_obj)
