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
from . import tree_panels as _tree_panels
from .. import dialog_base as _dialog_base
from ....gl import canvas_3d as _canvas_3d
from ....utils.mesh_surface_picker import MeshSurfacePicker as _MeshSurfacePicker
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .... import ui as _ui


Config = _dialog_config.Config


@_check_types.do
def _shape_polygon_points(kind: str, params: dict, segments: int = 24) -> list:
    """
    Build world-space outline points for a manually-drawn cavity marker.

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


class SurfaceOverlay(QtWidgets.QWidget):
    """Transparent child widget that projects selected surfaces as 2D highlights."""

    @_check_types.do
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

    @_check_types.do
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.Resize:
            self.setGeometry(QtCore.QRect(0, 0, obj.width(), obj.height()))

        return False

    @_check_types.do
    def paintEvent(self, event):
        dlg = self._dialog
        if not dlg.surfaces or dlg.vertices is None:
            return

        camera = dlg.canvas._canvas.camera  # NOQA

        if camera.clip is None or camera.viewport is None:
            return

        # camera.clip = projection @ modelview, already computed each frame.
        # viewport is in physical pixels; divide by DPR for logical QPainter coords.
        clip_mat = camera.clip.astype(np.float64)
        vx, vy, vw, vh = camera.viewport
        dpr = dlg.canvas._canvas.devicePixelRatio()  # NOQA

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)

        verts = dlg.vertices.reshape(-1, 3).astype(np.float64)

        @_check_types.do
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

        @_check_types.do
        def draw_surf(surf_, r_, g_, b_, alpha=80):
            painter.setBrush(QtGui.QBrush(QtGui.QColor(r_, g_, b_, alpha)))
            for ti_ in surf_.tri_indices:
                pts_ = [project(verts[3 * ti_ + k]) for k in range(3)]

                if all(p is not None for p in pts_):
                    painter.drawPolygon(QtGui.QPolygonF(pts_))

        # --- wire plane groups (orange) --- always shown, independent of
        # select_mode -- both trees are visible/interactive simultaneously
        # now, not gated to whichever pick mode is active.
        wire_active = bool(dlg.wire_sel_surf_idxs)

        for group in dlg.wire_plane_groups:
            for si in group:
                if not wire_active:
                    draw_surf(dlg.surfaces[si], 255, 140, 0, 80)
                elif si in dlg.wire_sel_surf_idxs:
                    # selected → bright red
                    draw_surf(dlg.surfaces[si], 255, 40, 40, 200)
                else:
                    # unselected → dim orange
                    draw_surf(dlg.surfaces[si], 255, 140, 0, 20)

        # --- terminal plane groups (blue) ---
        term_active = bool(dlg.term_sel_surf_idxs)

        for group in dlg.term_plane_groups:
            for si in group:
                if not term_active:
                    draw_surf(dlg.surfaces[si], 51, 153, 255, 80)
                elif si in dlg.term_sel_surf_idxs:
                    # selected → bright red
                    draw_surf(dlg.surfaces[si], 255, 40, 40, 200)
                else:
                    # unselected → dim blue
                    draw_surf(dlg.surfaces[si], 51, 153, 255, 20)

        # --- selected cavity surface highlights
        # (only when not in a pick mode) ---
        if dlg.select_mode is None:
            w_si = dlg.selected_cavity_wire_si
            t_si = dlg.selected_cavity_term_si

            if 0 <= w_si < len(dlg.surfaces):
                # yellow = wire
                draw_surf(dlg.surfaces[w_si], 255, 220, 0, 120)
            if 0 <= t_si < len(dlg.surfaces):
                # cyan = terminal
                draw_surf(dlg.surfaces[t_si], 0, 210, 255, 120)

        # --- individual terminals (per-surface colours) ---
        for idx in dlg.terminal_surf_idxs:
            surf = dlg.surfaces[idx]
            rf, gf, bf = dlg.terminal_surf_colors.get(idx, (0.5, 0.5, 0.5))
            draw_surf(surf, int(rf * 255), int(gf * 255), int(bf * 255))

        # --- pending (not yet accepted) cavity overlays ---
        items = dlg.cavity_tree_panel.items()
        if items:
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
        @_check_types.do
        def draw_shape(kind, params, r_, g_, b_, a_=140):
            poly_pts = [project(pt) for pt in _shape_polygon_points(kind, params)]
            if all(p is not None for p in poly_pts):
                painter.setBrush(QtGui.QBrush(QtGui.QColor(r_, g_, b_, a_)))
                painter.drawPolygon(QtGui.QPolygonF(poly_pts))

        for m in dlg.manual_cavities:
            # green = finalized
            draw_shape(m['kind'], m['params'], 40, 220, 80)

        if dlg.draw_preview is not None:
            # red = live drag
            draw_shape(dlg.draw_preview['kind'],
                       dlg.draw_preview['params'],
                       255, 60, 60, 170)

        painter.end()


@_check_types.do
def _ray_plane_hit(
    origin: np.ndarray, direction: np.ndarray,
    normal: np.ndarray, point_on_plane: np.ndarray,
) -> Optional[np.ndarray]:
    """
    Intersect a world-space ray with an (unbounded) plane.

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

    @_check_types.do
    def __init__(self, dialog: "HousingEditorDialog"):
        super().__init__(dialog.canvas._canvas)  # NOQA
        self._dialog = dialog
        self._is_moved = False

        dialog.canvas._canvas.installEventFilter(self)  # NOQA

    # ── manual draw mode ─────────────────────────────────────────────────────

    @_check_types.do
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

    @_check_types.do
    def _ray_at(self, event: QtGui.QMouseEvent):
        pos = event.position().toPoint()

        return self._dialog._picker.compute_ray_world(pos.x(), pos.y())  # NOQA

    @_check_types.do
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

    @_check_types.do
    def _update_draw(self, event: QtGui.QMouseEvent) -> None:
        dlg = self._dialog
        if dlg._draw_center is None:  # NOQA
            return

        origin, direction = self._ray_at(event)
        if origin is None:
            return

        hit = _ray_plane_hit(origin, direction,
                             dlg._draw_normal, dlg._draw_center)  # NOQA
        if hit is None:
            return

        delta = hit - dlg._draw_center  # NOQA
        du = float(delta @ dlg._draw_u)  # NOQA
        dv = float(delta @ dlg._draw_v)  # NOQA
        dlg.draw_preview = dict(
            kind=dlg.draw_mode,
            params=dict(
                normal=dlg._draw_normal.astype(np.float32),  # NOQA
                u=dlg._draw_u.astype(np.float32),   # NOQA
                v=dlg._draw_v.astype(np.float32),  # NOQA
                center=dlg._draw_center.astype(np.float32),  # NOQA
                radius=float(np.hypot(du, dv)), half_w=abs(du), half_h=abs(dv)))

        if dlg.surface_overlay is not None:
            dlg.surface_overlay.update()

    @_check_types.do
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
                dlg.term_tree_panel.set_info(
                    f'{n} cavity shape{"s" if n != 1 else ""} drawn manually.'
                    f' Run Analyze when ready.')
            else:
                dlg.term_tree_panel.set_info('Draw too small — discarded.')

        dlg.draw_preview = None
        dlg.draw_mode = None
        dlg.draw_group = -1

        if dlg.surface_overlay is not None:
            dlg.surface_overlay.update()

    # ── event filter ─────────────────────────────────────────────────────────

    _QtEvents = (QtGui.QMouseEvent | QtCore.QChildEvent | QtCore.QEvent |
                 QtCore.QDynamicPropertyChangeEvent | QtGui.QMoveEvent |
                 QtGui.QResizeEvent | QtGui.QPaintEvent | QtGui.QShowEvent |
                 QtGui.QEnterEvent | QtGui.QHoverEvent | QtGui.QInputMethodQueryEvent |
                 QtGui.QFocusEvent | QtGui.QContextMenuEvent | QtGui.QWheelEvent |
                 QtGui.QKeyEvent | QtGui.QHideEvent)

    @_check_types.do
    def eventFilter(self, obj, event: QtCore.QEvent | QtGui.QMouseEvent):
        dlg = self._dialog
        t = event.type()

        if dlg.draw_mode is not None:
            if t == QtCore.QEvent.Type.MouseButtonPress:
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    self._start_draw(event)

                    return True

            elif t == QtCore.QEvent.Type.MouseMove:
                if dlg._draw_active:  # NOQA
                    self._update_draw(event)

                    return True

            elif t == QtCore.QEvent.Type.MouseButtonRelease:
                if (
                    event.button() == QtCore.Qt.MouseButton.LeftButton and
                    dlg._draw_active  # NOQA
                ):
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
    """
    Housing editor with integrated surface-picking for cavity detection.
    """

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame"):
        self.db_obj = None

        _dialog_base.BaseDialog.__init__(
            self, parent, 'Edit Housing', size=(1200, 900))

        # OK is disabled only while BOTH: the Cavity Detection tab is the
        # one being viewed, AND Accept Cavities hasn't been clicked yet this
        # session -- viewing any other tab (Cavities/Accessories) enables
        # it immediately, since there's no picking work in view to force a
        # decision on; once Accept Cavities is clicked it's a permanent,
        # literal one-time gate regardless of which tab is viewed after
        # that (see _on_accept_cavities / _on_controls_tab_changed).
        self._cavities_accepted: bool = False
        self._ok_button = self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setEnabled(False)

        w = Config.editor_3d.virtual_canvas.width
        h = Config.editor_3d.virtual_canvas.height

        self._obj_handler = None

        # This dialog's canvas is its own self-contained scene (the
        # housing being edited -- plus its HousingPegboard/
        # HousingSchematic facades, which need editor_pegboard/
        # editor_schematic bounds views even though only the 3D canvas
        # is ever shown), not a view into the real mainframe's
        # editor_3d/editor_pegboard/editor_schematic canvases -- it must
        # not share the real mainframe's pooled AABB/OBB arrays, or
        # objects added here would get mixed into the live editors'
        # picking pools while this dialog is open, and left there as a
        # stale entry after it closes.
        from .... import bounds as _bounds
        self._bounds_manager = _bounds.Manager()

        # Passes *self* (not self.panel) as the canvas's "mainframe" --
        # Qt widget-parenting is unaffected (the layout's addWidget()
        # below reparents the canvas to self.panel regardless), but
        # anything the canvas builds on its own (e.g. FocalPoint, created
        # in Canvas.initializeGL()) resolves canvas.mainframe.editor3d
        # through this dialog's own editor3d/context/config/Refresh
        # forwarding -- self.panel is a plain QWidget with none of that.
        self.canvas = _canvas_3d.Canvas3D(
            self, Config.editor_3d, size=(w, h))

        self.controls = QtWidgets.QTabWidget(self.panel)

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
        # Plane groups: each entry is a list of
        # surface indices on one clicked plane.
        self.wire_plane_groups: list[list[int]] = []
        self.term_plane_groups: list[list[int]] = []
        # Seed surface index per group — used to
        # re-expand when tolerance changes.
        self.wire_plane_seeds: list[int] = []
        self.term_plane_seeds: list[int] = []
        # Per-group sets of surfaces the user manually removed;
        # excluded from re-expansion.
        self.wire_plane_excludes: list[set[int]] = []
        self.term_plane_excludes: list[set[int]] = []
        # Plane distance tolerance for coplanar grouping.
        self.plane_tol: float = 0.05
        # Individual terminal surfaces (Add Terminal mode)
        self.terminal_surf_idxs: list[int] = []
        self.terminal_surf_colors: dict[int, tuple[float, float, float]] = {}
        self.terminal_overrides: dict[int, str] = {}
        self.term_color_idx: int = 0
        # Tree selection: global surface indices currently highlighted in
        # each tree, independent of one another -- both trees are visible
        # and interactive simultaneously now, not mode-gated.
        self.wire_sel_surf_idxs: set[int] = set()
        self.term_sel_surf_idxs: set[int] = set()
        # Per-surface area cache (world-space, from MeshSurfacePicker
        # surfaces) -- cheap to compute but shared by every plane-tree
        # reload and the "Group by Size" view, so memoize it.
        self._surface_area_cache: dict[int, float] = {}
        # Surfaces highlighted because the matching cavity tab is selected.
        # -1 = none (cavity loaded from DB has no session-time surface index).
        self.selected_cavity_wire_si: int = -1
        self.selected_cavity_term_si: int = -1
        self.length_factor: float = 1.0
        self.surface_filter: Optional[_SurfaceSelectFilter] = None

        # ── manual cavity drawing (single-plane housings) ──────────────────────
        # Draw a circle/rect directly on a selected terminal plane when the
        # housing has no distinct recessed mesh surface per cavity.

        # 'circle' | 'rect' | None
        self.draw_mode: Optional[str] = None

        # term_plane_groups index being drawn on
        self.draw_group: int = -1

        # live params while dragging
        self.draw_preview: Optional[dict] = None

        # button currently held
        self._draw_active: bool = False
        self._draw_center: Optional[np.ndarray] = None
        self._draw_normal: Optional[np.ndarray] = None
        self._draw_u: Optional[np.ndarray] = None
        self._draw_v: Optional[np.ndarray] = None
        # Finalized manual draws: [{'kind': 'circle'|'rect', 'params': {...}}]
        # params schema matches connector_analysis.classify_loop's output.
        self.manual_cavities: list[dict] = []

        # ── analysis preview state ────────────────────────────────────────────
        self.analysis_selected: int = -1

        # Relocated at the end of __init__ to sit left of the dialog's own
        # OK button, separated from OK/Cancel by a gap, once
        # self.button_box exists.
        self._btn_accept_cavities = QtWidgets.QPushButton('Accept Cavities')
        self._btn_accept_cavities.setStyleSheet(
            'QPushButton { padding: 4px 12px; }')

        self._btn_accept_cavities.clicked.connect(self._on_accept_cavities)

        # ── bottom area: a single always-present notebook. The picking
        # trees live in their own tab ("Cavity Detection") alongside
        # Cavities/Accessories (added later, in SetValue) instead of being
        # swapped away to a separate page -- this lets the user come back
        # to picking after Accept Cavities instead of it being one-way.
        # No hard maximumHeight here: self.controls is now a direct
        # splitter pane below, and a fixed ceiling fights the splitter's
        # own size negotiation -- it can freeze the sash once the pane's
        # natural minimum size gets close to that ceiling. The splitter's
        # initial setSizes(...) call below picks a sane starting split
        # instead; dragging is then unconstrained beyond each pane's own
        # natural minimum size.
        self._picking_page = QtWidgets.QWidget(self.controls)
        picking_layout = QtWidgets.QVBoxLayout(self._picking_page)
        picking_layout.setContentsMargins(4, 4, 4, 4)
        picking_layout.setSpacing(4)

        # Wire/terminal pick mode is no longer toggled by a button here --
        # selecting an item (including the "Click me to add surfaces."
        # placeholder) in the wire or terminal tree itself now arms that
        # side's pick mode (see _on_wire_sel_changed/_on_term_sel_changed).
        settings_row = QtWidgets.QHBoxLayout()

        self._len_label = QtWidgets.QLabel('Length: 100%', self._picking_page)
        self._len_slider = QtWidgets.QSlider(
            QtCore.Qt.Orientation.Horizontal, self._picking_page)

        self._len_slider.setRange(10, 100)
        self._len_slider.setValue(100)
        self._len_slider.setFixedWidth(120)

        settings_row.addWidget(self._len_label)
        settings_row.addWidget(self._len_slider)
        settings_row.addSpacing(12)

        self._tol_label = QtWidgets.QLabel('Tol: 0.05', self._picking_page)

        self._tol_slider = QtWidgets.QSlider(
            QtCore.Qt.Orientation.Horizontal, self._picking_page)

        # 0.01 – 0.50 in 0.01 steps
        self._tol_slider.setRange(1, 50)

        # default 0.05
        self._tol_slider.setValue(5)

        self._tol_slider.setFixedWidth(100)
        settings_row.addWidget(self._tol_label)
        settings_row.addWidget(self._tol_slider)
        settings_row.addStretch(1)

        self._len_slider.valueChanged.connect(self._on_length_changed)
        self._tol_slider.valueChanged.connect(self._on_tol_changed)

        picking_layout.addLayout(settings_row)

        trees_row = QtWidgets.QHBoxLayout()

        self.wire_tree_panel = _tree_panels.PlaneTreePanel(
            self._picking_page, is_terminal=False, caption='Wire-Side Surfaces')
        self.term_tree_panel = _tree_panels.PlaneTreePanel(
            self._picking_page, is_terminal=True, caption='Terminal-Side Surfaces')
        self.cavity_tree_panel = _tree_panels.CavityTreePanel(
            self._picking_page, caption='Detected Cavities')

        arrow_col = QtWidgets.QVBoxLayout()
        arrow_col.addStretch(1)
        self._btn_analyze = QtWidgets.QPushButton('→', self._picking_page)
        self._btn_analyze.setEnabled(False)
        analyze_font = self._btn_analyze.font()
        analyze_font.setPointSize(analyze_font.pointSize() + 8)
        analyze_font.setBold(True)
        self._btn_analyze.setFont(analyze_font)
        self._btn_analyze.setFixedSize(44, 44)
        self._btn_analyze.setToolTip('Analyze')
        arrow_col.addWidget(self._btn_analyze)
        arrow_col.addStretch(1)

        trees_row.addWidget(self.wire_tree_panel, 1)
        trees_row.addWidget(self.term_tree_panel, 1)
        trees_row.addLayout(arrow_col)
        trees_row.addWidget(self.cavity_tree_panel, 1)

        picking_layout.addLayout(trees_row, 1)

        self._edit_panel = _analysis_panel.EditPanel(self._picking_page)
        picking_layout.addWidget(self._edit_panel)

        # First tab added to an empty QTabWidget becomes current immediately
        # (before currentChanged is connected below), so Accept Cavities'
        # initial visibility is set explicitly rather than relying on that
        # first, unobserved signal.
        self.controls.addTab(self._picking_page, 'Cavity Detection')
        self._btn_accept_cavities.setVisible(True)
        self.controls.currentChanged.connect(self._on_controls_tab_changed)

        self.wire_tree_panel.selectionChanged.connect(self._on_wire_sel_changed)
        self.wire_tree_panel.removeRequested.connect(self._on_wire_remove)
        self.wire_tree_panel.removeAllRequested.connect(self._on_remove_all_wire)

        self.term_tree_panel.selectionChanged.connect(self._on_term_sel_changed)
        self.term_tree_panel.removeRequested.connect(self._on_term_remove)
        self.term_tree_panel.addManualRequested.connect(self._on_add_manual_cavity)
        self.term_tree_panel.addTerminalToggled.connect(self._on_add_terminal_toggled)
        self.term_tree_panel.clearTerminalsRequested.connect(self._clear_terminals)

        self.cavity_tree_panel.selectionChanged.connect(
            self._on_cavity_tree_sel_changed)
        self.cavity_tree_panel.removeAllRequested.connect(
            self._on_remove_all_cavities)

        self._edit_panel.itemChanged.connect(self._on_cavity_item_edited)

        self._btn_analyze.clicked.connect(self.run_analysis)

        # ── main layout ───────────────────────────────────────────────────────
        # A draggable sash between the canvas and the notebook below it, so
        # the user can trade canvas height for more room to work in the
        # trees, or vice versa.
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, self.panel)
        splitter.setHandleWidth(3)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.controls)
        # Dragging the sash overrides these, but on an ordinary dialog
        # resize the canvas should absorb the extra/lost space, not the
        # (already height-capped) controls area below it.
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([600, 340])

        v_layout = QtWidgets.QVBoxLayout(self.panel)
        v_layout.addWidget(splitter, 1)

        # ── relocate Accept Cavities next to the dialog's own OK/Cancel ───────
        # BaseDialog.__init__ already built its own bottom row as
        # `root.addWidget(self.button_box)` -- pull button_box back out and
        # rebuild that row as [stretch, Accept Cavities, vline, button_box]
        # so the whole cluster sits at the right edge of the dialog (like
        # OK/Cancel always have), with Accept Cavities just a small ~20px
        # gap (a vertical rule sunk into the middle of it) away from OK --
        # visually separate from the OK/Cancel pair, not clear across the
        # dialog from it.
        accept_sep = QtWidgets.QFrame(self)
        accept_sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        accept_sep.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)

        root_layout = self.layout()
        button_box_idx = root_layout.indexOf(self.button_box)
        root_layout.removeWidget(self.button_box)

        bottom_row = QtWidgets.QHBoxLayout()
        bottom_row.addStretch(1)
        bottom_row.addWidget(self._btn_accept_cavities)
        bottom_row.addSpacing(8)
        bottom_row.addWidget(accept_sep)
        bottom_row.addSpacing(8)
        bottom_row.addWidget(self.button_box)
        root_layout.insertLayout(button_box_idx, bottom_row)

    @property
    @_check_types.do
    def can_select(self) -> bool:
        return self.select_mode not in ('wire', 'terminal_plane', 'terminal')

    # ── SetValue ──────────────────────────────────────────────────────────────

    @_check_types.do
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
        self.surface_overlay = SurfaceOverlay(self.canvas._canvas, self)  # NOQA

        # Housing3D pre-bakes model.angle3d / model.position3d into the VBO so
        # its own position/angle/scale are identity.  MeshSurfacePicker therefore
        # works in world space — no additional transform is applied to the ray.
        self._picker = _MeshSurfacePicker(self.housing.obj3d, self.canvas)

        # (N*3, 3) float64, world space
        self.vertices = self._picker.vertices

        # MeshSurfacePicker.Surface list
        self.surfaces = self._picker.surfaces

        # Populates both trees with their "Click me to add surfaces."
        # placeholder -- without this, the trees start out genuinely empty
        # (no rows at all, placeholder included) and the user would have
        # nothing to click to ever enter wire/terminal pick mode.
        self._reload_wire_tree()
        self._reload_term_tree()

        self.wire_tree_panel.set_info(
            f'Mesh loaded — {len(self.surfaces)} surfaces detected')

        self.update()

    # ── surface picking ───────────────────────────────────────────────────────

    @_check_types.do
    def pick_surface_at(self, px: int, py: int) -> int:
        if self._picker is None:
            return -1

        idx, _ = self._picker.pick_surface_at(px, py)

        return idx

    # ── selection modes ───────────────────────────────────────────────────────

    @_check_types.do
    def _next_color(self) -> tuple[float, float, float]:
        col = _TERMINAL_COLORS[self.term_color_idx % len(_TERMINAL_COLORS)]
        self.term_color_idx += 1

        return col

    @_check_types.do
    def _on_add_terminal_toggled(self, checked: bool) -> None:
        if checked:
            # Clear both plane trees' own selections first, while
            # select_mode still holds whatever it was before -- lets their
            # reentrant selectionChanged handlers (fired by clearSelection()
            # below) correctly notice they're no longer the active mode
            # before this method claims it explicitly.
            self.wire_tree_panel.clear_tree_selection()
            self.term_tree_panel.clear_tree_selection()
            self.select_mode = 'terminal'
            self.wire_tree_panel.set_info('')
            self.term_tree_panel.set_info(
                'Click individual terminal recesses to add/remove')
        else:
            if self.select_mode == 'terminal':
                self.select_mode = None
            self.term_tree_panel.set_info('')

    @_check_types.do
    def _on_add_manual_cavity(self, group_idx: int, kind: str) -> None:
        self.draw_mode = kind
        self.draw_group = group_idx
        self._draw_active = False
        self.draw_preview = None
        shape_name = 'circle' if kind == 'circle' else 'rectangle'
        self.term_tree_panel.set_info(
            f'Click and drag on the plane to draw the {shape_name} cavity.')

    @_check_types.do
    def assign_surface(self, idx: int) -> None:
        if self.select_mode in ('wire', 'terminal_plane'):
            self._toggle_plane_group(idx)

        elif self.select_mode == 'terminal':
            if idx in self.terminal_surf_idxs:
                self.terminal_surf_idxs.remove(idx)
                self.terminal_surf_colors.pop(idx, None)
                self.term_tree_panel.set_info(
                    f'Terminal removed ({len(self.terminal_surf_idxs)} selected)')
            else:
                color = self._next_color()
                self.terminal_surf_idxs.append(idx)
                self.terminal_surf_colors[idx] = color
                self.term_tree_panel.set_info(
                    f'Terminal added ({len(self.terminal_surf_idxs)} selected)')

            self._update_analyze_enabled()

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    @_check_types.do
    def _coplanar_idxs(self, idx: int) -> list[int]:
        ref = self.surfaces[idx]
        tol = self.plane_tol

        return [
            i for i, s in enumerate(self.surfaces)
            if (float(np.dot(s.normal, ref.normal)) > 0.98
                and abs(s.plane_dist - ref.plane_dist) < tol)
        ]

    @_check_types.do
    def _toggle_plane_group(self, idx: int) -> None:
        is_wire = self.select_mode == 'wire'
        groups = self.wire_plane_groups if is_wire else self.term_plane_groups
        seeds = self.wire_plane_seeds if is_wire else self.term_plane_seeds
        excludes = self.wire_plane_excludes if is_wire else self.term_plane_excludes
        panel = self.wire_tree_panel if is_wire else self.term_tree_panel
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
            n = len(groups)

            panel.set_info(
                f'{label}: plane removed ({n} plane{"s" if n != 1 else ""} selected)')
        else:
            groups.append(plane_idxs)
            seeds.append(idx)
            excludes.append(set())
            n = len(groups)

            panel.set_info(
                f'{label}: {len(plane_idxs)} surface'
                f'{"s" if len(plane_idxs) != 1 else ""} added'
                f' ({n} plane{"s" if n != 1 else ""} total)')

        if is_wire:
            self._reload_wire_tree()
        else:
            self._reload_term_tree()

        # Keep this tree "active" after the reload's fresh (unselected)
        # rebuild -- select_mode is derived from tree selection now, so
        # without this a single 3D-canvas click would add the plane and
        # then immediately fall back out of pick mode.
        panel.select_last_top_level()

        self._update_analyze_enabled()

    @_check_types.do
    def _surface_area(self, si: int) -> float:
        if si not in self._surface_area_cache:
            self._surface_area_cache[si] = _analysis.surface_area(
                self.surfaces[si], self.vertices)

        return self._surface_area_cache[si]

    @_check_types.do
    def _reload_wire_tree(self) -> None:
        areas = {si: self._surface_area(si)
                 for group in self.wire_plane_groups for si in group}

        self.wire_tree_panel.load(self.wire_plane_groups, self.surfaces, areas)

    @_check_types.do
    def _reload_term_tree(self) -> None:
        areas = {si: self._surface_area(si)
                 for group in self.term_plane_groups for si in group}

        self.term_tree_panel.load(self.term_plane_groups, self.surfaces, areas)

    @_check_types.do
    def _update_analyze_enabled(self) -> None:
        enabled = bool(self.wire_plane_groups) and bool(
            self.term_plane_groups or self.terminal_surf_idxs)

        self._btn_analyze.setEnabled(enabled)

    # ── analysis ──────────────────────────────────────────────────────────────

    @_check_types.do
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

    @_check_types.do
    def _match_wire_surface(self, n_t, boundary_pts, wire_surf_items):
        """Find the wire-side surface that fully contains the terminal
        shape's own footprint once extruded straight along the terminal's
        normal -- not just the nearest one in cross-section, since a
        nearby-but-wrong (too small, or belonging to a different cavity)
        wire surface must never be picked just because its centroid happens
        to be close. When more than one surface contains it, the tightest
        (smallest-area) one wins.
        """
        best_ws_si = None
        best_ws = None
        best_wc = None
        best_area = float('inf')

        for wsi, ws in wire_surf_items:
            ws_n = ws.normal.astype(np.float64)
            ws_n /= np.linalg.norm(ws_n) + 1e-12

            denom = float(np.dot(ws_n, n_t))
            if abs(denom) < 1e-9:
                continue

            # Extrude each boundary point straight along the terminal's own
            # normal until it reaches this candidate's plane.
            t = (float(ws.plane_dist) - boundary_pts @ ws_n) / denom
            projected = boundary_pts + t[:, None] * n_t

            if not _analysis.surface_contains_points(ws, projected, self.vertices):
                continue

            area = _analysis.surface_area(ws, self.vertices)
            if area < best_area:
                best_area = area
                best_ws_si = wsi
                best_ws = ws
                best_wc = _analysis.surface_centroid(ws, self.vertices)

        if best_ws_si is None:
            # No candidate fully contains the projected shape -- fall back
            # to nearest-in-cross-section so a hairline containment miss
            # (real-world mesh imprecision) doesn't just drop the cavity.
            c_t = boundary_pts.mean(axis=0)
            c_t_perp = c_t - float(np.dot(c_t, n_t)) * n_t
            best_d = float('inf')

            for wsi, ws in wire_surf_items:
                wc = _analysis.surface_centroid(ws, self.vertices)
                c_w_perp = wc - float(np.dot(wc, n_t)) * n_t
                d = float(np.linalg.norm(c_t_perp - c_w_perp))

                if d < best_d:
                    best_d = d
                    best_ws_si, best_ws, best_wc = wsi, ws, wc

        return best_ws_si, best_ws, best_wc

    @_check_types.do
    def run_analysis(self) -> None:
        covered_groups = self._manual_covered_group_idxs()

        all_terminal = [i for gi, grp in enumerate(self.term_plane_groups)
                        if gi not in covered_groups
                        for i in grp]

        for i in self.terminal_surf_idxs:
            if i not in all_terminal:
                all_terminal.append(i)

        # Flatten all selected wire surfaces, keeping their picker surface index.
        wire_surf_items: list[tuple[int, object]] = [(si, self.surfaces[si])
                                                     for grp in self.wire_plane_groups
                                                     for si in grp]

        results = []
        for ti in all_terminal:
            term_surf = self.surfaces[ti]
            n_t = term_surf.normal.astype(np.float64)
            n_t /= np.linalg.norm(n_t) + 1e-12

            try:
                kind, params = _analysis.get_surface_shape(
                    term_surf, self.vertices)

                override = self.terminal_overrides.get(ti)
                if override in ('circle', 'rect'):
                    kind = override

                boundary_pts = np.array(
                    _shape_polygon_points(kind, params), dtype=np.float64)

                best_ws_si, best_ws, best_wc = self._match_wire_surface(
                    n_t, boundary_pts, wire_surf_items)

                (kind, params,
                 verts, _norms) = _analysis.generate_terminal_geometry(
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
            # Just this cavity's own surfaces -- not _group_containing's
            # whole coplanar-selection group, which can span several
            # cavities that happen to share a plane (see wire_is_shared
            # below for the legitimate wire-side sharing case).
            wire_indices = [best_ws_si]
            term_indices = [ti]

            results.append((kind, params, d_start, d_end, proj_u, proj_v, verts,
                            best_ws_si, ti, False, wire_indices, term_indices))

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

            boundary_pts = np.array(
                _shape_polygon_points(m['kind'], params), dtype=np.float64)

            best_ws_si, _best_ws, best_wc = self._match_wire_surface(
                n_t, boundary_pts, wire_surf_items)

            d_start = float(c_t @ n_t)
            d_full = float(best_wc @ n_t)
            d_end = d_start + (d_full - d_start) * self.length_factor

            verts, _norms = _analysis.generate_hole_geometry(
                m['kind'], params, d_start, d_end)

            u_ax, v_ax = _analysis.plane_frame(n_t)
            proj_u = float(c_t @ u_ax)
            proj_v = float(c_t @ v_ax)
            wire_indices = [best_ws_si]

            results.append(
                (m['kind'], params, d_start, d_end, proj_u, proj_v, verts,
                 best_ws_si, -1, True, wire_indices, []))

        if not results:
            self.cavity_tree_panel.set_info('Analysis produced no results.')
            return

        # Flag cavities whose matched wire-side surface is shared with
        # another cavity — real per-cavity wire-side mesh geometry doesn't
        # exist for these (the manufacturer modeled one continuous wire-side
        # wall), so match_cavity_surfaces() will render/click-test a
        # synthetic marker for the wire side instead, built from this
        # cavity's own OBB back face (already computed above from its
        # terminal-side footprint extruded to d_end) rather than the shared
        # real surface.
        wire_si_counts: dict = {}
        for r in results:
            wire_si = r[7]
            if wire_si >= 0:
                wire_si_counts[wire_si] = wire_si_counts.get(wire_si, 0) + 1

        # Sort: top-to-bottom (decreasing proj_v), left-to-right (increasing proj_u)
        results.sort(key=lambda r_: (-r_[5], r_[4]))

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
                wire_is_shared=wire_si_counts.get(wire_si, 0) > 1,
            )
            items.append(item)

        self.analysis_selected = 0
        self.cavity_tree_panel.load(items)

        if self.surface_overlay is not None:
            self.surface_overlay.update()

        self.cavity_tree_panel.set_info(
            f'{len(results)} cavities detected — click Accept Cavities when ready.')

    @_check_types.do
    def _on_accept_cavities(self) -> None:
        if self.cavity_panel is not None:
            items = self.cavity_tree_panel.items()
            start_idx = len(self.cavity_panel.cavities)
            for i, item in enumerate(items):
                self.cavity_panel.commit_cavity(start_idx + i, item)

            self.cavity_tree_panel.load([])
            self._edit_panel.load(None)
            self.analysis_selected = -1

        self._clear_all()

        if self.surface_overlay is not None:
            self.surface_overlay.update()

        self._cavities_accepted = True
        self._ok_button.setEnabled(True)

        # Jump to the Cavities tab to show what was just committed --
        # this also hides Accept Cavities via _on_controls_tab_changed,
        # since it's no longer the tab being viewed.
        if self.cavity_panel is not None:
            self.controls.setCurrentWidget(self.cavity_panel)

    @_check_types.do
    def _on_controls_tab_changed(self, index: int) -> None:
        is_picking_tab = self.controls.widget(index) is self._picking_page
        self._btn_accept_cavities.setVisible(is_picking_tab)

        if not self._cavities_accepted:
            self._ok_button.setEnabled(not is_picking_tab)

    @_check_types.do
    def _on_cavity_tree_sel_changed(self, item_idxs: list) -> None:
        items = self.cavity_tree_panel.items()

        if item_idxs and 0 <= item_idxs[0] < len(items):
            self.analysis_selected = item_idxs[0]
            self._edit_panel.load(items[self.analysis_selected])
        else:
            self.analysis_selected = -1
            self._edit_panel.load(None)

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    @_check_types.do
    def _on_remove_all_cavities(self) -> None:
        self.cavity_tree_panel.load([])
        self._edit_panel.load(None)
        self.analysis_selected = -1

        if self.surface_overlay is not None:
            self.surface_overlay.update()

        self.cavity_tree_panel.set_info('All detected cavities removed.')

    @_check_types.do
    def _on_cavity_item_edited(self) -> None:
        self.cavity_tree_panel.refresh_labels()

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    # ── toolbar helpers ───────────────────────────────────────────────────────

    @_check_types.do
    def _on_length_changed(self, value: int) -> None:
        self._len_label.setText(f'Length: {value}%')
        self.length_factor = value / 100.0

    @_check_types.do
    def _on_tol_changed(self, value: int) -> None:
        self.plane_tol = value / 100.0
        self._tol_label.setText(f'Tol: {self.plane_tol:.2f}')
        self._reexpand_all_groups()

    @_check_types.do
    def _reexpand_all_groups(self) -> None:
        for i, seed in enumerate(self.wire_plane_seeds):
            expanded = self._coplanar_idxs(seed)
            self.wire_plane_groups[i] = [
                si for si in expanded if si not in self.wire_plane_excludes[i]]

        for i, seed in enumerate(self.term_plane_seeds):
            expanded = self._coplanar_idxs(seed)
            self.term_plane_groups[i] = [
                si for si in expanded if si not in self.term_plane_excludes[i]]

        self._reload_wire_tree()
        self._reload_term_tree()

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    @_check_types.do
    def _clear_terminals(self) -> None:
        self.term_plane_groups = []
        self.term_plane_seeds = []
        self.term_plane_excludes = []
        self.terminal_surf_idxs.clear()
        self.terminal_surf_colors.clear()
        self.terminal_overrides.clear()
        self.term_color_idx = 0
        self.manual_cavities = []
        self.draw_mode = None
        self.draw_group = -1
        self.draw_preview = None
        self._draw_active = False
        self._draw_center = None
        self._draw_normal = None
        self._draw_u = None
        self._draw_v = None

        self.wire_tree_panel.clear_tree_selection()
        self.term_tree_panel.set_add_terminal_checked(False)
        self.select_mode = None

        self._reload_term_tree()
        self._update_analyze_enabled()

        if self.surface_overlay is not None:
            self.surface_overlay.update()

        self.term_tree_panel.set_info('Terminals cleared.')

    @_check_types.do
    def _clear_all(self) -> None:
        self.wire_plane_groups = []
        self.wire_plane_seeds = []
        self.wire_plane_excludes = []
        self._reload_wire_tree()
        self._clear_terminals()

    @_check_types.do
    def _on_remove_all_wire(self) -> None:
        self.wire_plane_groups = []
        self.wire_plane_seeds = []
        self.wire_plane_excludes = []
        self._reload_wire_tree()
        self._update_analyze_enabled()

        if self.surface_overlay is not None:
            self.surface_overlay.update()

        self.wire_tree_panel.set_info('All wire planes removed.')

    # ── plane tree event handlers ─────────────────────────────────────────────

    @_check_types.do
    def _on_wire_sel_changed(self, surf_idxs: list) -> None:
        self.wire_sel_surf_idxs = set(surf_idxs)

        if self.wire_tree_panel.has_selection():
            # An active selection here (including the empty-tree
            # placeholder) arms wire pick mode -- deselect the terminal
            # side so only one tree is ever "active" at a time. select_mode
            # is set BEFORE clearing the other tree's selection so its own
            # reentrant selectionChanged handler sees the already-updated
            # mode instead of stomping back to None.
            self.select_mode = 'wire'
            self.term_tree_panel.set_add_terminal_checked(False)
            self.term_tree_panel.clear_tree_selection()
            self.term_tree_panel.set_info('')
            self.wire_tree_panel.set_info(
                'Click a wire-side plane to add it — click a selected'
                ' plane again to remove')
        elif self.select_mode == 'wire':
            self.select_mode = None
            self.wire_tree_panel.set_info('')

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    @_check_types.do
    def _on_term_sel_changed(self, surf_idxs: list) -> None:
        self.term_sel_surf_idxs = set(surf_idxs)

        if self.term_tree_panel.has_selection():
            self.select_mode = 'terminal_plane'
            self.term_tree_panel.set_add_terminal_checked(False)
            self.wire_tree_panel.clear_tree_selection()
            self.wire_tree_panel.set_info('')
            self.term_tree_panel.set_info(
                'Click a terminal plane to add it — click again to remove')
        elif self.select_mode == 'terminal_plane':
            self.select_mode = None
            self.term_tree_panel.set_info('')

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    @_check_types.do
    def _remove_from_groups(
        self, surf_idxs: list,
        groups: list, seeds: list, excludes: list,
    ) -> None:
        to_remove = set(surf_idxs)
        empty_groups: list[int] = []

        for g, group in enumerate(groups):
            removed = [si for si in group if si in to_remove]
            if not removed:
                continue

            groups[g] = [si for si in group if si not in to_remove]
            excludes[g].update(removed)

            if not groups[g]:
                empty_groups.append(g)

        # Highest index first so popping doesn't shift the indices still
        # to be popped.
        for g in sorted(empty_groups, reverse=True):
            groups.pop(g)
            seeds.pop(g)
            excludes.pop(g)

    @_check_types.do
    def _on_wire_remove(self, surf_idxs: list) -> None:
        if not surf_idxs:
            return

        self._remove_from_groups(
            surf_idxs, self.wire_plane_groups,
            self.wire_plane_seeds, self.wire_plane_excludes)

        self._reload_wire_tree()
        self._update_analyze_enabled()

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    @_check_types.do
    def _on_term_remove(self, surf_idxs: list) -> None:
        if not surf_idxs:
            return

        self._remove_from_groups(
            surf_idxs, self.term_plane_groups,
            self.term_plane_seeds, self.term_plane_excludes)

        self._reload_term_tree()
        self._update_analyze_enabled()

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    @_check_types.do
    def _on_cavity_selected(self, wire_si: int, term_si: int) -> None:
        self.selected_cavity_wire_si = wire_si
        self.selected_cavity_term_si = term_si

        if self.surface_overlay is not None:
            self.surface_overlay.update()

    # ── boilerplate (unchanged from original) ─────────────────────────────────

    @_check_types.do
    def closeEvent(self, event):
        if self._picker is not None:
            self._picker.cleanup()

        self.canvas.cleanup()
        super().closeEvent(event)

    @property
    @_check_types.do
    def editor2d(self):
        return None

    @property
    @_check_types.do
    def editor3d(self):
        return self

    @property
    @_check_types.do
    def editor_pegboard(self):
        return None

    @property
    @_check_types.do
    def bounds_manager(self):
        return self._bounds_manager

    @_check_types.do
    def add_object(self, obj):
        self.canvas.add_object(obj)

    @_check_types.do
    def remove_object(self, obj):
        self.canvas.remove_object(obj)

    @_check_types.do
    def _set_selected(self, obj):
        self._selected_obj = obj
        self.canvas.set_selected(obj)

    @_check_types.do
    def set_selected(self, obj):  # NOQA
        if obj is not None:
            obj.set_selected(True)

    @_check_types.do
    def get_selected(self):
        return self._selected_obj

    @property
    @_check_types.do
    def config(self):
        return Config.editor_3d

    @_check_types.do
    def Refresh(self, *_, **__):
        self.canvas.update()
        if self.surface_overlay is not None:
            self.surface_overlay.update()

    @property
    @_check_types.do
    def context(self):
        return self.canvas.context
