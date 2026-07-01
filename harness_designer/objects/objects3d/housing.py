# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer
import numpy as np
from OpenGL import GL

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...ui.dialogs import housing_editor as _housing_editor
from ...ui.widgets import float_ctrl as _float_ctrl
from ...ui.dialogs import error as _error_dialog
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import box as _box
from ...utils import mesh_surface_picker as _mesh_surface_picker
from ...gl import materials as _materials
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import cavity as _cavity
    from . import cavity as _cavity3d
    from ...database.global_db import cavity as _global_cavity_mod
    from .. import housing as _housing
    from ... import ui as _ui


Config = _config.Config.editor3d


class Housing(_base3d.Base3D):
    """Represent a housing in :mod:`harness_designer.objects.objects3d.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_housing.Housing" = None
    db_obj: "_pjt_housing.PJTHousing" = None

    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):
        """Initialise the :class:`Housing` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_housing.Housing`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_housing.PJTHousing`
        """
        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part

        model = self._part.model3d

        vbo = _box.create_vbo()

        width = self._part.width
        height = self._part.height
        length = self._part.length

        if 0.0 in (length, width, height):
            length_ctrl = _float_ctrl.FloatCtrl(
                None, 'Length', 0.00, 500.0, 0.01)

            width_ctrl = _float_ctrl.FloatCtrl(
                None, 'Width', 0.00, 500.0, 0.01)

            height_ctrl = _float_ctrl.FloatCtrl(
                None, 'Height', 0.00, 500.0, 0.01)

            length_ctrl.SetValue(length)
            width_ctrl.SetValue(width)
            height_ctrl.SetValue(height)

            dlg = _error_dialog.ErrorDialog(
                parent.mainframe,
                'Dimensions are not valid.\n\nPlease set correct dimensions.',
                'Dimension Error', length_ctrl, width_ctrl, height_ctrl)

            while 0.0 in (length, width, height):
                dlg.exec()
                length = length_ctrl.GetValue()
                width = width_ctrl.GetValue()
                height = height_ctrl.GetValue()

            db_obj.length = length
            db_obj.width = width
            db_obj.height = height

        scale = _point.Point(width, height, length)
        material = _materials.Plastic(self._part.color.ui)
        angle = db_obj.angle3d

        _base3d.Base3D.__init__(
            self, parent, db_obj, vbo, angle, db_obj.position3d,
            scale, material)

        parent.mainframe.editor3d.context.release()

        canvas3d = parent.mainframe.editor3d.editor
        self._picker = _mesh_surface_picker.MeshSurfacePicker(self, canvas3d)
        self._selected_global_cavity = None
        self._surf_to_cavity: dict = {}

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

    @property
    def cavities(self) -> list:
        return [c.obj3d for c in self.parent.cavities
                if c is not None and c.obj3d is not None]

    def _set_model(self, model):
        for cavity in self._part.cavities:
            if cavity is not None:
                break
        else:
            from ...ui.dialogs import housing_editor

            dlg = housing_editor.HousingEditorDialog(self.parent.mainframe)
            dlg.SetValue(self._part)
            dlg.exec()
            dlg.deleteLater()

        super()._set_model(model)
        self.match_cavity_surfaces()

    @property
    def seal_position(self) -> _point.Point:
        """Return the seal position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.db_obj.seal_position3d

    def match_cavity_surfaces(self) -> None:
        self._picker.update_vbo()

        surfaces = self._picker.surfaces
        cavities = self.cavities

        if not surfaces or not cavities:
            return

        verts = self._picker.vertices
        n_surf = len(surfaces)
        n_cav = len(cavities)
        centroids = np.empty((n_surf, 3), dtype=np.float64)
        surf_normals = np.empty((n_surf, 3), dtype=np.float64)
        for i, surf in enumerate(surfaces):
            idxs = [3 * ti + j for ti in surf.tri_indices for j in range(3)]
            centroids[i] = verts[idxs].mean(axis=0)
            surf_normals[i] = np.asarray(surf.normal, dtype=np.float64)

        # Build separate distance matrices for terminal (corners 4-7) and
        # wire (corners 0-3) faces.  Both use the cavity-axis parallel filter
        # since |dot| > 0.85 accepts normals pointing either way along the axis.
        term_dist = np.full((n_cav, n_surf), np.inf)
        wire_dist = np.full((n_cav, n_surf), np.inf)
        for ci, cavity_3d in enumerate(cavities):
            part = cavity_3d.db_obj.part
            obb = part.obb if part is not None else None
            if obb is not None:
                obb_f = obb.astype(np.float64)
                term_center = obb_f[4:].mean(axis=0)
                wire_center = obb_f[:4].mean(axis=0)
                cav_axis = term_center - wire_center
                cav_axis /= np.linalg.norm(cav_axis) + 1e-12
                dots = np.abs(surf_normals @ cav_axis)
                parallel = dots > 0.85
                t_dists = np.linalg.norm(centroids - term_center, axis=1)
                w_dists = np.linalg.norm(centroids - wire_center, axis=1)
                if parallel.any():
                    t_dists = np.where(parallel, t_dists, np.inf)
                    w_dists = np.where(parallel, w_dists, np.inf)
                term_dist[ci] = t_dists
                wire_dist[ci] = w_dists
            else:
                entry = part.position3d.as_numpy.astype(np.float64)
                term_dist[ci] = np.linalg.norm(centroids - entry, axis=1)

        self._surf_to_cavity = {}
        assigned_surfs: set = set()

        # First pass: terminal faces — sets the primary surf_idx on each cavity.
        assigned_cavs: set = set()
        flat = term_dist.ravel()
        for k in np.argsort(flat):
            if flat[k] == np.inf:
                break
            ci = int(k) // n_surf
            si = int(k) % n_surf
            if ci not in assigned_cavs and si not in assigned_surfs:
                cavities[ci].surf_idx = si
                self._surf_to_cavity[si] = cavities[ci]
                assigned_cavs.add(ci)
                assigned_surfs.add(si)

        # Second pass: wire faces — each cavity gets at most one additional
        # surface so clicking from the back also resolves to the same cavity.
        assigned_cavs_wire: set = set()
        flat_wire = wire_dist.ravel()
        for k in np.argsort(flat_wire):
            if flat_wire[k] == np.inf:
                break
            ci = int(k) // n_surf
            si = int(k) % n_surf
            if ci not in assigned_cavs_wire and si not in assigned_surfs:
                self._surf_to_cavity[si] = cavities[ci]
                assigned_cavs_wire.add(ci)
                assigned_surfs.add(si)

    def on_surface_selected(self, idx: int):
        cavity_3d = self._surf_to_cavity.get(idx)
        if cavity_3d is not None:
            self._picker.select(idx)
            self._selected_global_cavity = cavity_3d.db_obj.part
        return cavity_3d

    def _on_right_click(self, global_pos) -> None:
        if self._selected_global_cavity is None:
            return

        menu = HousingCavityMenu(self, self._selected_global_cavity)
        menu.exec(global_pos)
        menu.deleteLater()

    def try_pick_cavity(self, x: int, y: int):
        """Ray-cast at pixel (x, y); highlight the cavity surface if hit."""
        idx, _ = self._picker.pick_surface_at(x, y)
        if idx < 0:
            return None
        return self.on_surface_selected(idx)

    def clear_cavity_overlay(self) -> None:
        """Hide any active cavity-plane highlight for this housing."""
        self._selected_global_cavity = None
        self._picker.clear_selection()

    def render(self, faces_program, edges_program, vertices_program):
        super().render(faces_program, edges_program, vertices_program)

        picker = self._picker
        if picker is None or picker.selected_surf_idx is None:
            return

        surf  = picker.surfaces[picker.selected_surf_idx]
        verts = picker.vertices     # (N, 3) float64, housing local space
        rot   = picker.rot_mat
        scale = picker.scale_arr
        pos   = picker.pos_arr

        # Gather vertex indices for the selected surface and transform to
        # world space in one vectorised step.
        tri_arr = np.asarray(surf.tri_indices, dtype=np.int64)
        idx = (tri_arr[:, None] * 3 + np.arange(3, dtype=np.int64)).ravel()
        positions = ((verts[idx] * scale) @ rot + pos).astype(np.float32)

        r, g, b, a = picker.overlay_color

        GL.glUseProgram(0)
        GL.glDepthMask(GL.GL_FALSE)
        GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
        GL.glPolygonOffset(-1.0, -1.0)

        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glColor4f(r / 255.0, g / 255.0, b / 255.0, a / 255.0)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, positions)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(positions))
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

        GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
        GL.glPolygonOffset(0.0, 0.0)
        GL.glDepthMask(GL.GL_TRUE)

    def delete(self):
        """Clean up the picker before delegating to Base3D."""
        self._picker.cleanup()
        self._picker = None
        super().delete()

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return HousingMenu(self.mainframe, self)


