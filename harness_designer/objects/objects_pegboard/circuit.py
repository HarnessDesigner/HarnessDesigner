# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_circuit as _pjt_circuit
    from .. import circuit as _circuit


class Circuit(_base_pegboard.BasePegboard):
    """Peg-board representation of a circuit.

    A circuit is a logical grouping (a traced signal path across wires,
    splices, and terminals), not a placed physical part -- it has no
    rendering presence on the board.
    """
    db_obj: "_pjt_circuit.PJTCircuit"

    @_check_types.do
    def __init__(self, parent: "_circuit.Circuit", db_obj: "_pjt_circuit.PJTCircuit"):
        """Initialise the :class:`Circuit` instance.

        :param parent: Parent object.
        :type parent: :class:`_circuit.Circuit`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_circuit.PJTCircuit`
        """

        super().__init__(parent, db_obj, None, None,
                         None, None, None)

    def render(self, _, __, ___):
        pass
