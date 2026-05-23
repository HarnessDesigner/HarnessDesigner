# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base2d as _base2d


if TYPE_CHECKING:
    from ...database.project_db import pjt_seal as _pjt_seal
    from .. import seal as _seal


class Seal(_base2d.Base2D):
    """Represent a seal in :mod:`harness_designer.objects.objects2d.seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_seal.Seal" = None
    db_obj: "_pjt_seal.PJTSeal"

    def __init__(self, parent: "_seal.Seal", db_obj: "_pjt_seal.PJTSeal"):
        """Initialise the :class:`Seal` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_seal.Seal`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_seal.PJTSeal`
        """
        _base2d.Base2D.__init__(self, parent, db_obj)
