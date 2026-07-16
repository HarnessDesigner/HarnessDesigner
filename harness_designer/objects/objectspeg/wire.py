# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import basepeg as _basepeg


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire


class Wire(_basepeg.BasePeg):
    """Peg-board representation of a wire.

    Wires have no independent anchor presence on the board -- bundled
    wires are covered by their bundle's own strand, and bare-terminated
    wires are drawn as individual strands by
    ``gl.canvas_pegboard.layout_graph.build_bare_wire_strands`` (a
    graph-level construct, not a per-object anchor). This wrapper has no
    rendering presence of its own.
    """
    db_obj: "_pjt_wire.PJTWire"

    def __init__(self, parent: "_wire.Wire", db_obj: "_pjt_wire.PJTWire"):
        """Initialise the :class:`Wire` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire.Wire`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire.PJTWire`
        """
        _basepeg.BasePeg.__init__(self, parent, db_obj, position=None, angle=None)
