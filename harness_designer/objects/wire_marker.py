# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import wire_marker as _wire_marker_3d
from .objects_schematic import wire_marker as _wire_marker_schematic
from .objectspeg import wire_marker as _wire_marker_peg
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..database.project_db import pjt_wire_marker as _wire_marker
    from ..ui import mainframe as _mainframe


class WireMarker(_ObjectBase):
    """Represent a wire marker in :mod:`harness_designer.objects.wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: _wire_marker_schematic.WireMarker = None
    obj3d: _wire_marker_3d.WireMarker = None
    objpeg: _wire_marker_peg.WireMarker = None
    db_obj: "_wire_marker.PJTWireMarker" = None

    @_check_types.do
    def __init__(self, mainframe: "_mainframe.MainFrame",
                 db_obj: "_wire_marker.PJTWireMarker", project_load=False):
        """Initialise the :class:`WireMarker` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_wire_marker.PJTWireMarker`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.objschematic = _wire_marker_schematic.WireMarker(self, db_obj)
        self.obj3d = _wire_marker_3d.WireMarker(self, db_obj)
        self.objpeg = _wire_marker_peg.WireMarker(self, db_obj)

        self.mainframe.add_object(self)

    @_check_types.do
    def select2d(self, evt):
        """Execute the select 2D operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        pass

    @_check_types.do
    def select3d(self, evt):
        """Execute the select 3D operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        pass

    @_check_types.do
    def delete(self):
        super().delete()
        self.mainframe.project.delete_wire_marker(self.db_obj.db_id)
        self.db_obj.delete()
