# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_schematic as _base_schematic
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_tpa_lock as _pjt_tpa_lock
    from .. import tpa_lock as _tpa_lock


class TPALock(_base_schematic.BaseSchematic):
    """Represent a TPA lock in :mod:`harness_designer.objects.objects_schematic.tpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_tpa_lock.TPALock" = None
    db_obj: "_pjt_tpa_lock.PJTTPALock"

    @_check_types.do
    def __init__(self, parent: "_tpa_lock.TPALock",
                 db_obj: "_pjt_tpa_lock.PJTTPALock"):
        """Initialise the :class:`TPALock` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_tpa_lock.TPALock`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_tpa_lock.PJTTPALock`
        """

        super().__init__(parent, db_obj, None, None,
                         None, None, None)

    def render(self, shaders):
        pass