class HousingCavityMenu(QMenu):
    """Context menu shown on right-click over a highlighted cavity plane."""

    def __init__(self, housing_3d: "Housing",
                 global_cavity: "_global_cavity_mod.Cavity"):
        super().__init__()
        self._housing_3d = housing_3d
        self._global_cavity = global_cavity
        self._pjt_cavity = self._find_pjt_cavity()

        has_terminal = (self._pjt_cavity is not None and
                        self._pjt_cavity.terminal is not None)
        has_seal = (self._pjt_cavity is not None and
                    self._pjt_cavity.seal is not None)
        terminal_sealable = (has_terminal and
                             self._pjt_cavity.terminal.part.sealing)

        if has_terminal:
            act = self.addAction('Edit Terminal')
            act.triggered.connect(self.on_edit_terminal)
        else:
            act = self.addAction('Add Terminal')
            act.triggered.connect(self.on_add_terminal)

        if has_seal:
            act = self.addAction('Edit Seal')
            act.triggered.connect(self.on_edit_seal)
        elif has_terminal and terminal_sealable:
            act = self.addAction('Add Wire Seal')
            act.triggered.connect(self.on_add_wire_seal)
        elif not has_terminal:
            act = self.addAction('Add Plug Seal')
            act.triggered.connect(self.on_add_plug_seal)

    def _find_pjt_cavity(self):
        g_id = self._global_cavity.db_id
        for pc in self._housing_3d.db_obj.cavities:
            if pc.part_id == g_id:
                return pc
        return None

    def _get_or_create_pjt_cavity(self):
        if self._pjt_cavity is not None:
            return self._pjt_cavity

        housing = self._housing_3d
        g_cavity = self._global_cavity
        ptables = housing.mainframe.project.ptables

        pjt_cavity = ptables.pjt_cavities_table.insert(
            g_cavity.db_id, housing.db_obj.db_id, g_cavity.name)

        self._pjt_cavity = pjt_cavity
        return pjt_cavity

    def _cavity_midpoint(self, pjt_cavity) -> tuple[float, float, float]:
        cpos_np = pjt_cavity.position3d.as_numpy.astype(np.float64)
        cav_ang = pjt_cavity.angle3d
        length = float(self._global_cavity.length)

        ref_local = np.array([[0.0, 0.0, length]], dtype=np.float64)
        ref_world = np.asarray(ref_local @ cav_ang, dtype=np.float64)[0] + cpos_np
        mid = (cpos_np + ref_world) / 2.0
        return float(mid[0]), float(mid[1]), float(mid[2])

    def on_add_terminal(self):
        from .. import cavity as _cavity_mod
        from ... import handlers as _handlers

        pjt_cavity = self._get_or_create_pjt_cavity()
        mainframe = self._housing_3d.mainframe
        housing_wrapper = self._housing_3d.parent

        cavity_obj = pjt_cavity.get_object()
        if cavity_obj is None:
            cavity_obj = _cavity_mod.Cavity(mainframe, pjt_cavity)
            mainframe.project.add_cavity(cavity_obj)

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddTerminalHandler(
                mainframe, housing=housing_wrapper, cavity=cavity_obj))

    def on_add_wire_seal(self):
        from ... import handlers as _handlers

        if self._pjt_cavity is None:
            return
        terminal_db = self._pjt_cavity.terminal
        if terminal_db is None:
            return
        terminal_obj = terminal_db.get_object()
        if terminal_obj is None:
            return

        mainframe = self._housing_3d.mainframe
        _menu_ops.run_attached_handler(
            lambda: _handlers.AddSealHandler(mainframe, terminal=terminal_obj))

    def on_add_plug_seal(self):
        from .. import cavity as _cavity_mod
        from ... import handlers as _handlers

        pjt_cavity = self._get_or_create_pjt_cavity()
        mainframe = self._housing_3d.mainframe

        cavity_obj = pjt_cavity.get_object()
        if cavity_obj is None:
            cavity_obj = _cavity_mod.Cavity(mainframe, pjt_cavity)
            mainframe.project.add_cavity(cavity_obj)

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddSealHandler(mainframe, cavity=cavity_obj))

    def on_edit_terminal(self):
        def _do():
            from . import menu_ops as _menu_ops

            if self._pjt_cavity is None:
                return
            terminal_db = self._pjt_cavity.terminal
            if terminal_db is None:
                return
            parent = terminal_db.get_object()
            if parent is None or parent.obj3d is None:
                return
            _menu_ops.show_properties(parent.obj3d)

        QTimer.singleShot(0, _do)

    def on_edit_seal(self):
        def _do():
            from . import menu_ops as _menu_ops

            if self._pjt_cavity is None:
                return
            seal_db = self._pjt_cavity.seal
            if seal_db is None:
                return
            parent = seal_db.get_object()
            if parent is None or parent.obj3d is None:
                return
            _menu_ops.show_properties(parent.obj3d)

        QTimer.singleShot(0, _do)


