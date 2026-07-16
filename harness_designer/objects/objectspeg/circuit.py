# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import basepeg as _basepeg


if TYPE_CHECKING:
    from ...database.project_db import pjt_circuit as _pjt_circuit
    from .. import circuit as _circuit


class Circuit(_basepeg.BasePeg):
    """Peg-board representation of a circuit.

    A circuit is a logical grouping (a traced signal path across wires,
    splices, and terminals), not a placed physical part -- it has no
    rendering presence on the board.
    """
    db_obj: "_pjt_circuit.PJTCircuit"

    def __init__(self, parent: "_circuit.Circuit", db_obj: "_pjt_circuit.PJTCircuit"):
        """Initialise the :class:`Circuit` instance.

        :param parent: Parent object.
        :type parent: :class:`_circuit.Circuit`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_circuit.PJTCircuit`
        """
        _basepeg.BasePeg.__init__(self, parent, db_obj, position=None, angle=None)
