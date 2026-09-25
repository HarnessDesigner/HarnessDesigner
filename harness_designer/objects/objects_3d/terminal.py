# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union
from collections.abc import Callable

import os

import numpy as np
from PySide6 import QtWidgets

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...gl.canvas_base import interaction as _interaction
from ...shapes import cylinder as _cylinder
from ...shapes import box as _box
from ...gl import materials as _materials
from ... import color as _color
from ... import config as _config
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from ...database.project_db import pjt_cavity as _pjt_cavity_db
    from ...database.global_db import model3d as _model3d
    from ...database.global_db import terminal as _global_terminal
    from .. import terminal as _terminal
    from .. import wire as _wire
    from .. import housing as _housing
    from .. import cavity as _cavity
    from ...gl import shaders as _shaders
    from ... import ui as _ui
    from ...ui.dialogs import part_search as _part_search


Config = _config.Config.editor_3d

_BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_GENERIC_MODEL_PATH = os.path.join(_BASE_PATH, 'models')


class Terminal(_base_3d.Base3D):
    """Represent a terminal in :mod:`harness_designer.objects.objects_3d.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_terminal.Terminal" = None
    db_obj: "_pjt_terminal.PJTTerminal" = None

    # Position is always computed from the owning cavity (see
    # terminal_handler._female_terminal_position/_male_terminal_position),
    # never placed freely by the user -- floor lock would silently overwrite
    # that computed Y and persist the overwrite to the DB.
    _floor_lock_exempt = True

    @_check_types.do
    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal") -> None:
        """Initialise the :class:`Terminal` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_terminal.Terminal`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_terminal.PJTTerminal`
        """

        with parent.mainframe.editor3d.context:
            self._part = db_obj.part
            color = self._part.plating.color
            self._color = color.ui
            material = _materials.Polished(color.ui)

            model = self._part.model3d

            is_round = self._part.round_terminal

            if is_round:
                vbo = _cylinder.create_vbo()
            else:
                vbo = _box.create_vbo()

            # Placeholder/analog geometry shown while the real model downloads
            # (or when none is assigned) -- fall back to the cavity's own
            # dimensions when this part is missing any of its own measurements.
            pjt_cavity = db_obj.cavity
            if pjt_cavity is not None:
                width, height, length = self._part.effective_size(pjt_cavity.part)
            else:
                width, height, length = self._part.width, self._part.height, self._part.length

            if model is None:
                family = self._part.family.name.lower()
                series = self._part.series.name.lower()

                if family == 'deutsch' or series == 'deutsch':
                    pn = self._part.part_number

                    for pre in (
                        '2362989-1', '5960-203-04141', '0460-256',
                        '0460-002', '0460-010', '0460-202', '0460-204'
                    ):
                        if pn.startswith(pre):
                            filepath = os.path.join(_GENERIC_MODEL_PATH, 'deutsch terminal male solid.stl')
                            model = parent.mainframe.global_db.models3d_table.insert(filepath)

                            if model is not None:
                                self._part.model3d_id = model.db_id

                            break
                    else:
                        for pre in (
                            '0462-004', '0462-005', '0462-006',
                            '0462-201', '0462-203'
                        ):
                            if pn.startswith(pre):
                                filepath = os.path.join(_GENERIC_MODEL_PATH, 'deutsch terminal female solid.stl')
                                model = parent.mainframe.global_db.models3d_table.insert(filepath)

                                if model is not None:
                                    self._part.model3d_id = model.db_id
                else:
                    gender = self._part.gender
                    blade_size = self._part.blade_size

                    if gender is not None and blade_size:
                        gender = gender.name
                        filename = f'generic terminal {gender.lower()} {blade_size}'

                        if is_round:
                            filename += ' round'

                        filename += '.stp'

                        filepath = os.path.join(_GENERIC_MODEL_PATH, filename)
                        if os.path.exists(filepath):
                            model = parent.mainframe.global_db.models3d_table.insert(filepath)

                            if model is not None:
                                self._part.model3d_id = model.db_id

            scale = _point.Point(width, height, length)
            angle = db_obj.angle3d

            super().__init__(parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

            # Cavity surface overlay (wire-side always, pin-side for
            # female/undetermined-gender terminals) — resolved lazily in
            # render() and cached until the owning cavity changes.
            self._overlay_cavity_id = None
            self._overlay_housing_3d = None
            self._overlay_cavity_obj = None
            self._overlay_wire_surf_idx: int | None = None
            self._overlay_wire_marker = None
            self._overlay_pin_surf_idx: int | None = None

        # model.load()'s callback (_set_model) always fires, whether the
        # model needed a fresh download/conversion or was already cached
        # from a prior session -- checked here, before load() can possibly
        # run synchronously, to tell those two cases apart once _set_model
        # actually fires. uuid is only populated once conversion finishes,
        # so uuid is None means this is a genuine first-time download: the
        # placeholder scale above was necessarily computed from Terminal.
        # effective_size/catalog dimensions (no model to measure yet), which
        # can meaningfully differ from the real, converted model's size, so
        # the position (computed from that same placeholder length by
        # AddTerminalHandler) needs recomputing once the real model lands.
        # uuid already set means the position was already computed from
        # real model data (or a user has since moved it) -- leave it alone.
        self._model_is_first_download = model is not None and model.uuid is None

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

    @_check_types.do
    def _update_position(self, position: _point.Point) -> None:
        super()._update_position(position)

        # A free-standing terminal's wire points ride along with it (no-op
        # for a seated one -- its housing carries them).
        self.db_obj.sync_free_wire_points('3d')

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle) -> None:
        super()._update_angle(angle)
        self.db_obj.sync_free_wire_points('3d')

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_terminals

        return smooth

    @smooth.setter
    @_check_types.do
    def smooth(self, value: bool | None) -> None:
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def _set_model(self, model: "_model3d.Model3D") -> None:
        super()._set_model(model)

        family = self._part.family.name.lower()
        series = self._part.series.name.lower()

        if family == 'deutsch' or series == 'deutsch':
            pn = self._part.part_number

            for pre in (
                '2362989-1', '5960-203-04141', '0460-256', '0460-002',
                '0460-010', '0460-202', '0460-204', '0462-004', '0462-005',
                '0462-006', '0462-201', '0462-203'
            ):
                if pn.startswith(pre):
                    width, height, length = self._part.size

                    if width and height and length:
                        with self._scale:
                            self._scale.x = width
                            self._scale.y = height
                            self._scale.z = length
                    break

        if self._model_is_first_download:
            self._model_is_first_download = False

            from ...handlers import terminal_handler as _terminal_handler

            _terminal_handler.reposition_from_model(self.db_obj)

    @_check_types.do
    def _refresh_overlay_state(self) -> None:
        """(Re)resolve which of the housing's mesh surfaces this terminal
        should overlay, and which wrapper object's selection state drives
        the overlay color.

        The cavity/housing object lookup (walking .get_object() chains) is
        cached by cavity_id -- cheap no-op once the owning cavity stops
        changing between calls. But cavity_3d.surf_idx/wire_surf_idx/
        _wire_marker are re-read every call, uncached: match_cavity_
        surfaces() runs asynchronously (once the housing's model finishes
        loading) and can still be pending the first few times this terminal
        renders (e.g. on project load, where every object gets constructed
        before any housing's async model callback has had a chance to run)
        -- caching a still -1/None value against cavity_id would otherwise
        permanently freeze the overlay off even after match_cavity_surfaces
        later resolves it.
        """
        pjt_cavity = self.db_obj.cavity
        cavity_id = pjt_cavity.db_id if pjt_cavity is not None else None

        if cavity_id != self._overlay_cavity_id:
            self._overlay_cavity_id = cavity_id
            self._overlay_housing_3d = None
            self._overlay_cavity_obj = None

            if pjt_cavity is not None:
                cavity_obj = pjt_cavity.get_object()
                if cavity_obj is not None and cavity_obj.obj3d is not None:
                    housing_pjt = pjt_cavity.housing
                    housing_obj = (
                        housing_pjt.get_object() if housing_pjt is not None else None)
                    if housing_obj is not None and housing_obj.obj3d is not None:
                        self._overlay_cavity_obj = cavity_obj
                        self._overlay_housing_3d = housing_obj.obj3d

        self._overlay_wire_surf_idx = None
        self._overlay_wire_marker = None
        self._overlay_pin_surf_idx = None

        if self._overlay_cavity_obj is None:
            return

        cavity_3d = self._overlay_cavity_obj.obj3d
        if cavity_3d.wire_surf_idx >= 0:
            self._overlay_wire_surf_idx = cavity_3d.wire_surf_idx
        elif cavity_3d._wire_marker is not None:  # NOQA
            self._overlay_wire_marker = cavity_3d._wire_marker  # NOQA

        if self._pin_overlay_needed(pjt_cavity) and cavity_3d.surf_idx >= 0:
            self._overlay_pin_surf_idx = cavity_3d.surf_idx

    @_check_types.do
    def _pin_overlay_needed(self, pjt_cavity: "_pjt_cavity_db.PJTCavity") -> bool:
        """Male terminals never show a pin-side overlay; female terminals
        always do; an undetermined gender defaults to showing it (terminal
        part gender checked first, then the housing's gender).
        """
        term_gender = (self._part.gender.name or '').strip().lower()
        if term_gender == 'male':
            return False
        if term_gender == 'female':
            return True

        housing_gender = (pjt_cavity.housing.part.gender.name or '').strip().lower()
        if housing_gender == 'male':
            return False

        return True

    @_check_types.do
    def render_cavity_overlay(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw this terminal's cavity wire-side/pin-side overlay onto the
        owning housing's mesh.

        Called from ``Housing3D.render()`` immediately after the housing's
        own base mesh -- NOT from this terminal's own ``render()`` -- because
        the per-frame object draw order (``gl.canvas3d.culling``) sorts
        opaque objects by camera distance, not by any housing/terminal
        relationship. Drawing the overlay from this terminal's own render()
        call left it just as likely to land BEFORE the housing's own opaque
        mesh renders in a given frame as after, and ``_draw_overlay_triangles``
        draws with depth writes off (so it never protects itself once drawn)
        -- whenever the housing rendered second it silently painted over the
        overlay, producing exactly the hit-or-miss visibility this fixes.
        Confirmed by the housing always showing every cavity's overlay
        correctly once selected -- a selected translucent object is deferred
        to render after every opaque object in the scene (see
        gl.canvas3d.canvas._on_draw), which incidentally forced the housing
        to always draw last too.
        """
        self._refresh_overlay_state()

        housing_3d = self._overlay_housing_3d
        if housing_3d is None:
            return

        cavity_obj = self._overlay_cavity_obj
        if cavity_obj is not None and cavity_obj.is_selected:
            color = self._selected_material.diffuse
        else:
            # self._unselected_material is a PolishedMaterial -- it remaps
            # any input color into a narrow metallic-looking band (see
            # PolishedMaterial.__init__), so its .diffuse is nearly the same
            # dull gray/brass regardless of the terminal's actual color and
            # is useless as a distinct identifier. Use the terminal's raw
            # color instead, same as self._color already stores.
            color = self._color.rgba_scalar

        if self._overlay_wire_surf_idx is not None:
            housing_3d.render_surface_overlay(shaders, self._overlay_wire_surf_idx, color)
        elif self._overlay_wire_marker is not None:
            housing_3d.render_marker_overlay(shaders, self._overlay_wire_marker, color)

        if self._overlay_pin_surf_idx is not None:
            housing_3d.render_surface_overlay(shaders, self._overlay_pin_surf_idx, color)

    @property
    @_check_types.do
    def seal_position(self) -> _point.Point:
        """Return the seal position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.wire_position

    @property
    @_check_types.do
    def wire_position(self) -> _point.Point:
        """Return the wire position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.db_obj.wire_position3d

    @classmethod
    @_check_types.do
    def _search_params_for_cavity(
        cls, mainframe: "_ui.MainFrame", housing: "_housing.Housing", cavity: "_cavity.Cavity"
    ) -> "_part_search.SearchParameters":
        """Search-box seed for Mode 1 (housing AND cavity both given).

        The cavity's own manually-curated ``compat_terminals`` list, if
        the catalog has one -- rendered as real ``part number: "PN1",
        "PN2"`` search text, literally visible (and further editable)
        in the search box. Otherwise the housing's actual gender plus
        this cavity's actual expected blade size(s), same as if the
        user had typed/clicked those filters themselves -- a LIVE
        filter against current catalog data every time the dialog
        opens, not a precomputed, staleness-prone part-number list.
        This is what fixes the original bug (a part silently dropping
        out of the default view after its own dimensions got filled in
        the first time it was used) -- see
        ``ui.dialogs.part_search``'s "Compat-seed integration"
        design notes for the full reasoning.
        """
        from ...ui.dialogs import part_search as _part_search

        g_cavity = cavity.db_obj.part
        g_housing = housing.db_obj.part

        compat = g_cavity.compat_terminals
        if compat:
            params = _part_search.SearchParameters()
            for t in compat:
                params.add('part_number', _part_search.SearchTerm(phrase=t.part_number))
            return params

        params = _part_search.SearchParameters()

        gender = mainframe.global_db.genders_table[g_housing.gender_id]
        params.add('gender_id', _part_search.SearchTerm(phrase=gender.name))

        terminal_sizes = g_cavity.terminal_sizes
        if terminal_sizes:
            for size in terminal_sizes:
                params.add('blade_size', _part_search.SearchTerm(value=str(size)))
            return params

        max_dim = max(g_cavity.width or 0.0, g_cavity.height or 0.0)
        if max_dim > 0.0:
            params.add('blade_size', _part_search.SearchTerm(operator='<=', value=str(max_dim)))

        return params

    @classmethod
    @_check_types.do
    def _search_params_for_housing(
        cls, mainframe: "_ui.MainFrame", housing: "_housing.Housing"
    ) -> "_part_search.SearchParameters":
        """Search-box seed for Mode 2 (housing only) -- see
        :meth:`_search_params_for_cavity`, aggregated across every
        cavity in the housing instead of just one.
        """
        from ...ui.dialogs import part_search as _part_search

        g_housing = housing.db_obj.part

        compat = g_housing.compat_terminals
        if compat:
            params = _part_search.SearchParameters()
            for t in compat:
                params.add('part_number', _part_search.SearchTerm(phrase=t.part_number))
            return params

        params = _part_search.SearchParameters()

        gender = mainframe.global_db.genders_table[g_housing.gender_id]
        params.add('gender_id', _part_search.SearchTerm(phrase=gender.name))

        all_sizes = set()
        for g_cav in g_housing.cavities:
            all_sizes.update(g_cav.terminal_sizes)

        if all_sizes:
            for size in all_sizes:
                params.add('blade_size', _part_search.SearchTerm(value=str(size)))
            return params

        max_dim = 0.0
        for pjt_cav in housing.db_obj.cavities:
            g_cav = pjt_cav.part
            max_dim = max(max_dim, g_cav.width or 0.0, g_cav.height or 0.0)

        if max_dim > 0.0:
            params.add('blade_size', _part_search.SearchTerm(operator='<=', value=str(max_dim)))

        return params

    @staticmethod
    @_check_types.do
    def _pick_free_part(mainframe: "_ui.MainFrame") -> _Union["_global_terminal.Terminal", None]:
        """Part-search dialog + dimension check for a terminal that is not
        going into a cavity (so no cavity-derived search filters). None if
        cancelled."""
        from ...handlers import terminal_handler as _terminal_handler
        from ...ui.dialogs import part_search as _part_search
        from ...ui import editor_db as _editor_db
        from ...ui.dialogs.dimensions_dialog import ensure_dimensions

        dlg = _part_search.SearchDialog(
            mainframe, _editor_db.TerminalsPage, mainframe.global_db.terminals_table, 'Add Terminal')

        part_id = None
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            part_id = dlg.GetValue()

        dlg.deleteLater()

        if part_id is None:
            return None

        part = mainframe.project.ptables.global_db.terminals_table[part_id]

        estimates, suggested = _terminal_handler.estimate_dimensions(mainframe, part)
        if not ensure_dimensions(mainframe, part, part.part_number, estimates, suggested):
            return None

        return part

    @classmethod
    @_check_types.do
    def _create_free(
        cls, mainframe: "_ui.MainFrame", part: "_global_terminal.Terminal",
        direction3d: tuple[float, float, float], direction_pegboard: tuple[float, float, float],
        place: Callable[[], tuple[tuple[float, float, float], tuple[float, float, float]]]
    ) -> "_terminal.Terminal":
        """Build a terminal that is not seated in any cavity, facing
        *direction3d*/*direction_pegboard* (its +Z), at whatever *place*
        returns -- ``((x, y, z), (px, py, pz))``, the 3D and peg-board
        positions. *place* runs twice: once before the facade exists (so
        the terminal is never created at the origin) and again after it
        does, since Terminal.__init__ may only then assign a generic model
        to a part that had none (see start_add's Mode 1) and *place* may
        depend on the part's measured extent.
        """
        from .. import terminal as _terminal_facade

        ptables = mainframe.project.ptables

        (x, y, z), _ = place()
        point_db = ptables.pjt_points3d_table.insert(x, y, z)

        name = f'{part.manufacturer.name} {part.part_number}'
        db_obj = ptables.pjt_terminals_table.insert(part.db_id, name, None, point_db.db_id, None)

        # Written before anything reads the terminal's angles, so the row is
        # created already facing the right way (+Z is canonical forward).
        db_obj._update_angle3d(_angle.Angle.from_direction(np.array(direction3d)))  # NOQA
        db_obj._update_angle_pegboard(_angle.Angle.from_direction(np.array(direction_pegboard)))  # NOQA

        facade = _terminal_facade.Terminal(mainframe, db_obj)

        (x, y, z), (px, py, pz) = place()

        position = db_obj.position3d
        position += _point.Point(x, y, z) - position

        pegboard_position = db_obj.position_pegboard
        pegboard_position += _point.Point(px, py, pz) - pegboard_position

        mainframe.project.add_terminal(facade)
        facade.reconnect_free_wires()

        return facade

    @classmethod
    @_check_types.do
    def add_at_wire_end(
        cls, mainframe: "_ui.MainFrame", wire: "_wire.Wire", end: str
    ) -> _Union["_terminal.Terminal", None]:
        """Crimp a new terminal, not seated in any cavity, onto the free
        (dangling) *end* ('start' or 'stop') of *wire*.

        The terminal's back (wire-side) face center lands on the wire's end
        in both the 3D and peg-board views, its front facing away along the
        wire's last segment, and :meth:`objects.terminal.Terminal.
        reconnect_free_wires` then attaches the wire (its end is at that
        terminal's own wire-side point, the same match a replacement terminal
        in a cavity gets). Synchronous once a part has been picked.
        """
        from ...handlers import terminal_handler as _terminal_handler

        if end == 'start':
            sibling = wire.start_sibling
        else:
            sibling = wire.stop_sibling

        if sibling is not None:
            return None

        part = cls._pick_free_part(mainframe)
        if part is None:
            return None

        wire_db = wire.db_obj

        def _end_and_direction(
            waypoints: list, start_point: _point.Point, stop_point: _point.Point
        ) -> tuple[_point.Point, tuple[float, float, float]]:
            if end == 'start':
                end_point = start_point

                if waypoints:
                    neighbor = waypoints[0].point
                else:
                    neighbor = stop_point
            else:
                end_point = stop_point

                if waypoints:
                    neighbor = waypoints[-1].point
                else:
                    neighbor = start_point

            return end_point, _terminal_handler.free_end_direction(end_point, neighbor)

        end3d, direction3d = _end_and_direction(
            wire_db.waypoints3d, wire_db.start_position3d, wire_db.stop_position3d)
        end_pegboard, direction_pegboard = _end_and_direction(
            wire_db.waypoints_pegboard, wire_db.start_position_pegboard,
            wire_db.stop_position_pegboard)

        def _place() -> tuple[tuple[float, float, float], tuple[float, float, float]]:
            return (_terminal_handler.free_end_position(part, end3d, direction3d),
                    _terminal_handler.free_end_position(part, end_pegboard, direction_pegboard))

        return cls._create_free(mainframe, part, direction3d, direction_pegboard, _place)

    @classmethod
    @_check_types.do
    def add_free(
        cls, mainframe: "_ui.MainFrame", view: str, mouse_pos: _point.Point
    ) -> _Union["_terminal.Terminal", None]:
        """Place a terminal, not in any cavity and not on any wire, at the
        empty-space right click *mouse_pos* made in *view* ('3d' or
        'pegboard'), unrotated. The other view gets the same spot on the
        floor plane (y = 0), the way a placed housing does.
        """
        part = cls._pick_free_part(mainframe)
        if part is None:
            return None

        if view == '3d':
            click = mainframe.editor3d.editor.camera.get_position_on_focal_plane(mouse_pos)
        else:
            click = mainframe.editor_pegboard.editor.camera.screen_to_world(mouse_pos)

        cx, cy, cz = click.as_float

        if view == '3d':
            placement = ((cx, cy, cz), (cx, 0.0, cz))
        else:
            placement = ((cx, 0.0, cz), (cx, cy, cz))

        def _place() -> tuple[tuple[float, float, float], tuple[float, float, float]]:
            return placement

        forward = (0.0, 0.0, 1.0)
        return cls._create_free(mainframe, part, forward, forward, _place)

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", housing: _Union["_housing.Housing", None] = None,
        cavity: _Union["_cavity.Cavity", None] = None
    ) -> _Union["_terminal.Terminal", None]:
        """Three placement modes, exactly matching
        handlers.terminal_handler.AddTerminalHandler's own docstring:

        - *housing* and *cavity* both given: place immediately into that
          cavity -- synchronous, no interactive session armed at all.
        - *housing* only: interactive, snaps only to that housing's own
          empty cavities.
        - Neither given: interactive, snaps to any compatible cavity in
          the whole project.
        """
        from ...handlers import terminal_handler as _terminal_handler
        from ...ui.dialogs import part_search as _part_search
        from ...ui import editor_db as _editor_db

        canvas = mainframe.editor3d.editor

        if housing is not None and cavity is not None:
            initial_params = cls._search_params_for_cavity(mainframe, housing, cavity)
        elif housing is not None:
            initial_params = cls._search_params_for_housing(mainframe, housing)
        else:
            initial_params = None

        # Mode 3 checks the editor DB first; modes 1 & 2 always open the dialog.
        if housing is None:
            part_id = mainframe.editor_db.editor.terminals.GetSelection()
        else:
            part_id = None

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.TerminalsPage, mainframe.global_db.terminals_table,
                'Add Terminal', initial_params=initial_params)

            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()

            dlg.deleteLater()

            if part_id is None:
                return None

        ptables = mainframe.project.ptables
        part = ptables.global_db.terminals_table[part_id]

        from ...ui.dialogs.dimensions_dialog import ensure_dimensions
        estimates, suggested = _terminal_handler.estimate_dimensions(mainframe, part)
        if not ensure_dimensions(mainframe, part, part.part_number, estimates, suggested):
            return None

        name = f'{part.manufacturer.name} {part.part_number}'

        from .. import terminal as _terminal_facade
        from ...handlers import handler_base as _handler_base

        if cavity is not None:
            # Mode 1 -- immediate, synchronous, no interactive session.
            pjt_cavity = cavity.db_obj
            is_male = _terminal_handler._resolve_is_male(part, pjt_cavity.housing.part)  # NOQA

            # Terminal.__init__ assigns a generic stand-in model to a part
            # that has none. The position seeded below is measured before
            # that happens (no model -> symmetric split of the catalog
            # length), so it has to be recomputed once the facade exists.
            had_model = part.model3d is not None

            if is_male:
                tx, ty, tz = _terminal_handler._male_terminal_position(part, pjt_cavity)  # NOQA
            else:
                tx, ty, tz = _terminal_handler._female_terminal_position(part, pjt_cavity)  # NOQA

            point_db = ptables.pjt_points3d_table.insert(tx, ty, tz)
            db_obj = ptables.pjt_terminals_table.insert(
                part_id, name, None, point_db.db_id, pjt_cavity.db_id)

            facade = _terminal_facade.Terminal(mainframe, db_obj)
            _handler_base.HandlerBase.set_angle_from_cavity(facade, pjt_cavity)

            # Peg-board equivalent of the position3d seed above -- same
            # reasoning as position3d itself: this terminal needs its own
            # real, absolute position_pegboard the moment it's seated, not
            # just whatever PJTHousing._update_position_pegboard's cascade
            # happens to leave it at on a later housing move (that only
            # ever adds a delta, it never seeds an initial absolute
            # value). Confirmed 2026-09-11 (Kevin).
            if is_male:
                px, py, pz = _terminal_handler._male_terminal_position_pegboard(part, pjt_cavity)  # NOQA
            else:
                px, py, pz = _terminal_handler._female_terminal_position_pegboard(part, pjt_cavity)  # NOQA

            pegboard_position = db_obj.position_pegboard
            pegboard_position += _point.Point(px, py, pz) - pegboard_position

            if not had_model and part.model3d is not None:
                _terminal_handler.reposition_from_model(db_obj)

            mainframe.project.add_terminal(facade)
            facade.reconnect_free_wires()
            return facade

        preview_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.preview_color))
        compat_highlight = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.splice_highlight))
        plain_highlight = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.housing_highlight))

        project_cavities = []

        if housing is not None:
            # Mode 2 -- floating preview, snaps only to this housing's cavities.
            is_male = _terminal_handler._resolve_is_male(part, housing.db_obj.part)  # NOQA

            for cav in housing.cavities:
                if cav.db_obj.terminal is not None:
                    continue

                cav.identify(compat_highlight)
                project_cavities.append(cav)
        else:
            # Mode 3 -- floating preview, snaps to any empty cavity in the
            # project. Compatibility (compat_terminals/terminal_sizes/blade
            # size+gender) only decides the highlight color (compat_highlight
            # vs plain_highlight) -- it's advisory, not a snap gate, since
            # many real parts are missing enough DB data to ever match it,
            # which would otherwise make plenty of genuinely empty cavities
            # permanently unsnappable. Mirrors add_handlers.editor_schematic.
            # terminal's own Mode 3 ("every empty cavity project-wide").
            is_male = _terminal_handler._resolve_is_male(part)  # NOQA
            part_number = part.part_number
            blade_size = part.blade_size
            part_gender_id = part.gender_id

            for cav in mainframe.project.cavities:
                if cav.db_obj.terminal is not None:
                    continue

                g_cavity = cav.db_obj.part
                g_housing = cav.db_obj.housing.part

                compat = g_cavity.compat_terminals
                if any(t.part_number == part_number for t in compat):
                    cav.identify(compat_highlight)
                    project_cavities.append(cav)
                    continue

                gender_match = (g_housing.gender_id == part_gender_id)
                terminal_sizes = g_cavity.terminal_sizes

                if (
                    terminal_sizes and blade_size and
                    blade_size in terminal_sizes and gender_match
                ):
                    cav.identify(compat_highlight)
                    project_cavities.append(cav)
                    continue

                if not terminal_sizes and gender_match and blade_size:
                    max_dim = max(g_cavity.width or 0.0, g_cavity.height or 0.0)
                    if max_dim > 0.0 and blade_size <= max_dim:
                        cav.identify(compat_highlight)
                        project_cavities.append(cav)
                        continue

                cav.identify(plain_highlight)
                project_cavities.append(cav)

        pos_obj = ptables.pjt_points3d_table.insert(0, 0, 0)
        db_obj = ptables.pjt_terminals_table.insert(part_id, name, None, pos_obj.db_id, None)

        facade = _terminal_facade.Terminal(mainframe, db_obj)
        facade.identify(preview_material)

        from ...add_handlers.editor_3d import terminal as _add_terminal

        handler = _add_terminal.Terminal(canvas, facade, part, project_cavities, is_male)
        facade.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.obj3d

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object: object | None
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to Base3D's own generic drag/rotation handling otherwise.
        """
        from ...add_handlers.editor_3d import terminal as _add_terminal  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_terminal.Terminal):
            # A local reference, not another read of self._active_handler
            # below -- a CANCEL can delete this object's own facade,
            # whose generic delete() sees self._active_handler is this
            # same handler and clears it right there, before this call
            # even returns (see objects_3d.wire.Wire.handle_interaction).
            handler = self._active_handler
            handled = handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if handler.is_finished and self._active_handler is handler:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

    @_check_types.do
    def get_context_menu(self) -> "TerminalMenu":
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return TerminalMenu(self.mainframe.editor3d.editor, self)


class TerminalMenu(QtWidgets.QMenu):
    """Represent a terminal menu in :mod:`harness_designer.objects.objects_3d.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas: object, selected: "Terminal") -> None:
        """Initialise the :class:`TerminalMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QtWidgets.QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected.parent)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected.parent)
        self.addMenu(mirror_menu)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

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
    def on_add_wire(self) -> None:
        """Start the interactive wire placement flow, pinned to this
        terminal's own attach point -- the part-search dialog (pre-filtered
        to wires whose diameter fits) opens immediately, straight into
        phase 1, same as a cavity's/splice's own pinned Add Wire."""
        from PySide6 import QtCore
        from . import wire as _wire_3d

        mainframe = self.selected.mainframe
        terminal_obj = self.selected.parent

        @_check_types.do
        def _do() -> None:
            _wire_3d.Wire.start_add(mainframe, terminal=terminal_obj)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_seal(self) -> None:
        """Attach a seal to this terminal."""
        from PySide6 import QtCore
        from . import seal as _seal_3d

        mainframe = self.selected.mainframe
        terminal = self.selected.parent

        @_check_types.do
        def _do() -> None:
            _seal_3d.Seal.start_add(mainframe, terminal=terminal)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_trace_circuit(self) -> None:
        """Highlight every object on this terminal's circuit."""
        _menu_ops.trace_circuit(self.selected)

    @_check_types.do
    def on_select(self) -> None:
        """Make this terminal the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_clone(self) -> None:
        """Arm clone mode using this terminal as the template."""
        _menu_ops.clone_object(self.selected)

    @_check_types.do
    def on_delete(self) -> None:
        """Delete this terminal from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self) -> None:
        """Show this terminal's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
