# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu, QMessageBox
from PySide6.QtCore import QTimer
from OpenGL import GL
import numpy as np

from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...ui.widgets import context_menus as _context_menus
from ...shapes import cylinder as _cylinder
from ...shapes import box as _box
from ...gl import materials as _materials
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import color as _color
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from .. import cavity as _cavity


class Cavity(_base_3d.Base3D):
    """Represent a cavity in :mod:`harness_designer.objects.objects_3d.cavity`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_cavity.Cavity" = None
    db_obj: "_pjt_cavity.PJTCavity" = None

    @_check_types.do
    def set_selected(self, state: bool) -> None:
        super().set_selected(state)

    @_check_types.do
    def identify(self, material: _materials.GLMaterial | None) -> None:
        """Highlight (or un-highlight) this cavity for an interactive
        add/snap session.

        A cavity's own outline box/cylinder is invisible by default
        (``is_visible3d`` defaults to 0 -- see
        ``database.create_database.cavities.pjt_table`` -- the housing's
        own mesh is what's normally shown; this shape only exists to
        make the cavity itself pick/snap-able while a session needs it
        highlighted). ``BaseVar.identify`` only ever swaps the display
        material, never touches visibility, so a cavity ``identify()``-d
        by e.g. ``objects.objects_3d.terminal.Terminal.start_add``
        stayed invisible the whole time -- invisible objects never reach
        ``camera.objects_in_view`` (see ``gl.canvas_base.canvas_base.
        Canvas._draw_scene``), so ``is_in_3dview`` was always False for
        every cavity and the interactive snap-to-cavity pool
        (``add_handlers.editor_3d.terminal.Terminal.snap_pool``) was
        always empty. Show the cavity while it carries an override
        material, hide it again once the override clears.
        """
        super().identify(material)
        self.is_visible = material is not None

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu."""
        return CavityMenu(self)

    @_check_types.do
    def __init__(self, parent: "_cavity.Cavity",
                 db_obj: "_pjt_cavity.PJTCavity"):
        """Initialise the :class:`Cavity` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_cavity.Cavity`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cavity.PJTCavity`
        """

        with parent.mainframe.editor3d.context:
            self._part = db_obj.part
            scale = db_obj.part.scale
            # Use the global part angle for the Base3D binding (drives _update_angle
            # when the part definition changes). The project-specific world-space
            # angle is stored separately and used for rendering.
            angle = db_obj.angle3d
            position = db_obj.position3d
            material = _materials.Metallic(_color.Color(200, 200, 200, 75))

            if db_obj.part.round_terminal:
                vbo = _cylinder.create_vbo()
            else:
                vbo = _box.create_vbo()

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)
            self.surf_idx: int = -1
            self.wire_surf_idx: int = -1
            # Index into the owning Housing3D._cavity_markers, set instead of
            # wire_surf_idx when Cavity.render_wire_marker is True (the wire
            # side has no distinguishable real mesh surface of its own).
            self.wire_marker_idx: int = -1

            # Which side of this cavity the housing's last try_pick_cavity hit
            # landed on -- set by Housing3D._select_marker/on_surface_selected,
            # read by CavityMenu to decide whether "Add Wire" belongs on the
            # menu.
            self._selected_is_wire_side: bool = False

    @_check_types.do
    def wire_surface_center(self) -> _point.Point | None:
        """
        Return the world-space centroid of this cavity's wire-side mesh
        surface (or, for a cavity sharing its wire-side wall with others,
        its synthetic wire marker -- see Cavity.render_wire_marker), or
        None if neither is available yet (match_cavity_surfaces hasn't
        run, or found nothing to assign for this cavity). Callers should
        fall back to a geometric approximation in that case -- this is the
        real mesh location where the wire actually exits the housing, more
        accurate than any such approximation whenever it's available.

        Mean of all triangle-corner positions, same as the centroid
        computation match_cavity_surfaces() itself already uses for
        nearest-surface matching -- not a true area-weighted centroid, but
        consistent with the rest of this analysis pipeline.
        """
        housing_pjt = self.db_obj.housing
        housing_obj = housing_pjt.get_object() if housing_pjt is not None else None
        if housing_obj is None or housing_obj.obj3d is None:
            return None

        housing_3d = housing_obj.obj3d
        picker = housing_3d._picker  # NOQA
        if picker is None:
            return None

        if 0 <= self.wire_surf_idx < len(picker.surfaces):
            surf = picker.surfaces[self.wire_surf_idx]
            verts = picker.vertices
            rot = picker.rot_mat
            scale = picker.scale_arr
            pos = picker.pos_arr

            tri_arr = np.asarray(surf.tri_indices, dtype=np.int64)
            idx = (tri_arr[:, None] * 3 + np.arange(3, dtype=np.int64)).ravel()
            positions = (verts[idx] * scale) @ rot + pos
            center = positions.mean(axis=0)
            return _point.Point(float(center[0]), float(center[1]), float(center[2]))

        cavity_markers = housing_3d._cavity_markers  # NOQA
        if 0 <= self.wire_marker_idx < len(cavity_markers):
            marker = cavity_markers[self.wire_marker_idx]
            rot = picker.rot_mat
            scale = picker.scale_arr
            pos = picker.pos_arr

            positions = (marker.local_verts.astype(np.float64) * scale) @ rot + pos
            center = positions.mean(axis=0)
            return _point.Point(float(center[0]), float(center[1]), float(center[2]))

        return None

    @_check_types.do
    def _update_position(self, position: _point.Point):
        accessory = self.db_obj.terminal or self.db_obj.seal
        if accessory is not None:
            delta = position - self._o_position
            pos = accessory.position3d
            pos += delta

        super()._update_position(position)

    @property
    @_check_types.do
    def seal_position(self) -> _point.Point:
        """Return the seal position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.db_obj.position3d


class CavityMenu(QMenu):
    """Context menu shown on right-click over a cavity -- either the
    cavity object itself, or (with the "Add Wire" option) a highlighted
    wire-side plane.
    """
    @_check_types.do
    def __init__(self, cavity_3d: Cavity):
        """Initialise the :class:`CavityMenu` instance.

        :param cavity_3d: The cavity this menu was opened on. Its own
            db_obj is used directly -- unlike a housing-mesh-surface hit,
            a Cavity3D instance always already has a real project-level
            pjt_cavity row (that's what it was constructed from).
        :type cavity_3d: :class:`Cavity`
        """
        QMenu.__init__(self)
        self._cavity_3d = cavity_3d

        pjt_cavity = cavity_3d.db_obj
        has_terminal = pjt_cavity.terminal is not None

        # A cavity holds a terminal XOR a cavity-level (plug) seal, never
        # both -- pjt_cavity.seal only ever finds a seal linked via
        # cavity_id. Once a terminal is seated, any seal on it (a wire
        # seal) is linked via terminal_id instead, invisible to
        # pjt_cavity.seal -- must go through pjt_cavity.terminal.seal to
        # see it. See PJTHousing._update_angle3d for the same distinction.
        if has_terminal:
            has_seal = pjt_cavity.terminal.seal is not None
        else:
            has_seal = pjt_cavity.seal is not None

        if has_terminal:
            action = self.addAction('Edit Terminal')
            action.triggered.connect(self.on_edit_terminal)
        else:
            action = self.addAction('Add Terminal')
            action.setEnabled(not has_seal)
            action.triggered.connect(self.on_add_terminal)

        # Single "Add Seal" covers both a cavity plug seal (no terminal
        # present) and a wire seal on the terminal (terminal present) --
        # on_add_seal decides which; grayed out once one is already
        # attached rather than switching to a separate "Edit" action.
        action = self.addAction('Add Seal')
        action.setEnabled(not has_seal)
        action.triggered.connect(self.on_add_seal)

        if cavity_3d._selected_is_wire_side:  # NOQA
            action = self.addAction('Add Wire')
            action.setEnabled(has_terminal)
            action.triggered.connect(self.on_add_wire)

        self.addSeparator()
        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_add_terminal(self):
        """Add a terminal into this cavity."""
        from PySide6.QtCore import QTimer
        from . import terminal as _terminal_3d

        mainframe = self._cavity_3d.mainframe
        housing_wrapper = self._cavity_3d.db_obj.housing.get_object()
        cavity_obj = self._cavity_3d.parent

        # start_add's own Mode 1 (housing AND cavity given) finalizes
        # synchronously and never arms an interactive session -- still
        # deferred past the menu closing since it may open a modal
        # part-search dialog, same reasoning menu_ops.run_attached_handler
        # exists for.
        @_check_types.do
        def _do():
            _terminal_3d.Terminal.start_add(
                mainframe, housing=housing_wrapper, cavity=cavity_obj)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_seal(self):
        """Add a seal: a wire seal onto the terminal already in this
        cavity if one is seated, otherwise a plug seal into the cavity
        itself."""
        from . import seal as _seal_3d

        mainframe = self._cavity_3d.mainframe
        terminal_db = self._cavity_3d.db_obj.terminal

        if terminal_db is None:
            cavity_obj = self._cavity_3d.parent

            @_check_types.do
            def _do():
                _seal_3d.Seal.start_add(mainframe, cavity=cavity_obj)

            QTimer.singleShot(0, _do)
            return

        terminal_obj = terminal_db.get_object()
        if terminal_obj is None:
            return

        if not terminal_db.part.sealing:
            # Manufacturer-scraped catalog data isn't reliable enough to
            # block a wire seal outright just because this terminal's own
            # "sealing" field came back 0/unset -- confirm with the user
            # instead of silently trusting or silently ignoring it.
            res = QMessageBox.question(
                mainframe,
                'Add Wire Seal',
                f'"{terminal_db.part.part_number}" is not marked as a '
                f'sealable terminal in the parts catalog. Add a wire '
                f'seal to it anyway?')

            if res != QMessageBox.StandardButton.Yes:
                return

        @_check_types.do
        def _do():
            _seal_3d.Seal.start_add(mainframe, terminal=terminal_obj)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_wire(self):
        """Start placing a wire from the terminal already in this cavity."""
        from . import wire as _wire_3d

        terminal_db = self._cavity_3d.db_obj.terminal
        if terminal_db is None:
            return
        terminal_obj = terminal_db.get_object()
        if terminal_obj is None:
            return

        mainframe = self._cavity_3d.mainframe

        @_check_types.do
        def _do():
            _wire_3d.Wire.start_add(mainframe, terminal=terminal_obj)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_edit_terminal(self):
        """Open the properties dialog for the terminal already in this cavity."""
        @_check_types.do
        def _do():
            terminal_db = self._cavity_3d.db_obj.terminal
            if terminal_db is None:
                return
            parent = terminal_db.get_object()
            if parent is None or parent.obj3d is None:
                return
            _menu_ops.show_properties(parent.obj3d)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_select(self):
        """Make this cavity the active selection."""
        _menu_ops.select_object(self._cavity_3d)

    @_check_types.do
    def on_properties(self):
        """Show this cavity's properties in the object editor."""
        _menu_ops.show_properties(self._cavity_3d)
