# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
FoldPanelBar — PySide6 port of the wxPython AGW FoldPanelBar widget.

Public API is fully preserved so all call sites work without modification:
    bar = FoldPanelBar(parent, agwStyle=FPB_VERTICAL)
    fp  = bar.AddFoldPanel("Title", collapsed=False, cbstyle=style)
    bar.AddFoldPanelWindow(fp, some_widget)
    bar.AddFoldPanelSeparator(fp)
    bar.Collapse(fp) / bar.Expand(fp)
    bar.ApplyCaptionStyleAll(style)

CaptionBarStyle keeps all its setter/getter methods unchanged.
"""

import base64

from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui
from ... import check_types as _check_types

# ---------------------------------------------------------------------------
# Embedded icons (same PNG data as the original, decoded once at import)
# ---------------------------------------------------------------------------
_EXPANDED_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAEJJ"
    "REFUOI1jZGRiZqAEMFGke1AYwIIu8P/f3/+4FDMyMTNS3QUYBmCzBZ84bQIR3TZcttPOBci2"
    "4rOdKi5gHM0LDACevARXGc9htQAAAABJRU5ErkJggg=="
)
_COLLAPSED_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAADdJ"
    "REFUOI1jZGRiZqAEMFGke/Ab8P/f3/8D5wKY7YRcQRsXoNuKzxXUdwEu23CJU+wCxtG8wAAA"
    "mvUb+vltJD8AAAAASUVORK5CYII="
)


@_check_types.do
def _load_icon_pixmap(b64: str) -> QtGui.QPixmap:
    """Load the icon pixmap.

    UNKNOWN details are inferred from the callable name and signature.

    :param b64: Value for ``b64``.
    :type b64: str
    :returns: Return value. UNKNOWN details.
    :rtype: :class:`QPixmap`
    """
    data = base64.b64decode(b64)
    img = QtGui.QImage.fromData(data)
    return QtGui.QPixmap.fromImage(img)


_EXPANDED_PIXMAP: QtGui.QPixmap | None = None
_COLLAPSED_PIXMAP: QtGui.QPixmap | None = None


@_check_types.do
def _get_icons() -> tuple[QtGui.QPixmap, QtGui.QPixmap]:
    """Return the icons.

    UNKNOWN details are inferred from the callable name and signature.

    :returns: Return value. UNKNOWN details.
    :rtype: tuple[QPixmap, QPixmap]
    """
    global _EXPANDED_PIXMAP, _COLLAPSED_PIXMAP

    if _EXPANDED_PIXMAP is None:
        _EXPANDED_PIXMAP = _load_icon_pixmap(_EXPANDED_PNG_B64)
        _COLLAPSED_PIXMAP = _load_icon_pixmap(_COLLAPSED_PNG_B64)

    return _EXPANDED_PIXMAP, _COLLAPSED_PIXMAP


# ---------------------------------------------------------------------------
# Constants (identical values to the originals)
# ---------------------------------------------------------------------------
CAPTIONBAR_NOSTYLE = 0
CAPTIONBAR_GRADIENT_V = 1
CAPTIONBAR_GRADIENT_H = 2
CAPTIONBAR_SINGLE = 3
CAPTIONBAR_RECTANGLE = 4
CAPTIONBAR_FILLED_RECTANGLE = 5

FPB_EXTRA_X = 10
FPB_EXTRA_Y = 4
FPB_BMP_RIGHTSPACE = 2

FPB_SINGLE_FOLD = 0x0001
FPB_COLLAPSE_TO_BOTTOM = 0x0002
FPB_EXCLUSIVE_FOLD = 0x0004
FPB_HORIZONTAL = 0x0008
FPB_VERTICAL = 0x0010

FPB_ALIGN_LEFT = 0
FPB_ALIGN_WIDTH = 1

FPB_DEFAULT_LEFTSPACING = 5
FPB_DEFAULT_RIGHTSPACING = 10
FPB_DEFAULT_SPACING = 8
FPB_DEFAULT_LEFTLINESPACING = 2
FPB_DEFAULT_RIGHTLINESPACING = 2


# ---------------------------------------------------------------------------
# CaptionBarStyle  (pure Python — no wx types)
# ---------------------------------------------------------------------------
class CaptionBarStyle:
    """
    Encapsulates visual styles for a CaptionBar.

    API identical to original.
    """

    @_check_types.do
    def __init__(self):
        """Initialise the :class:`CaptionBarStyle` instance.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._captionFont: QtGui.QFont | None = None
        self._textColour:  QtGui.QColor | None = None
        self._firstColour: QtGui.QColor | None = None
        self._secondColour: QtGui.QColor | None = None

        self._captionFontUsed = False
        self._firstColourUsed = False
        self._secondColourUsed = False
        self._textColourUsed = False
        self._captionStyleUsed = False
        self._captionStyle = CAPTIONBAR_GRADIENT_V

    @_check_types.do
    def ResetDefaults(self):
        """Execute the reset defaults operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._firstColourUsed = False
        self._secondColourUsed = False
        self._textColourUsed = False
        self._captionFontUsed = False
        self._captionStyleUsed = False
        self._captionStyle = CAPTIONBAR_GRADIENT_V

    # Font
    @_check_types.do
    def SetCaptionFont(self, font: QtGui.QFont):
        """Execute the set caption font operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param font: Value for ``font``.
        :type font: :class:`QFont`
        """
        self._captionFont = font
        self._captionFontUsed = True

    @_check_types.do
    def CaptionFontUsed(self) -> bool:
        """Execute the caption font used operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self._captionFontUsed

    @_check_types.do
    def GetCaptionFont(self) -> QtGui.QFont:
        """Execute the get caption font operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`QFont`
        """
        return self._captionFont

    # First colour
    @_check_types.do
    def SetFirstColour(self, colour: QtGui.QColor):
        """Execute the set first colour operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param colour: Value for ``colour``.
        :type colour: :class:`QColor`
        """
        self._firstColour = colour
        self._firstColourUsed = True

    @_check_types.do
    def FirstColourUsed(self) -> bool:
        """Execute the first colour used operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self._firstColourUsed

    @_check_types.do
    def GetFirstColour(self) -> QtGui.QColor:
        """Execute the get first colour operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`QColor`
        """
        return self._firstColour

    # Second colour
    @_check_types.do
    def SetSecondColour(self, colour: QtGui.QColor):
        """Execute the set second colour operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param colour: Value for ``colour``.
        :type colour: :class:`QColor`
        """
        self._secondColour = colour
        self._secondColourUsed = True

    @_check_types.do
    def SecondColourUsed(self) -> bool:
        """Execute the second colour used operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self._secondColourUsed

    @_check_types.do
    def GetSecondColour(self) -> QtGui.QColor:
        """Execute the get second colour operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`QColor`
        """
        return self._secondColour

    # Caption (text) colour
    @_check_types.do
    def SetCaptionColour(self, colour: QtGui.QColor):
        """Execute the set caption colour operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param colour: Value for ``colour``.
        :type colour: :class:`QColor`
        """
        self._textColour = colour
        self._textColourUsed = True

    @_check_types.do
    def CaptionColourUsed(self) -> bool:
        """Execute the caption colour used operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self._textColourUsed

    @_check_types.do
    def GetCaptionColour(self) -> QtGui.QColor:
        """Execute the get caption colour operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`QColor`
        """
        return self._textColour

    # Caption style
    @_check_types.do
    def SetCaptionStyle(self, style: int):
        """Execute the set caption style operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param style: Value for ``style``.
        :type style: int
        """
        self._captionStyle = style
        self._captionStyleUsed = True

    @_check_types.do
    def CaptionStyleUsed(self) -> bool:
        """Execute the caption style used operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self._captionStyleUsed

    @_check_types.do
    def GetCaptionStyle(self) -> int:
        """Execute the get caption style operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        return self._captionStyle


EmptyCaptionBarStyle = CaptionBarStyle()


# ---------------------------------------------------------------------------
# CaptionBar
# ---------------------------------------------------------------------------
class CaptionBar(QtWidgets.QWidget):
    """Clickable gradient caption strip with a collapse/expand arrow."""

    # Emitted when the user clicks to collapse or expand
    caption_toggled: QtCore.SignalInstance = QtCore.Signal(object)   # passes self (the CaptionBar)

    _ICON_W = 16
    _ICON_H = 16

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, caption: str = '',
                 cbstyle: CaptionBarStyle | None = None,
                 rightIndent: int = FPB_BMP_RIGHTSPACE,
                 collapsed: bool = False):
        """Initialise the :class:`CaptionBar` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`QWidget`
        :param caption: Value for ``caption``.
        :type caption: str
        :param cbstyle: Value for ``cbstyle``.
        :type cbstyle: CaptionBarStyle | None
        :param rightIndent: Value for ``rightIndent``.
        :type rightIndent: int
        :param collapsed: Value for ``collapsed``.
        :type collapsed: bool
        """

        super().__init__(parent)
        self.setMinimumSize(20, 20)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.setMouseTracking(True)

        self._caption = caption
        self._collapsed = collapsed
        self._rightIndent = rightIndent
        self._style: CaptionBarStyle = CaptionBarStyle()
        self._expanded_pm, self._collapsed_pm = _get_icons()

        self.ApplyCaptionStyle(cbstyle, applyDefault=True)

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------
    @_check_types.do
    def ApplyCaptionStyle(self, cbstyle: CaptionBarStyle | None = None,
                          applyDefault: bool = True):
        """Execute the apply caption style operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param cbstyle: Value for ``cbstyle``.
        :type cbstyle: CaptionBarStyle | None
        :param applyDefault: Value for ``applyDefault``.
        :type applyDefault: bool
        """
        if cbstyle is None:
            cbstyle = EmptyCaptionBarStyle

        if applyDefault:
            if not cbstyle.FirstColourUsed():
                cbstyle.SetFirstColour(QtGui.QColor(QtCore.Qt.GlobalColor.white))

            if not cbstyle.SecondColourUsed():

                if self.parent():
                    bg = self.parent().palette().color(self.parent().backgroundRole())
                else:
                    bg = QtGui.QColor(180, 180, 180)

                r = min(255, (bg.red() >> 1) + 20)
                g = min(255, (bg.green() >> 1) + 20)
                b = min(255, (bg.blue() >> 1) + 20)
                cbstyle.SetSecondColour(QtGui.QColor(r, g, b))

            if not cbstyle.CaptionColourUsed():
                cbstyle.SetCaptionColour(QtGui.QColor(QtCore.Qt.GlobalColor.black))

            if not cbstyle.CaptionFontUsed():
                cbstyle.SetCaptionFont(self.font())

            if not cbstyle.CaptionStyleUsed():
                cbstyle.SetCaptionStyle(CAPTIONBAR_GRADIENT_V)

        self._style = cbstyle
        self.update()

    @_check_types.do
    def SetCaptionStyle(self, cbstyle: CaptionBarStyle | None = None,
                        applyDefault: bool = True):
        """Execute the set caption style operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param cbstyle: Value for ``cbstyle``.
        :type cbstyle: CaptionBarStyle | None
        :param applyDefault: Value for ``applyDefault``.
        :type applyDefault: bool
        """

        self.ApplyCaptionStyle(cbstyle, applyDefault)

    @_check_types.do
    def GetCaptionStyle(self) -> CaptionBarStyle:
        """Execute the get caption style operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`CaptionBarStyle`
        """
        return self._style

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    @_check_types.do
    def IsCollapsed(self) -> bool:
        """Execute the is collapsed operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self._collapsed

    @_check_types.do
    def Collapse(self):
        """Execute the collapse operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._collapsed = True
        self.update()

    @_check_types.do
    def Expand(self):
        """Execute the expand operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._collapsed = False
        self.update()

    @_check_types.do
    def SetRightIndent(self, pixels: int):
        """Execute the set right indent operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param pixels: Value for ``pixels``.
        :type pixels: int
        """
        assert pixels >= 0
        self._rightIndent = pixels
        self.update()

    @_check_types.do
    def SetBoldFont(self):
        """Execute the set bold font operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        f = self.font()
        f.setBold(True)
        self.setFont(f)

    @_check_types.do
    def SetNormalFont(self):
        """Execute the set normal font operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        f = self.font()
        f.setBold(False)
        self.setFont(f)

    @_check_types.do
    def IsVertical(self) -> bool:
        """Execute the is vertical operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        bar = self._fold_panel_bar()
        if bar is not None:
            return bar.IsVertical()

        return True

    @_check_types.do
    def _fold_panel_bar(self) -> "FoldPanelBar":
        """Execute the fold panel bar operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`FoldPanelBar`
        """
        # CaptionBar -> FoldPanelItem -> (inner panel of) FoldPanelBar
        p = self.parent()
        while p is not None:
            if isinstance(p, FoldPanelBar):
                return p

            p = p.parent()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    @_check_types.do
    def sizeHint(self) -> QtCore.QSize:
        """Execute the size hint operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`QSize`
        """
        fm = QtGui.QFontMetrics(self._style.GetCaptionFont() or self.font())
        if self.IsVertical():
            tw = fm.horizontalAdvance(self._caption)
            th = fm.height()
        else:
            th = fm.horizontalAdvance(self._caption)
            tw = fm.height()
        w = max(tw, self._ICON_W) + FPB_EXTRA_X
        h = max(th, self._ICON_H) + FPB_EXTRA_Y
        return QtCore.QSize(w, h)

    @_check_types.do
    def paintEvent(self, event: QtGui.QPaintEvent):
        """Execute the paint event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: :class:`QPaintEvent`
        """
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, False)
        rect = self.rect()
        vertical = self.IsVertical()

        self._fill_background(painter, rect)

        # Draw caption text
        font = self._style.GetCaptionFont() or self.font()
        painter.setFont(font)
        painter.setPen(
            QtGui.QPen(self._style.GetCaptionColour() or
                       QtGui.QColor(QtCore.Qt.GlobalColor.black)))

        if vertical:
            painter.drawText(4, FPB_EXTRA_Y // 2,
                             rect.width(), rect.height(),
                             QtCore.Qt.AlignmentFlag.AlignVCenter |
                             QtCore.Qt.AlignmentFlag.AlignLeft,
                             self._caption)
        else:
            painter.save()
            painter.translate(FPB_EXTRA_Y // 2, rect.bottom() - 4)
            painter.rotate(-90)
            painter.drawText(0, 0, self._caption)
            painter.restore()

        # Draw collapse/expand icon
        pm = self._collapsed_pm if self._collapsed else self._expanded_pm
        if not pm.isNull():
            iw, ih = pm.width(), pm.height()
            if vertical:
                x = rect.right() - iw - self._rightIndent
                y = (rect.height() - ih) // 2
            else:
                x = (rect.width() - iw) // 2
                y = self._rightIndent

            painter.drawPixmap(x, y, pm)

        painter.end()

    @_check_types.do
    def _fill_background(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        """Execute the fill background operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param painter: Value for ``painter``.
        :type painter: :class:`QPainter`
        :param rect: Value for ``rect``.
        :type rect: :class:`QRect`
        """
        style = self._style.GetCaptionStyle()
        c1 = self._style.GetFirstColour() or QtGui.QColor(QtCore.Qt.GlobalColor.white)
        c2 = self._style.GetSecondColour() or QtGui.QColor(180, 180, 180)
        vertical = self.IsVertical()

        if style == CAPTIONBAR_GRADIENT_V:
            grad = QtGui.QLinearGradient(rect.left(), rect.top(),
                                         rect.left() if vertical else rect.right(),
                                         rect.bottom() if vertical else rect.top())

            grad.setColorAt(0.0, c1)
            grad.setColorAt(1.0, c2)
            painter.fillRect(rect, QtGui.QBrush(grad))

        elif style == CAPTIONBAR_GRADIENT_H:
            grad = QtGui.QLinearGradient(rect.left(), rect.top(),
                                         rect.right() if vertical else rect.left(),
                                         rect.top() if vertical else rect.bottom())

            grad.setColorAt(0.0, c1)
            grad.setColorAt(1.0, c2)
            painter.fillRect(rect, QtGui.QBrush(grad))

        elif style == CAPTIONBAR_SINGLE:
            painter.fillRect(rect, QtGui.QBrush(c1))

        elif style in (CAPTIONBAR_RECTANGLE, CAPTIONBAR_FILLED_RECTANGLE):
            if style == CAPTIONBAR_RECTANGLE:
                fill = self.parent().palette().window().color()
            else:
                fill = c1

            painter.fillRect(rect, QtGui.QBrush(fill))
            painter.setPen(QtGui.QPen(c2))
            painter.drawRect(rect.adjusted(0, 0, -1, -2))

        else:
            painter.fillRect(rect, QtGui.QBrush(c1))

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------
    @_check_types.do
    def _icon_hit(self, pos: QtCore.QPoint) -> bool:
        """Execute the icon hit operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param pos: Value for ``pos``.
        :type pos: :class:`QPoint`
        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        rect = self.rect()
        iw = self._ICON_W
        vertical = self.IsVertical()
        if vertical:
            drw = rect.width() - iw - self._rightIndent
            return pos.x() > drw

        return pos.y() < (self._ICON_H + self._rightIndent)

    @_check_types.do
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Execute the mouse press event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: :class:`QMouseEvent`
        """
        if (
            event.button() == QtCore.Qt.MouseButton.LeftButton and
            self._icon_hit(event.position().toPoint())
        ):
            self.caption_toggled.emit(self)

        super().mousePressEvent(event)

    @_check_types.do
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        """Execute the mouse double click event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: :class:`QMouseEvent`
        """
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.caption_toggled.emit(self)
        super().mouseDoubleClickEvent(event)

    @_check_types.do
    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Execute the mouse move event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: :class:`QMouseEvent`
        """
        if self._icon_hit(event.position().toPoint()):
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        else:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        super().mouseMoveEvent(event)

    @_check_types.do
    def leaveEvent(self, event):
        """Execute the leave event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        super().leaveEvent(event)


# ---------------------------------------------------------------------------
# FoldWindowItem  (pure data / geometry helper — no wx base class)
# ---------------------------------------------------------------------------
class FoldWindowItem:
    """Tracks a single child (window or separator) inside a FoldPanelItem."""

    @_check_types.do
    def __init__(self, parent: 'FoldPanelItem', window: QtWidgets.QWidget | None, **kw):
        """Initialise the :class:`FoldWindowItem` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`FoldPanelItem`
        :param window: Value for ``window``.
        :type window: QWidget | None
        :param kw: Value for ``kw``.
        :type kw: UNKNOWN
        :raises ValueError: Raised when the operation cannot be completed.
        """
        typ = kw.get('Type')

        if typ not in ('WINDOW', 'SEPARATOR'):
            raise ValueError(
                f'FoldWindowItem Type must be WINDOW or SEPARATOR, got {typ!r}')

        self._type = typ
        self._parent = parent
        self._wnd = window
        self._flags = kw.get('flags', FPB_ALIGN_WIDTH)
        self._spacing = kw.get('spacing', FPB_DEFAULT_SPACING)
        self._leftSpacing = kw.get('leftSpacing', FPB_DEFAULT_LEFTSPACING)
        self._rightSpacing = kw.get('rightSpacing', FPB_DEFAULT_RIGHTSPACING)
        self._lineY = kw.get('y',          0)
        self._sepLineColour = kw.get('colour',  QtGui.QColor(QtCore.Qt.GlobalColor.black))
        self._lineLength = 0

    @_check_types.do
    def GetType(self) -> str:
        """Execute the get type operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._type

    @_check_types.do
    def GetLineY(self) -> int:
        """Execute the get line y operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        return self._lineY

    @_check_types.do
    def GetLineLength(self) -> int:
        """Execute the get line length operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        return self._lineLength

    @_check_types.do
    def GetLineColour(self) -> QtGui.QColor:
        """Execute the get line colour operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`QColor`
        """
        return self._sepLineColour

    @_check_types.do
    def GetLeftSpacing(self) -> int:
        """Execute the get left spacing operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        return self._leftSpacing

    @_check_types.do
    def GetRightSpacing(self) -> int:
        """Execute the get right spacing operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        return self._rightSpacing

    @_check_types.do
    def GetSpacing(self) -> int:
        """Execute the get spacing operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        return self._spacing

    @_check_types.do
    def GetWindowLength(self, vertical: bool = True) -> int:
        """Execute the get window length operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param vertical: Value for ``vertical``.
        :type vertical: bool
        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        if self._type == 'WINDOW' and self._wnd:
            sz = self._wnd.size()

            if vertical:
                return sz.height() + self._spacing

            return sz.width() + self._spacing

        elif self._type == 'SEPARATOR':
            return 1 + self._spacing

        return 0

    @_check_types.do
    def ResizeItem(self, size: int, vertical: bool = True):
        """Execute the resize item operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param size: Value for ``size``.
        :type size: int
        :param vertical: Value for ``vertical``.
        :type vertical: bool
        """
        if self._flags & FPB_ALIGN_WIDTH:
            my_size = max(10, size - self._leftSpacing - self._rightSpacing)

            if self._type == 'SEPARATOR':
                self._lineLength = my_size
            elif self._wnd:
                if vertical:
                    self._wnd.setFixedWidth(my_size)
                else:
                    self._wnd.setFixedHeight(my_size)


