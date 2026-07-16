# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import basepeg as _basepeg
from ...gl.canvas_pegboard import flatten as _flatten
from ...gl.canvas_pegboard import table_rows as _table_rows
from ...shapes import cylinder as _cylinder


if TYPE_CHECKING:
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice


class Splice(_basepeg.BasePeg):
    """
    Peg Board Editor representation of a splice -- reuses the real 3D
    mesh/material/scale the 3D editor already holds, laid flat via its
    part's OBB-derived "up" face (see ``gl.canvas_pegboard.flatten``).
    """
    db_obj: "_pjt_splice.PJTSplice"

    def __init__(self, parent: "_splice.Splice",
                 db_obj: "_pjt_splice.PJTSplice"):
        """Initialise the :class:`Splice` instance.

        :param parent: Parent object.
        :type parent: :class:`_splice.Splice`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_splice.PJTSplice`
        """
        obj3d = parent.obj3d
        self._part = db_obj.part
        self._model = self._part.model3d

        # Placeholder-then-real-model lifecycle, same as Base3D itself
        # (objects.objects3d.splice.Splice.__init__): a unit cylinder,
        # scaled to obj3d's own already-computed diameter/length Scale
        # point (derived there from summed wire cross-sectional area, not
        # recomputed here) -- never vbo=None (see housing.py's own
        # comment on this for why).
        parent.mainframe.editor_pegboard.context.acquire()

        vbo = _cylinder.create_vbo()

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

        # Identity key for gl.canvas_pegboard's bundle-graph matching --
        # a splice has no single position3d, so (matching the "pick one"
        # simplification already used elsewhere) key off the start point.
        self.point3d_id = db_obj.start_position3d_id

        # Seed a sensible initial peg-board position -- a splice has no
        # single position3d, so use the start/stop midpoint (same "pick
        # one" simplification this feature already makes elsewhere).
        if self._position.x == 0.0 and self._position.z == 0.0:
            p1 = db_obj.start_position3d
            p2 = db_obj.stop_position3d
            self._position.x = float(p1.x + p2.x) / 2.0
            self._position.z = float(p1.z + p2.z) / 2.0

        if self._model is not None:
            self._model.load(
                self._part.manufacturer.name, self._part.part_number, self._set_model)

    def _flatten_hook(self) -> tuple:
        """Return the current OBB-derived "lay it flat" Euler orientation."""
        flatten_quat = _flatten.flatten_quaternion_for_model3d(
            self._vbo.local_obb, self._model.forward_up)  # NOQA
        return flatten_quat.as_euler

    def build_table_rows(self, project, point3d_id: int) -> list:
        """Start-side, then stop-side, then branch-side wires -- see
        ``table_rows.build_rows_for_splice``.
        """
        return _table_rows.build_rows_for_splice(self.db_obj)
