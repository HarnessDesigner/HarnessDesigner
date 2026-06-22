# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Cavity plane picker overlay for the main 3D editor.

When a Housing is selected, this module installs a transparent overlay + mouse
event filter on the inner GL canvas so the user can left-click any face of the
housing mesh to highlight the cavity plane behind it, then right-click to show
a per-cavity context menu (Add/Edit Terminal, Add/Edit Seal).
"""

from typing import TYPE_CHECKING, ClassVar, List, Optional, Tuple

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from ...ui.dialogs.housing_editor import connector_analysis as _analysis
from ...geometry import angle as _angle
from ...geometry import point as _point

if TYPE_CHECKING:
    from . import housing as _housing3d
    from ...database.global_db import cavity as _global_cavity_mod


def _unproject(ndc_x, ndc_y, ndc_z, inv_mvp):
    clip = np.array([ndc_x, ndc_y, ndc_z, 1.0], dtype=np.float64)
    world = inv_mvp.dot(clip)
    if abs(float(world[3])) < 1e-12:
        return None
    world /= world[3]
    return world[:3]


def _point_in_triangle(p, a, b, c):
    v0 = c - a
    v1 = b - a
    v2 = p - a
    d00 = float(v0 @ v0)
    d01 = float(v0 @ v1)
    d02 = float(v0 @ v2)
    d11 = float(v1 @ v1)
    d12 = float(v1 @ v2)
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-12:
        return False
    inv = 1.0 / denom
    u = (d11 * d02 - d01 * d12) * inv
    v = (d00 * d12 - d01 * d02) * inv
    return u >= -1e-4 and v >= -1e-4 and (u + v) <= 1.0 + 1e-4


class CavityPlaneOverlay(QtWidgets.QWidget):
    """Transparent widget parented to the GL canvas that projects the selected
    cavity plane as a semi-transparent blue highlight."""

    def __init__(self, gl_widget, picker: "HousingCavityPicker"):
        super().__init__(gl_widget)
        self._picker = picker
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(gl_widget.rect())
        gl_widget.installEventFilter(self)
        gl_widget.frameSwapped.connect(self.update)
        self.show()
        self.raise_()

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.Resize:
            self.setGeometry(QtCore.QRect(0, 0, obj.width(), obj.height()))

        return False

    def paintEvent(self, event):
        picker = self._picker
        if not picker._surfaces or picker.vertices is None:
            return

        if picker.selected_surf_idx is None:
            return

        camera = picker._gl_widget.camera
        if camera.clip is None or camera.viewport is None:
            return

        clip_mat = camera.clip.astype(np.float64)
        vx, vy, vw, vh = camera.viewport
        dpr = picker._gl_widget.devicePixelRatio()

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(100, 180, 255, 110)))

        verts = picker.vertices.reshape(-1, 3).astype(np.float64)

        def project(pt):
            v = np.array([pt[0], pt[1], pt[2], 1.0], dtype=np.float64)
            c = clip_mat @ v
            w_val = float(c[3])
            if abs(w_val) < 1e-8:
                return None

            ndc = c / w_val
            sx = float((ndc[0] + 1.0) * 0.5 * vw + vx) / dpr
            sy = float((1.0 - ndc[1]) * 0.5 * vh + vy) / dpr
            return QtCore.QPointF(sx, sy)

        surf = picker._surfaces[picker.selected_surf_idx]
        for ti in surf.tri_indices:
            pts = [project(verts[3 * ti + k]) for k in range(3)]
            if all(p is not None for p in pts):
                painter.drawPolygon(QtGui.QPolygonF(pts))

        painter.end()

    def cleanup(self):
        self._picker._gl_widget.removeEventFilter(self)
        try:
            self._picker._gl_widget.frameSwapped.disconnect(self.update)
        except RuntimeError:
            pass

        self.hide()
        self.setParent(None)
        self.deleteLater()



class HousingCavityMenu(QtWidgets.QMenu):
    """Context menu shown on right-click over a highlighted cavity plane.

    Operates against the global ``Cavity`` from the housing part definition.
    A ``PJTCavity`` is only created lazily when the user actually adds a
    terminal or seal, because cavity project-DB rows do not exist until
    something is assigned to the slot.
    """

    def __init__(self, housing_3d: "_housing3d.Housing",
                 global_cavity: "_global_cavity_mod.Cavity"):
        super().__init__()
        self._housing_3d = housing_3d
        self._global_cavity = global_cavity
        self._pjt_cavity = self._find_pjt_cavity()

        has_terminal = (self._pjt_cavity is not None and
                        self._pjt_cavity.terminal is not None)
        has_seal = (self._pjt_cavity is not None and
                    self._pjt_cavity.seal is not None)

        if has_terminal:
            act = self.addAction('Edit Terminal')
            act.triggered.connect(self.on_edit_terminal)
        else:
            act = self.addAction('Add Terminal')
            act.triggered.connect(self.on_add_terminal)

        if has_seal:
            act = self.addAction('Edit Seal')
            act.triggered.connect(self.on_edit_seal)
        else:
            act = self.addAction('Add Seal')
            act.triggered.connect(self.on_add_seal)

    # ── helpers ────────────────────────────────────────────────────────────────

    def _find_pjt_cavity(self):
        """Return the existing PJTCavity for this global cavity, or None."""
        g_id = self._global_cavity.db_id
        for pc in self._housing_3d.db_obj.cavities:
            if pc.part_id == g_id:
                return pc
        return None

    def _get_or_create_pjt_cavity(self):
        """Return the PJTCavity, creating it lazily at world-space coords if needed."""
        if self._pjt_cavity is not None:
            return self._pjt_cavity

        housing = self._housing_3d
        g_cavity = self._global_cavity
        ptables = housing.mainframe.project.ptables

        pjt_cavity = ptables.pjt_cavities_table.insert(
            g_cavity.db_id, housing.db_obj.db_id)

        # pjt_cavities_table.insert() seeds position3d from the global
        # cavity's housing-local coords.  Transform to world space now so
        # subsequent terminal/seal positions are correct regardless of where
        # the housing sits in the scene.
        # g_cavity.position3d is in normalised VBO space (as stored by the
        # housing editor), so multiply by the housing scale first.
        scale = housing._scale.as_numpy.astype(np.float64)
        local_pos = g_cavity.position3d.as_numpy.astype(np.float64) * scale
        h_pos = housing._position.as_numpy.astype(np.float64)
        h_angle = housing._angle
        world_pos = np.asarray(
            local_pos.reshape(1, 3) @ h_angle, dtype=np.float64
        )[0] + h_pos

        cpos = pjt_cavity.position3d
        with cpos:
            cpos.x = float(world_pos[0])
            cpos.y = float(world_pos[1])
        cpos.z = float(world_pos[2])

        self._pjt_cavity = pjt_cavity
        return pjt_cavity

    def _cavity_midpoint(self, pjt_cavity) -> Tuple[float, float, float]:
        """Return world-space midpoint along the cavity axis as (x, y, z)."""
        cpos_np = pjt_cavity.position3d.as_numpy.astype(np.float64)
        cav_ang = pjt_cavity.angle3d
        length = float(self._global_cavity.length)

        ref_local = np.array([[0.0, 0.0, length]], dtype=np.float64)
        ref_world = np.asarray(ref_local @ cav_ang, dtype=np.float64)[0] + cpos_np
        mid = (cpos_np + ref_world) / 2.0
        return float(mid[0]), float(mid[1]), float(mid[2])

    # ── actions ────────────────────────────────────────────────────────────────

    def on_add_terminal(self):
        def _do():
            from .. import terminal as _terminal_obj
            from . import menu_ops as _menu_ops

            housing = self._housing_3d
            mainframe = housing.mainframe
            g_cavity = self._global_cavity

            compat_ids = [t.db_id for t in g_cavity.compat_terminals]

            part_id = _menu_ops.get_part_id(
                mainframe, 'terminals',
                mainframe.global_db.terminals_table, 'Add Terminal',
                initial_results=compat_ids)

            if part_id is None:
                return

            pjt_cavity = self._get_or_create_pjt_cavity()

            # Male terminals mate at the cavity opening (position3d = mating face).
            # Female terminals sit centered inside the cavity (midpoint along axis).
            g_terminal = mainframe.global_db.terminals_table[part_id]
            is_male = g_terminal.gender.name.lower() == 'male'

            if is_male:
                tx, ty, tz = pjt_cavity.position3d.as_float
            else:
                tx, ty, tz = self._cavity_midpoint(pjt_cavity)

            ptables = mainframe.project.ptables
            p3d = ptables.pjt_points3d_table.insert(tx, ty, tz)

            terminal_db = ptables.pjt_terminals_table.insert(
                part_id, None, p3d.db_id, pjt_cavity.db_id)

            terminal = _terminal_obj.Terminal(mainframe, terminal_db)
            mainframe.project.add_terminal(terminal)

        QtCore.QTimer.singleShot(0, _do)

    def on_add_seal(self):
        def _do():
            from . import menu_ops as _menu_ops
            from ...objects import seal as _seal_obj

            housing = self._housing_3d
            mainframe = housing.mainframe
            g_cavity = self._global_cavity

            # Find compatible plug seals by matching cavity dimensions
            mainframe.global_db.seals_table.execute(
                'SELECT seals.id FROM seals '
                'JOIN seal_types ON seals.type_id = seal_types.id '
                'WHERE UPPER(seal_types.name) = "PLUG" '
                'AND seals.width = ? AND seals.height = ?;',
                (g_cavity.width, g_cavity.height))
            compat_ids = [row[0] for row in mainframe.global_db.seals_table.fetchall()]

            part_id = _menu_ops.get_part_id(
                mainframe, 'seals',
                mainframe.global_db.seals_table, 'Add Seal',
                initial_results=compat_ids)

            if part_id is None:
                return

            pjt_cavity = self._get_or_create_pjt_cavity()
            mx, my, mz = self._cavity_midpoint(pjt_cavity)

            ptables = mainframe.project.ptables
            p3d = ptables.pjt_points3d_table.insert(mx, my, mz)

            seal_db = ptables.pjt_seals_table.insert(
                part_id, p3d.db_id, None, None, pjt_cavity.db_id)

            seal = _seal_obj.Seal(mainframe, seal_db)
            mainframe.project.add_seal(seal)

        QtCore.QTimer.singleShot(0, _do)

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

        QtCore.QTimer.singleShot(0, _do)

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

        QtCore.QTimer.singleShot(0, _do)


class HousingCavityPicker:
    """Manages cavity plane selection for a Housing in the 3D editor.

    Created when a Housing3D object is initialised; cleaned up when it is
    deleted.  Installs a transparent overlay and a mouse event filter on the
    inner GL canvas widget.  Cavity picking is always active — no prior housing
    selection is required.
    """

    # Max signed distance (mm) from a surface plane to a cavity position3d for
    # the cavity to be considered as belonging to that plane.
    _PLANE_TOL = 5.0

    # Only one picker may have an active highlight at a time across all
    # housings in the scene.  Selecting a cavity on one housing auto-clears
    # any highlight from other housings.
    _active: ClassVar[Optional["HousingCavityPicker"]] = None

    def _set_active(self) -> None:
        """Make `picker` the active one, clearing any prior active picker."""
        if (
            HousingCavityPicker._active is not None and
            HousingCavityPicker._active is not self
        ):
            HousingCavityPicker._active._clear_selection()

        HousingCavityPicker._active = self

    def __init__(self, housing: "_housing3d.Housing"):
        self.selected_surf_idx: int = None
        self.selected_cavity = None

        self._housing = housing
        # inner QOpenGLWidget — same as dialog.canvas._canvas in the housing editor
        self._gl_widget = housing.mainframe.editor3d.editor._canvas

        self.vertices: np.ndarray = housing._vbo.vertices.reshape(-1, 3).copy()
        self.normals: np.ndarray = housing._vbo.face_normals.reshape(-1, 3).copy()

        self.scale: _point.Point = self._housing.scale
        self.position: _point.Point = self._housing.position
        self.angle: _angle.Angle = self._housing.angle

        self.o_scale: _point.Point = self.scale.copy()
        self.o_angle: _angle.Angle = self.angle.copy()
        self.o_position: _point.Point = self.position.copy()

        self.vertices @= self.angle
        self.normals @= self.angle
        self.vertices *= self.scale
        self.vertices += self.position

        self.scale.bind(self._on_scale)
        self.position.bind(self._on_position)
        self.angle.bind(self._on_angle)

        self._build_surfaces()
        self.overlay = CavityPlaneOverlay(self._gl_widget, self)

    def _on_scale(self, scale: _point.Point):
        delta = scale - self.o_scale
        self.o_scale = scale.copy()

        self.vertices *= delta
        self._build_surfaces()

    def _on_position(self, position: _point.Point):
        delta = position - self.o_position
        self.o_position = position.copy()

        self.vertices += delta
        self._build_surfaces()

    def _on_angle(self, angle: _angle.Angle):
        delta = angle - self.o_angle
        self.o_angle = angle.copy()

        self.vertices -= self.position
        self.vertices @= delta
        self.normals @= delta

        self._build_surfaces()

    # ── surface construction ───────────────────────────────────────────────────

    def update_vbo(self):
        if self.scale is not None:
            self.scale.unbind(self._on_scale)

        if self.position is not None:
            self.position.unbind(self._on_position)

        if self.angle is not None:
            self.angle.unbind(self._on_angle)

        self.vertices = self._housing._vbo.vertices.reshape(-1, 3).copy()
        self.normals = self._housing._vbo.face_normals.reshape(-1, 3).copy()

        self.scale = self._housing.scale
        self.position = self._housing.position
        self.angle: _angle.Angle = self._housing.angle

        self.o_scale = self.scale.copy()
        self.o_angle = self.angle.copy()
        self.o_position = self.position.copy()

        self.vertices @= self.angle
        self.normals @= self.angle
        self.vertices *= self.scale
        self.vertices += self.position

        self.scale.bind(self._on_scale)
        self.position.bind(self._on_position)
        self.angle.bind(self._on_angle)

    def _build_surfaces(self):
        raw = _analysis.compute_surfaces(self.vertices, self.normals)
        self._surfaces = [
            s for grp in raw
            for s in _analysis.split_into_components(grp, self.vertices)
        ]

    # ── ray picking ────────────────────────────────────────────────────────────

    def compute_ray(self, px: int, py: int):
        camera = self._gl_widget.camera
        if (camera.projection is None or
                camera.modelview is None or
                camera.viewport is None):
            return None, None

        pj = camera.projection.astype(np.float64)
        mv = camera.modelview.astype(np.float64)
        vx, vy, vw, vh = camera.viewport

        if vw < 1 or vh < 1:
            return None, None

        dpr = self._gl_widget.devicePixelRatio()
        wx = float(px) * dpr
        wy = float(vh - py * dpr)

        ndc_x = (2.0 * (wx - vx) / vw) - 1.0
        ndc_y = (2.0 * (wy - vy) / vh) - 1.0

        mvp = pj.dot(mv)
        inv_mvp = np.linalg.inv(mvp)

        near = _unproject(ndc_x, ndc_y, -1.0, inv_mvp)
        far = _unproject(ndc_x, ndc_y, 1.0, inv_mvp)
        if near is None or far is None:
            return None, None

        d = far - near
        mag = float(np.linalg.norm(d))
        if mag < 1e-10:
            return None, None

        return near, d / mag

    def pick_surface_at(
        self, px: int, py: int
    ) -> Tuple[int, Optional[np.ndarray]]:
        """Ray-cast against the housing mesh.  Returns (surf_idx, hit_point)."""

        origin, direction = self.compute_ray(px, py)
        if origin is None:
            return -1, None

        return self.pick_surface_at_ray(origin, direction)

    def pick_surface_at_ray(
        self, origin: np.ndarray, direction: np.ndarray
    ) -> Tuple[int, Optional[np.ndarray]]:
        """Ray-cast against the housing mesh using a pre-computed ray.
        Returns (surf_idx, hit_point)."""

        if not self._surfaces or self.vertices is None:
            return -1, None

        verts = self.vertices.astype(np.float64)
        best_t = float('inf')
        best_idx = -1
        best_hit: Optional[np.ndarray] = None

        for i, surf in enumerate(self._surfaces):
            n = surf.normal.astype(np.float64)
            denom = float(n @ direction)
            if abs(denom) < 1e-8:
                continue

            t = (float(surf.plane_dist) - float(n @ origin)) / denom
            if t < 0.0 or t >= best_t:
                continue

            hit = origin + t * direction
            for ti in surf.tri_indices:
                a = verts[3 * ti]
                b = verts[3 * ti + 1]
                c = verts[3 * ti + 2]

                if _point_in_triangle(hit, a, b, c):
                    best_t = t
                    best_idx = i
                    best_hit = hit
                    break

        return best_idx, best_hit

    # ── cavity matching ────────────────────────────────────────────────────────

    def _ray_hits_obb(self, origin: np.ndarray, direction: np.ndarray,
                      pjt_cavity, g_cavity) -> float:
        """Slab-method ray-OBB intersection.  Returns t >= 0 on hit, -1 on miss.

        The OBB is built from the PJTCavity's world-space position3d (start
        face centre) and angle3d (orientation), with half-extents taken from
        the global cavity's width, height, and length.
        """

        hw = float(g_cavity.width) / 2.0
        hh = float(g_cavity.height) / 2.0
        hl = float(g_cavity.length) / 2.0

        cav_angle = pjt_cavity.angle3d
        start = pjt_cavity.position3d.as_numpy.astype(np.float64)

        axis_x = np.asarray(
            np.array([[1.0, 0.0, 0.0]]) @ cav_angle, dtype=np.float64)[0]

        axis_y = np.asarray(
            np.array([[0.0, 1.0, 0.0]]) @ cav_angle, dtype=np.float64)[0]

        axis_z = np.asarray(
            np.array([[0.0, 0.0, 1.0]]) @ cav_angle, dtype=np.float64)[0]

        center = start + axis_z * hl
        d = center - origin

        t_min = -np.inf
        t_max = np.inf

        for axis, half_ext in ((axis_x, hw), (axis_y, hh), (axis_z, hl)):
            e = float(np.dot(axis, d))
            f = float(np.dot(axis, direction))
            if abs(f) > 1e-8:
                t1 = (e - half_ext) / f
                t2 = (e + half_ext) / f

                if t1 > t2:
                    t1, t2 = t2, t1

                t_min = max(t_min, t1)
                t_max = min(t_max, t2)
                if t_min > t_max:
                    return -1.0

            elif abs(e) > half_ext:
                return -1.0

        return t_min if t_min >= 0.0 else t_max

    def match_cavity(
        self, origin: np.ndarray, direction: np.ndarray
    ) -> Optional["_global_cavity_mod.Cavity"]:
        """Return the global Cavity whose PJTCavity OBB the ray hits first,
        or None if no cavity is intersected."""

        g_lookup = {g.db_id: g
                    for g in self._housing.db_obj.part.cavities
                    if g is not None}

        best_t = float('inf')
        best_cavity = None

        for pjt_cavity in self._housing.db_obj.cavities:
            g = g_lookup.get(pjt_cavity.part_id)
            if g is None:
                continue
            t = self._ray_hits_obb(origin, direction, pjt_cavity, g)
            if 0.0 <= t < best_t:
                best_t = t
                best_cavity = g

        return best_cavity

    # ── event callbacks ────────────────────────────────────────────────────────

    def _on_surface_selected(self, idx: int, hit_point: np.ndarray):
        self.selected_surf_idx = idx
        self.selected_cavity = self.match_cavity(idx, hit_point)

        if self.selected_cavity is not None:
            HousingCavityPicker._set_active(self)

        if self.overlay is not None:
            self.overlay.update()

    def clear_selection(self):
        self.selected_surf_idx = None
        self.selected_cavity = None
        if HousingCavityPicker._active is self:
            HousingCavityPicker._active = None
        if self.overlay is not None:
            self.overlay.update()

    def _on_right_click(self, global_pos: QtCore.QPoint):
        if self.selected_cavity is None:
            return

        menu = HousingCavityMenu(self._housing, self.selected_cavity)
        menu.exec(global_pos)
        menu.deleteLater()

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def cleanup(self):
        """Remove the overlay from the GL canvas."""
        if HousingCavityPicker._active is self:
            HousingCavityPicker._active = None

        if self.overlay is not None:
            self.overlay.cleanup()
            self.overlay = None
