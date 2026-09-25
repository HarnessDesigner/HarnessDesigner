# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np
import build123d

from . import base_pegboard as _base_pegboard
from ...shapes import box as _box
from ...shapes import cylinder as _cylinder
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import check_types as _check_types
from ... import config as _config
from ...geometry import point as _point
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_seal as _pjt_seal
    from .. import seal as _seal


Config = _config.Config.editor_pegboard


def _build_sws(length: float, o_dia: float, i_dia: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Build the sws.

    :param length: Value for ``length``.
    :type length: float

    :param o_dia: Value for ``o_dia``.
    :type o_dia: float

    :param i_dia: Value for ``i_dia``.
    :type i_dia: float

    :returns: Return value. UNKNOWN details.
    :rtype: tuple[np.ndarray, np.ndarray]
    """

    o_radius = round(o_dia / 2.0, 6)
    i_radius = round(i_dia / 2.0, 6)

    model1 = build123d.Cylinder(o_radius, length * 0.50)
    model2 = build123d.Cylinder(o_radius * 0.66, length)

    model1.move(build123d.Location((0, 0, -length * 0.25)))
    model = model1 + model2

    hole = build123d.Cylinder(i_radius, length)
    model -= hole

    vertices, faces = _utils.convert_model_to_mesh(model)
    return vertices, faces


class Seal(_base_pegboard.BasePegboard):
    """
    Peg Board Editor representation of a seal -- reuses the real 3D
    mesh/scale the 3D editor already holds, laid flat (no rotation seed
    needed -- only Transition needs one). Visibility on the peg board is
    driven entirely by ``is_visible_pegboard`` -- whether that's on by
    default only while a seal's housing is selected is handled elsewhere
    (out of scope here), not by any selection-aware logic in this class.

    Like ``objects_3d.seal.Seal``, no async ``Model3D.load()`` step --
    every seal type (SWS/Plug/other) is built synchronously, so the vbo
    is picked up immediately at construction time:

    - SWS: a part-specific mesh, pooled by id
      (``objects_3d.seal.Seal._vbo_id``) via ``PooledVBOHandler`` --
      re-resolved here through that same id (not aliased from ``obj3d.
      _vbo`` directly) to get this object its own properly ref-counted
      handle on the pool, since ``PooledVBOHandler`` entries are held by
      weakref (see ``gl.vbo.VBOSingleton.__call__``) and only stay alive
      as long as something holds a strong reference.
    - Plug: a plain shared unit cylinder (not part-specific, no pooling
      needed -- built directly, same as ``objects_pegboard.terminal``'s
      own round-terminal case).
    - Anything else: a plain shared unit box, same rationale.
    """
    db_obj: "_pjt_seal.PJTSeal"

    @_check_types.do
    def __init__(self, parent: "_seal.Seal", db_obj: "_pjt_seal.PJTSeal"):
        """Initialise the :class:`Seal` instance.

        :param parent: Parent object.
        :type parent: :class:`_seal.Seal`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_seal.PJTSeal`
        """

        with parent.mainframe.editor_pegboard.context:
            self._part = db_obj.part

            model = self._part.model3d
            category = self._part.type.category

            if category == 'SWS':
                vbo_id = self._part.manufacturer.name
                vbo_id += ':' + self._part.part_number
                vbo_id += ':pegboard'
                length = self._part.length
                o_dia = self._part.o_dia
                scale = _point.Point(1.0, 1.0, 1.0)

                if vbo_id in _vbo.PooledVBOHandler:
                    vbo = _vbo.PooledVBOHandler(vbo_id)
                else:
                    i_dia = self._part.i_dia
                    vertices, faces = _build_sws(length, o_dia, i_dia)

                    packed, count = _utils.compute_normals(vertices, faces)
                    vertices = packed[:count * 3].reshape(-1, 3)

                    aabb1, aabb2 = _utils.compute_aabb(vertices)
                    obb = _utils.compute_obb(aabb1, aabb2)
                    aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)

                    vbo = _vbo.PooledVBOHandler(vbo_id, packed, count, aabb=aabb, obb=obb)

            elif category == 'PLUG':
                self._vbo_id = None
                vbo = _cylinder.create_vbo()
                length = self._part.length
                o_dia = self._part.o_dia
                scale = _point.Point(o_dia, o_dia, length)
            else:
                self._vbo_id = None
                vbo = _box.create_vbo()
                scale = _point.Point(self._part.width, self._part.height, self._part.length)

            material = _materials.Rubber(self._part.color.ui)
            angle = db_obj.angle_pegboard

            # Always this seal's OWN position_pegboard -- exactly the
            # same pattern objects_3d.seal.Seal.__init__ uses for
            # position3d (unconditionally db_obj.position3d, regardless
            # of whether it's seated on a terminal/cavity/housing). Y is
            # honored (not locked to 0 like a housing's own anchor).
            # Previously branched on db_obj.terminal/cavity/housing to
            # substitute that parent's own position_pegboard instead --
            # inconsistent with position3d's own pattern and with
            # PJTHousing._update_position_pegboard, which already
            # cascades this seal's own position_pegboard on every housing
            # move (see that method's own docstring) as if it were always
            # the authoritative value. Confirmed 2026-09-11 (Kevin).
            pegboard_position = db_obj.position_pegboard

            super().__init__(parent, db_obj, vbo, angle, pegboard_position, scale, material)

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

        # Identity key for gl.canvas_pegboard's bundle-graph matching --
        # keyed by this seal's own peg-board point, not its 3D one (see
        # housing.py's own comment on why).
        self.point3d_id = db_obj.position_pegboard_id

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_seals

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass
