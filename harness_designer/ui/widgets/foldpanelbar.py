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

import math
import base64

from PySide6.QtWidgets import QWidget, QScrollArea, QSizePolicy
from PySide6.QtCore import Qt, Signal, QSize, QRect, QPoint
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics,
    QLinearGradient, QPixmap, QImage, QPaintEvent,
    QMouseEvent, QResizeEvent, QCursor
)

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


def _load_icon_pixmap(b64: str) -> QPixmap:
    data = base64.b64decode(b64)
    img = QImage.fromData(data)
    return QPixmap.fromImage(img)


_EXPANDED_PIXMAP: QPixmap | None = None
_COLLAPSED_PIXMAP: QPixmap | None = None


def _get_icons() -> tuple[QPixmap, QPixmap]:
    global _EXPANDED_PIXMAP, _COLLAPSED_PIXMAP
    if _EXPANDED_PIXMAP is None:
        _EXPANDED_PIXMAP = _load_icon_pixmap(_EXPANDED_PNG_B64)
        _COLLAPSED_PIXMAP = _load_icon_pixmap(_COLLAPSED_PNG_B64)
    return _EXPANDED_PIXMAP, _COLLAPSED_PIXMAP


# ---------------------------------------------------------------------------
# Constants (identical values to the originals)
# ---------------------------------------------------------------------------
CAPTIONBAR_NOSTYLE          = 0
CAPTIONBAR_GRADIENT_V       = 1
CAPTIONBAR_GRADIENT_H       = 2
CAPTIONBAR_SINGLE           = 3
CAPTIONBAR_RECTANGLE        = 4
CAPTIONBAR_FILLED_RECTANGLE = 5

FPB_EXTRA_X           = 10
FPB_EXTRA_Y           = 4
FPB_BMP_RIGHTSPACE    = 2

FPB_SINGLE_FOLD       = 0x0001
FPB_COLLAPSE_TO_BOTTOM= 0x0002
FPB_EXCLUSIVE_FOLD    = 0x0004
FPB_HORIZONTAL        = 0x0008
FPB_VERTICAL          = 0x0010

FPB_ALIGN_LEFT        = 0
FPB_ALIGN_WIDTH       = 1

FPB_DEFAULT_LEFTSPACING    = 5
FPB_DEFAULT_RIGHTSPACING   = 10
FPB_DEFAULT_SPACING        = 8
FPB_DEFAULT_LEFTLINESPACING  = 2
FPB_DEFAULT_RIGHTLINESPACING = 2


# ---------------------------------------------------------------------------
# CaptionBarStyle  (pure Python — no wx types)
# ---------------------------------------------------------------------------
class CaptionBarStyle:
    """Encapsulates visual styles for a CaptionBar.  API identical to original."""

    def __init__(self):
        self._captionFont: QFont | None = None
        self._textColour:  QColor | None = None
        self._firstColour: QColor | None = None
        self._secondColour: QColor | None = None

        self._captionFontUsed   = False
        self._firstColourUsed   = False
        self._secondColourUsed  = False
        self._textColourUsed    = False
        self._captionStyleUsed  = False
        self._captionStyle      = CAPTIONBAR_GRADIENT_V

    def ResetDefaults(self):
        self._firstColourUsed   = False
        self._secondColourUsed  = False
        self._textColourUsed    = False
        self._captionFontUsed   = False
        self._captionStyleUsed  = False
        self._captionStyle      = CAPTIONBAR_GRADIENT_V

    # Font
    def SetCaptionFont(self, font: QFont):
        self._captionFont = font
        self._captionFontUsed = True

    def CaptionFontUsed(self) -> bool:
        return self._captionFontUsed

    def GetCaptionFont(self) -> QFont:
        return self._captionFont

    # First colour
    def SetFirstColour(self, colour: QColor):
        self._firstColour = colour
        self._firstColourUsed = True

    def FirstColourUsed(self) -> bool:
        return self._firstColourUsed

    def GetFirstColour(self) -> QColor:
        return self._firstColour

    # Second colour
    def SetSecondColour(self, colour: QColor):
        self._secondColour = colour
        self._secondColourUsed = True

    def SecondColourUsed(self) -> bool:
        return self._secondColourUsed

    def GetSecondColour(self) -> QColor:
        return self._secondColour

    # Caption (text) colour
    def SetCaptionColour(self, colour: QColor):
        self._textColour = colour
        self._textColourUsed = True

    def CaptionColourUsed(self) -> bool:
        return self._textColourUsed

    def GetCaptionColour(self) -> QColor:
        return self._textColour

    # Caption style
    def SetCaptionStyle(self, style: int):
        self._captionStyle = style
        self._captionStyleUsed = True

    def CaptionStyleUsed(self) -> bool:
        return self._captionStyleUsed

    def GetCaptionStyle(self) -> int:
        return self._captionStyle


