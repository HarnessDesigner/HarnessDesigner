# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base2d as _base2d


if TYPE_CHECKING:
    from ...database.project_db import pjt_boot as _pjt_boot
    from .. import boot as _boot


class Boot(_base2d.Base2D):
    """Represent a boot in :mod:`harness_designer.objects.objects2d.boot`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_boot.Boot" = None
    db_obj: "_pjt_boot.PJTBoot"

    def __init__(self, parent: "_boot.Boot", db_obj: "_pjt_boot.PJTBoot"):
        """Initialise the :class:`Boot` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_boot.Boot`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_boot.PJTBoot`
        """
        _base2d.Base2D.__init__(self, parent, db_obj)
