# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


class Note(_base_pegboard.BasePegboard):
    """Peg-board representation of a note.

    A note is an annotation, not a physical part placed on the board --
    it has no rendering presence.
    """
    db_obj: "_pjt_note.PJTNote"

    @_check_types.do
    def __init__(self, parent: "_note.Note", db_obj: "_pjt_note.PJTNote"):
        """Initialise the :class:`Note` instance.

        :param parent: Parent object.
        :type parent: :class:`_note.Note`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_note.PJTNote`
        """
        super().__init__(parent, db_obj, position=None, angle=None)
