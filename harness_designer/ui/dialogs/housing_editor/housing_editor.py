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
from ....utils.mesh_surface_picker import MeshSurfacePicker as _MeshSurfacePicker


if TYPE_CHECKING:
    from .... import ui as _ui


Config = _dialog_config.Config


def _shape_polygon_points(kind: str, params: dict, segments: int = 24) -> list:
    """Build world-space outline points for a manually-drawn cavity marker.

    ``params`` matches the schema produced by
    ``connector_analysis.classify_loop``/``plane_frame``: ``center``, ``u``,
    ``v``, plus ``radius`` (circle) or ``half_w``/``half_h`` (rect).
    """
    center = np.asarray(params['center'], dtype=np.float64)
    u = np.asarray(params['u'], dtype=np.float64)
    v = np.asarray(params['v'], dtype=np.float64)

    if kind == 'circle':
        r = float(params['radius'])
        angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
        return [center + r * (np.cos(a) * u + np.sin(a) * v) for a in angles]

    hw = float(params['half_w'])
    hh = float(params['half_h'])
    return [
        center - hw * u - hh * v,
        center + hw * u - hh * v,
        center + hw * u + hh * v,
        center - hw * u + hh * v,
    ]


_TERMINAL_COLORS: list[tuple[float, float, float]] = [
    (0.20, 0.60, 1.00),
    (0.20, 0.90, 0.40),
    (1.00, 0.70, 0.10),
    (0.90, 0.20, 0.90),
    (0.10, 0.90, 0.90),
    (1.00, 0.40, 0.20),
]


