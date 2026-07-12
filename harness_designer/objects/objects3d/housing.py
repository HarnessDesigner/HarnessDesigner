# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING
from dataclasses import dataclass

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


@dataclass
class _CavityMarker:
    """A synthetic circle/rectangle decal standing in for a cavity that has
    no distinguishable recessed mesh surface of its own (single-plane
    housings).  Position/orientation/size come from the cavity's stored OBB;
    all vectors are in the housing's local mesh space (same frame
    ``MeshSurfacePicker.vertices`` uses).
    """
    cavity_3d: object
    kind: str                # 'circle' | 'rect'
    normal: np.ndarray
    u: np.ndarray
    v: np.ndarray
    center: np.ndarray
    half_w: float
    half_h: float
    local_verts: np.ndarray  # (3N, 3) float32 triangle soup, local space


def _build_marker_local_verts(
    kind: str, center: np.ndarray, u: np.ndarray, v: np.ndarray,
    half_w: float, half_h: float, segments: int = 24,
) -> np.ndarray:
    """Triangle soup for a marker decal, in the same local space as the OBB
    it was derived from.  Winding doesn't matter — these are drawn unlit.
    """
    if kind == 'circle':
        r = half_w  # half_w == half_h for round cavities
        angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
        ring = [center + r * (np.cos(a) * u + np.sin(a) * v) for a in angles]
        verts = []
        for i in range(segments):
            j = (i + 1) % segments
            verts.extend([center, ring[i], ring[j]])
        return np.array(verts, dtype=np.float32)

    c0 = center - half_w * u - half_h * v
    c1 = center + half_w * u - half_h * v
    c2 = center + half_w * u + half_h * v
    c3 = center - half_w * u + half_h * v
    return np.array([c0, c1, c2, c0, c2, c3], dtype=np.float32)


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
        self._selected_is_wire_side = False
        self._surf_to_cavity: dict = {}
        self._cavity_markers: list = []
        self._selected_marker_idx: int = -1

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

        self._cavity_markers = []
        self._surf_to_cavity = {}

        # Cavities with no distinguishable recessed mesh surface of their own
        # (single-plane housings) get a synthetic marker instead, built
        # directly from their OBB — they must not compete for a real surface
        # slot in the nearest-neighbor matching below.
        marker_cavities = [c for c in cavities if c.db_obj.part.render_terminal_marker]
        normal_cavities = [c for c in cavities if not c.db_obj.part.render_terminal_marker]

        for cavity_3d in marker_cavities:
            obb = cavity_3d.db_obj.part.obb
            if obb is None:
                continue

            obb_f = obb.astype(np.float64)
            c4, c5, c6, c7 = obb_f[4], obb_f[5], obb_f[6], obb_f[7]
            u_vec = c6 - c4
            v_vec = c5 - c4
            half_w = float(np.linalg.norm(u_vec)) / 2.0
            half_h = float(np.linalg.norm(v_vec)) / 2.0
            if half_w < 1e-9 or half_h < 1e-9:
                continue

            u_dir = u_vec / (half_w * 2.0)
            v_dir = v_vec / (half_h * 2.0)
            normal = np.cross(u_dir, v_dir)
            n_norm = np.linalg.norm(normal)
            if n_norm < 1e-9:
                continue
            normal /= n_norm
            center = (c4 + c5 + c6 + c7) / 4.0

            kind = 'circle' if cavity_3d.db_obj.part.round_terminal else 'rect'
            local_verts = _build_marker_local_verts(
                kind, center, u_dir, v_dir, half_w, half_h)

            self._cavity_markers.append(_CavityMarker(
                cavity_3d=cavity_3d, kind=kind, normal=normal, u=u_dir,
                v=v_dir, center=center, half_w=half_w, half_h=half_h,
                local_verts=local_verts))

        if not surfaces or not normal_cavities:
            return

        n_surf = len(surfaces)

        # Cavities whose terminal/wire surfaces were already hand-picked in
        # the housing editor (persisted on the catalog Cavity row) skip the
        # nearest-neighbor OBB heuristic entirely — just replay the stored
        # mapping. That heuristic (centroid + distance-matrix computation
        # over every surface in the mesh) is the expensive part of a project
        # load with many cavities; once a part has been through the editor
        # this whole block below never runs for it again. Bounds-checked
        # against the current surface count so a stale mapping from before a
        # model re-simplification falls back to the heuristic instead of
        # pointing at the wrong surface.
        heuristic_cavities = []
        for cavity_3d in normal_cavities:
            part = cavity_3d.db_obj.part
            if part is None:
                heuristic_cavities.append(cavity_3d)
                continue

            term_idxs = [i for i in part.terminal_surf_indices if 0 <= i < n_surf]
            wire_idxs = [i for i in part.wire_surf_indices if 0 <= i < n_surf]

            if not term_idxs and not wire_idxs:
                heuristic_cavities.append(cavity_3d)
                continue

            if term_idxs:
                cavity_3d.surf_idx = term_idxs[0]
                for si in term_idxs:
                    self._surf_to_cavity[si] = cavity_3d

            if wire_idxs:
                cavity_3d.wire_surf_idx = wire_idxs[0]
                for si in wire_idxs:
                    self._surf_to_cavity[si] = cavity_3d

        if not heuristic_cavities:
            return

        normal_cavities = heuristic_cavities

        verts = self._picker.vertices
        n_cav = len(normal_cavities)
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
        for ci, cavity_3d in enumerate(normal_cavities):
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

        # Don't let the heuristic reassign surfaces already claimed by the
        # stored-index fast path above.
        assigned_surfs: set = set(self._surf_to_cavity.keys())

        # First pass: terminal faces — sets the primary surf_idx on each cavity.
        assigned_cavs: set = set()
        flat = term_dist.ravel()
        for k in np.argsort(flat):
            if flat[k] == np.inf:
                break
            ci = int(k) // n_surf
            si = int(k) % n_surf
            if ci not in assigned_cavs and si not in assigned_surfs:
                normal_cavities[ci].surf_idx = si
                self._surf_to_cavity[si] = normal_cavities[ci]
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
                normal_cavities[ci].wire_surf_idx = si
                self._surf_to_cavity[si] = normal_cavities[ci]
                assigned_cavs_wire.add(ci)
                assigned_surfs.add(si)

    def _pick_marker(self, x: int, y: int) -> int:
        """Ray-cast against synthetic cavity-marker decals.

        Returns an index into ``self._cavity_markers``, or -1 on miss.
        Checked before the real mesh surfaces in ``try_pick_cavity`` so
        markers act as the click target for cavities with no distinguishable
        recessed geometry of their own.
        """
        if not self._cavity_markers:
            return -1

        origin_w, direction_w = self._picker.compute_ray_world(x, y)
        if origin_w is None:
            return -1

        origin_l, direction_l = self._picker.transform_ray_to_local(
            origin_w, direction_w)
        if origin_l is None:
            return -1

        best_idx = -1
        best_t = float('inf')
        for i, marker in enumerate(self._cavity_markers):
            denom = float(direction_l @ marker.normal)
            if abs(denom) < 1e-9:
                continue

            t = float((marker.center - origin_l) @ marker.normal) / denom
            if t < 0.0 or t >= best_t:
                continue

            hit = origin_l + t * direction_l
            delta = hit - marker.center
            du = float(delta @ marker.u)
            dv = float(delta @ marker.v)

            if marker.kind == 'circle':
                if du * du + dv * dv > marker.half_w * marker.half_w:
                    continue
            elif abs(du) > marker.half_w or abs(dv) > marker.half_h:
                continue

            best_t = t
            best_idx = i

        return best_idx

    def _select_marker(self, marker_idx: int):
        marker = self._cavity_markers[marker_idx]
        self._picker.clear_selection()
        self._selected_marker_idx = marker_idx
        self._selected_global_cavity = marker.cavity_3d.db_obj.part
        self._selected_is_wire_side = False
        return marker.cavity_3d

    def on_surface_selected(self, idx: int):
        cavity_3d = self._surf_to_cavity.get(idx)
        if cavity_3d is not None:
            self._picker.select(idx)
            self._selected_marker_idx = -1
            self._selected_global_cavity = cavity_3d.db_obj.part
            self._selected_is_wire_side = (idx != cavity_3d.surf_idx)
        return cavity_3d

    def _on_right_click(self, global_pos) -> None:
        if self._selected_global_cavity is None:
            return

        menu = HousingCavityMenu(
            self, self._selected_global_cavity, self._selected_is_wire_side)
        menu.exec(global_pos)
        menu.deleteLater()

    def try_pick_cavity(self, x: int, y: int):
        """Ray-cast at pixel (x, y); highlight the cavity (or its synthetic
        marker) if hit.  Markers are checked first — they are the only click
        target for cavities that have no distinguishable recessed mesh
        surface of their own.
        """
        marker_idx = self._pick_marker(x, y)
        if marker_idx >= 0:
            return self._select_marker(marker_idx)

        # Only ray-test surfaces already married to a cavity by
        # match_cavity_surfaces() at load time — the rest of the housing
        # shell can never be a cavity hit and shouldn't be tested per click.
        idx, _ = self._picker.pick_surface_at(
            x, y, candidate_indices=self._surf_to_cavity.keys())
        if idx < 0:
            return None
        return self.on_surface_selected(idx)

    def clear_cavity_overlay(self) -> None:
        """Hide any active cavity-plane highlight for this housing."""
        self._selected_global_cavity = None
        self._selected_is_wire_side = False
        self._selected_marker_idx = -1
        self._picker.clear_selection()

    @staticmethod
    def _draw_overlay_triangles(positions_world: np.ndarray, color) -> None:
        """Immediate-mode filled-triangle draw used for both the picker's
        hover/click surface highlight and the persistent cavity-marker
        decals.  *color* is an RGBA sequence with components in the
        0.0-1.0 range (matches ``GLMaterial.diffuse``).
        """
        r, g, b, a = color

        GL.glUseProgram(0)
        GL.glDepthMask(GL.GL_FALSE)
        GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
        GL.glPolygonOffset(-1.0, -1.0)

        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glColor4f(r, g, b, a)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, positions_world)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(positions_world))
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

        GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
        GL.glPolygonOffset(0.0, 0.0)
        GL.glDepthMask(GL.GL_TRUE)

    def render_surface_overlay(self, surf_idx: int, color) -> None:
        """Draw an overlay on one of this housing's mesh surfaces.

        *color* is an RGBA sequence with components in the 0.0-1.0 range
        (matches ``GLMaterial.diffuse``).  Used by objects that want to
        persistently mark one of the housing's surfaces (e.g. a terminal
        marking its cavity's wire-side/pin-side faces), independent of the
        picker's single-selection hover/click highlight.
        """
        picker = self._picker
        if picker is None or surf_idx is None or surf_idx < 0:
            return

        if surf_idx >= len(picker.surfaces):
            return

        surf = picker.surfaces[surf_idx]
        verts = picker.vertices     # (N, 3) float64, housing local space
        rot = picker.rot_mat
        scale = picker.scale_arr
        pos = picker.pos_arr

        # Gather vertex indices for the surface and transform to world
        # space in one vectorised step.
        tri_arr = np.asarray(surf.tri_indices, dtype=np.int64)
        idx = (tri_arr[:, None] * 3 + np.arange(3, dtype=np.int64)).ravel()
        positions = ((verts[idx] * scale) @ rot + pos).astype(np.float32)

        self._draw_overlay_triangles(positions, color)

    def _render_cavity_markers(self) -> None:
        """Draw every synthetic cavity-marker decal — persistent, not just
        on selection, since these are the only visual cue for cavities that
        have no real recessed mesh geometry of their own.
        """
        if not self._cavity_markers:
            return

        picker = self._picker
        rot = picker.rot_mat
        scale = picker.scale_arr
        pos = picker.pos_arr

        default_color = (0.85, 0.85, 0.85, 0.35)
        selected_color = (0.4, 0.9, 1.0, 0.55)

        for i, marker in enumerate(self._cavity_markers):
            positions = ((marker.local_verts.astype(np.float64) * scale) @
                         rot + pos).astype(np.float32)

            color = selected_color if i == self._selected_marker_idx else default_color
            self._draw_overlay_triangles(positions, color)

    def render(self, faces_program, edges_program, vertices_program):
        super().render(faces_program, edges_program, vertices_program)

        self._render_cavity_markers()

        picker = self._picker
        if picker is None or picker.selected_surf_idx is None:
            return

        r, g, b, a = picker.overlay_color
        self.render_surface_overlay(
            picker.selected_surf_idx, (r / 255.0, g / 255.0, b / 255.0, a / 255.0))

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
                 global_cavity: "_global_cavity_mod.Cavity",
                 is_wire_side: bool = False):
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
            act.setEnabled(not has_seal)
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

        if is_wire_side:
            act = self.addAction('Add Wire')
            act.setEnabled(has_terminal)
            act.triggered.connect(self.on_add_wire)

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

    def on_add_wire(self):
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
        _menu_ops.start_handler(
            mainframe,
            lambda: _handlers.AddWireHandler(mainframe, terminal=terminal_obj))

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
