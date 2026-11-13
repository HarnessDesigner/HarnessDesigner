# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_3d as _base_3d
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import cable_conductor as _cable_conductor
    from ...database.project_db import pjt_cable_conductor as _pjt_cable_conductor


class ConductorRun(_base_3d.Base3D):
    """The 3D editor's view of a cable conductor as the schematic draws it (``objects.cable_conductor.ConductorRun``): an inert
    placeholder, on purpose.

    The conductor is drawn in the 3D editor by its cable's trunk and its leads, so a run has nothing to draw here, but the run can be
    the selected object (a click on it in the schematic), and every canvas has to be able to hold the selected object (without a view
    it logged ``the selected ConductorRun has no view in the editor3d canvas`` once per canvas, user's log 2026-11-12).

    Built exactly like ``objects_3d/circuit.py``: no VBO, angle, position, scale or material, and not visible, so ``render`` skips it,
    the canvas does not register it and the mouse can not pick it.
    """
    parent: "_cable_conductor.ConductorRun" = None
    db_obj: "_pjt_cable_conductor.PJTCableConductor"

    @_check_types.do
    def __init__(self, parent: "_cable_conductor.ConductorRun", db_obj: "_pjt_cable_conductor.PJTCableConductor"):
        """Initialise the :class:`ConductorRun` instance.

        :param parent: The run.
        :type parent: :class:`_cable_conductor.ConductorRun`
        :param db_obj: The conductor's row.
        :type db_obj: :class:`_pjt_cable_conductor.PJTCableConductor`
        """
        super().__init__(parent, db_obj, None, None, None, None, None)

        # a conductor row has no is_visible3d column; say so directly, the same way an unplaced Note does
        self._is_visible = False
