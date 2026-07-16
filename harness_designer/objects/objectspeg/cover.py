# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import basepeg as _basepeg


if TYPE_CHECKING:
    from ...database.project_db import pjt_cover as _pjt_cover
    from .. import cover as _cover


class Cover(_basepeg.BasePeg):
    """Peg-board representation of a cover.

    A cover is a mounted sub-part of a housing assembly, not
    independently positioned on the board -- it has no rendering presence
    of its own (covered by its housing's own anchor).
    """
    db_obj: "_pjt_cover.PJTCover"

    def __init__(self, parent: "_cover.Cover", db_obj: "_pjt_cover.PJTCover"):
        """Initialise the :class:`Cover` instance.

        :param parent: Parent object.
        :type parent: :class:`_cover.Cover`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cover.PJTCover`
        """
        _basepeg.BasePeg.__init__(self, parent, db_obj, position=None, angle=None)
