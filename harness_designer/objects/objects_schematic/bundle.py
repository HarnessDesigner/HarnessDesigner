# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_schematic as _base_schematic
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle as _pjt_bundle
    from .. import bundle as _bundle


class Bundle(_base_schematic.BaseSchematic):
    """Represent a bundle in :mod:`harness_designer.objects.objects_schematic.bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_bundle.Bundle" = None
    db_obj: "_pjt_bundle.PJTBundle"

    @_check_types.do
    def __init__(self, parent: "_bundle.Bundle",
                 db_obj: "_pjt_bundle.PJTBundle"):
        """Initialise the :class:`Bundle` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_bundle.Bundle`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_bundle.PJTBundle`
        """

        super().__init__(parent, db_obj, None, None, None, None, None)