# ---------------------------------------------------------------------------
# FoldPanelItem
# ---------------------------------------------------------------------------
class FoldPanelItem(QtWidgets.QWidget):
    """One collapsible section (caption bar + content area)."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, caption: str = '',
                 cbstyle: CaptionBarStyle | None = None,
                 collapsed: bool = False):
        """Initialise the :class:`FoldPanelItem` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`QWidget`
        :param caption: Value for ``caption``.
        :type caption: str
        :param cbstyle: Value for ``cbstyle``.
        :type cbstyle: CaptionBarStyle | None
        :param collapsed: Value for ``collapsed``.
        :type collapsed: bool
        """

        super().__init__(parent)
        self.setMinimumSize(1, 1)

        self._UserSize = 0
        self._PanelSize = 0
        self._LastInsertPos = 0
        self._itemPos = 0
        self._userSized = False
        self._items: list[FoldWindowItem] = []

        if cbstyle is None:
            cbstyle = EmptyCaptionBarStyle

        self._captionBar = CaptionBar(self, caption=caption, cbstyle=cbstyle,
                                      collapsed=collapsed)

        self._captionBar.caption_toggled.connect(self._on_caption_toggle)

        # Initial panel size = caption height
        self._PanelSize = self._captionBar.sizeHint().height()
        self._LastInsertPos = self._PanelSize

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    @_check_types.do
    def _on_caption_toggle(self, bar: CaptionBar):
        """Handle the caption toggle event.

        UNKNOWN details are inferred from the callable name and signature.

        :param bar: Value for ``bar``.
        :type bar: :class:`CaptionBar`
        """
        # Bubble up to FoldPanelBar
        fpb = self._fold_panel_bar()
        if fpb is None:
            return

        if bar.IsCollapsed():
            fpb.Expand(self)
        else:
            fpb.Collapse(self)

    @_check_types.do
    def _fold_panel_bar(self) -> "FoldPanelBar":
        """Execute the fold panel bar operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`FoldPanelBar`
        """
        p = self.parent()
        while p is not None:
            if isinstance(p, FoldPanelBar):
                return p

            p = p.parent()

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------
    @_check_types.do
    def IsVertical(self) -> bool:
        """Execute the is vertical operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        fpb = self._fold_panel_bar()
        if fpb:
            return fpb.IsVertical()

        return True

    @_check_types.do
    def IsExpanded(self) -> bool:
        """Execute the is expanded operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return not self._captionBar.IsCollapsed()

    @_check_types.do
    def GetItemPos(self) -> int:
        """Execute the get item pos operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        return self._itemPos

    @_check_types.do
    def GetPanelLength(self) -> int:
        """Execute the get panel length operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        if self._captionBar.IsCollapsed():
            return self.GetCaptionLength()

        if self._userSized:
            return self._UserSize

        return self._PanelSize

    @_check_types.do
    def GetCaptionLength(self) -> int:
        """Execute the get caption length operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        sz = self._captionBar.sizeHint()

        if self.IsVertical():
            return sz.height()

        return sz.width()

    @_check_types.do
    def Reposition(self, pos: int) -> int:
        """Execute the reposition operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param pos: Value for ``pos``.
        :type pos: int
        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        vertical = self.IsVertical()
        if vertical:
            self.move(0, pos)
        else:
            self.move(pos, 0)

        self._itemPos = pos

        return self.GetPanelLength()

    @_check_types.do
    def ResizePanel(self):
        """Execute the resize panel operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        vertical = self.IsVertical()
        parent_size = self.parent().size()

        if self._captionBar.IsCollapsed():
            cap_len = self.GetCaptionLength()
            self._PanelSize = cap_len

            if vertical:
                self.resize(parent_size.width(), cap_len)
                self._captionBar.resize(parent_size.width(),
                                        self._captionBar.sizeHint().height())
            else:
                self.resize(cap_len, parent_size.height())
                self._captionBar.resize(self._captionBar.sizeHint().width(),
                                        parent_size.height())
        else:
            if vertical:
                cap_h = self._captionBar.sizeHint().height()
            else:
                cap_h = self._captionBar.sizeHint().width()

            content_len = self._LastInsertPos
            total = cap_h + content_len
            self._PanelSize = total

            if self._UserSize:
                total = self._UserSize

            if vertical:
                self.resize(parent_size.width(), total)
                self._captionBar.resize(parent_size.width(), cap_h)
            else:
                self.resize(total, parent_size.height())
                self._captionBar.resize(cap_h, parent_size.height())

            # Resize child windows
            if vertical:
                available = parent_size.width()
            else:
                available = parent_size.height()

            for item in self._items:
                item.ResizeItem(available, vertical)

        self.update()

    # ------------------------------------------------------------------
    # Adding content
    # ------------------------------------------------------------------
    @_check_types.do
    def AddWindow(self, window: QtWidgets.QWidget, flags: int = FPB_ALIGN_WIDTH,
                  spacing: int = FPB_DEFAULT_SPACING,
                  leftSpacing: int = FPB_DEFAULT_LEFTLINESPACING,
                  rightSpacing: int = FPB_DEFAULT_RIGHTLINESPACING):
        """Execute the add window operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param window: Value for ``window``.
        :type window: :class:`QWidget`
        :param flags: Value for ``flags``.
        :type flags: int
        :param spacing: Value for ``spacing``.
        :type spacing: int
        :param leftSpacing: Value for ``leftSpacing``.
        :type leftSpacing: int
        :param rightSpacing: Value for ``rightSpacing``.
        :type rightSpacing: int
        """

        wi = FoldWindowItem(self, window, Type='WINDOW', flags=flags,
                            spacing=spacing, leftSpacing=leftSpacing,
                            rightSpacing=rightSpacing)

        self._items.append(wi)
        window.setParent(self)

        vertical = self.IsVertical()

        if vertical:
            xpos = leftSpacing
            ypos = self._LastInsertPos + spacing
        else:
            xpos = self._LastInsertPos + spacing
            ypos = leftSpacing

        window.move(xpos, ypos)
        window.show()

        self._LastInsertPos += wi.GetWindowLength(vertical)
        self.ResizePanel()

    @_check_types.do
    def AddSeparator(self, colour: QtGui.QColor = None, spacing: int = FPB_DEFAULT_SPACING,
                     leftSpacing: int = FPB_DEFAULT_LEFTSPACING,
                     rightSpacing: int = FPB_DEFAULT_RIGHTSPACING):
        """Execute the add separator operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param colour: Value for ``colour``.
        :type colour: :class:`QColor`
        :param spacing: Value for ``spacing``.
        :type spacing: int
        :param leftSpacing: Value for ``leftSpacing``.
        :type leftSpacing: int
        :param rightSpacing: Value for ``rightSpacing``.
        :type rightSpacing: int
        """

        if colour is None:
            colour = QtGui.QColor(QtCore.Qt.GlobalColor.black)

        wi = FoldWindowItem(self, window=None, Type='SEPARATOR',
                            flags=FPB_ALIGN_WIDTH, y=self._LastInsertPos,
                            colour=colour, spacing=spacing,
                            leftSpacing=leftSpacing, rightSpacing=rightSpacing)

        self._items.append(wi)
        self._LastInsertPos += wi.GetWindowLength(self.IsVertical())
        self.ResizePanel()

    # ------------------------------------------------------------------
    # Style delegation
    # ------------------------------------------------------------------
    @_check_types.do
    def ApplyCaptionStyle(self, cbstyle: CaptionBarStyle):
        """Execute the apply caption style operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param cbstyle: Value for ``cbstyle``.
        :type cbstyle: :class:`CaptionBarStyle`
        """
        self._captionBar.SetCaptionStyle(cbstyle)

    @_check_types.do
    def GetCaptionStyle(self) -> CaptionBarStyle:
        """Execute the get caption style operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`CaptionBarStyle`
        """
        return self._captionBar.GetCaptionStyle()

    # ------------------------------------------------------------------
    # Collapse / Expand (called by FoldPanelBar)
    # ------------------------------------------------------------------
    @_check_types.do
    def Collapse(self):
        """Execute the collapse operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._captionBar.Collapse()
        self.ResizePanel()

    @_check_types.do
    def Expand(self):
        """Execute the expand operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._captionBar.Expand()
        self.ResizePanel()

    # ------------------------------------------------------------------
    # Paint separators
    # ------------------------------------------------------------------
    @_check_types.do
    def paintEvent(self, event: QtGui.QPaintEvent):
        """Execute the paint event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: :class:`QPaintEvent`
        """
        painter = QtGui.QPainter(self)
        vertical = self.IsVertical()

        for item in self._items:
            if item.GetType() == 'SEPARATOR':
                painter.setPen(
                    QtGui.QPen(item.GetLineColour(), 1, QtCore.Qt.PenStyle.SolidLine))

                a = item.GetLeftSpacing()
                b = item.GetLineY() + item.GetSpacing()
                c = item.GetLineLength()
                d = a + c

                if vertical:
                    painter.drawLine(a, b, d, b)
                else:
                    painter.drawLine(b, a, b, d)

        painter.end()


