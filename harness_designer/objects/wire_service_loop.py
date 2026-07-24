# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import wire_service_loop as _wire_service_loop_3d
from .objects2d import wire_service_loop as _wire_service_loop_2d
from .objectspeg import wire_service_loop as _wire_service_loop_peg


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire_service_loop as _pjt_wire_service_loop


class WireServiceLoop(_ObjectBase):
    """Represent a wire service loop in :mod:`harness_designer.objects.wire_service_loop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _wire_service_loop_2d.WireServiceLoop = None
    obj3d: _wire_service_loop_3d.WireServiceLoop = None
    objpeg: _wire_service_loop_peg.WireServiceLoop = None
    db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop", project_load=False):
        """Initialise the :class:`WireServiceLoop` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _wire_service_loop_2d.WireServiceLoop(self, db_obj)
        self.obj3d = _wire_service_loop_3d.WireServiceLoop(self, db_obj)
        self.objpeg = _wire_service_loop_peg.WireServiceLoop(self, db_obj)

        self.mainframe.add_object(self)

    def delete(self):
        # TODO: Wires should be reconnected after removal.
        super().delete()
        self.mainframe.project.delete_wire_service_loop(self.db_obj.db_id)
        self.db_obj.delete()
