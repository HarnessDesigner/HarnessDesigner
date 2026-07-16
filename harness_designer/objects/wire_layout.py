# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import wire_layout as _wire3d_layout
from .objects2d import wire_layout as _wire2d_layout
from .objectspeg import wire_layout as _wirepeg_layout


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire_layout as _pjt_wire_layout


class WireLayout(_ObjectBase):
    """Represent a wire layout in :mod:`harness_designer.objects.wire_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _wire2d_layout.WireLayout = None
    obj3d: _wire3d_layout.WireLayout = None
    objpeg: _wirepeg_layout.WireLayout = None
    db_obj: "_pjt_wire_layout.PJTWireLayout" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire_layout.PJTWireLayout", project_load=False):
        """Initialise the :class:`WireLayout` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_layout.PJTWireLayout`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _wire2d_layout.WireLayout(self, db_obj)
        self.obj3d = _wire3d_layout.WireLayout(self, db_obj)
        self.objpeg = _wirepeg_layout.WireLayout(self, db_obj)

        self.mainframe.add_object(self)
