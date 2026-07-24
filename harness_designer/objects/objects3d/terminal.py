# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

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


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal


Config = _config.Config.editor3d


class Terminal(_base3d.Base3D):
    """Represent a terminal in :mod:`harness_designer.objects.objects3d.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_terminal.Terminal" = None
    db_obj: "_pjt_terminal.PJTTerminal" = None

    # Position is always computed from the owning cavity (see
    # terminal_handler._female_terminal_position/_male_terminal_position),
    # never placed freely by the user -- floor lock would silently overwrite
    # that computed Y and persist the overwrite to the DB.
    _floor_lock_exempt = True

    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal"):
        """Initialise the :class:`Terminal` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_terminal.Terminal`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_terminal.PJTTerminal`
        """

        parent.mainframe.editor3d.context.acquire()

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

        parent.mainframe.editor3d.context.release()

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

    def _set_model(self, model):
        super()._set_model(model)

        if self._model_is_first_download:
            self._model_is_first_download = False

            from ...handlers import terminal_handler as _terminal_handler

            _terminal_handler.reposition_from_model(self.db_obj)

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

    def render(self, faces_program, edges_program, vertices_program):
        super().render(faces_program, edges_program, vertices_program)

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

    def _update_position(self, position: _point.Point):
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        seal = self.db_obj.seal
        if seal is not None:
            delta = position - self._o_position
            t_position = seal.position3d
            t_position += delta

        _base3d.Base3D._update_position(self, position)

    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        seal = self.db_obj.seal
        if seal is not None:
            delta = angle - self._o_angle
            t_angle = seal.angle3d
            t_angle += delta

        _base3d.Base3D._update_angle(self, angle)

    @property
    def seal_position(self) -> _point.Point:
        """Return the seal position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.wire_position

    @property
    def wire_position(self) -> _point.Point:
        """Return the wire position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.db_obj.wire_position3d

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return TerminalMenu(self.mainframe.editor3d.editor, self)

    def _delete(self):
        self._delete_wire_routing_stub()
        super()._delete()

    def _delete_wire_routing_stub(self):
        """Remove the internal wire-routing stub(s)/layout(s) this terminal
        owns.

        See handlers.wire_handler._route_from_terminal for how these are
        built: a stub wire + WireLayout from the terminal's own crimp
        point (attach_point3d_id) to its wire-side layout point
        (wire_point3d_id) -- and, when seated in a cavity, a second stub +
        layout continuing on from there to the cavity's own wire-side
        point. Same behavior either way: whatever real wire(s) continue
        from the last point in that chain are left dangling there, not
        deleted, and every wire past the first sharing that point gets its
        own new point at the same coordinates so removing this terminal
        doesn't leave them all still joined to each other.
        """
        db_obj = self.db_obj
        ptables = self.mainframe.project.ptables

        attach_id = db_obj.attach_point3d_id_raw
        back_id = db_obj.wire_point3d_id_raw

        if attach_id is None or back_id is None:
            return

        self._delete_wire_stub_between(ptables, attach_id, back_id)
        self._delete_layout_at(ptables, back_id)

        final_point_id = back_id

        cavity = db_obj.cavity
        if cavity is not None:
            cav_back_id = cavity.wire_point3d_id_raw
            if cav_back_id is not None:
                self._delete_wire_stub_between(ptables, back_id, cav_back_id)
                self._delete_layout_at(ptables, cav_back_id)
                final_point_id = cav_back_id

        if final_point_id != back_id:
            from ...handlers.transition_handler import _delete_point_if_orphaned
            _delete_point_if_orphaned(ptables, back_id)

        self._detach_extra_wires_at(ptables, final_point_id)

    @staticmethod
    def _delete_wire_stub_between(ptables, start_id, stop_id):
        """Delete the wire (if any) spanning exactly start_id -> stop_id."""
        for row in ptables.pjt_wires_table.select('id', start_point3d_id=start_id):
            wire_db = ptables.pjt_wires_table[row[0]]
            if wire_db.stop_position3d_id != stop_id:
                continue

            obj = wire_db.get_object()
            if obj is not None:
                obj.delete()
            break

    @staticmethod
    def _delete_layout_at(ptables, point_id):
        """Delete the WireLayout (if any) sitting at point_id."""
        for row in ptables.pjt_wire_layouts_table.select('id', position3d_id=point_id):
            layout_db = ptables.pjt_wire_layouts_table[row[0]]

            obj = layout_db.get_object()
            if obj is not None:
                obj.delete()
            break

    @staticmethod
    def _detach_extra_wires_at(ptables, point_id):
        """Give every wire but the first one attached at point_id its own
        new point at the same coordinates.

        Only the first wire found keeps the shared point -- it becomes
        uniquely its own once the terminal and its routing stub(s) are
        gone. Every additional wire sharing the point would otherwise
        stay joined to it (and to each other) through a point that no
        longer represents a real connection.
        """
        x, y, z = ptables.pjt_points3d_table[point_id].point.as_float
        seen_first = False

        for column in ('start_point3d_id', 'stop_point3d_id'):
            for row in ptables.pjt_wires_table.select('id', **{column: point_id}):
                wire_db = ptables.pjt_wires_table[row[0]]

                if not seen_first:
                    seen_first = True
                    continue

                new_point = ptables.pjt_points3d_table.insert(x, y, z)
                attr = column.replace('_point3d_id', '_position3d_id')
                setattr(wire_db, attr, new_point.db_id)


class TerminalMenu(QMenu):
    """Represent a terminal menu in :mod:`harness_designer.objects.objects3d.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

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

    def on_add_wire(self):
        """Start the interactive wire placement flow from this terminal."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe

        def _factory():
            part_id = _menu_ops.get_part_id(
                mainframe, 'wires', mainframe.global_db.wires_table,
                'Add Wire')

            if part_id is None:
                return None

            return _handlers.AddWireHandler(mainframe, part_id)

        _menu_ops.start_handler(mainframe, _factory)

    def on_add_seal(self):
        """Attach a seal to this terminal."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        terminal = self.selected.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddSealHandler(mainframe, terminal))

    def on_trace_circuit(self):
        """Highlight every object on this terminal's circuit."""
        _menu_ops.trace_circuit(self.selected)

    def on_select(self):
        """Make this terminal the active selection."""
        _menu_ops.select_object(self.selected)

    def on_clone(self):
        """Arm clone mode using this terminal as the template."""
        _menu_ops.clone_object(self.selected)

    def on_delete(self):
        """Delete this terminal from the project."""
        _menu_ops.delete_object(self.selected)

    def on_properties(self):
        """Show this terminal's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
