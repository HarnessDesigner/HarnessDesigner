# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base2d as _base2d


if TYPE_CHECKING:
    from ...database.project_db import pjt_cover as _pjt_cover
    from .. import cover as _cover


class Cover(_base2d.Base2D):
    """Represent a cover in :mod:`harness_designer.objects.objects2d.cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_cover.Cover" = None
    db_obj: "_pjt_cover.PJTCover"

    def __init__(self, parent: "_cover.Cover", db_obj: "_pjt_cover.PJTCover"):
        """Initialise the :class:`Cover` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_cover.Cover`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cover.PJTCover`
        """
        _base2d.Base2D.__init__(self, parent, db_obj)