class PlaneTreePanel(QtWidgets.QWidget):
    """Side panel that shows selected plane groups as a tree.

    Top-level (bold) nodes = one plane group per coplanar click, labelled
    "Plane N — X surfaces".  Each node expands to show its individual
    surfaces, labelled "Surface M — Y tris".

    Clicking a top-level node highlights all surfaces in that group and
    dims all surfaces in other groups.  Clicking a child node highlights
    only that one surface.  Clicking the already-selected item deselects
    (everything in this mode returns to full brightness).

    Remove: if a group node is selected, the whole group is removed.
            if a surface node is selected, only that surface is removed.
    Done: exits the active mode (unchecks the toolbar button).
    """

    # (group_idx, surf_local_idx)  –  surf_local_idx = -1 means whole group
    selectionChanged = QtCore.Signal(int, int)
    removeRequested = QtCore.Signal(int, int)
    accepted = QtCore.Signal()
    # Emitted from the group-node context menu: (group_idx, 'circle'|'rect')
    addManualRequested = QtCore.Signal(int, str)

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)

        self._sel_group: int = -1
        self._sel_surf: int = -1   # local index inside the group, -1 = whole group
        self._is_terminal: bool = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self._label = QtWidgets.QLabel('Selected Surfaces', self)
        self._label.setStyleSheet('font-weight: bold;')
        layout.addWidget(self._label)

        self._tree = QtWidgets.QTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setStyleSheet(
            'QTreeWidget::item:selected {'
            '  background-color: #cc1100;'
            '  color: white;'
            '}'
        )
        self._tree.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_ctx_menu)

        layout.addWidget(self._tree, 1)

        btn_row = QtWidgets.QHBoxLayout()
        self._btn_remove = QtWidgets.QPushButton('Remove', self)
        self._btn_done = QtWidgets.QPushButton('Done', self)
        btn_row.addWidget(self._btn_remove)
        btn_row.addStretch(1)
        btn_row.addWidget(self._btn_done)
        layout.addLayout(btn_row)

        self._tree.itemClicked.connect(self._on_item_clicked)
        self._btn_remove.clicked.connect(self._on_remove)
        self._btn_done.clicked.connect(self.accepted)

        self.setMinimumWidth(210)
        self.setMaximumWidth(290)
        self.hide()

    def load(
        self,
        groups: list[list[int]],
        surfaces: list,
        label: str = 'Selected Surfaces',
        is_terminal: bool = False,
    ) -> None:
        """Rebuild the tree from plane groups.

        groups[g] is the list of surface indices for plane group g.
        surfaces is the full picker surface list (for triangle-count labels).
        is_terminal controls whether the group-node context menu offers
        "Add Circle Cavity" / "Add Rectangle Cavity" (terminal-plane mode
        only — used to hand-mark cavities on a single continuous plane).
        """
        self._is_terminal = is_terminal
        self._label.setText(label)
        self._tree.clear()
        self._sel_group = -1
        self._sel_surf = -1

        for g, group in enumerate(groups):
            n = len(group)
            parent_item = QtWidgets.QTreeWidgetItem(
                self._tree,
                [f'Plane {g + 1}  —  {n} surface{"s" if n != 1 else ""}'],
            )
            parent_item.setData(
                0, QtCore.Qt.ItemDataRole.UserRole, (g, -1))
            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)

            for s, si in enumerate(group):
                n_tris = len(surfaces[si].tri_indices)
                child = QtWidgets.QTreeWidgetItem(
                    parent_item,
                    [f'  Surface {s + 1}  —  {n_tris}'
                     f' tri{"s" if n_tris != 1 else ""}'],
                )
                child.setData(
                    0, QtCore.Qt.ItemDataRole.UserRole, (g, s))

            parent_item.setExpanded(True)

        if groups:
            self.show()
        else:
            self.hide()

    def selection(self) -> tuple[int, int]:
        return self._sel_group, self._sel_surf

    def _on_item_clicked(
        self, item: QtWidgets.QTreeWidgetItem, _col: int
    ) -> None:
        g, s = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if g == self._sel_group and s == self._sel_surf:
            # Same item clicked again → deselect
            self._tree.clearSelection()
            self._sel_group = -1
            self._sel_surf = -1
            self.selectionChanged.emit(-1, -1)
        else:
            self._sel_group = g
            self._sel_surf = s
            self.selectionChanged.emit(g, s)

    def _on_remove(self) -> None:
        if self._sel_group >= 0:
            self.removeRequested.emit(self._sel_group, self._sel_surf)

    def _on_ctx_menu(self, pos: QtCore.QPoint) -> None:
        item = self._tree.itemAt(pos)
        if item is None:
            return

        g, s = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        menu = QtWidgets.QMenu(self._tree)
        act = menu.addAction('Remove')
        act.triggered.connect(lambda: self.removeRequested.emit(g, s))

        if self._is_terminal and s < 0:
            menu.addSeparator()
            act = menu.addAction('Add Circle Cavity')
            act.triggered.connect(
                lambda: self.addManualRequested.emit(g, 'circle'))
            act = menu.addAction('Add Rectangle Cavity')
            act.triggered.connect(
                lambda: self.addManualRequested.emit(g, 'rect'))

        menu.exec(self._tree.mapToGlobal(pos))


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

        def draw_surf(surf, r, g, b, alpha=80):
            painter.setBrush(QtGui.QBrush(QtGui.QColor(r, g, b, alpha)))
            for ti in surf.tri_indices:
                pts = [project(verts[3 * ti + k]) for k in range(3)]
                if all(p is not None for p in pts):
                    painter.drawPolygon(QtGui.QPolygonF(pts))

        mode = dlg.select_mode
        g_sel = dlg.plane_sel_group
        s_sel = dlg.plane_sel_surf

        # --- wire plane groups (orange) ---
        wire_g = g_sel if mode == 'wire' else -1
        wire_s = s_sel if mode == 'wire' else -1

        for g, group in enumerate(dlg.wire_plane_groups):
            for s, si in enumerate(group):
                if wire_g < 0:
                    draw_surf(dlg.surfaces[si], 255, 140, 0, 80)
                elif g == wire_g and (wire_s < 0 or s == wire_s):
                    draw_surf(dlg.surfaces[si], 255, 40, 40, 200)   # selected → bright red
                else:
                    draw_surf(dlg.surfaces[si], 255, 140, 0, 20)    # unselected → dim orange

        # --- terminal plane groups (blue) ---
        term_g = g_sel if mode == 'terminal_plane' else -1
        term_s = s_sel if mode == 'terminal_plane' else -1

        for g, group in enumerate(dlg.term_plane_groups):
            for s, si in enumerate(group):
                if term_g < 0:
                    draw_surf(dlg.surfaces[si], 51, 153, 255, 80)
                elif g == term_g and (term_s < 0 or s == term_s):
                    draw_surf(dlg.surfaces[si], 255, 40, 40, 200)   # selected → bright red
                else:
                    draw_surf(dlg.surfaces[si], 51, 153, 255, 20)   # unselected → dim blue

        # --- selected cavity surface highlights (only when not in a pick mode) ---
        if dlg.select_mode is None:
            w_si = dlg.selected_cavity_wire_si
            t_si = dlg.selected_cavity_term_si
            if 0 <= w_si < len(dlg.surfaces):
                draw_surf(dlg.surfaces[w_si], 255, 220, 0, 120)    # yellow = wire
            if 0 <= t_si < len(dlg.surfaces):
                draw_surf(dlg.surfaces[t_si], 0, 210, 255, 120)    # cyan = terminal

        # --- individual terminals (per-surface colours) ---
        for idx in dlg.terminal_surf_idxs:
            surf = dlg.surfaces[idx]
            rf, gf, bf = dlg.terminal_surf_colors.get(idx, (0.5, 0.5, 0.5))
            draw_surf(surf, int(rf * 255), int(gf * 255), int(bf * 255))

        # --- analysis-result cavity overlays ---
        if dlg.analysis_panel.isVisible():
            items = dlg.analysis_panel.items()
            selected = dlg.analysis_selected
            for i, item in enumerate(items):
                if i == selected:
                    rgba = (80, 255, 80, 130)
                else:
                    rgba = (200, 200, 200, 55)

                painter.setBrush(QtGui.QBrush(QtGui.QColor(*rgba)))

                cavity_verts = item.verts.reshape(-1, 3).astype(np.float64)
                n_tris = len(cavity_verts) // 3
                for ti in range(n_tris):
                    pts = [project(cavity_verts[3 * ti + k]) for k in range(3)]
                    if all(p is not None for p in pts):
                        painter.drawPolygon(QtGui.QPolygonF(pts))

        # --- manually-drawn cavity markers (single-plane housings) ---
        def draw_shape(kind, params, r, g, b, a=140):
            poly_pts = [project(pt) for pt in _shape_polygon_points(kind, params)]
            if all(p is not None for p in poly_pts):
                painter.setBrush(QtGui.QBrush(QtGui.QColor(r, g, b, a)))
                painter.drawPolygon(QtGui.QPolygonF(poly_pts))

        for m in dlg.manual_cavities:
            draw_shape(m['kind'], m['params'], 40, 220, 80)     # green = finalized

        if dlg.draw_preview is not None:
            draw_shape(dlg.draw_preview['kind'], dlg.draw_preview['params'],
                       255, 60, 60, 170)                         # red = live drag

        painter.end()