# ---------------------------------------------------------------------------
# FoldPanelBar
# ---------------------------------------------------------------------------
class FoldPanelBar(QtWidgets.QWidget):
    """Container for multiple collapsible FoldPanelItem sections.

    Replacement for wx.lib.agw.foldpanelbar.FoldPanelBar.
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None, agwStyle: int = 0):
        """Initialise the :class:`FoldPanelBar` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: QWidget | None
        :param agwStyle: Value for ``agwStyle``.
        :type agwStyle: int
        """
        super().__init__(parent)

        if not agwStyle & (FPB_HORIZONTAL | FPB_VERTICAL):
            agwStyle |= FPB_VERTICAL

        self._isVertical = bool(agwStyle & FPB_VERTICAL)
        self._agwStyle = agwStyle
        self._panels: list[FoldPanelItem] = []
        self._cbstyle: CaptionBarStyle | None = None

        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                           QtWidgets.QSizePolicy.Policy.Expanding)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @_check_types.do
    def IsVertical(self) -> bool:
        """Execute the is vertical operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self._isVertical

    @_check_types.do
    def AddFoldPanel(self, caption: str = '', collapsed: bool = False,
                     foldIcons=None,   # NOQA IGNORED
                     cbstyle: CaptionBarStyle | None = None) -> FoldPanelItem:
        """Execute the add fold panel operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param caption: Value for ``caption``.
        :type caption: str
        :param collapsed: Value for ``collapsed``.
        :type collapsed: bool
        :param foldIcons: Value for ``foldIcons``.
        :type foldIcons: UNKNOWN
        :param cbstyle: Value for ``cbstyle``.
        :type cbstyle: CaptionBarStyle | None
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`FoldPanelItem`
        """

        if cbstyle is None:
            cbstyle = EmptyCaptionBarStyle
        else:
            cbstyle = self._cbstyle

        item = FoldPanelItem(
            self, caption=caption, cbstyle=cbstyle, collapsed=collapsed)

        pos = 0
        if self._panels:
            last = self._panels[-1]
            pos = last.GetItemPos() + last.GetPanelLength()

        item.Reposition(pos)
        item.show()
        self._panels.append(item)

        return item

    @_check_types.do
    def AddFoldPanelWindow(self, panel: FoldPanelItem, window: QtWidgets.QWidget,
                           flags: int = FPB_ALIGN_WIDTH,
                           spacing: int = FPB_DEFAULT_SPACING,
                           leftSpacing: int = FPB_DEFAULT_LEFTLINESPACING,
                           rightSpacing: int = FPB_DEFAULT_RIGHTLINESPACING) -> int:
        """Execute the add fold panel window operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param panel: Value for ``panel``.
        :type panel: :class:`FoldPanelItem`
        :param window: Value for ``window``.
        :type window: :class:`QWidget`
        :param flags: Value for ``flags``.
        :type flags: int
        :param spacing: Value for ``spacing``.
        :type spacing: int
        :param leftSpacing: Value for ``leftSpacing``.
        :type leftSpacing: int
        :param rightSpacing: Value for ``rightSpacing``.
        :type rightSpacing: int
        :returns: Return value. UNKNOWN details.
        :rtype: int
        :raises ValueError: Raised when the operation cannot be completed.
        """

        if panel not in self._panels:
            raise ValueError(
                f'Invalid panel passed to AddFoldPanelWindow: {panel!r}')

        panel.AddWindow(window, flags, spacing, leftSpacing, rightSpacing)

        return 0

    @_check_types.do
    def AddFoldPanelSeparator(self, panel: FoldPanelItem, colour: QtGui.QColor | None = None,
                              spacing: int = FPB_DEFAULT_SPACING,
                              leftSpacing: int = FPB_DEFAULT_LEFTLINESPACING,
                              rightSpacing: int = FPB_DEFAULT_RIGHTLINESPACING) -> int:
        """Execute the add fold panel separator operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param panel: Value for ``panel``.
        :type panel: :class:`FoldPanelItem`
        :param colour: Value for ``colour``.
        :type colour: QColor | None
        :param spacing: Value for ``spacing``.
        :type spacing: int
        :param leftSpacing: Value for ``leftSpacing``.
        :type leftSpacing: int
        :param rightSpacing: Value for ``rightSpacing``.
        :type rightSpacing: int
        :returns: Return value. UNKNOWN details.
        :rtype: int
        :raises ValueError: Raised when the operation cannot be completed.
        """

        if panel not in self._panels:
            raise ValueError(
                f'Invalid panel passed to AddFoldPanelSeparator: {panel!r}')

        panel.AddSeparator(colour, spacing, leftSpacing, rightSpacing)

        return 0

    @_check_types.do
    def Collapse(self, foldpanel: FoldPanelItem):
        """Execute the collapse operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param foldpanel: Value for ``foldpanel``.
        :type foldpanel: :class:`FoldPanelItem`
        :raises ValueError: Raised when the operation cannot be completed.
        """
        if foldpanel not in self._panels:
            raise ValueError(
                f'Invalid panel passed to Collapse: {foldpanel!r}')

        foldpanel.Collapse()
        self.RefreshPanelsFrom(foldpanel)

    @_check_types.do
    def Expand(self, foldpanel: FoldPanelItem):
        """Execute the expand operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param foldpanel: Value for ``foldpanel``.
        :type foldpanel: :class:`FoldPanelItem`
        :raises ValueError: Raised when the operation cannot be completed.
        """
        if foldpanel not in self._panels:
            raise ValueError(f'Invalid panel passed to Expand: {foldpanel!r}')

        if self._agwStyle & (FPB_SINGLE_FOLD | FPB_EXCLUSIVE_FOLD):
            for p in self._panels:
                p.Collapse()

        foldpanel.Expand()

        if self._agwStyle & FPB_EXCLUSIVE_FOLD:
            self.RepositionCollapsedToBottom()
            self.RefreshPanelsFrom(self._panels[0])
        elif self._agwStyle & FPB_SINGLE_FOLD:
            self.RefreshPanelsFrom(self._panels[0])
        else:
            self.RefreshPanelsFrom(foldpanel)

    @_check_types.do
    def ApplyCaptionStyle(self, foldpanel: FoldPanelItem,  # NOQA
                          cbstyle: CaptionBarStyle):
        """Execute the apply caption style operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param foldpanel: Value for ``foldpanel``.
        :type foldpanel: :class:`FoldPanelItem`
        :param cbstyle: Value for ``cbstyle``.
        :type cbstyle: :class:`CaptionBarStyle`
        """

        foldpanel.ApplyCaptionStyle(cbstyle)

    @_check_types.do
    def ApplyCaptionStyleAll(self, cbstyle: CaptionBarStyle):
        """Execute the apply caption style all operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param cbstyle: Value for ``cbstyle``.
        :type cbstyle: :class:`CaptionBarStyle`
        """
        for p in self._panels:
            self.ApplyCaptionStyle(p, cbstyle)

        self._cbstyle = cbstyle

    @_check_types.do
    def GetCaptionStyle(self, foldpanel: FoldPanelItem) -> CaptionBarStyle:  # NOQA
        """Execute the get caption style operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param foldpanel: Value for ``foldpanel``.
        :type foldpanel: :class:`FoldPanelItem`
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`CaptionBarStyle`
        """
        return foldpanel.GetCaptionStyle()

    @_check_types.do
    def GetFoldPanel(self, item: int) -> FoldPanelItem:
        """Execute the get fold panel operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: int
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`FoldPanelItem`
        :raises ValueError: Raised when the operation cannot be completed.
        """
        try:
            return self._panels[item]
        except IndexError:
            raise ValueError(
                f'Index {item} out of range (0..{len(self._panels)-1})')

    @_check_types.do
    def GetCount(self) -> int:
        """Execute the get count operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        return len(self._panels)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    @_check_types.do
    def RefreshPanelsFrom(self, item: FoldPanelItem):
        """Execute the refresh panels from operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: :class:`FoldPanelItem`
        :raises ValueError: Raised when the operation cannot be completed.
        """
        try:
            i = self._panels.index(item)
        except ValueError:
            raise ValueError(
                f'Invalid panel passed to RefreshPanelsFrom: {item!r}')

        if self._agwStyle & (FPB_COLLAPSE_TO_BOTTOM | FPB_EXCLUSIVE_FOLD):
            offset = 0
            for p in self._panels:
                if p.IsExpanded():
                    offset += p.Reposition(offset)

            self.RepositionCollapsedToBottom()
        else:
            pos = self._panels[i].GetItemPos() + self._panels[i].GetPanelLength()
            for j in range(i + 1, len(self._panels)):
                pos += self._panels[j].Reposition(pos)

        self.update()

    @_check_types.do
    def RepositionCollapsedToBottom(self):
        """Execute the reposition collapsed to bottom operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        vertical = self._isVertical
        total = self.height() if vertical else self.width()

        collapsed_len, expanded_len, _ = (
            self.GetPanelsLength(0, 0))

        if total - expanded_len - collapsed_len < 0:
            offset = expanded_len
        else:
            offset = total - collapsed_len

        for p in self._panels:
            if not p.IsExpanded():
                offset += p.Reposition(offset)

    @_check_types.do
    def GetPanelsLength(self, collapsed: int, expanded: int):
        """Execute the get panels length operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param collapsed: Value for ``collapsed``.
        :type collapsed: int
        :param expanded: Value for ``expanded``.
        :type expanded: int
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        value = 0
        for p in self._panels:
            length = p.GetPanelLength()
            value += length

            if p.IsExpanded():
                expanded += length
            else:
                collapsed += length

        return collapsed, expanded, value

    @_check_types.do
    def RedisplayFoldPanelItems(self):
        """Execute the redisplay fold panel items operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        for p in self._panels:
            p.ResizePanel()
            p.update()

    # ------------------------------------------------------------------
    # Qt events
    # ------------------------------------------------------------------
    @_check_types.do
    def resizeEvent(self, event: QtGui.QResizeEvent):
        """Execute the resize event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: :class:`QResizeEvent`
        """
        super().resizeEvent(event)

        if self._agwStyle & (FPB_COLLAPSE_TO_BOTTOM | FPB_EXCLUSIVE_FOLD):
            self.RepositionCollapsedToBottom()

        self.RedisplayFoldPanelItems()