class HousingMenu(QMenu):
    """Represent a housing menu in :mod:`harness_designer.objects.objects3d.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_ui.MainFrame", obj: Housing):
        """Initialise the :class:`HousingMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param obj: Object instance to operate on.
        :type obj: :class:`Housing`
        """
        QMenu.__init__(self)
        self.mainframe = mainframe
        self.canvas = mainframe.editor3d.editor
        self.obj = obj

        if self.obj.db_obj.part.sealing:
            action = self.addAction('Add Mat Seal')
            action.triggered.connect(self.on_add_mat_seal)

        action = self.addAction('Add Cavity Seal')
        action.triggered.connect(self.on_add_cavity_seal)

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

        rotate_menu = _context_menus.Rotate3DMenu(self.canvas, obj.parent)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(self.canvas, obj.parent)
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

        action = self.addAction('Housing Editor')
        action.triggered.connect(self.on_housing_editor)

    def on_housing_editor(self):
        """Handle the housing editor event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        def _do(housing):
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param housing: Value for ``housing``.
            :type housing: UNKNOWN
            """
            dlg = _housing_editor.HousingEditorDialog(self.mainframe)

            QTimer.singleShot(0, lambda: dlg.SetValue(housing))

            dlg.exec()

        QTimer.singleShot(0, lambda: _do(self.obj.db_obj.part))

    def on_add_mat_seal(self):
        """Attach a MAT seal to this housing."""
        from ... import handlers as _handlers

        housing = self.obj.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddSealHandler(self.mainframe, housing=housing))

    def on_add_cavity_seal(self):
        """Add a plug seal interactively to one of this housing's cavities."""
        from ... import handlers as _handlers

        housing = self.obj.parent

        _menu_ops.start_handler(
            self.mainframe,
            lambda: _handlers.AddSealHandler(
                self.mainframe, housing=housing, for_cavity=True))

    def on_add_terminal(self):
        """Add terminals to this housing's cavities with a snapping preview."""
        from ... import handlers as _handlers

        housing = self.obj.parent

        _menu_ops.start_handler(
            self.mainframe,
            lambda: _handlers.AddTerminalHandler(
                self.mainframe, housing=housing))

    def on_add_cpa_lock(self):
        """Attach a CPA lock to this housing."""
        from ... import handlers as _handlers

        housing = self.obj.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddCPALockHandler(self.mainframe, housing))

    def on_add_tpa_lock(self):
        """Attach a TPA lock to this housing."""
        from ... import handlers as _handlers

        housing = self.obj.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddTPALockHandler(self.mainframe, housing))

    def on_add_cover(self):
        """Attach a cover to this housing."""
        from ... import handlers as _handlers

        housing = self.obj.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddCoverHandler(self.mainframe, housing))

    def on_add_boot(self):
        """Attach a boot to this housing."""
        def _do():
            from .. import boot as _boot_obj

            housing = self.obj.db_obj

            try:
                compat_boots = housing.part.compat_boots_array
            except AttributeError:
                compat_boots = []

            part_id = _menu_ops.get_part_id(
                self.mainframe, 'boots',
                self.mainframe.global_db.boots_table, 'Add Boot',
                initial_results=compat_boots)

            if part_id is None:
                return

            db_obj = self.mainframe.project.ptables.pjt_boots_table.insert(
                part_id, housing.boot_position3d_id, housing.db_id)

            from ...handlers import handler_base as _handler_base
            _handler_base.set_angle_from_housing(db_obj, housing)

            boot = _boot_obj.Boot(self.mainframe, db_obj)
            self.mainframe.project.add_boot(boot)

        QTimer.singleShot(0, _do)

    def on_select(self):
        """Make this housing the active selection."""
        _menu_ops.select_object(self.obj)

    def on_clone(self):
        """Arm clone mode using this housing as the template."""
        _menu_ops.clone_object(self.obj)

    def on_delete(self):
        """Delete this housing from the project."""
        _menu_ops.delete_object(
            self.obj, self.mainframe.project.delete_housing)

    def on_properties(self):
        """Show this housing's properties in the object editor."""
        _menu_ops.show_properties(self.obj)
