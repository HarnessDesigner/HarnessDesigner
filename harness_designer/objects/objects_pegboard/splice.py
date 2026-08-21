# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from ...shapes import cylinder as _cylinder
from ...gl import materials as _materials
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice


Config = _config.Config.editor_pegboard


class Splice(_base_pegboard.BasePegboard):
    """
    Peg Board Editor representation of a splice -- reuses the real 3D
    mesh/material/scale the 3D editor already holds, laid flat via its
    part's OBB-derived "up" face. A single freely-rotatable anchor (like
    Housing/Terminal/Transition), not the start/stop-pair connector
    geometry ``objects_3d.splice.Splice`` derives from the two wires it
    joins -- ``PJTSplice`` only has ``position_pegboard``/
    ``angle_pegboard`` for this view, not a peg-board equivalent of
    ``StartStopPosition3DMixin``.
    """
    db_obj: "_pjt_splice.PJTSplice"

    @_check_types.do
    def __init__(self, parent: "_splice.Splice",
                 db_obj: "_pjt_splice.PJTSplice"):
        """Initialise the :class:`Splice` instance.

        :param parent: Parent object.
        :type parent: :class:`_splice.Splice`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_splice.PJTSplice`
        """
        self._part = db_obj.part
        self._model = self._part.model3d

        # Placeholder-then-real-model lifecycle, same as Base3D itself
        # (objects.objects_3d.splice.Splice.__init__): a unit cylinder,
        # scaled to the splice's own real width/height/length -- never
        # vbo=None (see housing.py's own comment on this).
        #
        # scale/material are built fresh here, never borrowed from
        # obj3d -- see housing.py's own comment on why. scale comes from
        # the database (db_obj.scale3d); material is rebuilt from the
        # catalog part's own color, mirroring
        # objects_3d.splice.Splice.__init__'s own Rubber material choice
        # (a splice cap, not a plated/polished metal part).
        with parent.mainframe.editor_pegboard.context:
            vbo = _cylinder.create_vbo()

            super().__init__(
                parent, db_obj,
                vbo=vbo,
                angle=db_obj.angle_pegboard,
                position=db_obj.position_pegboard,
                scale=db_obj.scale3d,
                material=_materials.Rubber(self._part.color.ui),
            )

        # Identity key for gl.canvas_pegboard's bundle-graph matching --
        # keyed by this splice's own peg-board point, not its 3D one
        # (see housing.py's own comment on why).
        self.point3d_id = db_obj.position_pegboard_id

        # Seed a sensible initial peg-board position from the real 3D
        # position -- only the first time ever, same sentinel convention
        # housing.py/terminal.py use (position_pegboard starts at the
        # (0.0, 0.0) fresh-row default). Splice has no single position3d
        # of its own (StartStopPosition3DMixin -- start/stop, not one
        # point), so start_position3d is the closest equivalent anchor.
        if self._position.x == 0.0 and self._position.z == 0.0:
            pos3d = db_obj.start_position3d
            self._position.x = float(pos3d.x)
            self._position.z = float(pos3d.z)

        if self._model is not None:
            self._model.load(
                self._part.manufacturer.name, self._part.part_number, self._set_model)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_splices

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass