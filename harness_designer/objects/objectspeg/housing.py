# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import basepeg as _basepeg
from ...gl.canvas_pegboard import flatten as _flatten
from ...gl.canvas_pegboard import table_rows as _table_rows
from ...shapes import box as _box


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing


class Housing(_basepeg.BasePeg):
    """
    Peg Board Editor representation of a housing -- reuses the real 3D
    mesh/material/scale the 3D editor already holds, laid flat via its
    part's OBB-derived "up" face (see ``gl.canvas_pegboard.flatten``).
    """
    db_obj: "_pjt_housing.PJTHousing"

    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):
        """Initialise the :class:`Housing` instance.

        :param parent: Parent object.
        :type parent: :class:`_housing.Housing`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_housing.PJTHousing`
        """
        obj3d = parent.obj3d
        self._part = db_obj.part
        self._model = self._part.model3d

        # Placeholder-then-real-model lifecycle, same as Base3D itself
        # (objects.objects3d.housing.Housing.__init__): a unit box, scaled
        # to the housing's real width/height/length (reusing obj3d's own
        # already-computed Scale point, not recomputed here), swapped for
        # the real mesh once model.load()'s callback fires (_set_model) --
        # never vbo=None, which would leave position/angle/scale/material
        # unset entirely (see BasePeg.__init__'s vbo-is-None branch).
        parent.mainframe.editor_pegboard.context.acquire()

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

        # Identity key for gl.canvas_pegboard's bundle-graph matching
        # (Canvas builds {anchor.point3d_id: anchor} to resolve which live
        # anchor a bundle chain's start/stop point3d_id claims) -- the
        # REAL 3D point identity, unrelated to the new position_peg row.
        self.point3d_id = db_obj.position3d_id

        # Seed a sensible initial peg-board position from the real 3D
        # position -- only the first time ever (position_peg starts at the
        # (0.0, 0.0) fresh-row default, same sentinel convention
        # _apply_flatten_if_untouched uses for rotation).
        if self._position.x == 0.0 and self._position.z == 0.0:
            pos3d = db_obj.position3d
            self._position.x = float(pos3d.x)
            self._position.z = float(pos3d.z)

        if self._model is not None:
            self._model.load(
                self._part.manufacturer.name, self._part.part_number, self._set_model)

    def _flatten_hook(self) -> tuple:
        """Return the current OBB-derived "lay it flat" Euler orientation
        (see :meth:`BasePeg._set_model`/``_apply_flatten_if_untouched``).
        """
        flatten_quat = _flatten.flatten_quaternion_for_model3d(
            self._vbo.local_obb, self._model.forward_up)  # NOQA
        return flatten_quat.as_euler

    def build_table_rows(self, project, point3d_id: int) -> list:
        """Every seated cavity's wire, cavity-index order -- see
        ``table_rows.build_rows_for_housing``.
        """
        return _table_rows.build_rows_for_housing(self.db_obj, project)

    @property
    def table_include_cavity_columns(self) -> bool:
        return True
