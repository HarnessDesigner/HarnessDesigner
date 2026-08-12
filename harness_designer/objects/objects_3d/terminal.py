# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import os
from PySide6.QtWidgets import QMenu

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import cylinder as _cylinder
from ...shapes import box as _box
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal


Config = _config.Config.editor3d

_BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_GENERIC_MODEL_PATH = os.path.join(_BASE_PATH, 'models')


class Terminal(_base3d.Base3D):
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
                 db_obj: "_pjt_terminal.PJTTerminal"):
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

            _base3d.Base3D.__init__(
                self, parent, db_obj, vbo, angle, db_obj.position3d,
                scale, material)

            # Cavity surface overlay (wire-side always, pin-side for
            # female/undetermined-gender terminals) — resolved lazily in
            # render() and cached until the owning cavity changes.
            self._overlay_cavity_id = None
            self._overlay_housing_3d = None
            self._overlay_cavity_obj = None
            self._overlay_wire_surf_idx: int = None
            self._overlay_wire_marker_idx: int = None
            self._overlay_pin_surf_idx: int = None

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
    def _set_model(self, model):
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
        wire_marker_idx are re-read every call, uncached: match_cavity_
        surfaces() runs asynchronously (once the housing's model finishes
        loading) and can still be pending the first few times this terminal
        renders (e.g. on project load, where every object gets constructed
        before any housing's async model callback has had a chance to run)
        -- caching a still -1 index against cavity_id would otherwise
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
        self._overlay_wire_marker_idx = None
        self._overlay_pin_surf_idx = None

        if self._overlay_cavity_obj is None:
            return

        cavity_3d = self._overlay_cavity_obj.obj3d
        if cavity_3d.wire_surf_idx >= 0:
            self._overlay_wire_surf_idx = cavity_3d.wire_surf_idx
        elif cavity_3d.wire_marker_idx >= 0:
            self._overlay_wire_marker_idx = cavity_3d.wire_marker_idx

        if self._pin_overlay_needed(pjt_cavity) and cavity_3d.surf_idx >= 0:
            self._overlay_pin_surf_idx = cavity_3d.surf_idx

    @_check_types.do
    def _pin_overlay_needed(self, pjt_cavity) -> bool:
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
    def render(self, faces_program, edges_program, vertices_program):
        super().render(faces_program, edges_program, vertices_program)

    @_check_types.do
    def render_cavity_overlay(self) -> None:
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
            housing_3d.render_surface_overlay(self._overlay_wire_surf_idx, color)
        elif self._overlay_wire_marker_idx is not None:
            housing_3d.render_marker_overlay(self._overlay_wire_marker_idx, color)

        if self._overlay_pin_surf_idx is not None:
            housing_3d.render_surface_overlay(self._overlay_pin_surf_idx, color)

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """

        delta = position - self._o_position

        for point in (
            self.db_obj.wire_position3d,
            self.db_obj.attach_position3d,
            self.db_obj.seal_position3d
        ):
            point += delta

        _base3d.Base3D._update_position(self, position)

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        seal = self.db_obj.seal
        delta = angle - self._o_angle
        inverse = self._o_angle.inverse

        if seal is not None:
            t_angle = seal.angle3d
            t_angle += delta

        for point in (
            self.db_obj.wire_position3d,
            self.db_obj.attach_position3d,
            self.db_obj.seal_position3d
        ):
            point -= self._o_position
            point @= inverse
            point @= angle
            point += self._o_position

        _base3d.Base3D._update_angle(self, angle)

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

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return TerminalMenu(self.mainframe.editor3d.editor, self)

    @_check_types.do
    def _delete(self):
        self._dangle_attached_wires()
        super()._delete()

    @_check_types.do
    def _dangle_attached_wires(self):
        """Detach every wire attached to this terminal (see
        objects.terminal.Terminal.add_wire/.wires), leaving each dangling
        at its own fresh point wherever its own routing through this
        terminal last reached, instead of deleted or left referencing a
        point this terminal (and its cavity, if seated) own.

        add_wire tags a wire's own back point (and, if seated in a
        cavity, the cavity's own wire-position point) as its interior
        waypoints -- those are removed here along with their WireLayouts,
        since they're only meaningful while this terminal exists. Each
        wire gets its own new point at the same location (not a shared
        one) so more than one wire attached here doesn't end up still
        joined to the others through a point that no longer represents a
        real connection.
        """
        terminal_obj = self.parent
        ptables = self.mainframe.project.ptables
        db_obj = self.db_obj

        back_id = db_obj.wire_position3d_id_raw
        cavity = db_obj.cavity
        cav_back_id = cavity.wire_position3d_id_raw if cavity is not None else None
        routing_ids = {i for i in (back_id, cav_back_id) if i is not None}

        if not routing_ids:
            return

        last_routing_id = cav_back_id if cav_back_id is not None else back_id
        last_pos = ptables.pjt_points3d_table[last_routing_id].point

        for wire in list(terminal_obj.wires):
            wire_db = wire.db_obj
            waypoints = wire_db.waypoints3d
            removed = [wp for wp in waypoints if wp.db_id in routing_ids]
            if not removed:
                continue

            remaining = sorted(
                (wp for wp in waypoints if wp.db_id not in routing_ids),
                key=lambda w: w.idx)
            for i, wp in enumerate(remaining):
                wp.idx = i

            is_start = wire.start_sibling is terminal_obj

            new_point = ptables.pjt_points3d_table.insert(*last_pos.as_float)
            if is_start:
                wire_db.start_position3d_id = new_point.db_id
                wire.obj3d.set_start_position(new_point.point)
                wire.set_sibling(None, 'start')
            else:
                wire_db.stop_position3d_id = new_point.db_id
                wire.obj3d.set_stop_position(new_point.point)
                wire.set_sibling(None, 'stop')

            for wp in removed:
                self._delete_layout_at(ptables, wp.db_id)
                wp.delete()

            wire.obj3d.refresh_waypoints()

    @staticmethod
    @_check_types.do
    def _delete_layout_at(ptables, point_id):
        """Delete the WireLayout (if any) sitting at point_id."""
        for row in ptables.pjt_wire_layouts_table.select('id', position3d_id=point_id):
            layout_db = ptables.pjt_wire_layouts_table[row[0]]

            obj = layout_db.get_object()
            if obj is not None:
                obj.delete()
            break


class TerminalMenu(QMenu):
    """Represent a terminal menu in :mod:`harness_designer.objects.objects_3d.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`TerminalMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
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
    def on_add_wire(self):
        """Start the interactive wire placement flow, pinned to this
        terminal's own attach point -- the part-search dialog (pre-filtered
        to wires whose diameter fits) opens immediately, straight into
        phase 1, same as a cavity's/splice's own pinned Add Wire."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        terminal_obj = self.selected.parent

        _menu_ops.start_handler(
            mainframe,
            lambda: _handlers.AddWireHandler(mainframe, terminal=terminal_obj))

    @_check_types.do
    def on_add_seal(self):
        """Attach a seal to this terminal."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        terminal = self.selected.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddSealHandler(mainframe, terminal))

    @_check_types.do
    def on_trace_circuit(self):
        """Highlight every object on this terminal's circuit."""
        _menu_ops.trace_circuit(self.selected)

    @_check_types.do
    def on_select(self):
        """Make this terminal the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_clone(self):
        """Arm clone mode using this terminal as the template."""
        _menu_ops.clone_object(self.selected)

    @_check_types.do
    def on_delete(self):
        """Delete this terminal from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self):
        """Show this terminal's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