EmptyCaptionBarStyle = CaptionBarStyle()


# ---------------------------------------------------------------------------
# CaptionBar
# ---------------------------------------------------------------------------
class CaptionBar(QWidget):
    """Clickable gradient caption strip with a collapse/expand arrow."""

    # Emitted when the user clicks to collapse or expand
    caption_toggled = Signal(object)   # passes self (the CaptionBar)

    _ICON_W = 16
    _ICON_H = 16

    def __init__(self, parent: QWidget, caption: str = '',
                 cbstyle: CaptionBarStyle | None = None,
                 rightIndent: int = FPB_BMP_RIGHTSPACE,
                 collapsed: bool = False):
        super().__init__(parent)
        self.setMinimumSize(20, 20)
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.setMouseTracking(True)

        self._caption   = caption
        self._collapsed = collapsed
        self._rightIndent = rightIndent
        self._style: CaptionBarStyle = CaptionBarStyle()
        self._expanded_pm, self._collapsed_pm = _get_icons()

        self.ApplyCaptionStyle(cbstyle, applyDefault=True)

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------
    def ApplyCaptionStyle(self, cbstyle: CaptionBarStyle | None = None,
                          applyDefault: bool = True):
        if cbstyle is None:
            cbstyle = EmptyCaptionBarStyle

        if applyDefault:
            if not cbstyle.FirstColourUsed():
                cbstyle.SetFirstColour(QColor(Qt.white))
            if not cbstyle.SecondColourUsed():
                bg = self.parent().palette().color(self.parent().backgroundRole()) \
                    if self.parent() else QColor(180, 180, 180)
                r = min(255, (bg.red()   >> 1) + 20)
                g = min(255, (bg.green() >> 1) + 20)
                b = min(255, (bg.blue()  >> 1) + 20)
                cbstyle.SetSecondColour(QColor(r, g, b))
            if not cbstyle.CaptionColourUsed():
                cbstyle.SetCaptionColour(QColor(Qt.black))
            if not cbstyle.CaptionFontUsed():
                cbstyle.SetCaptionFont(self.font())
            if not cbstyle.CaptionStyleUsed():
                cbstyle.SetCaptionStyle(CAPTIONBAR_GRADIENT_V)

        self._style = cbstyle
        self.update()

    def SetCaptionStyle(self, cbstyle: CaptionBarStyle | None = None,
                        applyDefault: bool = True):
        self.ApplyCaptionStyle(cbstyle, applyDefault)

    def GetCaptionStyle(self) -> CaptionBarStyle:
        return self._style

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def IsCollapsed(self) -> bool:
        return self._collapsed

    def Collapse(self):
        self._collapsed = True
        self.update()

    def Expand(self):
        self._collapsed = False
        self.update()

    def SetRightIndent(self, pixels: int):
        assert pixels >= 0
        self._rightIndent = pixels
        self.update()

    def SetBoldFont(self):
        f = self.font()
        f.setBold(True)
        self.setFont(f)

    def SetNormalFont(self):
        f = self.font()
        f.setBold(False)
        self.setFont(f)

    def IsVertical(self) -> bool:
        bar = self._fold_panel_bar()
        if bar is not None:
            return bar.IsVertical()
        return True

    def _fold_panel_bar(self) -> 'FoldPanelBar | None':
        # CaptionBar -> FoldPanelItem -> (inner panel of) FoldPanelBar
        p = self.parent()
        while p is not None:
            if isinstance(p, FoldPanelBar):
                return p
            p = p.parent()
        return None

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self._style.GetCaptionFont() or self.font())
        if self.IsVertical():
            tw = fm.horizontalAdvance(self._caption)
            th = fm.height()
        else:
            th = fm.horizontalAdvance(self._caption)
            tw = fm.height()
        w = max(tw, self._ICON_W) + FPB_EXTRA_X
        h = max(th, self._ICON_H) + FPB_EXTRA_Y
        return QSize(w, h)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        rect = self.rect()
        vertical = self.IsVertical()

        self._fill_background(painter, rect)

        # Draw caption text
        font = self._style.GetCaptionFont() or self.font()
        painter.setFont(font)
        painter.setPen(QPen(self._style.GetCaptionColour() or QColor(Qt.black)))

        if vertical:
            painter.drawText(4, FPB_EXTRA_Y // 2,
                             rect.width(), rect.height(),
                             Qt.AlignVCenter | Qt.AlignLeft,
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

    def _fill_background(self, painter: QPainter, rect: QRect):
        style = self._style.GetCaptionStyle()
        c1 = self._style.GetFirstColour()  or QColor(Qt.white)
        c2 = self._style.GetSecondColour() or QColor(180, 180, 180)
        vertical = self.IsVertical()

        if style == CAPTIONBAR_GRADIENT_V:
            grad = QLinearGradient(
                rect.left(), rect.top(),
                rect.left() if vertical else rect.right(),
                rect.bottom() if vertical else rect.top()
            )
            grad.setColorAt(0.0, c1)
            grad.setColorAt(1.0, c2)
            painter.fillRect(rect, QBrush(grad))

        elif style == CAPTIONBAR_GRADIENT_H:
            grad = QLinearGradient(
                rect.left(), rect.top(),
                rect.right() if vertical else rect.left(),
                rect.top() if vertical else rect.bottom()
            )
            grad.setColorAt(0.0, c1)
            grad.setColorAt(1.0, c2)
            painter.fillRect(rect, QBrush(grad))

        elif style == CAPTIONBAR_SINGLE:
            painter.fillRect(rect, QBrush(c1))

        elif style in (CAPTIONBAR_RECTANGLE, CAPTIONBAR_FILLED_RECTANGLE):
            fill = (self.parent().palette().window().color()
                    if style == CAPTIONBAR_RECTANGLE else c1)
            painter.fillRect(rect, QBrush(fill))
            painter.setPen(QPen(c2))
            painter.drawRect(rect.adjusted(0, 0, -1, -2))

        else:
            painter.fillRect(rect, QBrush(c1))

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------
    def _icon_hit(self, pos: QPoint) -> bool:
        rect = self.rect()
        iw = self._ICON_W
        vertical = self.IsVertical()
        if vertical:
            drw = rect.width() - iw - self._rightIndent
            return pos.x() > drw
        else:
            return pos.y() < (self._ICON_H + self._rightIndent)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._icon_hit(event.position().toPoint()):
            self.caption_toggled.emit(self)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.setCursor(QCursor(Qt.ArrowCursor))
            self.caption_toggled.emit(self)
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._icon_hit(event.position().toPoint()):
            self.setCursor(QCursor(Qt.PointingHandCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))
        super().leaveEvent(event)


# ---------------------------------------------------------------------------
# FoldWindowItem  (pure data / geometry helper — no wx base class)
# ---------------------------------------------------------------------------
class FoldWindowItem:
    """Tracks a single child (window or separator) inside a FoldPanelItem."""

    def __init__(self, parent: 'FoldPanelItem', window: QWidget | None, **kw):
        typ = kw.get('Type')
        if typ not in ('WINDOW', 'SEPARATOR'):
            raise ValueError(f'FoldWindowItem Type must be WINDOW or SEPARATOR, got {typ!r}')

        self._type       = typ
        self._parent     = parent
        self._wnd        = window
        self._flags      = kw.get('flags',      FPB_ALIGN_WIDTH)
        self._spacing    = kw.get('spacing',    FPB_DEFAULT_SPACING)
        self._leftSpacing  = kw.get('leftSpacing',  FPB_DEFAULT_LEFTSPACING)
        self._rightSpacing = kw.get('rightSpacing', FPB_DEFAULT_RIGHTSPACING)
        self._lineY      = kw.get('y',          0)
        self._sepLineColour = kw.get('colour',  QColor(Qt.black))
        self._lineLength = 0

    def GetType(self) -> str:
        return self._type

    def GetLineY(self) -> int:
        return self._lineY

    def GetLineLength(self) -> int:
        return self._lineLength

    def GetLineColour(self) -> QColor:
        return self._sepLineColour

    def GetLeftSpacing(self) -> int:
        return self._leftSpacing

    def GetRightSpacing(self) -> int:
        return self._rightSpacing

    def GetSpacing(self) -> int:
        return self._spacing

    def GetWindowLength(self, vertical: bool = True) -> int:
        if self._type == 'WINDOW' and self._wnd:
            sz = self._wnd.size()
            return (sz.height() if vertical else sz.width()) + self._spacing
        elif self._type == 'SEPARATOR':
            return 1 + self._spacing
        return 0

    def ResizeItem(self, size: int, vertical: bool = True):
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
class FoldPanelItem(QWidget):
    """One collapsible section (caption bar + content area)."""

    def __init__(self, parent: QWidget, caption: str = '',
                 cbstyle: CaptionBarStyle | None = None,
                 collapsed: bool = False):
        super().__init__(parent)
        self.setMinimumSize(1, 1)

        self._UserSize    = 0
        self._PanelSize   = 0
        self._LastInsertPos = 0
        self._itemPos     = 0
        self._userSized   = False
        self._items: list[FoldWindowItem] = []

        if cbstyle is None:
            cbstyle = EmptyCaptionBarStyle

        self._captionBar = CaptionBar(self, caption=caption, cbstyle=cbstyle,
                                      collapsed=collapsed)
        self._captionBar.caption_toggled.connect(self._on_caption_toggle)

        # Initial panel size = caption height
        self._PanelSize   = self._captionBar.sizeHint().height()
        self._LastInsertPos = self._PanelSize

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_caption_toggle(self, bar: CaptionBar):
        # Bubble up to FoldPanelBar
        fpb = self._fold_panel_bar()
        if fpb is None:
            return
        if bar.IsCollapsed():
            fpb.Expand(self)
        else:
            fpb.Collapse(self)

    def _fold_panel_bar(self) -> 'FoldPanelBar | None':
        p = self.parent()
        while p is not None:
            if isinstance(p, FoldPanelBar):
                return p
            p = p.parent()
        return None

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------
    def IsVertical(self) -> bool:
        fpb = self._fold_panel_bar()
        return fpb.IsVertical() if fpb else True

    def IsExpanded(self) -> bool:
        return not self._captionBar.IsCollapsed()

    def GetItemPos(self) -> int:
        return self._itemPos

    def GetPanelLength(self) -> int:
        if self._captionBar.IsCollapsed():
            return self.GetCaptionLength()
        if self._userSized:
            return self._UserSize
        return self._PanelSize

    def GetCaptionLength(self) -> int:
        sz = self._captionBar.sizeHint()
        return sz.height() if self.IsVertical() else sz.width()

    def Reposition(self, pos: int) -> int:
        vertical = self.IsVertical()
        if vertical:
            self.move(0, pos)
        else:
            self.move(pos, 0)
        self._itemPos = pos
        return self.GetPanelLength()

    def ResizePanel(self):
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
            cap_h = self._captionBar.sizeHint().height() if vertical \
                else self._captionBar.sizeHint().width()
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
            available = parent_size.width() if vertical else parent_size.height()
            for item in self._items:
                item.ResizeItem(available, vertical)

        self.update()

    # ------------------------------------------------------------------
    # Adding content
    # ------------------------------------------------------------------
    def AddWindow(self, window: QWidget,
                  flags: int = FPB_ALIGN_WIDTH,
                  spacing: int = FPB_DEFAULT_SPACING,
                  leftSpacing: int = FPB_DEFAULT_LEFTLINESPACING,
                  rightSpacing: int = FPB_DEFAULT_RIGHTLINESPACING):
        wi = FoldWindowItem(self, window, Type='WINDOW', flags=flags,
                            spacing=spacing, leftSpacing=leftSpacing,
                            rightSpacing=rightSpacing)
        self._items.append(wi)
        window.setParent(self)

        vertical = self.IsVertical()
        cap_h = self._captionBar.sizeHint().height() if vertical \
            else self._captionBar.sizeHint().width()

        xpos = leftSpacing if vertical else self._LastInsertPos + spacing
        ypos = self._LastInsertPos + spacing if vertical else leftSpacing
        window.move(xpos, ypos)
        window.show()

        self._LastInsertPos += wi.GetWindowLength(vertical)
        self.ResizePanel()

    def AddSeparator(self, colour: QColor = None,
                     spacing: int = FPB_DEFAULT_SPACING,
                     leftSpacing: int = FPB_DEFAULT_LEFTSPACING,
                     rightSpacing: int = FPB_DEFAULT_RIGHTSPACING):
        if colour is None:
            colour = QColor(Qt.black)
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
    def ApplyCaptionStyle(self, cbstyle: CaptionBarStyle):
        self._captionBar.SetCaptionStyle(cbstyle)

    def GetCaptionStyle(self) -> CaptionBarStyle:
        return self._captionBar.GetCaptionStyle()

    # ------------------------------------------------------------------
    # Collapse / Expand (called by FoldPanelBar)
    # ------------------------------------------------------------------
    def Collapse(self):
        self._captionBar.Collapse()
        self.ResizePanel()

    def Expand(self):
        self._captionBar.Expand()
        self.ResizePanel()

    # ------------------------------------------------------------------
    # Paint separators
    # ------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        vertical = self.IsVertical()

        for item in self._items:
            if item.GetType() == 'SEPARATOR':
                painter.setPen(QPen(item.GetLineColour(), 1, Qt.SolidLine))
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
class FoldPanelBar(QWidget):
    """Container for multiple collapsible FoldPanelItem sections.

    Replacement for wx.lib.agw.foldpanelbar.FoldPanelBar.
    """

    def __init__(self, parent: QWidget | None = None, agwStyle: int = 0):
        super().__init__(parent)

        if not agwStyle & (FPB_HORIZONTAL | FPB_VERTICAL):
            agwStyle |= FPB_VERTICAL

        self._isVertical = bool(agwStyle & FPB_VERTICAL)
        self._agwStyle   = agwStyle
        self._panels: list[FoldPanelItem] = []
        self._cbstyle: CaptionBarStyle | None = None

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def IsVertical(self) -> bool:
        return self._isVertical

    def AddFoldPanel(self, caption: str = '', collapsed: bool = False,
                     foldIcons=None,   # ignored — we use our own embedded icons
                     cbstyle: CaptionBarStyle | None = None) -> FoldPanelItem:
        if cbstyle is None:
            cbstyle = self._cbstyle if self._cbstyle is not None else EmptyCaptionBarStyle

        item = FoldPanelItem(self, caption=caption, cbstyle=cbstyle,
                             collapsed=collapsed)

        pos = 0
        if self._panels:
            last = self._panels[-1]
            pos = last.GetItemPos() + last.GetPanelLength()

        item.Reposition(pos)
        item.show()
        self._panels.append(item)
        return item

    def AddFoldPanelWindow(self, panel: FoldPanelItem, window: QWidget,
                           flags: int = FPB_ALIGN_WIDTH,
                           spacing: int = FPB_DEFAULT_SPACING,
                           leftSpacing: int = FPB_DEFAULT_LEFTLINESPACING,
                           rightSpacing: int = FPB_DEFAULT_RIGHTLINESPACING) -> int:
        if panel not in self._panels:
            raise ValueError(f'Invalid panel passed to AddFoldPanelWindow: {panel!r}')
        panel.AddWindow(window, flags, spacing, leftSpacing, rightSpacing)
        return 0

    def AddFoldPanelSeparator(self, panel: FoldPanelItem,
                               colour: QColor | None = None,
                               spacing: int = FPB_DEFAULT_SPACING,
                               leftSpacing: int = FPB_DEFAULT_LEFTLINESPACING,
                               rightSpacing: int = FPB_DEFAULT_RIGHTLINESPACING) -> int:
        if panel not in self._panels:
            raise ValueError(f'Invalid panel passed to AddFoldPanelSeparator: {panel!r}')
        panel.AddSeparator(colour, spacing, leftSpacing, rightSpacing)
        return 0

    def Collapse(self, foldpanel: FoldPanelItem):
        if foldpanel not in self._panels:
            raise ValueError(f'Invalid panel passed to Collapse: {foldpanel!r}')
        foldpanel.Collapse()
        self.RefreshPanelsFrom(foldpanel)

    def Expand(self, foldpanel: FoldPanelItem):
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

    def ApplyCaptionStyle(self, foldpanel: FoldPanelItem,
                          cbstyle: CaptionBarStyle):
        foldpanel.ApplyCaptionStyle(cbstyle)

    def ApplyCaptionStyleAll(self, cbstyle: CaptionBarStyle):
        for p in self._panels:
            self.ApplyCaptionStyle(p, cbstyle)
        self._cbstyle = cbstyle

    def GetCaptionStyle(self, foldpanel: FoldPanelItem) -> CaptionBarStyle:
        return foldpanel.GetCaptionStyle()

    def GetFoldPanel(self, item: int) -> FoldPanelItem:
        try:
            return self._panels[item]
        except IndexError:
            raise ValueError(f'Index {item} out of range (0..{len(self._panels)-1})')

    def GetCount(self) -> int:
        return len(self._panels)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def RefreshPanelsFrom(self, item: FoldPanelItem):
        try:
            i = self._panels.index(item)
        except ValueError:
            raise ValueError(f'Invalid panel passed to RefreshPanelsFrom: {item!r}')

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

    def RepositionCollapsedToBottom(self):
        vertical = self._isVertical
        total = self.height() if vertical else self.width()

        collapsed_len, expanded_len, _ = self.GetPanelsLength(0, 0)

        if total - expanded_len - collapsed_len < 0:
            offset = expanded_len
        else:
            offset = total - collapsed_len

        for p in self._panels:
            if not p.IsExpanded():
                offset += p.Reposition(offset)

    def GetPanelsLength(self, collapsed: int, expanded: int):
        value = 0
        for p in self._panels:
            length = p.GetPanelLength()
            value += length
            if p.IsExpanded():
                expanded += length
            else:
                collapsed += length
        return collapsed, expanded, value

    def RedisplayFoldPanelItems(self):
        for p in self._panels:
            p.ResizePanel()
            p.update()

    # ------------------------------------------------------------------
    # Qt events
    # ------------------------------------------------------------------
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        foldrect = self.rect()

        if self._agwStyle & (FPB_COLLAPSE_TO_BOTTOM | FPB_EXCLUSIVE_FOLD):
            self.RepositionCollapsedToBottom()

        self.RedisplayFoldPanelItems()
