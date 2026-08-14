# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
from OpenGL import GL

from . import base_pegboard as _base_pegboard
from ...geometry import angle as _angle
from ... import utils as _utils
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_layout as _pjt_wire_layout
    from .. import wire_layout as _wire_layout


class WireLayout(_base_pegboard.BasePegboard):
    """
    2D representation of a wire layout (grab handle) for schematic view

    Renders as a circular grab handle using OpenGL.
    """
    _parent: "_wire_layout.WireLayout" = None
    db_obj: "_pjt_wire_layout.PJTWireLayout"

    @_check_types.do
    def __init__(self, parent: "_wire_layout.WireLayout",
                 db_obj: "_pjt_wire_layout.PJTWireLayout"):
        """Initialise the :class:`WireLayout` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire_layout.WireLayout`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_layout.PJTWireLayout`
        """

        super().__init__(parent, db_obj, None, None)
