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

from PySide6 import QtCore, QtWidgets

from ...geometry import point as _point
from . import table_model as _table_model


if TYPE_CHECKING:
    from PySide6 import QtGui
    from . import canvas as _canvas


# Default new-table geometry, world units (mm) -- an arbitrary, visually
# reasonable starting box; the user freely resizes/repositions afterward
# (persisted to pjt_pegboard_tables.width/height/x/z on release).
_DEFAULT_TABLE_WIDTH_MM = 220.0
_DEFAULT_TABLE_HEIGHT_MM = 110.0

# Row height / image-column width / font / title-strip height, WORLD units
# (mm) -- scaled to screen pixels via pixels_per_world (1000.0 /
# camera.distance, the same formula Camera2D itself already uses for
# world<->screen conversion) so font, row height, and the wire image all
# scale together as the user zooms, per the original plan's design.
_ROW_HEIGHT_MM = 10.0
_IMAGE_COLUMN_WIDTH_MM = 40.0
_FONT_HEIGHT_MM = 6.0
_TITLE_STRIP_HEIGHT_MM = 6.0

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

    def mousePressEvent(self, event: "QtGui.QMouseEvent") -> None:
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        self._drag_start_global = event.globalPosition()
        self._drag_start_pos = self._owner.pos()
        self._owner.canvas.begin_table_drag(self._owner.anchor_world_pos)

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

        self.canvas = canvas
        self.point3d_id = point3d_id

        # This table's owning anchor point's world position -- refreshed by
        # TablesOverlay.ensure_table() each time the anchor list is rebuilt
        # (load_project/add_anchor), NOT re-derived live on every access.
        # Only used for the drag leader-line, which doesn't need
        # frame-perfect accuracy if the anchor happens to move between
        # rebuilds -- see module docstring. A real 3D point (.y always
        # 0.0, the board is flat), matching every other peg-board position
        # in this codebase -- .x/.z read directly with no relabeling.
        self.anchor_world_pos = _point.Point(0.0, 0.0, 0.0)

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

    def set_anchor_world_pos(self, x: float, z: float) -> None:
        self.anchor_world_pos = _point.Point(x, 0.0, z)

    def apply_zoom_scale(self, pixels_per_world: float) -> None:
        """Rescale row height/font/image-column width for the current
        camera zoom -- called by :meth:`TablesOverlay.reposition_all`.

        :param pixels_per_world: ``1000.0 / camera.distance`` -- the same
            world<->screen scale factor ``Camera2D`` itself uses.
        :type pixels_per_world: float
        """
        row_h = max(4, int(_ROW_HEIGHT_MM * pixels_per_world))
        font_h = max(4, int(_FONT_HEIGHT_MM * pixels_per_world))
        image_w = max(8, int(_IMAGE_COLUMN_WIDTH_MM * pixels_per_world))
        strip_h = max(4, int(_TITLE_STRIP_HEIGHT_MM * pixels_per_world))

        font = self._view.font()
        font.setPixelSize(font_h)
        self._view.setFont(font)
        self._view.verticalHeader().setDefaultSectionSize(row_h)
        self._view.setColumnWidth(_table_model.COL_IMAGE, image_w)

        self._title_strip.setFixedHeight(strip_h)

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

        table_row.x = top_left.x
        table_row.z = top_left.y
        table_row.width = bottom_right.x - top_left.x
        table_row.height = bottom_right.y - top_left.y

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
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
        rows: list, include_cavity_columns: bool,
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

        widget.set_anchor_world_pos(world_x, world_z)
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
            table_row = tables_table.get_from_point3d_id(point3d_id)
            if table_row is None or table_row.is_collapsed:
                continue

            top_left = camera.world_to_screen(_point.Point(table_row.x, table_row.z))
            bottom_right = camera.world_to_screen(
                _point.Point(table_row.x + table_row.width, table_row.z + table_row.height))

            widget.setGeometry(
                int(top_left.x), int(top_left.y),
                max(20, int(bottom_right.x - top_left.x)),
                max(20, int(bottom_right.y - top_left.y)))
            widget.apply_zoom_scale(pixels_per_world)
