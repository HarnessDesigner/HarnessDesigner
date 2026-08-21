# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from ...shapes import box as _box
from ...shapes import cylinder as _cylinder
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_seal as _pjt_seal
    from .. import seal as _seal


Config = _config.Config.editor_pegboard


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
        obj3d = parent.obj3d
        self._part = db_obj.part
        type_ = self._part.type.name.lower()

        # scale/material are built fresh here, never borrowed from obj3d --
        # see objects_pegboard.housing.Housing.__init__'s own comment on
        # why. scale comes from the database (db_obj.scale3d, same
        # Scale3DMixin housing/terminal/splice already use here); material
        # is rebuilt from the catalog part's own color, mirroring
        # objects_3d.seal.Seal.__init__'s own Rubber choice for every type.
        with parent.mainframe.editor_pegboard.context:
            if type_ in ('sws', 'single wire seal'):
                vbo = _vbo.PooledVBOHandler(obj3d._vbo_id)  # NOQA
            elif type_ == 'plug':
                vbo = _cylinder.create_vbo()
            else:
                vbo = _box.create_vbo()

            super().__init__(
                parent, db_obj,
                vbo=vbo,
                angle=db_obj.angle_pegboard,
                position=db_obj.position_pegboard,
                scale=db_obj.scale3d,
                material=_materials.Rubber(self._part.color.ui),
            )

        # Identity key for gl.canvas_pegboard's bundle-graph matching --
        # keyed by this seal's own peg-board point, not its 3D one (see
        # housing.py's own comment on why).
        self.point3d_id = db_obj.position_pegboard_id

        if self._position.x == 0.0 and self._position.z == 0.0:
            pos3d = db_obj.position3d
            self._position.x = float(pos3d.x)
            self._position.z = float(pos3d.z)

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
