# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_schematic as _base_schematic
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import circuit as _circuit
    from ...database.project_db import pjt_circuit as _pjt_circuit


class Circuit(_base_schematic.BaseSchematic):
    """The 2D schematic editor's view of a circuit: an inert placeholder, never drawn and never pickable with the mouse. See
    ``objects.objects_3d.circuit.Circuit`` for why it exists and how it behaves."""
    parent: "_circuit.Circuit" = None
    db_obj: "_pjt_circuit.PJTCircuit"

    @_check_types.do
    def __init__(self, parent: "_circuit.Circuit", db_obj: "_pjt_circuit.PJTCircuit"):
        """Initialise the :class:`Circuit` instance.

        :param parent: Parent object.
        :type parent: :class:`_circuit.Circuit`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_circuit.PJTCircuit`
        """
        super().__init__(parent, db_obj, None, None, None, None, None)

        # a circuit row has no is_visible2d column; say so directly, the same way an unplaced Note does
        self._is_visible = False

    @_check_types.do
    def set_selected(self, flag: bool) -> None:
        """Select or deselect this view. Deselecting also tells the circuit editor, so its table stops showing the circuit's row as selected.

        A click on another object, or on empty space, in an editor ends the circuit's selection through ``Circuit.set_selected(False)``, which
        calls this on each of the circuit's views. The circuit editor does nothing when its selected row is not this circuit's, which is also
        what ends the loop when it was the circuit editor that changed the selection.

        :param flag: ``True`` to select, ``False`` to deselect.
        :type flag: bool
        """
        super().set_selected(flag)

        if not flag:
            self.parent.deselect_in_editor()
