# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from .. import cavity as _cavity


class Cavity(_base_pegboard.BasePegboard):
    """Peg-board representation of a cavity.

    A cavity is a sub-feature of a housing, not an independently placed
    physical part -- it has no rendering presence of its own on the board
    (a seated terminal resolves through its housing's own anchor).
    """
    db_obj: "_pjt_cavity.PJTCavity"

    @_check_types.do
    def __init__(self, parent: "_cavity.Cavity", db_obj: "_pjt_cavity.PJTCavity"):
        """Initialise the :class:`Cavity` instance.

        :param parent: Parent object.
        :type parent: :class:`_cavity.Cavity`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cavity.PJTCavity`
        """
        _base_pegboard.BasePegboard.__init__(self, parent, db_obj, position=None, angle=None)
