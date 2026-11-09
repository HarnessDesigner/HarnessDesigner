# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_schematic as _base_schematic
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import cable as _cable
    from ...database.project_db import pjt_cable as _pjt_cable


class Cable(_base_schematic.BaseSchematic):
    """The 2D schematic editor's view of a placed cable: an inert placeholder, never drawn and never pickable with the mouse.

    A cable is not in the schematic: each of its conductors is drawn there as a wire of its own (``objects_schematic/
    cable_conductor.py``). But the cable can be the selected object while the schematic editor is showing (chosen in the object
    browser, or selected in the 3D editor), and every canvas has to hold its selected object, so it has this view, built like the
    circuit's (``objects_schematic/circuit.py``): no VBO, angle, position, scale or material, and not visible.
    """
    parent: "_cable.Cable" = None
    db_obj: "_pjt_cable.PJTCable"

    @_check_types.do
    def __init__(self, parent: "_cable.Cable", db_obj: "_pjt_cable.PJTCable"):
        """Initialise the :class:`Cable` instance.

        :param parent: Parent object.
        :type parent: :class:`_cable.Cable`
        :param db_obj: The cable's row.
        :type db_obj: :class:`_pjt_cable.PJTCable`
        """
        super().__init__(parent, db_obj, None, None, None, None, None)

        # a cable row has no is_visible2d column; say so directly, the same way a circuit does
        self._is_visible = False
