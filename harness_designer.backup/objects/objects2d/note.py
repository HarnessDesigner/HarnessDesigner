
from typing import TYPE_CHECKING
import weakref

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import base2d as _base2d


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


class Note(_base2d.Base2D):
    _parent: "_note.Note" = None

    def __init__(self, parent: "_note.Note", db_obj: "_pjt_note.PJTNote"):
        _base2d.Base2D.__init__(self, parent)

        self._db_obj: "_pjt_note.PJTNote" = db_obj

        self._position = db_obj.point3d.point
        self._o_position = self._position.copy()
        self._angle = db_obj.angle2d

        self._color = db_obj.color.ui

        self._position.bind(self._update_position)
        self._angle.bind(self._update_angle)