def _ray_plane_hit(
    origin: np.ndarray, direction: np.ndarray,
    normal: np.ndarray, point_on_plane: np.ndarray,
) -> Optional[np.ndarray]:
    """Intersect a world-space ray with an (unbounded) plane.

    Unlike ``MeshSurfacePicker.pick_surface_at``, this does not require the
    hit to land inside any particular triangle — used while dragging out a
    manually-drawn cavity marker, since the shape can grow past the seed
    triangle's own boundary.
    """
    denom = float(direction @ normal)
    if abs(denom) < 1e-9:
        return None

    t = float((point_on_plane - origin) @ normal) / denom
    if t < 0.0:
        return None

    return origin + t * direction


class _SurfaceSelectFilter(QtCore.QObject):
    """
    Event filter installed on the inner canvas
    to intercept clicks for surface picking, and (while ``dialog.draw_mode``
    is set) press/drag/release for manually drawing a circle or rectangle
    cavity marker on a selected terminal plane.
    """

    def __init__(self, dialog: "HousingEditorDialog"):
        super().__init__(dialog.canvas._canvas)
        self._dialog = dialog
        self._is_moved = False

        dialog.canvas._canvas.installEventFilter(self)

    # ── manual draw mode ─────────────────────────────────────────────────────

    def _target_plane(self) -> tuple:
        dlg = self._dialog
        g = dlg.draw_group
        if not (0 <= g < len(dlg.term_plane_seeds)):
            return None, None

        seed = dlg.term_plane_seeds[g]
        if not (0 <= seed < len(dlg.surfaces)):
            return None, None

        surf = dlg.surfaces[seed]
        normal = np.asarray(surf.normal, dtype=np.float64)
        normal /= np.linalg.norm(normal) + 1e-12
        point = normal * float(surf.plane_dist)
        return normal, point

    def _ray_at(self, event: QtGui.QMouseEvent):
        pos = event.position().toPoint()
        return self._dialog._picker.compute_ray_world(pos.x(), pos.y())  # NOQA

    def _start_draw(self, event: QtGui.QMouseEvent) -> None:
        dlg = self._dialog
        normal, point = self._target_plane()
        if normal is None:
            return

        origin, direction = self._ray_at(event)
        if origin is None:
            return

        hit = _ray_plane_hit(origin, direction, normal, point)
        if hit is None:
            return

        u, v = _analysis.plane_frame(normal)
        dlg._draw_center = hit
        dlg._draw_normal = normal
        dlg._draw_u = u
        dlg._draw_v = v
        dlg._draw_active = True
        dlg.draw_preview = dict(
            kind=dlg.draw_mode,
            params=dict(
                normal=normal.astype(np.float32), u=u.astype(np.float32),
                v=v.astype(np.float32), center=hit.astype(np.float32),
                radius=0.0, half_w=0.0, half_h=0.0))

        if dlg.surface_overlay is not None:
            dlg.surface_overlay.update()

    def _update_draw(self, event: QtGui.QMouseEvent) -> None:
        dlg = self._dialog
        if dlg._draw_center is None:
            return

        origin, direction = self._ray_at(event)
        if origin is None:
            return

        hit = _ray_plane_hit(origin, direction, dlg._draw_normal, dlg._draw_center)
        if hit is None:
            return

        delta = hit - dlg._draw_center
        du = float(delta @ dlg._draw_u)
        dv = float(delta @ dlg._draw_v)
        dlg.draw_preview = dict(
            kind=dlg.draw_mode,
            params=dict(
                normal=dlg._draw_normal.astype(np.float32),
                u=dlg._draw_u.astype(np.float32), v=dlg._draw_v.astype(np.float32),
                center=dlg._draw_center.astype(np.float32),
                radius=float(np.hypot(du, dv)), half_w=abs(du), half_h=abs(dv)))

        if dlg.surface_overlay is not None:
            dlg.surface_overlay.update()

    def _finish_draw(self) -> None:
        dlg = self._dialog
        preview = dlg.draw_preview

        dlg._draw_active = False
        dlg._draw_center = None
        dlg._draw_normal = None
        dlg._draw_u = None
        dlg._draw_v = None

        min_size = 0.05
        if preview is not None:
            p = preview['params']
            if max(p['radius'], p['half_w'], p['half_h']) >= min_size:
                dlg.manual_cavities.append(preview)
                n = len(dlg.manual_cavities)
                dlg._set_status(
                    f'{n} cavity shape{"s" if n != 1 else ""} drawn manually.'
                    f' Run Analyze when ready.')
            else:
                dlg._set_status('Draw too small — discarded.')

        dlg.draw_preview = None
        dlg.draw_mode = None
        dlg.draw_group = -1

        if dlg.surface_overlay is not None:
            dlg.surface_overlay.update()

    # ── event filter ─────────────────────────────────────────────────────────

    def eventFilter(self, obj, event: QtGui.QMouseEvent):
        dlg = self._dialog
        t = event.type()

        if dlg.draw_mode is not None:
            if t == QtCore.QEvent.Type.MouseButtonPress:
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    self._start_draw(event)
                    return True
            elif t == QtCore.QEvent.Type.MouseMove:
                if dlg._draw_active:
                    self._update_draw(event)
                    return True
            elif t == QtCore.QEvent.Type.MouseButtonRelease:
                if (event.button() == QtCore.Qt.MouseButton.LeftButton and
                        dlg._draw_active):
                    self._finish_draw()
                    return True
            return False

        if t == QtCore.QEvent.Type.MouseButtonPress:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._is_moved = False

        elif t == QtCore.QEvent.Type.MouseMove:
            self._is_moved = True

        elif t == QtCore.QEvent.Type.MouseButtonRelease:
            if (
                not self._is_moved and
                event.button() == QtCore.Qt.MouseButton.LeftButton and
                dlg.select_mode is not None and
                dlg.surfaces
            ):

                pos = event.position().toPoint()
                idx = dlg.pick_surface_at(pos.x(), pos.y())
                if idx >= 0:
                    dlg.assign_surface(idx)

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
        self.surfaces: list = []
        self._picker: Optional[_MeshSurfacePicker] = None
        self.select_mode: Optional[str] = None
        # Plane groups: each entry is a list of surface indices on one clicked plane.
        self.wire_plane_groups: list[list[int]] = []
        self.term_plane_groups: list[list[int]] = []
        # Seed surface index per group — used to re-expand when tolerance changes.
        self.wire_plane_seeds: list[int] = []
        self.term_plane_seeds: list[int] = []
        # Per-group sets of surfaces the user manually removed; excluded from re-expansion.
        self.wire_plane_excludes: list[set[int]] = []
        self.term_plane_excludes: list[set[int]] = []
        # Plane distance tolerance for coplanar grouping.
        self.plane_tol: float = 0.05
        # Individual terminal surfaces (Add Terminal mode)
        self.terminal_surf_idxs: list[int] = []
        self.terminal_surf_colors: dict[int, tuple[float, float, float]] = {}
        self.terminal_overrides: dict[int, str] = {}
        self.term_color_idx: int = 0
        # Tree selection: which group and which surface within it are highlighted.
        # plane_sel_surf = -1 means the whole group is highlighted.
        self.plane_sel_group: int = -1
        self.plane_sel_surf: int = -1
        # Surfaces highlighted because the matching cavity tab is selected.
        # -1 = none (cavity loaded from DB has no session-time surface index).
        self.selected_cavity_wire_si: int = -1
        self.selected_cavity_term_si: int = -1
        self.length_factor: float = 1.0
        self.surface_filter: Optional[_SurfaceSelectFilter] = None

        # ── manual cavity drawing (single-plane housings) ──────────────────────
        # Draw a circle/rect directly on a selected terminal plane when the
        # housing has no distinct recessed mesh surface per cavity.
        self.draw_mode: Optional[str] = None       # 'circle' | 'rect' | None
        self.draw_group: int = -1                  # term_plane_groups index being drawn on
        self.draw_preview: Optional[dict] = None    # live params while dragging
        self._draw_active: bool = False             # button currently held
        self._draw_center: Optional[np.ndarray] = None
        self._draw_normal: Optional[np.ndarray] = None
        self._draw_u: Optional[np.ndarray] = None
        self._draw_v: Optional[np.ndarray] = None
        # Finalized manual draws: [{'kind': 'circle'|'rect', 'params': {...}}]
        # params schema matches connector_analysis.classify_loop's output.
        self.manual_cavities: list[dict] = []

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
        tb_layout.addSpacing(12)

        self._tol_label = QtWidgets.QLabel('Tol: 0.05', toolbar)
        self._tol_slider = QtWidgets.QSlider(
            QtCore.Qt.Orientation.Horizontal, toolbar)
        self._tol_slider.setRange(1, 50)   # 0.01 – 0.50 in 0.01 steps
        self._tol_slider.setValue(5)        # default 0.05
        self._tol_slider.setFixedWidth(100)
        tb_layout.addWidget(self._tol_label)
        tb_layout.addWidget(self._tol_slider)
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
        self._tol_slider.valueChanged.connect(self._on_tol_changed)

        # ── plane tree side-panel (shown while in wire/terminal_plane mode) ───
        self.plane_list_panel = PlaneTreePanel(self.panel)
        self.plane_list_panel.selectionChanged.connect(self._on_plane_sel_changed)
        self.plane_list_panel.removeRequested.connect(self._on_plane_remove)
        self.plane_list_panel.accepted.connect(self._on_plane_accepted)
        self.plane_list_panel.addManualRequested.connect(self._on_add_manual_cavity)

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
        h_layout.addWidget(self.plane_list_panel)  # shown in wire/terminal_plane mode
        h_layout.addWidget(self.analysis_panel)    # shown/hidden by load()
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

        self.cavity_panel.cavitySelected.connect(self._on_cavity_selected)

        # Install surface-picking event filter on the inner GL widget
        self.surface_filter = _SurfaceSelectFilter(self)
        self.surface_overlay = SurfaceOverlay(self.canvas._canvas, self)

        # Housing3D pre-bakes model.angle3d / model.position3d into the VBO so
        # its own position/angle/scale are identity.  MeshSurfacePicker therefore
        # works in world space — no additional transform is applied to the ray.
        self._picker = _MeshSurfacePicker(self.housing.obj3d, self.canvas)
        self.vertices = self._picker.vertices   # (N*3, 3) float64, world space
        self.surfaces = self._picker.surfaces   # MeshSurfacePicker.Surface list
        self._set_status(
            f'Mesh loaded — {len(self.surfaces)} surfaces detected')
        self.update()

    # ── surface picking ───────────────────────────────────────────────────────

    def pick_surface_at(self, px: int, py: int) -> int:
        if self._picker is None:
            return -1
        idx, _ = self._picker.pick_surface_at(px, py)
        return idx

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
            self.plane_sel_group = -1
            self.plane_sel_surf = -1

            for btn in self._mode_btns:
                if btn is not button:
                    btn.setChecked(False)

            hints = {
                'wire': 'Click a wire-side plane to add it — click a selected plane again to remove',
                'terminal_plane': 'Click a terminal plane to add it — click again to remove',
                'terminal': 'Click individual terminal recesses to add/remove',
            }
            self._set_status(hints.get(mode, ''))

            if mode == 'wire':
                self._reload_plane_tree(is_wire=True)
            elif mode == 'terminal_plane':
                self._reload_plane_tree(is_wire=False)
            else:
                self.plane_list_panel.hide()
        else:
            self.select_mode = None
            self.plane_sel_group = -1
            self.plane_sel_surf = -1
            self.plane_list_panel.hide()
            self._set_status('')

    def _on_add_manual_cavity(self, group_idx: int, kind: str) -> None:
        self.draw_mode = kind
        self.draw_group = group_idx
        self._draw_active = False
        self.draw_preview = None
        shape_name = 'circle' if kind == 'circle' else 'rectangle'
        self._set_status(
            f'Click and drag on the plane to draw the {shape_name} cavity.')

    def assign_surface(self, idx: int) -> None:
        if self.select_mode in ('wire', 'terminal_plane'):
            self._toggle_plane_group(idx)

        elif self.select_mode == 'terminal':
            if idx in self.terminal_surf_idxs:
                self.terminal_surf_idxs.remove(idx)
                self.terminal_surf_colors.pop(idx, None)
                self._set_status(
                    f'Terminal removed ({len(self.terminal_surf_idxs)} selected)')
            else:
                color = self._next_color()
                self.terminal_surf_idxs.append(idx)
                self.terminal_surf_colors[idx] = color
                self._set_status(
                    f'Terminal added ({len(self.terminal_surf_idxs)} selected)')

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    def _coplanar_idxs(self, idx: int) -> list[int]:
        ref = self.surfaces[idx]
        tol = self.plane_tol
        return [
            i for i, s in enumerate(self.surfaces)
            if (float(np.dot(s.normal, ref.normal)) > 0.98
                and abs(s.plane_dist - ref.plane_dist) < tol)
        ]

    def _toggle_plane_group(self, idx: int) -> None:
        is_wire = self.select_mode == 'wire'
        groups = self.wire_plane_groups if is_wire else self.term_plane_groups
        seeds = self.wire_plane_seeds if is_wire else self.term_plane_seeds
        excludes = self.wire_plane_excludes if is_wire else self.term_plane_excludes
        label = 'Wire' if is_wire else 'Terminal'

        plane_idxs = self._coplanar_idxs(idx)
        idx_set = set(plane_idxs)

        # Find if the clicked surface already belongs to any existing group.
        existing = next(
            (gi for gi, g in enumerate(groups) if idx in g or idx_set.intersection(g)),
            None)

        if existing is not None:
            groups.pop(existing)
            seeds.pop(existing)
            excludes.pop(existing)
            self.plane_sel_group = -1
            self.plane_sel_surf = -1
            n = len(groups)
            self._set_status(
                f'{label}: plane removed ({n} plane{"s" if n != 1 else ""} selected)')
        else:
            groups.append(plane_idxs)
            seeds.append(idx)
            excludes.append(set())
            n = len(groups)
            self._set_status(
                f'{label}: {len(plane_idxs)} surface'
                f'{"s" if len(plane_idxs) != 1 else ""} added'
                f' ({n} plane{"s" if n != 1 else ""} total)')

        self._reload_plane_tree(is_wire)

    def _reload_plane_tree(self, is_wire: bool) -> None:
        groups = self.wire_plane_groups if is_wire else self.term_plane_groups
        label = 'Wire Surfaces' if is_wire else 'Terminal Surfaces'
        self.plane_list_panel.load(
            groups, self.surfaces, label, is_terminal=not is_wire)

    # ── analysis ──────────────────────────────────────────────────────────────

    def _manual_covered_group_idxs(self) -> set:
        """term_plane_groups indices that are coplanar with a manually-drawn
        cavity — "the original single surface is ignored because the cavity
        was added manually."  Geometric, not index-based, so it stays correct
        even as groups are added/removed independently of manual draws.
        """
        tol = self.plane_tol
        covered = set()
        for m in self.manual_cavities:
            n = np.asarray(m['params']['normal'], dtype=np.float64)
            n /= np.linalg.norm(n) + 1e-12
            d = float(np.asarray(m['params']['center'], dtype=np.float64) @ n)
            for gi, seed in enumerate(self.term_plane_seeds):
                s = self.surfaces[seed]
                if (float(np.dot(s.normal, n)) > 0.98 and
                        abs(float(s.plane_dist) - d) < tol):
                    covered.add(gi)
        return covered

    @staticmethod
    def _group_containing(idx: int, groups: list) -> list:
        """Return the coplanar-surface group containing ``idx``, or ``[idx]``
        if it wasn't picked as part of a plane group (e.g. an individually
        toggled terminal surface)."""
        for grp in groups:
            if idx in grp:
                return list(grp)
        return [idx]

    @staticmethod
    def _match_wire_surface(n_t, c_t, wire_surf_items, wire_centroids):
        """Find the wire surface spatially closest to a terminal in the
        cross-sectional plane (perpendicular to the cavity axis).  This
        ensures each terminal exits through its own wire plane even when
        multiple wire planes exist at different depths.
        """
        c_t_perp = c_t - float(np.dot(c_t, n_t)) * n_t

        best_ws_si, best_ws = wire_surf_items[0]
        best_wc = wire_centroids[0]
        best_d = float('inf')
        for (wsi, ws), wc in zip(wire_surf_items, wire_centroids):
            c_w_perp = wc - float(np.dot(wc, n_t)) * n_t
            d = float(np.linalg.norm(c_t_perp - c_w_perp))
            if d < best_d:
                best_d = d
                best_ws_si = wsi
                best_ws = ws
                best_wc = wc

        return best_ws_si, best_ws, best_wc

    def run_analysis(self) -> None:
        if not self.wire_plane_groups:
            self._set_status('Select the wire side first.')
            return

        covered_groups = self._manual_covered_group_idxs()
        all_terminal = [
            i for gi, grp in enumerate(self.term_plane_groups)
            if gi not in covered_groups
            for i in grp
        ]
        for i in self.terminal_surf_idxs:
            if i not in all_terminal:
                all_terminal.append(i)

        if not all_terminal and not self.manual_cavities:
            self._set_status('Select at least one terminal plane first.')
            return

        # Flatten all selected wire surfaces, keeping their picker surface index.
        wire_surf_items: list[tuple[int, object]] = [
            (si, self.surfaces[si])
            for grp in self.wire_plane_groups
            for si in grp
        ]
        wire_centroids = [
            _analysis.surface_centroid(ws, self.vertices)
            for _, ws in wire_surf_items
        ]

        results = []
        for ti in all_terminal:
            term_surf = self.surfaces[ti]
            n_t = term_surf.normal.astype(np.float64)
            n_t /= np.linalg.norm(n_t) + 1e-12

            c_t = _analysis.surface_centroid(term_surf, self.vertices)
            best_ws_si, best_ws, best_wc = self._match_wire_surface(
                n_t, c_t, wire_surf_items, wire_centroids)

            try:
                kind, params, verts, _norms = _analysis.generate_terminal_geometry(
                    term_surf, best_ws, self.vertices,
                    kind_override=self.terminal_overrides.get(ti),
                    length_factor=self.length_factor,
                )
            except Exception:  # NOQA
                continue

            d_start = term_surf.plane_dist
            d_full = float(np.dot(best_wc, n_t))
            d_end = d_start + (d_full - d_start) * self.length_factor

            center = np.array(params['center'], dtype=np.float64)
            u_ax, v_ax = _analysis.plane_frame(n_t)
            proj_u = float(center @ u_ax)
            proj_v = float(center @ v_ax)
            wire_indices = self._group_containing(best_ws_si, self.wire_plane_groups)
            term_indices = self._group_containing(ti, self.term_plane_groups)
            results.append(
                (kind, params, d_start, d_end, proj_u, proj_v, verts,
                 best_ws_si, ti, False, wire_indices, term_indices)
            )

        # Manually-drawn cavities: kind/params are already known (from the
        # user's drag), so skip generate_terminal_geometry's mesh-boundary
        # shape detection and go straight to generate_hole_geometry — only
        # the matching wire-side plane still needs to be found, to compute
        # the cavity's length.
        for m in self.manual_cavities:
            params = dict(m['params'])
            n_t = np.asarray(params['normal'], dtype=np.float64)
            n_t /= np.linalg.norm(n_t) + 1e-12
            c_t = np.asarray(params['center'], dtype=np.float64)

            best_ws_si, _best_ws, best_wc = self._match_wire_surface(
                n_t, c_t, wire_surf_items, wire_centroids)

            d_start = float(c_t @ n_t)
            d_full = float(best_wc @ n_t)
            d_end = d_start + (d_full - d_start) * self.length_factor

            verts, _norms = _analysis.generate_hole_geometry(
                m['kind'], params, d_start, d_end)

            u_ax, v_ax = _analysis.plane_frame(n_t)
            proj_u = float(c_t @ u_ax)
            proj_v = float(c_t @ v_ax)
            wire_indices = self._group_containing(best_ws_si, self.wire_plane_groups)
            results.append(
                (m['kind'], params, d_start, d_end, proj_u, proj_v, verts,
                 best_ws_si, -1, True, wire_indices, [])
            )

        if not results:
            self._set_status('Analysis produced no results.')
            return

        # Sort: top-to-bottom (decreasing proj_v), left-to-right (increasing proj_u)
        results.sort(key=lambda r: (-r[5], r[4]))

        # Build preview items — names continue from existing cavity count
        existing = len(self.cavity_panel.cavities) if self.cavity_panel else 0
        items = []
        for i, (kind, params, d_start, d_end, _pu, _pv, verts, wire_si,
                term_si, is_manual, wire_indices, term_indices) in enumerate(results):
            item = _analysis_panel.AnalysisItem(
                name=str(existing + i + 1),
                kind=kind,
                params=dict(params),   # copy so edits don't alias the source
                d_start=d_start,
                d_end=d_end,
                verts=verts,
                wire_surf_si=wire_si,
                term_surf_si=term_si,
                is_manual=is_manual,
                wire_surf_indices=wire_indices,
                term_surf_indices=term_indices,
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

    def _on_tol_changed(self, value: int) -> None:
        self.plane_tol = value / 100.0
        self._tol_label.setText(f'Tol: {self.plane_tol:.2f}')
        self._reexpand_all_groups()

    def _reexpand_all_groups(self) -> None:
        for i, seed in enumerate(self.wire_plane_seeds):
            expanded = self._coplanar_idxs(seed)
            self.wire_plane_groups[i] = [
                si for si in expanded if si not in self.wire_plane_excludes[i]]
        for i, seed in enumerate(self.term_plane_seeds):
            expanded = self._coplanar_idxs(seed)
            self.term_plane_groups[i] = [
                si for si in expanded if si not in self.term_plane_excludes[i]]
        if self.select_mode == 'wire':
            self._reload_plane_tree(is_wire=True)
        elif self.select_mode == 'terminal_plane':
            self._reload_plane_tree(is_wire=False)
        if self.surface_overlay is not None:
            self.surface_overlay.update()

    def _clear_terminals(self) -> None:
        self.term_plane_groups = []
        self.term_plane_seeds = []
        self.term_plane_excludes = []
        self.terminal_surf_idxs.clear()
        self.terminal_surf_colors.clear()
        self.terminal_overrides.clear()
        self.term_color_idx = 0
        self.plane_sel_group = -1
        self.plane_sel_surf = -1
        self.manual_cavities = []
        self.draw_mode = None
        self.draw_group = -1
        self.draw_preview = None
        self._draw_active = False
        self._draw_center = None
        self._draw_normal = None
        self._draw_u = None
        self._draw_v = None

        for btn in self._mode_btns:
            btn.setChecked(False)

        self.select_mode = None
        self.plane_list_panel.hide()

        if self.surface_overlay is not None:
            self.surface_overlay.update()

        self._set_status('Terminals cleared.')

    def _clear_all(self) -> None:
        self.wire_plane_groups = []
        self.wire_plane_seeds = []
        self.wire_plane_excludes = []
        self.plane_sel_group = -1
        self.plane_sel_surf = -1
        self._clear_terminals()
        self._set_status('All selections cleared.')

    # ── plane tree event handlers ─────────────────────────────────────────────

    def _on_plane_sel_changed(self, g: int, s: int) -> None:
        self.plane_sel_group = g
        self.plane_sel_surf = s
        if self.surface_overlay is not None:
            self.surface_overlay.update()

    def _on_plane_remove(self, g: int, s: int) -> None:
        is_wire = self.select_mode == 'wire'
        groups = self.wire_plane_groups if is_wire else self.term_plane_groups
        seeds = self.wire_plane_seeds if is_wire else self.term_plane_seeds
        excludes = self.wire_plane_excludes if is_wire else self.term_plane_excludes

        if g < 0 or g >= len(groups):
            return

        if s < 0:
            # Remove the whole plane group
            groups.pop(g)
            seeds.pop(g)
            excludes.pop(g)
        else:
            # Remove just the one surface; remember it so the tolerance slider
            # re-expansion doesn't bring it back.
            if s < len(groups[g]):
                removed_si = groups[g].pop(s)
                excludes[g].add(removed_si)
                if not groups[g]:
                    groups.pop(g)
                    seeds.pop(g)
                    excludes.pop(g)

        self.plane_sel_group = -1
        self.plane_sel_surf = -1
        self._reload_plane_tree(is_wire)
        if self.surface_overlay is not None:
            self.surface_overlay.update()

    def _on_plane_accepted(self) -> None:
        for btn in self._mode_btns:
            btn.setChecked(False)
        self.select_mode = None
        self.plane_sel_group = -1
        self.plane_sel_surf = -1
        self.plane_list_panel.hide()
        self._set_status('')
        if self.surface_overlay is not None:
            self.surface_overlay.update()

    def _on_cavity_selected(self, wire_si: int, term_si: int) -> None:
        self.selected_cavity_wire_si = wire_si
        self.selected_cavity_term_si = term_si
        if self.surface_overlay is not None:
            self.surface_overlay.update()

    def _set_status(self, msg: str) -> None:
        self._status_label.setText(msg)

    # ── boilerplate (unchanged from original) ─────────────────────────────────

    def closeEvent(self, event):
        if self._picker is not None:
            self._picker.cleanup()
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
