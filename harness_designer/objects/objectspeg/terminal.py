# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import basepeg as _basepeg
from ...gl.canvas_pegboard import flatten as _flatten
from ...gl.canvas_pegboard import table_rows as _table_rows
from ...shapes import box as _box
from ...shapes import cylinder as _cylinder


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal


class Terminal(_basepeg.BasePeg):
    """
    Peg Board Editor representation of a terminal.

    Only a BARE terminal (``cavity_id is None`` -- not seated in any
    housing cavity) has a real, rendered peg-board presence, reusing the
    real 3D mesh/material/scale the 3D editor already holds, laid flat via
    its part's OBB-derived "up" face. A seated terminal is visually
    covered by its housing (which already has its own real anchor), so it
    stays permanently inert (``vbo=None``, never registers a model load) --
    :attr:`~.basepeg.BasePeg.is_active` is ``False`` and no vbo/material/
    rendering state is ever built.

    This decision is made once, at construction time (matching how the
    predecessor bulk-anchor-builder made the same check at each
    ``load_project()`` walk) -- a terminal seated/unseated after
    construction does not dynamically flip this instance's peg-board
    presence.
    """
    db_obj: "_pjt_terminal.PJTTerminal"

    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal"):
        """Initialise the :class:`Terminal` instance.

        :param parent: Parent object.
        :type parent: :class:`_terminal.Terminal`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_terminal.PJTTerminal`
        """
        if db_obj.cavity_id is not None:
            # Seated -- no independent peg-board presence.
            _basepeg.BasePeg.__init__(self, parent, db_obj)
            return

        obj3d = parent.obj3d
        self._part = db_obj.part
        self._model = self._part.model3d

        # Placeholder-then-real-model lifecycle, same as Base3D itself
        # (objects.objects3d.terminal.Terminal.__init__): a unit box or
        # cylinder (matching the catalog part's own round_terminal flag),
        # scaled to obj3d's own already-computed width/height/length Scale
        # point -- never vbo=None (see housing.py's own comment on this).
        parent.mainframe.editor_pegboard.context.acquire()

        if self._part.round_terminal:
            vbo = _cylinder.create_vbo()
        else:
            vbo = _box.create_vbo()

        _basepeg.BasePeg.__init__(
            self, parent, db_obj,
            vbo=vbo,
            angle=db_obj.anglepeg,
            position=db_obj.position_peg,
            scale=obj3d.scale,
            material=obj3d.material,
        )

        parent.mainframe.editor_pegboard.context.release()

        self.smooth = getattr(obj3d, 'smooth', False)

        # Identity key for gl.canvas_pegboard's bundle-graph matching.
        self.point3d_id = db_obj.position3d_id

        if self._position.x == 0.0 and self._position.z == 0.0:
            pos3d = db_obj.position3d
            self._position.x = float(pos3d.x)
            self._position.z = float(pos3d.z)

        if self._model is not None:
            self._model.load(
                self._part.manufacturer.name, self._part.part_number, self._set_model)

    def _flatten_hook(self) -> tuple:
        """Return the current OBB-derived "lay it flat" Euler orientation."""
        flatten_quat = _flatten.flatten_quaternion_for_model3d(
            self._vbo.local_obb, self._model.forward_up)  # NOQA
        return flatten_quat.as_euler

    def build_table_rows(self, project, point3d_id: int) -> list:
        """This bare terminal's single attached wire -- see
        ``table_rows.build_rows_for_terminal``. A *seated* terminal never
        reaches here (``is_active`` is ``False``, see :meth:`__init__`).
        """
        return _table_rows.build_rows_for_terminal(self.db_obj, project)
