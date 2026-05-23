# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base2d as _base2d


if TYPE_CHECKING:
    from ...database.project_db import pjt_cpa_lock as _pjt_cpa_lock
    from .. import cpa_lock as _cpa_lock


class CPALock(_base2d.Base2D):
    """Represent a CPA lock in :mod:`harness_designer.objects.objects2d.cpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_cpa_lock.CPALock"
    db_obj: "_pjt_cpa_lock.PJTCPALock"

    def __init__(self, parent: "_cpa_lock.CPALock",
                 db_obj: "_pjt_cpa_lock.PJTCPALock"):
        """Initialise the :class:`CPALock` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_cpa_lock.CPALock`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cpa_lock.PJTCPALock`
        """

        _base2d.Base2D.__init__(self, parent, db_obj)
