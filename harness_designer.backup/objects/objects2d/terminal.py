from typing import TYPE_CHECKING

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal


class Terminal(_base2d.Base2D):
    _parent: "_terminal.Terminal" = None

    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal"):

        _base2d.Base2D.__init__(self, parent)
        self._db_obj: "_pjt_terminal.PJTTerminal" = db_obj
