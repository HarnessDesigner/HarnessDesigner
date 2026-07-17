# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Floating, draggable/resizable data-table overlays for the Peg Board
Editor -- one per anchor point3d_id (or, for a transition, one per
populated branch's own ``position3d_id`` -- see
``objectspeg.transition.Transition.table_anchor_points``).

Structurally the closest existing precedent is
``gl.canvas3d.axis_overlay.Overlay`` (a plain ``QWidget`` child of a GL
canvas, positioned via ``setGeometry``/``move``, persisting its own
position/size) -- adapted here for: independent width/height (not
square-locked), a ``QSizeGrip`` for resize instead of 4 custom corner
zones, and persistence to a database row (``pjt_pegboard_tables``)
instead of a ``Config`` section.

Tables default to shown (``pjt_pegboard_tables.is_collapsed`` repurposed
as a hidden-flag, default 0/visible) -- right-click toggles visibility
(``mouse_handler.py``). Dragging a table's title strip renders a leader
line (``Canvas._render_table_drag_line``) from the table to its owning
anchor point for the duration of the drag, so it's always clear which
part of the harness a repositioned table still belongs to.
"""

from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets

from ...geometry import point as _point
from . import table_model as _table_model


if TYPE_CHECKING:
    from . import canvas as _canvas


# Default new-table geometry, world units (mm) -- an arbitrary, visually
# reasonable starting box; the user freely resizes/repositions afterward
# (persisted to pjt_pegboard_tables.width/height/x/z on release).
_DEFAULT_TABLE_WIDTH_MM = 220.0
_DEFAULT_TABLE_HEIGHT_MM = 110.0

# Image-column width / font, WORLD units (mm) -- scaled to screen pixels via
# pixels_per_world (1000.0 / camera.distance, the same formula Camera2D
# itself already uses for world<->screen conversion) so the font and the
# wire image scale together as the user zooms, per the original plan's
# design. Row/header/title-strip HEIGHTS are deliberately not guessed as a
# separate mm constant -- they're measured off the actual font's
# QFontMetrics instead (see apply_zoom_scale()), so they can never drift
# out of sync with the font size actually being rendered.
_IMAGE_COLUMN_WIDTH_MM = 40.0
_FONT_HEIGHT_MM = 8.0

# Vertical breathing room added to QFontMetrics.height() for rows/header/
# title-strip -- a bare font-metrics height renders text right up against
# the cell border.
_CELL_VERTICAL_PADDING_PX = 6
_TITLE_STRIP_VERTICAL_PADDING_PX = 6

# Debounce window (ms) for committing a resize (QSizeGrip fires
# resizeEvent continuously while dragging) -- restarted on every
# resizeEvent, so only the final size after the user stops is persisted.
_RESIZE_COMMIT_DEBOUNCE_MS = 300


class _TitleStrip(QtWidgets.QWidget):
    """Thin, draggable top strip -- the only chrome a table overlay has
    (no native window frame, matching this app's existing "no native
    chrome" convention for floating/dialog-like widgets elsewhere)."""

    def __init__(self, owner: "PegboardTableWidget", label: str):
        super().__init__(owner)

        self._owner = owner
        self._drag_start_global: "QtCore.QPointF | None" = None
        self._drag_start_pos: "QtCore.QPoint | None" = None

        self.setAutoFillBackground(True)
        self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)

        self._label_widget = QtWidgets.QLabel(label, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.addWidget(self._label_widget)

    def set_label(self, label: str) -> None:
        self._label_widget.setText(label)

    def apply_zoom_scale(self, font_h: int) -> None:
        """Rescale this strip's own label font/height for the current
        camera zoom -- called by :meth:`PegboardTableWidget.
        apply_zoom_scale`.

        Height is measured from the label's own actual
        :class:`~PySide6.QtGui.QFontMetrics` rather than a separately
        guessed mm constant, so the strip is always tall enough to show
        its text in full regardless of zoom (a fixed-height strip sized
        independently of the label's real font would clip the label the
        moment the two drifted out of sync -- which is exactly what a
        disconnected mm constant did before).

        :param font_h: Font pixel size for the label -- the same value
            :meth:`PegboardTableWidget.apply_zoom_scale` applies to the
            table view's own font, so the title and the table body scale
            together.
        :type font_h: int
        """
        font = self._label_widget.font()
        font.setPixelSize(font_h)
        self._label_widget.setFont(font)

        metrics = QtGui.QFontMetrics(font)
        self.setFixedHeight(metrics.height() + _TITLE_STRIP_VERTICAL_PADDING_PX)

    def mousePressEvent(self, event: "QtGui.QMouseEvent") -> None:
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        self._drag_start_global = event.globalPosition()
        self._drag_start_pos = self._owner.pos()
        self._owner.interacting = True
        self._owner.canvas.begin_table_drag(self._owner.anchor_live_position)

    def mouseMoveEvent(self, event: "QtGui.QMouseEvent") -> None:
        if self._drag_start_global is None:
            return

        delta = event.globalPosition() - self._drag_start_global
        new_x = self._drag_start_pos.x() + int(delta.x())
        new_y = self._drag_start_pos.y() + int(delta.y())

        self._owner.move(new_x, new_y)
        self._owner.canvas.update_table_drag(self._owner.center_world_pos())

    def mouseReleaseEvent(self, event: "QtGui.QMouseEvent") -> None:
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        self._drag_start_global = None
        self._drag_start_pos = None
        self._owner.canvas.end_table_drag()
        self._owner.commit_geometry()
        self._owner.interacting = False


class PegboardTableWidget(QtWidgets.QWidget):
    """One floating data-table overlay.

    :param canvas: The owning peg-board GL canvas (needed for
        camera-space<->world-space conversion and drag-line coordination).
    :type canvas: :class:`~harness_designer.gl.canvas_pegboard.canvas.Canvas`
    :param point3d_id: This table's own anchor key (an anchor's own
        ``point3d_id``, or -- for a transition -- one branch's own
        ``position3d_id``).
    :type point3d_id: int
    :param label: Title-strip text (e.g. ``"Housing: J1"``, ``"Branch 2"``).
    :type label: str
    """

    def __init__(self, canvas: "_canvas.Canvas", point3d_id: int, label: str):
        super().__init__(canvas)

        # Without this, QSizeGrip climbs up to the real top-level widget
        # (the main application window) and resizes *that* instead of this
        # widget -- Qt.SubWindow tells it to treat this widget itself as
        # its resize target, with no other effect (still a plain child
        # widget, no native frame, no reparenting).
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.SubWindow)

        self.canvas = canvas
        self.point3d_id = point3d_id

        # True for the duration of a user-driven title-strip drag --
        # TablesOverlay.reposition_all() skips this widget entirely while
        # it's set, so it doesn't fight the live drag with a setGeometry()
        # computed from the (not-yet-committed) persisted world position.
        self.interacting = False

        # True only for the duration of reposition_all()'s own
        # camera-driven setGeometry() call -- resizeEvent uses this to
        # tell that call apart from a real QSizeGrip drag, so it doesn't
        # arm the resize-commit-debounce timer (which would otherwise
        # re-derive and overwrite this table's persisted world
        # width/height from whatever screen size the camera produced).
        self._suppress_commit = False

        # This table's owning anchor point's live, bound position Point --
        # the actual object the anchor's own position mutates in place on
        # every drag (see objectspeg.basepeg.BasePeg.table_anchor_live_
        # position), NOT a detached copy of its x/z. Only used for the
        # drag leader-line's anchor-side endpoint, but it must be the live
        # reference: a one-time float snapshot goes stale (and the line's
        # object-end ends up nowhere near the real object) the moment the
        # anchor is moved and committed without a table-overlay rebuild in
        # between. Set by TablesOverlay.ensure_table() each time the
        # anchor list is rebuilt (load_project/add_anchor) -- rebuilding
        # doesn't invalidate the reference itself, it just re-fetches
        # whichever live Point the anchor currently has.
        self.anchor_live_position: "_point.Point | None" = None

        self.setAutoFillBackground(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        self._title_strip = _TitleStrip(self, label)
        layout.addWidget(self._title_strip)

        self._view = QtWidgets.QTableView(self)
        self._view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self._view.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._image_delegate = _table_model.WireImageDelegate(self._view)
        self._view.setItemDelegateForColumn(_table_model.COL_IMAGE, self._image_delegate)
        layout.addWidget(self._view, 1)

        grip_row = QtWidgets.QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch(1)
        self._size_grip = QtWidgets.QSizeGrip(self)
        grip_row.addWidget(self._size_grip)
        layout.addLayout(grip_row)

        self._model: "_table_model.PegboardTableModel | None" = None

        self._resize_commit_timer = QtCore.QTimer(self)
        self._resize_commit_timer.setSingleShot(True)
        self._resize_commit_timer.timeout.connect(self.commit_geometry)

    def set_rows(self, rows: list, include_cavity_columns: bool) -> None:
        """(Re)build this table's model from a fresh row list."""
        self._model = _table_model.PegboardTableModel(rows, include_cavity_columns, self)
        self._view.setModel(self._model)

    def set_label(self, label: str) -> None:
        self._title_strip.set_label(label)

    def set_anchor_live_position(self, point: "_point.Point") -> None:
        """Store a *reference* to the owning anchor's own live, bound
        position Point -- see :attr:`anchor_live_position`'s docstring for
        why this must not be a copy.
        """
        self.anchor_live_position = point

    def apply_zoom_scale(self, pixels_per_world: float) -> None:
        """Rescale row/header/title-strip height, font, and image-column
        width for the current camera zoom -- called by
        :meth:`TablesOverlay.reposition_all`.

        Row and header heights are measured off the actual font's
        ``QFontMetrics`` rather than a separately-guessed mm constant, so
        they can never drift out of sync with the font size actually
        being rendered (a fixed mm guess is exactly what left the title
        strip too short to show its own label -- see ``_TitleStrip.
        apply_zoom_scale``).

        The horizontal header additionally needs a *per-widget*
        stylesheet override: the app's Dark/Light theme both hardcode
        ``QHeaderView::section``'s ``font-size``, which silently wins
        over a plain ``header.setFont()`` call -- a widget-local
        stylesheet is the only thing Qt lets take priority over that.

        :param pixels_per_world: ``1000.0 / camera.distance`` -- the same
            world<->screen scale factor ``Camera2D`` itself uses.
        :type pixels_per_world: float
        """
        font_h = max(4, int(_FONT_HEIGHT_MM * pixels_per_world))
        image_w = max(8, int(_IMAGE_COLUMN_WIDTH_MM * pixels_per_world))

        font = self._view.font()
        font.setPixelSize(font_h)
        self._view.setFont(font)
        self._view.setColumnWidth(_table_model.COL_IMAGE, image_w)

        row_h = QtGui.QFontMetrics(font).height() + _CELL_VERTICAL_PADDING_PX

        v_header = self._view.verticalHeader()
        v_header.setFont(font)
        v_header.setDefaultSectionSize(row_h)

        h_header = self._view.horizontalHeader()
        h_header.setStyleSheet(f'QHeaderView::section {{ font-size: {font_h}px; }}')
        h_header.setFixedHeight(row_h)

        self._title_strip.apply_zoom_scale(font_h)

    def center_world_pos(self) -> "_point.Point":
        """This table's own current screen-center, converted to world
        coordinates -- used to draw the in-progress drag leader line.

        ``Camera2D.screen_to_world`` is a generic 2-component screen/world
        helper (shared with editor2d, unaware of a "z" axis) -- its result
        is immediately rebuilt into a real 3D point here (``.y`` always
        ``0.0``) rather than carried forward mislabeled.
        """
        center = self.geometry().center()
        result = self.canvas.camera.screen_to_world(
            _point.Point(float(center.x()), float(center.y())))
        return _point.Point(result.x, 0.0, result.y)

    def commit_geometry(self) -> None:
        """Persist this table's current screen geometry back to world
        units in ``pjt_pegboard_tables`` -- called once, on drag release
        (immediately) or resize (debounced via
        :data:`_RESIZE_COMMIT_DEBOUNCE_MS`) -- mirrors the rest of this
        feature's "mutate freely during a drag, commit once it settles"
        discipline, since converting screen<->world on *every* mouse-move
        for a table has no benefit (unlike an anchor, nothing else reads a
        table's live position mid-drag).
        """
        project = self.canvas.project
        if project is None:
            return

        # Camera2D.screen_to_world is a generic 2-component screen/world
        # helper (shared with editor2d) -- its ".y" result slot holds
        # world Z here, stored straight into the row's own real .z column.
        camera = self.canvas.camera
        top_left = camera.screen_to_world(
            _point.Point(float(self.x()), float(self.y())))
        bottom_right = camera.screen_to_world(
            _point.Point(float(self.x() + self.width()), float(self.y() + self.height())))

        table_row = project.ptables.pjt_pegboard_tables_table.get_from_point3d_id(self.point3d_id)
        if table_row is None:
            return

        table_row.x = float(top_left.x)
        table_row.z = float(top_left.y)
        table_row.width = float(bottom_right.x - top_left.x)
        table_row.height = float(bottom_right.y - top_left.y)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self._suppress_commit:
            self._resize_commit_timer.start(_RESIZE_COMMIT_DEBOUNCE_MS)


class TablesOverlay:
    """Owns every :class:`PegboardTableWidget` for one peg-board
    :class:`~harness_designer.gl.canvas_pegboard.canvas.Canvas`, keyed by
    the anchor point (or transition branch point) it belongs to.

    :param canvas: The owning peg-board GL canvas.
    :type canvas: :class:`~harness_designer.gl.canvas_pegboard.canvas.Canvas`
    """

    def __init__(self, canvas: "_canvas.Canvas"):
        self.canvas = canvas
        self._widgets: dict[int, PegboardTableWidget] = {}

    def ensure_table(
        self, point3d_id: int, world_x: float, world_z: float, label: str,
        rows: list, include_cavity_columns: bool, anchor_live_position: "_point.Point",
    ) -> None:
        """Create (or refresh) the table overlay for *point3d_id*.

        Auto-creates its ``pjt_pegboard_tables`` row (default position
        seeded from *world_x*/*world_z*, default size) the first time this
        point3d_id is ever seen -- tables default to shown, per the
        project's requirement.

        :param point3d_id: The owning anchor point (or transition branch
            point)'s own id.
        :type point3d_id: int
        :param world_x: This point's current world X (used only to seed a
            brand-new table's default position -- ignored for a table
            that already has a persisted position).
        :type world_x: float
        :param world_z: This point's current world Z.
        :type world_z: float
        :param label: Title-strip text.
        :type label: str
        :param rows: This table's rows -- see ``table_rows.build_rows_for_*``.
        :type rows: list[:class:`table_rows.WireTableRow`]
        :param include_cavity_columns: Forwarded to :class:`table_model.PegboardTableModel`.
        :type include_cavity_columns: bool
        :param anchor_live_position: The owning anchor's own live, bound
            position Point (``objectspeg.basepeg.BasePeg.
            table_anchor_live_position``) -- stored by reference, not
            copied, so the table-drag leader line always tracks the
            anchor's current position (see
            :attr:`PegboardTableWidget.anchor_live_position`).
        :type anchor_live_position: :class:`_point.Point`
        """
        project = self.canvas.project
        if project is None:
            return

        tables_table = project.ptables.pjt_pegboard_tables_table
        table_row = tables_table.get_from_point3d_id(point3d_id)
        if table_row is None:
            table_row = tables_table.insert(
                point3d_id, world_x, world_z,
                _DEFAULT_TABLE_WIDTH_MM, _DEFAULT_TABLE_HEIGHT_MM)

        widget = self._widgets.get(point3d_id)
        if widget is None:
            widget = PegboardTableWidget(self.canvas, point3d_id, label)
            self._widgets[point3d_id] = widget
        else:
            widget.set_label(label)

        widget.set_anchor_live_position(anchor_live_position)
        widget.set_rows(rows, include_cavity_columns)
        widget.setVisible(not table_row.is_collapsed)
        widget.show()

    def remove_table(self, point3d_id: int) -> None:
        """Tear down the table overlay for *point3d_id*, if one exists."""
        widget = self._widgets.pop(point3d_id, None)
        if widget is not None:
            widget.deleteLater()

    def remove_tables_for_points(self, point3d_ids) -> None:
        """Tear down every table overlay in *point3d_ids* -- called on
        anchor removal, once per that anchor's own :attr:`~objectspeg.
        basepeg.BasePeg.table_anchor_points`."""
        for point3d_id in point3d_ids:
            self.remove_table(point3d_id)

    def toggle_visibility(self, point3d_id: int) -> None:
        """Flip the shown/hidden state for *point3d_id*'s table, if one
        exists -- called from the peg board's right-click context menu."""
        project = self.canvas.project
        if project is None:
            return

        table_row = project.ptables.pjt_pegboard_tables_table.get_from_point3d_id(point3d_id)
        if table_row is None:
            return

        table_row.is_collapsed = 0 if table_row.is_collapsed else 1

        widget = self._widgets.get(point3d_id)
        if widget is not None:
            widget.setVisible(not table_row.is_collapsed)

    def is_visible(self, point3d_id: int) -> bool:
        """Whether *point3d_id*'s table is currently shown (for the
        right-click menu's Show/Hide label)."""
        project = self.canvas.project
        if project is None:
            return False

        table_row = project.ptables.pjt_pegboard_tables_table.get_from_point3d_id(point3d_id)
        return table_row is not None and not table_row.is_collapsed

    def clear(self) -> None:
        """Tear down every table overlay -- called by a full
        ``load_project()`` rebuild before repopulating."""
        for widget in self._widgets.values():
            widget.deleteLater()

        self._widgets.clear()

    def reposition_all(self) -> None:
        """Recompute every visible table's on-screen geometry and
        zoom-driven scaling from its own persisted world position/size --
        called on every camera change (see ``Canvas.Refresh``)."""
        project = self.canvas.project
        if project is None or not self._widgets:
            return

        camera = self.canvas.camera
        pixels_per_world = 1000.0 / camera.distance
        tables_table = project.ptables.pjt_pegboard_tables_table

        for point3d_id, widget in self._widgets.items():
            if widget.interacting:
                continue

            table_row = tables_table.get_from_point3d_id(point3d_id)
            if table_row is None or table_row.is_collapsed:
                continue

            top_left = camera.world_to_screen(_point.Point(table_row.x, table_row.z))
            bottom_right = camera.world_to_screen(
                _point.Point(table_row.x + table_row.width, table_row.z + table_row.height))

            widget._suppress_commit = True
            try:
                widget.setGeometry(
                    int(top_left.x), int(top_left.y),
                    max(20, int(bottom_right.x - top_left.x)),
                    max(20, int(bottom_right.y - top_left.y)))
                widget.apply_zoom_scale(pixels_per_world)
            finally:
                widget._suppress_commit = False
