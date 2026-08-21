# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
# from ...gl.canvas_pegboard import flatten as _flatten
# from ...gl.canvas_pegboard import table_rows as _table_rows
from ...gl import materials as _materials
from ...geometry import point as _point
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_transition as _pjt_transition
    from .. import transition as _transition


Config = _config.Config.editor_pegboard


class Transition(_base_pegboard.BasePegboard):
    """
    Peg Board Editor representation of a transition -- reuses the real 3D
    mesh/material/scale the 3D editor already holds. Transitions have no
    catalog part/``Model3D`` of their own (their mesh is procedurally
    generated at runtime, ``objects.objects_3d.transition._build_model``,
    always synchronously -- no async ``model.load()`` step, unlike
    ``Housing``/``Splice``/``Terminal``), so the real ``vbo`` is available
    immediately and the initial flatten rotation (a one-time -90° seed on
    ``angle_pegboard.x``, since ``_build_model`` confines every branch to
    local Z=0 -- see ``__init__``) is applied right here instead of
    deferred to :meth:`~.base_pegboard.BasePegboard._set_model`. Like
    ``Housing``/``Terminal``, this is only ever a one-time default --
    from then on ``angle_pegboard`` is a normal user-adjustable rotation,
    no further code-side flattening happens on every load.
    """
    db_obj: "_pjt_transition.PJTTransition"

    @_check_types.do
    def __init__(self, parent: "_transition.Transition",
                 db_obj: "_pjt_transition.PJTTransition"):
        """Initialise the :class:`Transition` instance.

        :param parent: Parent object.
        :type parent: :class:`_transition.Transition`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_transition.PJTTransition`
        """
        obj3d = parent.obj3d
        self._part = db_obj.part

        # scale/material are built fresh here, never borrowed from
        # obj3d -- see objects_pegboard.housing.Housing.__init__'s own
        # comment on why. A transition has no Scale3DMixin (no single
        # physical size stored for it), so scale falls back to identity;
        # material is rebuilt from the catalog part's own color, mirroring
        # objects_3d.transition.Transition.__init__'s own construction.
        # The mesh itself (vbo) is still reused -- that's the shared VBO/
        # arena system this whole feature is built on, not a per-view
        # mutable object.
        super().__init__(
            parent, db_obj,
            vbo=obj3d._vbo,  # NOQA
            angle=db_obj.angle_pegboard,
            position=db_obj.position_pegboard,
            scale=_point.Point(1.0, 1.0, 1.0),
            material=_materials.Rubber(self._part.color.ui),
        )

        # Identity key for gl.canvas_pegboard's bundle-graph matching --
        # keyed by this transition's own peg-board point, not its 3D one
        # (see housing.py's own comment on why).
        self.point3d_id = db_obj.position_pegboard_id

        if self._position.x == 0.0 and self._position.z == 0.0:
            pos3d = db_obj.position3d
            self._position.x = float(pos3d.x)
            self._position.z = float(pos3d.z)

        # Seed the transition's initial peg-board rotation to lay its
        # branches (built confined to local Z=0 -- see this class's own
        # docstring) flat in the board's XZ view plane; left unrotated,
        # they'd render edge-on viewed straight down world Y. Same
        # "only the very first time" sentinel discipline as the X/Z
        # position seed above (identity is the fresh-row default) --
        # from then on this is a normal user-adjustable rotation, same
        # as housing's/terminal's own angle_pegboard.
        if self._angle.x == 0.0 and self._angle.y == 0.0 and self._angle.z == 0.0:
            self._angle.x = -90.0

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_transitions

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass
