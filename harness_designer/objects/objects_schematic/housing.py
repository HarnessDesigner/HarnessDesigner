# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import build123d
from PySide6 import QtWidgets
from PySide6 import QtCore

from . import base_schematic as _base_schematic
from ... import config as _config
from ... import color as _color
from ... import check_types as _check_types
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...shapes import rectangle as _rectangle
from ...shapes import text as _text
from ...ui.widgets import context_menus as _context_menus
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing
    from ... import ui as _ui


Config = _config.Config.editor_schematic


def _is_180(degrees: float) -> bool:
    """Whether *degrees* (this housing's own live ``angle2d.y``) is the
    180 special case -- rotating the corner label's own glyphs a full
    half-turn along with the housing would render them upside-down, so
    at that one angle the glyph itself renders upright instead (see
    :meth:`Housing.render`) and the label's own internal line-
    justification flips to the opposite side instead (see
    :meth:`Housing._build_corner_label`) to keep reading in the same
    direction relative to its own anchor.
    """
    return round(degrees) % 360 == 180


class Housing(_base_schematic.BaseSchematic):
    """
    2D representation of a housing for schematic view

    Renders ONLY the housing rectangle (unit primitive from
    ``shapes.rectangle``, scaled) plus its own corner label (name/part
    number/manufacturer), via the schematic2d shader/VBO pipeline (see
    ``objects_schematic/base_schematic.py``'s ``BaseSchematic``) -- matches
    how ``Base3D`` subclasses render, no immediate-mode fallback. Every
    cavity's own name, and (for a cavity with a seated terminal) the "("
    bracket and the terminal's own name, are rendered independently by
    ``objects_schematic/cavity.py``'s ``Cavity``/``objects_schematic/terminal.py``'s
    ``Terminal`` -- each a real, individually selectable ``BaseSchematic``
    object with its own OBB/AABB, positioned from ``PJTHousing.
    cavity_geometry`` (see ``geometry.cavity_layout.
    compute_housing_cavity_geometry``) -- NOT computed by this class, and
    not pushed to them by this class either: a cavity's own initial
    ``position2d`` is written once, batched, by ``PJTHousingsTable.
    insert`` at housing-insert time, and a seated terminal's own is
    computed and persisted by ``objects_schematic/terminal.py``'s own
    ``Terminal.__init__`` the first time it's actually seated. This
    class plays no further part in either -- a housing move/rotate
    afterward is handled directly by ``database/project_db/
    pjt_housing.py``'s ``PJTHousing._update_position2d``/
    ``_update_angle2d`` batch-cascading straight into each cavity's/
    terminal's own bound ``position2d``, with no need to round-trip
    through this class at all (see :meth:`_update_position`/
    :meth:`_update_angle`'s own docstrings). A cavity's own NAME is
    treated as fixed once its row exists -- this class doesn't react to
    it changing (that would also reorder its own natural-sort stack
    slot, real added complexity deliberately deferred to its own
    session, 2026-09-10 Kevin).

    Sizing is font-size-driven rather than a fixed constant: this
    housing's own per-cavity slot height (:attr:`cavity_height`) is
    derived from ``shapes.text.CHARACTER_HEIGHT`` (the tallest glyph in
    the font, at font_size=1.0 -- see :func:`shapes.text.build_chars`)
    times ``Config.object_sizes.terminal.name_font_size`` (a terminal's
    own MAXIMUM font size, not a constant -- an individual terminal may
    render smaller to fit its own name inside this slot), plus 10%
    padding on top and bottom -- cached on ``PJTHousing`` as its own
    ``stack_geometry`` (see that property's own docstring), read once
    here in :meth:`__init__`.
    """

    _parent: "_housing.Housing" = None
    db_obj: "_pjt_housing.PJTHousing"

    @_check_types.do
    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):
        """
        Initialise the :class:`Housing` instance.

        :param parent: Parent object.
        :type parent: :class:`_housing.Housing`

        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_housing.PJTHousing`
        """

        self._part = db_obj.part

        position = db_obj.position2d
        angle = db_obj.angle2d
        material = _materials.Generic(_color.Color(*Config.colors.housing))

        # This housing's own font-driven cavity slot height and cavity-
        # axis/text-axis extents (see the class docstring's own "Sizing"
        # paragraph) -- cached on db_obj (see PJTHousing.stack_geometry's
        # own docstring), set once here and treated as fixed after that,
        # same as db_obj.cavity_geometry.

        with parent.mainframe.editor2d.editor.context:
            vbo = _rectangle.create_vbo()
            self._text_vbo = self._build_corner_label(db_obj, angle.y)

            height = self._text_vbo.height
            width = self._text_vbo.width

            stack_geometry = db_obj.stack_geometry

            padding = stack_geometry.text_padding
            cavity_extent = stack_geometry.cavity_extent
            housing_width = stack_geometry.housing_width

            x = (housing_width / 2.0) - padding - (width / 2.0)
            z = (cavity_extent / 2.0) - padding - (height / 2.0)

            self._text_position = _point.Point(x, 0.0, z)

            self._text_position @= angle
            self._text_position += position

            self._text_scale = _point.Point(1.0, 1.0, 1.0)
            self._text_material = _materials.Generic(
                _color.Color(*Config.colors.label))

            scale = _point.Point(stack_geometry.housing_width,
                                 1.0, stack_geometry.cavity_extent)

            super().__init__(parent, db_obj, vbo, angle,
                             position, scale, material)

            self.db_obj.bind(self._update_name, 'name')

    def _update_name(self, *_):

        with self.parent.mainframe.editor2d.editor.context:
            self._text_vbo = self._build_corner_label(self.db_obj, self.angle.y)

            height = self._text_vbo.height
            width = self._text_vbo.width

            stack_geometry = self.db_obj.stack_geometry

            padding = stack_geometry.text_padding
            cavity_extent = stack_geometry.cavity_extent
            housing_width = stack_geometry.housing_width

            self._text_position.x = (housing_width / 2.0) - padding - (width / 2.0)
            self._text_position.z = (cavity_extent / 2.0) - padding - (height / 2.0)

            self._text_position @= self.angle
            self._text_position += self._position

    @property
    @_check_types.do
    def smooth(self) -> bool:
        return False

    @smooth.setter
    def smooth(self, value: bool | None):
        pass

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """
        Update this housing's own OBB/AABB only -- nothing else
        needed here: ``PJTHousing._update_position2d`` is bound to this
        same ``position2d`` ``Point`` (see ``database/project_db/
        pjt_housing.py``, bound before this object's own inherited
        ``BaseVar.__init__`` binds :meth:`_update_position` to it --
        ``__init__`` above reads ``db_obj.position2d`` to get *position*
        before calling ``super().__init__()``) and already batch-
        translates every cavity's own ``position2d`` by the same delta,
        one ``executemany`` for the whole housing rather than a per-
        cavity write -- and each cavity's/seated terminal's own
        schematic view object already has its own bound ``position2d``/
        callback (inherited ``BaseVar._update_position``, a cheap
        OBB/AABB delta translate), fired by that same DB-level cascade's
        own ``pos._process_callbacks()``, so by the time this method
        runs every child is already correctly repositioned -- this class
        plays no part in propagating any of it.
        """

        delta = position - self._o_position
        self._text_position += delta

        super()._update_position(position)

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        """
        See :meth:`_update_position` -- same reason, for rotation:
        ``PJTHousing._update_angle2d`` already batch-rotates every
        cavity's own ``position2d`` (and, for a cavity with a seated
        terminal, that terminal's own ``position2d``/``wire_position2d``)
        about this housing's own ``position2d`` pivot -- neither a
        cavity nor a terminal has an ``angle2d`` of its own that follows
        the housing's rotation, only its schematic position does.
        """

        inverse = self._o_angle.inverse

        self._text_position -= self._position
        self._text_position @= inverse
        self._text_position @= angle
        self._text_position += self._position

        # h_align is baked into the Text's own vertex layout at
        # construction time -- unlike angle/position, render() can't
        # just swap it live -- so only rebuild when actually crossing
        # into/out of the 180 special case (see _is_180's own
        # docstring), not on every angle push.
        if _is_180(angle.y) != _is_180(self._o_angle.y):
            self._text_vbo = self._build_corner_label(self.db_obj, angle.y)

        super()._update_angle(angle)

    @_check_types.do
    def _build_corner_label(self, db_obj, degrees: float):
        text = f'{db_obj.name}\n{self._part.part_number}\n{self._part.manufacturer.name}'

        # RIGHT-justified normally (0/90/270, following the housing's
        # own rotation -- see render()) -- flipped to LEFT at 180, where
        # the glyph itself renders upright instead (see _is_180's own
        # docstring), so the block's own internal line-justification
        # flips to the opposite side to keep reading in the same
        # direction relative to its own anchor.
        if _is_180(degrees):
            h_align = build123d.TextAlign.LEFT
        else:
            h_align = build123d.TextAlign.RIGHT

        vbo = _text.Text(text, Config.object_sizes.housing.font_size,
                         build123d.FontStyle.ITALIC,
                         local_tilt=_text.TOP_DOWN_TILT,
                         h_align=h_align,
                         center_anchor=True)

        return vbo

    @_check_types.do
    def render(self, shaders):
        """
        Render the housing rectangle body, then swap this object's
        own ``_vbo``/``_material``/``_angle``/``_scale``/``_position``
        for the corner label's (one line at a time) and render again
        through the exact same inherited pipeline -- the same swap-
        call-super()-restore idiom ``objects_3d/wire.py``'s ``Wire``
        already uses for its own multi-segment render, rather than a
        separate hand-rolled draw path. ``Text`` stands in directly as
        a ``_vbo`` here (see its own "VBOHandlerBase-compatible
        interface" docstring in ``shapes/text.py``).

        This is the entire extent of what a ``Housing`` renders --
        cavity names and terminal brackets/names are each drawn
        independently by their own ``objects_schematic/cavity.py``'s
        ``Cavity``/``objects_schematic/terminal.py``'s ``Terminal``.
        """

        if not self.is_visible or self._position is None:
            return

        super().render(shaders)

        real_vbo, real_material, real_selected_material, real_angle, real_scale, real_position = (
            self._vbo, self._material, self._selected_material,
            self._angle, self._scale, self._position)

        self._material = self._text_material
        self._selected_material = self._text_material

        # Follows the housing's own rotation at 0/90/270, exactly like
        # the rectangle body just drawn above -- except at 180, where a
        # full half-turn would render the glyphs upside-down, so the
        # angle is forced back to identity instead (see _is_180's own
        # docstring -- _build_corner_label already flipped this same
        # Text's own h_align to compensate, whenever this last crossed
        # into/out of 180).
        if _is_180(real_angle.y):
            self._angle = _angle.Angle()
        else:
            self._angle = real_angle
        self._scale = self._text_scale
        self._position = self._text_position
        self._vbo = self._text_vbo

        super().render(shaders)

        self._vbo, self._material, self._selected_material, self._angle, self._scale, self._position = (
            real_vbo, real_material, real_selected_material,
            real_angle, real_scale, real_position)

    @_check_types.do
    def move_to(self, world_x: float, world_y: float):
        """
        Move housing to new position. Cavity/terminal positions cascade
        automatically via ``PJTHousing._update_position2d`` (see
        :meth:`_update_position`'s own docstring) -- no separate push
        needed here.
        """

        if self._position is None:
            return

        with self._position:
            self._position.x = world_x
            self._position.z = world_y

    @classmethod
    @_check_types.do
    def start_add(cls, mainframe: "_ui.MainFrame") -> "_housing.Housing | None":
        """
        Single-click free placement, schematic-native -- mirrors
        objects_3d.housing.Housing.start_add. This housing's own
        position3d is left unset here (None), same as position2d is
        left unset there -- PJTHousingsTable.insert auto-fills whichever
        one is left None with a fresh (0, 0, 0)/(0, 0) placeholder point,
        so it still renders (just unpositioned) in the view that didn't
        place it, rather than being truly inert.
        """

        canvas = mainframe.editor2d.editor

        part_id = mainframe.editor_db.editor.housings.GetSelection()

        if part_id is None:
            from ...ui.dialogs import part_search as _part_search
            from ...ui import editor_db as _editor_db
            from PySide6.QtWidgets import QDialog

            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.HousingsPage,
                mainframe.global_db.housings_table,
                'Add Housing')

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

        from .. import housing as _housing_facade

        ptables = mainframe.project.ptables
        part = mainframe.project.gtables.housings_table[part_id]
        name = f'{part.manufacturer.name} {part.part_number}'
        position2d = ptables.pjt_points2d_table.insert(0, 0)

        db_obj = ptables.pjt_housings_table.insert(
            part_id, name, None, position2d.db_id)

        facade = _housing_facade.Housing(mainframe, db_obj)

        from ...add_handlers.editor_schematic import housing as _add_housing

        handler = _add_housing.Housing(canvas, facade)
        facade.objschematic._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.objschematic

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """
        Forwards to an active add-session (see start_add); falls back
        to BaseSchematic's own generic drag handling otherwise.
        """

        # avoid a cycle at import time
        from ...add_handlers.editor_schematic import housing as _add_housing

        if isinstance(self._active_handler, _add_housing.Housing):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

    @_check_types.do
    def get_context_menu(self):
        """
        Return this housing's own right-click context menu (see
        ``ui/mainframe.py``'s ``_on_obj_right_click_2d``, which calls
        this on whatever ``objschematic`` was right-clicked).
        """

        return HousingMenu(self.editor2d.editor, self)


