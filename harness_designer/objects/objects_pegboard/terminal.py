# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
# from ...gl.canvas_pegboard import flatten as _flatten
# from ...gl.canvas_pegboard import table_rows as _table_rows
from ...shapes import box as _box
from ...shapes import cylinder as _cylinder
from ...gl import materials as _materials
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal


Config = _config.Config.editor_pegboard


class Terminal(_base_pegboard.BasePegboard):
    """
    Peg Board Editor representation of a terminal.

    Only a BARE terminal (``cavity_id is None`` -- not seated in any
    housing cavity) has a real, rendered peg-board presence, reusing the
    real 3D mesh/material/scale the 3D editor already holds, laid flat via
    its part's OBB-derived "up" face. A seated terminal is visually
    covered by its housing (which already has its own real anchor), so it
    stays permanently inert (``vbo=None``, never registers a model load) --
    :attr:`~.base_pegboard.BasePegboard.is_active` is ``False`` and no vbo/material/
    rendering state is ever built.

    This decision is made once, at construction time (matching how the
    predecessor bulk-anchor-builder made the same check at each
    ``load_project()`` walk) -- a terminal seated/unseated after
    construction does not dynamically flip this instance's peg-board
    presence.
    """
    db_obj: "_pjt_terminal.PJTTerminal"

    @_check_types.do
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
            super().__init__(parent, db_obj)
            return

        obj3d = parent.obj3d
        self._part = db_obj.part
        self._model = self._part.model3d

        # Placeholder-then-real-model lifecycle, same as Base3D itself
        # (objects.objects_3d.terminal.Terminal.__init__): a unit box or
        # cylinder (matching the catalog part's own round_terminal flag),
        # scaled to this terminal's own real width/height/length -- never
        # vbo=None (see housing.py's own comment on this).
        #
        # scale/material are built fresh here, never borrowed from
        # obj3d -- see housing.py's own comment on why. scale comes from
        # the database (db_obj.scale3d); material is rebuilt from the
        # catalog part's own plating color, mirroring
        # objects_3d.terminal.Terminal.__init__'s own construction.
        with parent.mainframe.editor_pegboard.context:
            if self._part.round_terminal:
                vbo = _cylinder.create_vbo()
            else:
                vbo = _box.create_vbo()

            super().__init__(
                parent, db_obj,
                vbo=vbo,
                angle=db_obj.angle_pegboard,
                position=db_obj.position_pegboard,
                scale=db_obj.scale3d,
                material=_materials.Polished(self._part.plating.color.ui),
            )

        # Identity key for gl.canvas_pegboard's bundle-graph matching --
        # keyed by this terminal's own peg-board point, not its 3D one
        # (see housing.py's own comment on why).
        self.point3d_id = db_obj.position_pegboard_id

        if self._position.x == 0.0 and self._position.z == 0.0:
            pos3d = db_obj.position3d
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
            smooth = Config.renderer.smooth_terminals

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass