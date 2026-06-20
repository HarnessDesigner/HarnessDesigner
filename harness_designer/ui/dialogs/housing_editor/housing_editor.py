# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Optional

import numpy as np
from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import config as _dialog_config
from . import housing_obj as _housing_obj
from . import cavity_panel as _cavity_panel
from . import accessory_panel as _accessory_panel
from . import connector_analysis as _analysis
from . import analysis_panel as _analysis_panel
from .. import dialog_base as _dialog_base
from ....gl import canvas3d as _canvas3d


if TYPE_CHECKING:
    from .... import ui as _ui


Config = _dialog_config.Config

_TERMINAL_COLORS: list[tuple[float, float, float]] = [
    (0.20, 0.60, 1.00),
    (0.20, 0.90, 0.40),
    (1.00, 0.70, 0.10),
    (0.90, 0.20, 0.90),
    (0.10, 0.90, 0.90),
    (1.00, 0.40, 0.20),
]


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


class SurfaceOverlay(QtWidgets.QWidget):
    """Transparent child widget that projects selected surfaces as 2D highlights."""

    def __init__(self, gl_widget, dialog: "HousingEditorDialog"):
        super().__init__(gl_widget)
        self._dialog = dialog
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(gl_widget.rect())
        gl_widget.installEventFilter(self)
        # frameSwapped fires after each GL frame is composited — reliable for
        # tracking camera movement without any UpdateRequest timing guesswork.
        gl_widget.frameSwapped.connect(self.update)
        self.show()
        self.raise_()

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.Resize:
            self.setGeometry(QtCore.QRect(0, 0, obj.width(), obj.height()))
        return False

    def paintEvent(self, event):
        dlg = self._dialog

        if not dlg.surfaces or dlg.vertices is None:
            return

        camera = dlg.canvas._canvas.camera

        if camera.clip is None or camera.viewport is None:
            return

        # camera.clip = projection @ modelview, already computed each frame.
        # viewport is in physical pixels; divide by DPR for logical QPainter coords.
        clip_mat = camera.clip.astype(np.float64)
        vx, vy, vw, vh = camera.viewport
        dpr = dlg.canvas._canvas.devicePixelRatio()

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)

        verts = dlg.vertices.reshape(-1, 3).astype(np.float64)

        def project(pt):
            v = np.array([pt[0], pt[1], pt[2], 1.0], dtype=np.float64)
            clip = clip_mat @ v

            w_val = float(clip[3])
            if abs(w_val) < 1e-8:
                return None

            ndc = clip / w_val
            # Physical screen coords → logical widget coords (÷ DPR)
            sx = float((ndc[0] + 1.0) * 0.5 * vw + vx) / dpr
            sy = float((1.0 - ndc[1]) * 0.5 * vh + vy) / dpr

            return QtCore.QPointF(sx, sy)

        def draw_surf(surf, r, g, b):
            painter.setBrush(QtGui.QBrush(QtGui.QColor(r, g, b, 80)))

            for ti in surf.tri_indices:
                pts = [project(verts[3 * ti + k]) for k in range(3)]

                if all(p is not None for p in pts):
                    painter.drawPolygon(QtGui.QPolygonF(pts))

        if dlg.wire_surf_idx is not None:
            draw_surf(dlg.surfaces[dlg.wire_surf_idx], 255, 140, 0)

        for idx in dlg.terminal_surf_idxs:
            surf = dlg.surfaces[idx]
            rf, gf, bf = dlg.terminal_surf_colors.get(idx, (0.5, 0.5, 0.5))
            draw_surf(surf, int(rf * 255), int(gf * 255), int(bf * 255))

        # Draw analysis-result cavity overlays when the preview panel is visible
        if dlg.analysis_panel.isVisible():
            items = dlg.analysis_panel.items()
            selected = dlg.analysis_selected
            for i, item in enumerate(items):
                if i == selected:
                    rgba = (80, 255, 80, 130)   # bright green = selected
                else:
                    rgba = (200, 200, 200, 55)  # dim grey = unselected

                painter.setBrush(QtGui.QBrush(QtGui.QColor(*rgba)))

                cavity_verts = item.verts.reshape(-1, 3).astype(np.float64)
                n_tris = len(cavity_verts) // 3
                for ti in range(n_tris):
                    pts = [project(cavity_verts[3 * ti + k]) for k in range(3)]
                    if all(p is not None for p in pts):
                        painter.drawPolygon(QtGui.QPolygonF(pts))

        painter.end()


