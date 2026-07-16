# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import wire as _wire_2d
from .objects3d import wire as _wire_3d
from .objectspeg import wire as _wire_peg


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire as _pjt_wire


class Wire(_ObjectBase):
    """Represent a wire in :mod:`harness_designer.objects.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _wire_2d.Wire = None
    obj3d: _wire_3d.Wire = None
    objpeg: _wire_peg.Wire = None
    db_obj: "_pjt_wire.PJTWire" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire.PJTWire", project_load=False):
        """Initialise the :class:`Wire` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire.PJTWire`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _wire_2d.Wire(self, db_obj)
        self.obj3d = _wire_3d.Wire(self, db_obj)
        self.objpeg = _wire_peg.Wire(self, db_obj)

        self.mainframe.add_object(self)
