# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base2d as _base2d
from ...geometry import point as _point
from ...geometry import angle as _angle


if TYPE_CHECKING:
    from ...database.project_db import pjt_tpa_lock as _pjt_tpa_lock
    from .. import tpa_lock as _tpa_lock


class TPALock(_base2d.Base2D):
    """Represent a TPA lock in :mod:`harness_designer.objects.objects2d.tpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_tpa_lock.TPALock" = None
    db_obj: "_pjt_tpa_lock.PJTTPALock"

    def __init__(self, parent: "_tpa_lock.TPALock",
                 db_obj: "_pjt_tpa_lock.PJTTPALock"):
        """Initialise the :class:`TPALock` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_tpa_lock.TPALock`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_tpa_lock.PJTTPALock`
        """

        _base2d.Base2D.__init__(self, parent, db_obj, None, None)