class HousingMenu(QtWidgets.QMenu):
    """
    Represent a housing menu in :mod:`harness_designer.objects.objects_schematic.housing`.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """
        Initialise the :class:`HousingMenu` instance.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN

        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """

        QtWidgets.QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        action = self.addAction('Add Terminal')
        action.triggered.connect(self.on_add_terminal)

        action = self.addAction('Add CPA Lock')
        action.triggered.connect(self.on_add_cpa_lock)

        action = self.addAction('Add TPA Lock')
        action.triggered.connect(self.on_add_tpa_lock)

        action = self.addAction('Add Cover')
        action.triggered.connect(self.on_add_cover)

        action = self.addAction('Add Boot')
        action.triggered.connect(self.on_add_boot)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate2DMenu(canvas, selected)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror2DMenu(canvas, selected)
        self.addMenu(mirror_menu)

        self.addSeparator()
        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_add_seal(self):
        """
        Handle the add seal event.
        """

        pass

    @_check_types.do
    def on_add_terminal(self):
        """
        Add terminals to this housing's cavities -- pick an empty
        cavity in the schematic view to seat one (see
        add_handlers.editor_schematic.terminal).
        """

        from . import terminal as _terminal_2d

        mainframe = self.selected.mainframe
        housing = self.selected.parent

        @_check_types.do
        def _do():
            _terminal_2d.Terminal.start_add(mainframe, housing=housing)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_cpa_lock(self):
        """
        Handle the add CPA lock event.
        """

        pass

    @_check_types.do
    def on_add_tpa_lock(self):
        """
        Handle the add TPA lock event.
        """

        pass

    @_check_types.do
    def on_add_cover(self):
        """
        Handle the add cover event.
        """

        pass

    @_check_types.do
    def on_add_boot(self):
        """
        Handle the add boot event.
        """

        pass

    @_check_types.do
    def on_select(self):
        """
        Handle the select event.
        """

        pass

    @_check_types.do
    def on_clone(self):
        """
        Handle the clone event.
        """

        pass

    @_check_types.do
    def on_delete(self):
        """
        Handle the delete event.
        """

        pass

    @_check_types.do
    def on_properties(self):
        """
        Handle the properties event.
        """

        pass
