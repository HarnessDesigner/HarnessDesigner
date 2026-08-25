# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
# from ...gl.canvas_pegboard import flatten as _flatten
# from ...gl.canvas_pegboard import table_rows as _table_rows
from ...shapes import box as _box
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing
    from ... import ui as _ui


Config = _config.Config.editor_pegboard


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

    @classmethod
    @_check_types.do
    def start_add(cls, mainframe: "_ui.MainFrame") -> "_housing.Housing | None":
        """Single-click free placement, pegboard-native -- mirrors
        objects_3d.housing.Housing.start_add/objects_schematic.housing.
        Housing.start_add. Unlike those two, this housing's own
        position_pegboard needs no explicit placeholder at all --
        PositionPegboardMixin.position_pegboard_id lazily creates one
        the first time anything reads it (this class's own __init__
        already does, to seed its initial position from position3d).
        """
        canvas = mainframe.editor_pegboard.editor

        part_id = mainframe.editor_db.editor.housings.GetSelection()

        if part_id is None:
            from ...ui.dialogs import part_search as _part_search
            from ...ui import editor_db as _editor_db
            from PySide6.QtWidgets import QDialog

            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.HousingsPage, title='Add Housing',
                table=mainframe.global_db.housings_table)
            part_id = dlg.GetValue() if dlg.exec() == QDialog.DialogCode.Accepted else None
            dlg.deleteLater()

            if part_id is None:
                return None

        from .. import housing as _housing_facade

        ptables = mainframe.project.ptables
        part = mainframe.project.gtables.housings_table[part_id]
        name = f'{part.manufacturer.name} {part.part_number}'
        position = ptables.pjt_points3d_table.insert(0, 0, 0)

        db_obj = ptables.pjt_housings_table.insert(part_id, name, position.db_id)
        facade = _housing_facade.Housing(mainframe, db_obj)

        from ...add_handlers.editor_pegboard import housing as _add_housing

        handler = _add_housing.Housing(canvas, facade)
        facade.objpegboard._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.objpegboard

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to BasePegboard's own generic drag handling otherwise.
        """
        from ...add_handlers.editor_pegboard import housing as _add_housing  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_housing.Housing):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_housings

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass