# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_schematic as _base_schematic
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_boot as _pjt_boot
    from .. import boot as _boot


class Boot(_base_schematic.BaseSchematic):
    """Represent a boot in :mod:`harness_designer.objects.objects_schematic.boot`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_boot.Boot" = None
    db_obj: "_pjt_boot.PJTBoot"

    @_check_types.do
    def __init__(self, parent: "_boot.Boot", db_obj: "_pjt_boot.PJTBoot"):
        """Initialise the :class:`Boot` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_boot.Boot`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_boot.PJTBoot`
        """

        super().__init__(parent, db_obj, None, None,
                         None, None, None)

    def render(self, shaders):
        pass