class _SurfaceSelectFilter(QtCore.QObject):
    """
    Event filter installed on the inner canvas
    to intercept clicks for surface picking.
    """

    def __init__(self, dialog: "HousingEditorDialog"):
        super().__init__(dialog.canvas._canvas)
        self._dialog = dialog
        self._is_moved = False

        dialog.canvas._canvas.installEventFilter(self)

    def eventFilter(self, obj, event: QtGui.QMouseEvent):
        t = event.type()
        if t == QtCore.QEvent.Type.MouseButtonPress:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._is_moved = False

        elif t == QtCore.QEvent.Type.MouseMove:
            self._is_moved = True

        elif t == QtCore.QEvent.Type.MouseButtonRelease:
            if (
                not self._is_moved and
                event.button() == QtCore.Qt.MouseButton.LeftButton and
                self._dialog.select_mode is not None and
                self._dialog.surfaces
            ):

                pos = event.position().toPoint()
                idx = self._dialog.pick_surface_at(pos.x(), pos.y())
                if idx >= 0:
                    self._dialog.assign_surface(idx)

        return False


class HousingEditorDialog(_dialog_base.BaseDialog):
    """Housing editor with integrated surface-picking for cavity detection."""

    def __init__(self, parent: "_ui.MainFrame"):
        self.db_obj = None

        _dialog_base.BaseDialog.__init__(
            self, parent, 'Edit Housing', size=(1200, 900))

        w = Config.editor3d.virtual_canvas.width
        h = Config.editor3d.virtual_canvas.height

        self.canvas = _canvas3d.Canvas3D(
            self.panel, Config.editor3d, size=(w, h))

        self.controls = QtWidgets.QTabWidget(self.panel)
        self.controls.setMaximumHeight(250)

        self.housing: _housing_obj.Housing = None
        self.cavity_panel: _cavity_panel.CavityPanel = None
        self.accessory_panel: _accessory_panel.AccessoryPanel = None
        self._selected_obj = None
        self.surface_overlay: Optional[SurfaceOverlay] = None

        # ── surface-picking state ─────────────────────────────────────────────
        self.vertices: Optional[np.ndarray] = None
        self.face_norms: Optional[np.ndarray] = None
        self.surfaces: list[_analysis.Surface] = []
        self.select_mode: Optional[str] = None
        self.wire_surf_idx: Optional[int] = None
        self.terminal_surf_idxs: list[int] = []
        self.terminal_surf_colors: dict[int, tuple[float, float, float]] = {}
        self.terminal_overrides: dict[int, str] = {}
        self.term_color_idx: int = 0
        self.length_factor: float = 1.0
        self.surface_filter: Optional[_SurfaceSelectFilter] = None

        # ── analysis preview state ────────────────────────────────────────────
        self.analysis_selected: int = -1

        # ── toolbar ───────────────────────────────────────────────────────────
        toolbar = QtWidgets.QWidget(self.panel)
        tb_layout = QtWidgets.QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 4, 4, 4)
        tb_layout.setSpacing(6)

        self._btn_wire = QtWidgets.QPushButton('Select Wire Side', toolbar)
        self._btn_wire.setCheckable(True)
        self._btn_wire.setStyleSheet(
            'QPushButton { padding: 4px 12px; } '
            'QPushButton:checked { background-color: #b06010; '
            'color: white; font-weight: bold; }')

        self._btn_trm_plane = QtWidgets.QPushButton(
            'Select Terminal Plane', toolbar)

        self._btn_trm_plane.setCheckable(True)
        self._btn_trm_plane.setStyleSheet(
            'QPushButton { padding: 4px 12px; } '
            'QPushButton:checked { background-color: #1a7a30; '
            'color: white; font-weight: bold; }')

        self._btn_terminal = QtWidgets.QPushButton('Add Terminal', toolbar)
        self._btn_terminal.setCheckable(True)
        self._btn_terminal.setStyleSheet(
            'QPushButton { padding: 4px 12px; } '
            'QPushButton:checked { background-color: #1a50a0; '
            'color: white; font-weight: bold; }')

        self._btn_analyze = QtWidgets.QPushButton('Analyze', toolbar)
        self._btn_analyze.setStyleSheet('QPushButton { padding: 4px 12px; }')

        self._btn_clear_terms = QtWidgets.QPushButton(
            'Clear Terminals', toolbar)
        self._btn_clear_terms.setStyleSheet('QPushButton { padding: 4px 12px; }')

        self._btn_clear_all = QtWidgets.QPushButton('Clear All', toolbar)
        self._btn_clear_all.setStyleSheet('QPushButton { padding: 4px 12px; }')

        tb_layout.addWidget(self._btn_wire)
        tb_layout.addWidget(self._btn_trm_plane)
        tb_layout.addWidget(self._btn_terminal)
        tb_layout.addSpacing(12)
        tb_layout.addWidget(self._btn_analyze)
        tb_layout.addWidget(self._btn_clear_terms)
        tb_layout.addWidget(self._btn_clear_all)
        tb_layout.addSpacing(12)

        self._len_label = QtWidgets.QLabel('Length: 100%', toolbar)
        self._len_slider = QtWidgets.QSlider(
            QtCore.Qt.Orientation.Horizontal, toolbar)

        self._len_slider.setRange(10, 100)
        self._len_slider.setValue(100)
        self._len_slider.setFixedWidth(120)

        tb_layout.addWidget(self._len_label)
        tb_layout.addWidget(self._len_slider)
        tb_layout.addStretch(1)

        self._status_label = QtWidgets.QLabel('', toolbar)
        tb_layout.addWidget(self._status_label)

        self._mode_btns = (
            self._btn_wire, self._btn_trm_plane, self._btn_terminal)

        self._btn_wire.clicked.connect(
            lambda checked:
            self._on_mode_btn('wire', self._btn_wire, checked))

        self._btn_trm_plane.clicked.connect(
            lambda checked:
            self._on_mode_btn('terminal_plane', self._btn_trm_plane, checked))

        self._btn_terminal.clicked.connect(
            lambda checked:
            self._on_mode_btn('terminal', self._btn_terminal, checked))

        self._btn_analyze.clicked.connect(self.run_analysis)
        self._btn_clear_terms.clicked.connect(self._clear_terminals)
        self._btn_clear_all.clicked.connect(self._clear_all)
        self._len_slider.valueChanged.connect(self._on_length_changed)

        # ── analysis result side-panel (hidden until Analyze is clicked) ──────
        self.analysis_panel = _analysis_panel.AnalysisResultPanel(self.panel)
        self.analysis_panel.accepted.connect(self._on_analysis_accepted)
        self.analysis_panel.rejected.connect(self._on_analysis_rejected)
        self.analysis_panel.selectionChanged.connect(
            self._on_analysis_selection)

        # ── main layout ───────────────────────────────────────────────────────
        v_layout = QtWidgets.QVBoxLayout(self.panel)
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.addWidget(self.canvas, 1)
        h_layout.addWidget(self.analysis_panel)   # shown/hidden by load()
        v_layout.addLayout(h_layout, 1)
        v_layout.addWidget(toolbar)
        v_layout.addSpacing(5)
        v_layout.addWidget(self.controls)

    @property
    def can_select(self) -> bool:
        return self.select_mode not in ('wire', 'terminal_plane', 'terminal')

    # ── SetValue ──────────────────────────────────────────────────────────────

    def SetValue(self, db_obj):
        self.db_obj = db_obj

        self.housing = _housing_obj.Housing(self, db_obj)

        self.cavity_panel = _cavity_panel.CavityPanel(
            self, self.controls, self.housing.obj3d)

        self.accessory_panel = _accessory_panel.AccessoryPanel(
            self, self.controls, self.housing.obj3d)

        self.controls.addTab(self.cavity_panel, 'Cavities')
        self.controls.addTab(self.accessory_panel, 'Accessories')

        # Install surface-picking event filter on the inner GL widget
        self.surface_filter = _SurfaceSelectFilter(self)
        self.surface_overlay = SurfaceOverlay(self.canvas._canvas, self)

        self._build_surfaces()
        self.update()

    def _build_surfaces(self) -> None:
        vbo = self.housing.obj3d._vbo
        # VBO already has model.angle3d / model.position3d pre-baked in by
        # housing_obj.py, so these arrays are already in world space.
        self.vertices = vbo.vertices.reshape(-1, 3).copy().astype(np.float32)
        self.face_norms = vbo.face_normals.reshape(-1, 3).copy().astype(np.float32)

        raw = _analysis.compute_surfaces(self.vertices, self.face_norms)

        self.surfaces = [
            s for grp in raw
            for s in _analysis.split_into_components(grp, self.vertices)]

        self._set_status(
            f'Mesh loaded — {len(self.surfaces)} surfaces detected')

    # ── surface picking ───────────────────────────────────────────────────────

    def _compute_ray(self, px: int, py: int):
        camera = self.canvas._canvas.camera

        if (
            camera.projection is None or
            camera.modelview is None or
            camera.viewport is None
        ):
            return None, None

        pj = camera.projection.astype(np.float64)
        mv = camera.modelview.astype(np.float64)
        viewport = camera.viewport

        vx, vy, vw, vh = viewport

        if vw < 1 or vh < 1:
            return None, None

        # event.position() is in logical pixels; the GL viewport is in physical
        # pixels. Scale up by DPR so both are in the same unit.
        dpr = self.canvas._canvas.devicePixelRatio()
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

    def pick_surface_at(self, px: int, py: int) -> int:
        origin, direction = self._compute_ray(px, py)

        if origin is None:
            return -1

        verts = self.vertices.reshape(-1, 3).astype(np.float64)
        best_t = float('inf')
        best_idx = -1

        for i, surf in enumerate(self.surfaces):
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
                    break

        return best_idx

    # ── selection modes ───────────────────────────────────────────────────────

    def _next_color(self) -> tuple[float, float, float]:
        col = _TERMINAL_COLORS[self.term_color_idx % len(_TERMINAL_COLORS)]
        self.term_color_idx += 1

        return col

    def _on_mode_btn(self, mode: str,
                     button: QtWidgets.QPushButton,
                     checked: bool) -> None:

        if checked:
            self.select_mode = mode

            for btn in self._mode_btns:
                if btn is not button:
                    btn.setChecked(False)

            hints = {
                'wire': 'Click the wire-side plane (click again to deselect)',
                'terminal_plane': 'Click any terminal recess — all on that plane selected',
                'terminal': 'Click individual terminal recesses to add/remove'}

            self._set_status(hints.get(mode, ''))
        else:
            self.select_mode = None
            self._set_status('')

    def assign_surface(self, idx: int) -> None:
        if self.select_mode == 'wire':
            if idx == self.wire_surf_idx:
                self.wire_surf_idx = None
                self._set_status('Wire side deselected')
            else:
                self.wire_surf_idx = idx
                self._set_status('Wire side set')

        elif self.select_mode == 'terminal':
            if idx in self.terminal_surf_idxs:
                self.terminal_surf_idxs.remove(idx)
                self.terminal_surf_colors.pop(idx, None)
                self._set_status(
                    f'Terminal removed '
                    f'({len(self.terminal_surf_idxs)} selected)')
            else:
                color = self._next_color()
                self.terminal_surf_idxs.append(idx)
                self.terminal_surf_colors[idx] = color
                self._set_status(
                    f'Terminal added '
                    f'({len(self.terminal_surf_idxs)} selected)')

        elif self.select_mode == 'terminal_plane':
            ref = self.surfaces[idx]
            plane_idxs = [
                i for i, s in enumerate(self.surfaces)
                if (float(np.dot(s.normal, ref.normal)) > 0.98
                    and abs(s.plane_dist - ref.plane_dist) < 0.5)
            ]

            if all(i in self.terminal_surf_idxs for i in plane_idxs):
                for i in plane_idxs:
                    self.terminal_surf_idxs.remove(i)
                    self.terminal_surf_colors.pop(i, None)

                self._set_status(
                    f'Plane deselected ({len(self.terminal_surf_idxs)} '
                    f'terminals remaining)')
            else:
                color = self._next_color()
                for i in plane_idxs:
                    if i not in self.terminal_surf_idxs:
                        self.terminal_surf_idxs.append(i)
                        self.terminal_surf_colors[i] = color

                self._set_status(
                    f'Plane selected — {len(plane_idxs)} '
                    f'surfaces ({len(self.terminal_surf_idxs)} total)')

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    # ── analysis ──────────────────────────────────────────────────────────────

    def run_analysis(self) -> None:
        if self.wire_surf_idx is None:
            self._set_status('Select the wire side first.')
            return
        if not self.terminal_surf_idxs:
            self._set_status('Select at least one terminal plane first.')
            return

        wire_surf = self.surfaces[self.wire_surf_idx]
        wire_centroid = _analysis.surface_centroid(wire_surf, self.vertices)

        results = []
        for ti in self.terminal_surf_idxs:
            term_surf = self.surfaces[ti]
            try:
                kind, params, verts, _norms = _analysis.generate_terminal_geometry(
                    term_surf, wire_surf, self.vertices,
                    kind_override=self.terminal_overrides.get(ti),
                    length_factor=self.length_factor,
                )
            except Exception:  # NOQA
                continue

            n_term = term_surf.normal.astype(np.float64)
            n_term /= np.linalg.norm(n_term) + 1e-12
            d_start = term_surf.plane_dist
            d_full = float(wire_centroid @ n_term)
            d_end = d_start + (d_full - d_start) * self.length_factor

            center = np.array(params['center'], dtype=np.float64)
            u_ax, v_ax = _analysis.plane_frame(n_term)
            proj_u = float(center @ u_ax)
            proj_v = float(center @ v_ax)
            results.append((kind, params, d_start, d_end, proj_u, proj_v, verts))

        if not results:
            self._set_status('Analysis produced no results.')
            return

        # Sort: top-to-bottom (decreasing proj_v), left-to-right (increasing proj_u)
        results.sort(key=lambda r: (-r[5], r[4]))

        # Build preview items — names continue from existing cavity count
        existing = len(self.cavity_panel.cavities) if self.cavity_panel else 0
        items = []
        for i, (kind, params, d_start, d_end, _pu, _pv, verts) in enumerate(results):
            item = _analysis_panel.AnalysisItem(
                name=str(existing + i + 1),
                kind=kind,
                params=dict(params),   # copy so edits don't alias the source
                d_start=d_start,
                d_end=d_end,
                verts=verts,
            )
            items.append(item)

        self.analysis_selected = 0
        self.analysis_panel.load(items)   # shows the side panel
        self._btn_analyze.setEnabled(False)

        if self.surface_overlay is not None:
            self.surface_overlay.update()

        self._set_status(
            f'{len(results)} cavities detected — review list then click OK.')

    def _on_analysis_accepted(self) -> None:
        if self.cavity_panel is None:
            return

        items = self.analysis_panel.items()
        start_idx = len(self.cavity_panel.cavities)
        for i, item in enumerate(items):
            self.cavity_panel.commit_cavity(start_idx + i, item)

        self.analysis_selected = -1
        self.analysis_panel.load([])    # hides the panel
        self._btn_analyze.setEnabled(True)

        if self.surface_overlay is not None:
            self.surface_overlay.update()

        # Clear both wire-plane and terminal selections per spec
        self._clear_all()
        self._set_status(f'{len(items)} cavities added.')

    def _on_analysis_rejected(self) -> None:
        self.analysis_selected = -1
        self.analysis_panel.load([])    # hides the panel
        self._btn_analyze.setEnabled(True)

        if self.surface_overlay is not None:
            self.surface_overlay.update()

        self._set_status('Analysis discarded — selections preserved.')

    def _on_analysis_selection(self, row: int) -> None:
        self.analysis_selected = row

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    # ── toolbar helpers ───────────────────────────────────────────────────────

    def _on_length_changed(self, value: int) -> None:
        self._len_label.setText(f'Length: {value}%')
        self.length_factor = value / 100.0

    def _clear_terminals(self) -> None:
        self.terminal_surf_idxs.clear()
        self.terminal_surf_colors.clear()
        self.terminal_overrides.clear()
        self.term_color_idx = 0

        for btn in self._mode_btns:
            btn.setChecked(False)

        self.select_mode = None

        if self.surface_overlay is not None:
            self.surface_overlay.update()

        self._set_status('Terminals cleared.')

    def _clear_all(self) -> None:
        self.wire_surf_idx = None
        self._clear_terminals()
        self._set_status('All selections cleared.')

    def _set_status(self, msg: str) -> None:
        self._status_label.setText(msg)

    # ── boilerplate (unchanged from original) ─────────────────────────────────

    def closeEvent(self, event):
        self.canvas.cleanup()
        super().closeEvent(event)

    @property
    def editor2d(self):
        return None

    @property
    def editor3d(self):
        return self

    def add_object(self, obj):
        self.canvas.add_object(obj)

    def remove_object(self, obj):
        self.canvas.remove_object(obj)

    def _set_selected(self, obj):
        self._selected_obj = obj
        self.canvas.set_selected(obj)

    def set_selected(self, obj):  # NOQA
        if obj is not None:
            obj.set_selected(True)

    def get_selected(self):
        return self._selected_obj

    @property
    def config(self):
        return Config.editor3d

    def Refresh(self, *_, **__):
        self.canvas.update()
        if self.surface_overlay is not None:
            self.surface_overlay.update()

    @property
    def context(self):
        return self.canvas.context
