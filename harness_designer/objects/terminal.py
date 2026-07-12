# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import terminal as _terminal_2d
from .objects3d import terminal as _terminal_3d
from ..geometry import point as _point


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_terminal as _pjt_terminal


class Terminal(_ObjectBase):
    """Represent a terminal in :mod:`harness_designer.objects.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _terminal_2d.Terminal = None
    obj3d: _terminal_3d.Terminal = None
    db_obj: "_pjt_terminal.PJTTerminal" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_terminal.PJTTerminal", project_load=False):
        """Initialise the :class:`Terminal` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_terminal.PJTTerminal`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _terminal_2d.Terminal(self, db_obj)
        self.obj3d = _terminal_3d.Terminal(self, db_obj)
        self.mainframe.add_object(self)

    def set_selected(self, flag):
        """Selecting a terminal selects its owning cavity instead.

        Terminals are never directly selectable — all manipulation of a
        terminal happens through the cavity it's placed in.
        """
        if flag:
            cavity = self.db_obj.cavity
            cavity_obj = cavity.get_object() if cavity is not None else None
            if cavity_obj is not None:
                cavity_obj.set_selected(True)
                return

        super().set_selected(flag)

    @property
    def wire_position(self) -> _point.Point:
        """Return the wire position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.db_obj.wire_position3d