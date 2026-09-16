# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Off-screen hosting for one peg-board floating wire table.

Wraps a :class:`~.wire_table.WireTable` (the real, DB-backed, virtually-
scrolled/sortable table) inside a hidden ``QMdiArea``/``QMdiSubWindow``
pair, never shown on a real screen (``WA_DontShowOnScreen``), and grabbed
on demand into a raw RGBA buffer that
``objects.objects_pegboard.pegboard_table.PegboardTable`` uploads as a GL
texture and draws on a world-space quad. Everything here is proven,
measured behavior ported from the scratch prototype this whole feature
started as (``scratches/pegboard_spreadsheet_widget/gl_qtable_test.py``) --
see that file's own module docstring and its many inline comments for the
"why" behind each piece (QMdiSubWindow's real Qt-painted title bar/close
button/drag-to-move/drag-to-resize, the hover-before-press requirement,
the fixed-headroom QMdiArea sizing, etc.).

The one real design change from the scratch prototype: cursor-change
forwarding here uses an installed :class:`QObject` event filter
(:class:`_CursorAndCloseFilter`) rather than the scratch's own two
separate ``QHeaderView``/``QMdiSubWindow`` subclasses -- ``WireTable`` is
the SHARED ``editor_db.base.EditorList`` (used by every other editor tab
in the app too, not just this one), so replacing its header or subclassing
its sub-window would mean either touching shared code that has nothing to
do with off-screen capture, or re-implementing a chunk of
``EditorList.__init__``'s own header setup on a replacement header. An
event filter observes ``QEvent.CursorChange``/``QEvent.Close`` on the
EXISTING widgets from outside instead, so nothing about ``WireTable``/
``EditorList`` needs to change or be duplicated at all.
"""

from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets

from . import wire_table as _wire_table
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_pegboard_table as _pjt_pegboard_table
    from ... import ui as _ui


# Fixed, generous headroom for the QMdiArea -- NOT kept matched to the
# sub-window's own size. QMdiSubWindowPrivate::setNewGeometry clamps a
# resize to fit within its PARENT's own bounds, so a QMdiArea sized
# exactly to its one sub-window leaves it nowhere to grow into and every
# resize attempt silently clamps right back to the current size (measured
# in the scratch prototype). Set once at construction and never touched
# again; PegboardTableHost.grab() reads only the sub-window's own
# rectangle out of this otherwise-mostly-empty area.
_MDI_AREA_SIZE = QtCore.QSize(2000, 1400)

# The sub-window is kept at this fixed anchor point (the middle of the
# oversized area above) between interactions, rather than at (0, 0) --
# QMdiArea's own interactive move/resize would not let the sub-window
# actually reach a negative local position (confirmed 2026-09-16: a
# title-bar drag could go left/right/down but never up, since up/left
# would require going negative from a (0, 0) rest position). Anchoring
# at the center instead gives equal room in all four directions before
# a drag could ever approach an edge of the still-oversized area.
SUB_WINDOW_ANCHOR = QtCore.QPoint(
    _MDI_AREA_SIZE.width() // 2, _MDI_AREA_SIZE.height() // 2)

# The sub-window's actual PAINTED top-left lands 3px down/right of
# whatever position .move() is given to (confirmed 2026-09-16, Kevin --
# the gray QMdiArea background was bleeding into every capture's
# top/left edges when the sub-window was moved to SUB_WINDOW_ANCHOR
# directly). Resting it here, 3px up/left of that anchor, instead means
# the ACTUAL PAINTED top-left lands exactly on SUB_WINDOW_ANCHOR,
# matching grab_rgba()'s own capture rect. sub_window_moved() computes
# its drag delta against THIS point, not SUB_WINDOW_ANCHOR -- using the
# plain anchor there would read a constant (-3, -3) "drag" at rest,
# with nothing actually moved.
_SUB_WINDOW_REST_POINT = QtCore.QPoint(
    SUB_WINDOW_ANCHOR.x() - 3, SUB_WINDOW_ANCHOR.y() - 3)

# World units in this codebase are millimeters (see e.g. wires.od_mm/
# conductor_dia_mm) -- a hidden widget captured 1 world-unit-per-logical-
# pixel would make even a modest table many hundreds of mm wide, dwarfing
# real components. This is the fixed scale between the two: every
# PJTPegboardTable.size mm dimension maps to PIXELS_PER_MM times as many
# logical pixels when the hidden sub-window is actually built/resized
# (see PegboardTableHost.__init__), and back again in
# objects_pegboard.pegboard_table.PegboardTable's own
# _regrab_texture/_screen_to_panel_local. Purely a pixel-density/text-
# legibility knob -- does NOT change a table's own WORLD/mm footprint
# (see pjt_pegboard_table.DEFAULT_TABLE_WIDTH/HEIGHT for that), and is
# deliberately a fixed constant, not tied to the peg-board camera's own
# zoom (Camera.world_per_pixel), so legibility stays constant regardless
# of how far the user has zoomed the board out. At 6.0, the 100x50mm
# default table (see pjt_pegboard_table.DEFAULT_TABLE_WIDTH/HEIGHT)
# captures at a comfortably readable 600x300 logical pixels.
PIXELS_PER_MM = 6.0


class _CursorAndCloseFilter(QtCore.QObject):
    """Installed on a widget from outside (see module docstring for why)
    to observe two events that otherwise have no way to reach code
    outside that widget for something that's never actually shown on a
    real screen:

    - ``QEvent.CursorChange`` -- ``QWidget.setCursor()`` is a plain
      (non-virtual) C++ method, so a widget's internal C++ code calling
      ``this->setCursor(...)`` on itself (e.g. ``QHeaderView`` showing a
      resize cursor, ``QMdiSubWindow`` showing one at its own resize
      edges) never dispatches through a Python-level ``setCursor``
      override -- confirmed empirically while prototyping this. The
      CursorChange event Qt sends through its normal event-dispatch path
      whenever the effective cursor changes, no matter what triggered
      it, is what this actually observes -- re-emitted as
      :attr:`cursor_changed` so whatever real on-screen widget is
      compositing this one's captured pixels can mirror it.
    - ``QEvent.Close`` -- filtered and ignored (returning True stops the
      event reaching the sub-window's own closeEvent at all, so Qt never
      actually destroys it) and re-emitted as :attr:`close_requested`
      instead, so the underlying WireTable/sub-window stays alive and
      the caller just stops drawing/dispatching to it -- matching how
      every other peg-board object's ``is_visible_pegboard`` already
      works, rather than needing to tear down and rebuild anything.
    """

    cursor_changed = QtCore.Signal(QtGui.QCursor)
    close_requested = QtCore.Signal()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.CursorChange:
            self.cursor_changed.emit(watched.cursor())
            return False

        if event.type() == QtCore.QEvent.Type.Close:
            event.ignore()
            self.close_requested.emit()
            return True

        return False


class PegboardTableHost(QtWidgets.QMdiArea):
    """Hidden ``QMdiArea`` hosting one real :class:`WireTable` in a
    ``QMdiSubWindow`` -- title bar, close button, drag-to-move, drag-to-
    resize all real Qt widget behavior (not OS-native chrome, so it
    still composites correctly via :meth:`grab` even though this is
    never shown on a real screen), and all fully native/interactive when
    driven with synthetic events (see :meth:`objects_pegboard.
    pegboard_table.PegboardTable`'s own dispatch code for the "why" on
    exactly how those need to be sequenced).
    """

    close_requested = QtCore.Signal()
    cursor_changed = QtCore.Signal(QtGui.QCursor)

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", title: str,
                 pegboard_table: "_pjt_pegboard_table.PJTPegboardTable"):
        """Initialise the :class:`PegboardTableHost` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param title: Title bar text for the hosted sub-window.
        :type title: str
        :param pegboard_table: The DB row backing this table's column
            selection/size -- passed straight through to
            :class:`WireTable`.
        :type pegboard_table: :class:`_pjt_pegboard_table.PJTPegboardTable`
        """
        super().__init__()
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        # Without this, Qt paints into an OPAQUE backing store
        # regardless of what brush/alpha setBackground() below is given
        # -- grab()/toImage() then always comes back with alpha forced
        # to 255 everywhere, which is why the (0,0,0,0) background
        # brush wasn't actually honored (confirmed 2026-09-16, Kevin).
        # With this set, Qt tracks a real alpha channel through its
        # paint pipeline, so a genuinely transparent background (and
        # anything else drawn with partial alpha) survives into the
        # captured image -- letting shaders.texture's existing
        # `sampled.a < 0.01: discard` (see fragment.frag) show through
        # to whatever's actually behind the table in the 3D scene,
        # rather than an opaque fill color.
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        self.table = _wire_table.WireTable(
            None, mainframe, title, mainframe.project.ptables.pjt_wires_table,
            pegboard_table)

        self._header_filter = _CursorAndCloseFilter(self)
        self._header_filter.cursor_changed.connect(self.cursor_changed.emit)
        self.table.horizontalHeader().installEventFilter(self._header_filter)

        self.sub_window = QtWidgets.QMdiSubWindow()
        self.sub_window.setWidget(self.table)
        self.sub_window.setWindowTitle(title)
        # Neither an empty QIcon() nor setSystemMenu(None) actually
        # suppresses the icon QMdiSubWindow draws at the title bar's
        # left edge (confirmed 2026-09-16, both still visible) -- Qt's
        # own title-bar painting checks windowIcon().isNull() and, when
        # true, substitutes QApplication::windowIcon() and then a
        # built-in style icon (QStyle::SP_TitleBarMenuButton), REGARDLESS
        # of whether a system menu is actually connected. A QIcon
        # constructed from a real (if fully transparent) QPixmap is
        # never null, so it skips that fallback chain entirely and
        # simply paints nothing.
        transparent_icon = QtGui.QPixmap(16, 16)
        transparent_icon.fill(QtCore.Qt.GlobalColor.transparent)
        self.sub_window.setWindowIcon(QtGui.QIcon(transparent_icon))
        # No system menu functionality wanted either (see the flags
        # right below -- title/close only).
        self.sub_window.setSystemMenu(None)
        # Title bar + close button only -- no minimize/maximize/system menu.
        self.sub_window.setWindowFlags(
            QtCore.Qt.WindowType.CustomizeWindowHint
            | QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowCloseButtonHint)
        # No custom style/stylesheet applied to the sub-window or its
        # content anymore (Kevin, 2026-09-16: "there should be no
        # reason to apply any styling") -- an earlier attempt assigned
        # the Fusion style directly to this widget to get a plain
        # square frame, but that made Fusion's OWN "active window" look
        # (blue title bar, bold text) show instead of the app's real
        # Dark theme until the table was selected, and its close button
        # didn't look right either. It's the captured pixels that get
        # cleaned up now (see fragment.frag's topLeftMarginPx/
        # cornerRadiusPx), not Qt's styling of the source widget.

        self._sub_window_filter = _CursorAndCloseFilter(self)
        self._sub_window_filter.cursor_changed.connect(self.cursor_changed.emit)
        self._sub_window_filter.close_requested.connect(self.close_requested.emit)
        self.sub_window.installEventFilter(self._sub_window_filter)

        self.addSubWindow(self.sub_window)

        # pegboard_table.size is world-space mm -- scale up to logical
        # pixels for the actual widget (see PIXELS_PER_MM's own comment).
        width_mm, height_mm = pegboard_table.size
        self.sub_window.resize(
            int(width_mm * PIXELS_PER_MM), int(height_mm * PIXELS_PER_MM))

        self.sub_window.move(_SUB_WINDOW_REST_POINT)

        self.sub_window.show()
        self.setActiveSubWindow(self.sub_window)

        color = QtGui.QColor(0, 0, 0, 0)
        brush = QtGui.QBrush(color)
        self.setBackground(brush)

        self.resize(_MDI_AREA_SIZE)

    @_check_types.do
    def sub_window_moved(self) -> QtCore.QPoint:
        """Return how far the sub-window has drifted from
        :data:`_SUB_WINDOW_REST_POINT` -- a nonzero result means the
        user just dragged its title bar or an edge/corner. The caller
        (:class:`PegboardTable`) is responsible for folding this into
        its own world-space position and calling
        :meth:`reset_sub_window_position` to zero it back out; kept
        separate from that reset so the caller can choose its own
        world-space scale/axis convention rather than this module
        assuming one.

        :returns: The sub-window's current position, relative to
            :data:`_SUB_WINDOW_REST_POINT`.
        :rtype: :class:`QtCore.QPoint`
        """
        return self.sub_window.pos() - _SUB_WINDOW_REST_POINT

    @_check_types.do
    def reset_sub_window_position(self) -> None:
        """Snap the sub-window's local position back to
        :data:`_SUB_WINDOW_REST_POINT` -- see :meth:`sub_window_moved`.
        """
        self.sub_window.move(_SUB_WINDOW_REST_POINT)

    @_check_types.do
    def grab_rgba(self) -> tuple[bytes, int, int]:
        """Capture the sub-window's current appearance.

        Grabs only the sub-window's own rectangle out of the (much
        larger, see :data:`_MDI_AREA_SIZE`) ``QMdiArea`` -- the
        sub-window is always kept at :data:`SUB_WINDOW_ANCHOR` by the
        caller via :meth:`reset_sub_window_position`.

        The capture rect's SIZE comes from ``self.sub_window.size()``
        -- correct and current the instant it's read (``resize()``
        updates it synchronously), but what actually matters is whether
        the PAINTED content ``grab()`` captures has caught up with any
        pending layout/style work Qt deferred to the next event-loop
        pass, not the size value itself. Flushing the event queue
        immediately before every capture (not just once, right after
        construction, which is what an earlier version of this did) is
        what actually guarantees that -- confirmed 2026-09-16 against
        the title bar/font-weight bug this was originally written for,
        and matches an identical finding from this feature's own
        scratch prototype.

        :returns: Raw RGBA8888 bytes, width, height -- ready for
            ``glTexImage2D``.
        :rtype: tuple[bytes, int, int]
        """
        QtWidgets.QApplication.processEvents()

        rect = QtCore.QRect(SUB_WINDOW_ANCHOR, self.sub_window.size())
        pixmap = self.grab(rect)
        image = pixmap.toImage().convertToFormat(QtGui.QImage.Format.Format_RGBA8888)

        return bytes(image.constBits()), image.width(), image.height()
