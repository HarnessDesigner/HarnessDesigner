# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from ...gl.canvas_pegboard import flatten as _flatten
from ...gl.canvas_pegboard import table_rows as _table_rows
from ...shapes import box as _box
from ...gl import materials as _materials
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing


class Housing(_base_pegboard.BasePegboard):
    """
    Peg Board Editor representation of a housing -- reuses the real 3D
    mesh/material/scale the 3D editor already holds, laid flat via its
    part's OBB-derived "up" face (see ``gl.canvas_pegboard.flatten``).
    """
    db_obj: "_pjt_housing.PJTHousing"

    @_check_types.do
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
        # (objects.objects_3d.housing.Housing.__init__): a unit box, scaled
        # to the housing's own real width/height/length -- swapped for the
        # real mesh once model.load()'s callback fires (_set_model) --
        # never vbo=None, which would leave position/angle/scale/material
        # unset entirely (see BasePegboard.__init__'s vbo-is-None branch).
        #
        # scale/material are built fresh here, never borrowed from
        # obj3d -- obj3d's own Scale/GLMaterial instances are that OTHER
        # view's own live, mutable objects; sharing them would silently
        # couple this view's rendering to whatever the 3D editor happens
        # to do to its own copies. scale comes straight from the database
        # (db_obj.scale3d, the one shared physical size -- there is no
        # separate scale_pegboard, unlike position/angle); material is
        # rebuilt from the catalog part's own color, mirroring
        # objects_3d.housing.Housing.__init__'s own construction exactly.
        with parent.mainframe.editor_pegboard.context:
            vbo = _box.create_vbo()

            super().__init__(
                parent, db_obj,
                vbo=vbo,
                angle=db_obj.angle_pegboard,
                position=db_obj.position_pegboard,
                scale=db_obj.scale3d,
                material=_materials.Plastic(self._part.color.ui),
            )

        self.smooth = db_obj.smooth

        # Identity key for gl.canvas_pegboard's bundle-graph matching
        # (Canvas builds {anchor.point3d_id: anchor} to resolve which live
        # anchor a bundle chain's start/stop point3d_id claims) -- keyed
        # by this housing's own peg-board point, not its 3D one, so it
        # actually matches what PJTBundle/PJTWire's own
        # start_position_pegboard_id/stop_position_pegboard_id reference.
        self.point3d_id = db_obj.position_pegboard_id

        # Seed a sensible initial peg-board position from the real 3D
        # position -- only the first time ever (position_pegboard starts at the
        # (0.0, 0.0) fresh-row default, same sentinel convention
        # _apply_flatten_if_untouched uses for rotation).
        if self._position.x == 0.0 and self._position.z == 0.0:
            pos3d = db_obj.position3d
            self._position.x = float(pos3d.x)
            self._position.z = float(pos3d.z)

        if self._model is not None:
            self._model.load(
                self._part.manufacturer.name, self._part.part_number, self._set_model)

    @_check_types.do
    def _flatten_hook(self) -> tuple:
        """Return the current OBB-derived "lay it flat" Euler orientation
        (see :meth:`BasePegboard._set_model`/``_apply_flatten_if_untouched``).
        """
        flatten_quat = _flatten.flatten_quaternion_for_model3d(
            self._vbo.local_obb, self._model.forward_up)  # NOQA
        return flatten_quat.as_euler

    @_check_types.do
    def build_table_rows(self, project, point3d_id: bytes) -> list:
        """Every seated cavity's wire, cavity-index order -- see
        ``table_rows.build_rows_for_housing``.
        """
        return _table_rows.build_rows_for_housing(self.db_obj, project)

    @property
    @_check_types.do
    def table_include_cavity_columns(self) -> bool:
        return True
