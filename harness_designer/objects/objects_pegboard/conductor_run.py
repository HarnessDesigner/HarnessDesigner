# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import cable_conductor as _cable_conductor
    from ...database.project_db import pjt_cable_conductor as _pjt_cable_conductor


class ConductorRun(_base_pegboard.BasePegboard):
    """The peg-board editor's view of a cable conductor as the schematic draws it: an inert placeholder, never drawn and never
    pickable with the mouse. See ``objects.objects_3d.conductor_run.ConductorRun`` for why it exists and how it behaves."""
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
        super().__init__(parent, db_obj)

        # a conductor row has no peg-board visibility column; say so directly, the same way an unplaced Note does
        self._is_visible = False
