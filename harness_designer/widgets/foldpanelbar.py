
import wx
from wx.lib import scrolledpanel

from wx.lib.embeddedimage import PyEmbeddedImage

CollapsedIcon = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAADdJ"
    "REFUOI1jZGRiZqAEMFGke/Ab8P/f3/8D5wKY7YRcQRsXoNuKzxXUdwEu23CJU+wCxtG8wAAA"
    "mvUb+vltJD8AAAAASUVORK5CYII=")

ExpandedIcon = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAEJJ"
    "REFUOI1jZGRiZqAEMFGke1AYwIIu8P/f3/+4FDMyMTNS3QUYBmCzBZ84bQIR3TZcttPOBci2"
    "4rOdKi5gHM0LDACevARXGc9htQAAAABJRU5ErkJggg==")

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


class CaptionBarStyle(object):

    def __init__(self):
        self._firstColourUsed = False
        self._secondColourUsed = False
        self._textColourUsed = False
        self._captionFontUsed = False
        self._captionStyleUsed = False
        self._captionStyle = CAPTIONBAR_GRADIENT_V

        self._captionFont = None
        self._firstColour = None
        self._secondColour = None
        self._textColour = None

        self.ResetDefaults()

    def ResetDefaults(self):
        self._firstColourUsed = False
        self._secondColourUsed = False
        self._textColourUsed = False
        self._captionFontUsed = False
        self._captionStyleUsed = False
        self._captionStyle = CAPTIONBAR_GRADIENT_V

    def SetCaptionFont(self, font):
        self._captionFont = font
        self._captionFontUsed = True

    def CaptionFontUsed(self):
        return self._captionFontUsed

    def GetCaptionFont(self):
        return self._captionFont

    def SetFirstColour(self, colour):
        self._firstColour = colour
        self._firstColourUsed = True

    def FirstColourUsed(self):
        return self._firstColourUsed

    def GetFirstColour(self):
        return self._firstColour

    def SetSecondColour(self, colour):
        self._secondColour = colour
        self._secondColourUsed = True

    def SecondColourUsed(self):
        return self._secondColourUsed

    def GetSecondColour(self):
        return self._secondColour

    def SetCaptionColour(self, colour):
        self._textColour = colour
        self._textColourUsed = True

    def CaptionColourUsed(self):
        return self._textColourUsed

    def GetCaptionColour(self):
        return self._textColour

    def SetCaptionStyle(self, style):
        self._captionStyle = style
        self._captionStyleUsed = True

    def CaptionStyleUsed(self):
        return self._captionStyleUsed

    def GetCaptionStyle(self):
        return self._captionStyle


wxEVT_CAPTIONBAR = wx.NewEventType()
EVT_CAPTIONBAR = wx.PyEventBinder(wxEVT_CAPTIONBAR, 0)

EmptyCaptionBarStyle = CaptionBarStyle()


class CaptionBarEvent(wx.CommandEvent):
    def __init__(self, evtType):
        wx.CommandEvent.__init__(self, evtType)

        self._tag = None
        self._bar = None

    def GetFoldStatus(self):
        return not self._bar.IsCollapsed()

    def GetBar(self):
        return self._bar

    def SetTag(self, tag):
        self._tag = tag

    def GetTag(self):
        return self._tag

    def SetBar(self, bar):
        self._bar = bar


class CaptionBar(wx.Window):
    def __init__(self, parent, id, pos, size, caption="",
                 foldIcons=None, cbstyle=None,
                 rightIndent=FPB_BMP_RIGHTSPACE,
                 iconWidth=16, iconHeight=16, collapsed=False):

        wx.Window.__init__(self, parent, wx.ID_ANY, pos=pos,
                           size=(20, 20), style=wx.NO_BORDER)

        self._controlCreated = False
        self._collapsed = collapsed
        self.ApplyCaptionStyle(cbstyle, True)

        if foldIcons is None:
            foldIcons = wx.ImageList(16, 16)

            bmp = ExpandedIcon.GetBitmap()
            foldIcons.Add(bmp)
            bmp = CollapsedIcon.GetBitmap()
            foldIcons.Add(bmp)

        # set initial size
        if foldIcons:
            assert foldIcons.GetImageCount() > 1
            iconWidth, iconHeight = foldIcons.GetSize(0)

        self._caption = caption
        self._foldIcons = foldIcons
        self._style = cbstyle
        self._rightIndent = rightIndent
        self._iconWidth = iconWidth
        self._iconHeight = iconHeight
        self._oldSize = wx.Size(20, 20)

        self._controlCreated = True

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def ApplyCaptionStyle(self, cbstyle=None, applyDefault=True):
        if cbstyle is None:
            cbstyle = EmptyCaptionBarStyle

        newstyle = cbstyle

        if applyDefault:

            if not newstyle.FirstColourUsed():
                newstyle.SetFirstColour(wx.WHITE)

            if not newstyle.SecondColourUsed():
                colour = self.GetParent().GetBackgroundColour()
                r, g, b = int(colour.Red()), int(colour.Green()), int(colour.Blue())
                colour = ((r >> 1) + 20, (g >> 1) + 20, (b >> 1) + 20)
                newstyle.SetSecondColour(wx.Colour(colour[0], colour[1], colour[2]))

            if not newstyle.CaptionColourUsed():
                newstyle.SetCaptionColour(wx.BLACK)

            if not newstyle.CaptionFontUsed():
                newstyle.SetCaptionFont(self.GetParent().GetFont())

            if not newstyle.CaptionStyleUsed():
                newstyle.SetCaptionStyle(CAPTIONBAR_GRADIENT_V)

        self._style = newstyle

    def SetCaptionStyle(self, cbstyle=None, applyDefault=True):
        if cbstyle is None:
            cbstyle = EmptyCaptionBarStyle

        self.ApplyCaptionStyle(cbstyle, applyDefault)
        self.Refresh()

    def GetCaptionStyle(self):
        return self._style

    def IsCollapsed(self):
        return self._collapsed

    def SetRightIndent(self, pixels):
        assert pixels >= 0
        self._rightIndent = pixels
        if self._foldIcons:
            self.Refresh()

    def Collapse(self):
        self._collapsed = True
        self.RedrawIconBitmap()

    def Expand(self):
        self._collapsed = False
        self.RedrawIconBitmap()

    def SetBoldFont(self):
        self.GetFont().SetWeight(wx.FONTWEIGHT_BOLD)

    def SetNormalFont(self):
        self.GetFont().SetWeight(wx.FONTWEIGHT_NORMAL)

    def IsVertical(self):
        fld = self.GetParent().GetGrandParent()
        if isinstance(fld, FoldPanelBar):
            return self.GetParent().GetGrandParent().IsVertical()
        else:
            raise Exception("ERROR: Wrong Parent " + repr(fld))

    def OnPaint(self, event):
        if not self._controlCreated:
            event.Skip()
            return

        dc = wx.BufferedPaintDC(self)
        wndRect = self.GetRect()
        vertical = self.IsVertical()

        self.FillCaptionBackground(dc)
        dc.SetFont(self._style.GetCaptionFont())
        dc.SetTextForeground(self._style.GetCaptionColour())

        if vertical:
            dc.DrawText(self._caption, 4, FPB_EXTRA_Y//2)
        else:
            dc.DrawRotatedText(self._caption, FPB_EXTRA_Y//2,
                               wndRect.GetBottom() - 4, 90)

        if self._foldIcons:

            index = self._collapsed

            if vertical:
                drw = wndRect.GetRight() - self._iconWidth - self._rightIndent
                self._foldIcons.Draw(index, dc, drw,
                                     (wndRect.GetHeight() - self._iconHeight)//2,
                                     wx.IMAGELIST_DRAW_TRANSPARENT)
            else:
                self._foldIcons.Draw(index, dc,
                                     (wndRect.GetWidth() - self._iconWidth)//2,
                                     self._rightIndent, wx.IMAGELIST_DRAW_TRANSPARENT)

    def FillCaptionBackground(self, dc):
        style = self._style.GetCaptionStyle()

        if style == CAPTIONBAR_GRADIENT_V:
            if self.IsVertical():
                self.DrawVerticalGradient(dc, self.GetRect())
            else:
                self.DrawHorizontalGradient(dc, self.GetRect())

        elif style == CAPTIONBAR_GRADIENT_H:
            if self.IsVertical():
                self.DrawHorizontalGradient(dc, self.GetRect())
            else:
                self.DrawVerticalGradient(dc, self.GetRect())

        elif style == CAPTIONBAR_SINGLE:
            self.DrawSingleColour(dc, self.GetRect())
        elif style == CAPTIONBAR_RECTANGLE or style == CAPTIONBAR_FILLED_RECTANGLE:
            self.DrawSingleRectangle(dc, self.GetRect())
        else:
            raise Exception("STYLE Error: Undefined Style Selected: " + repr(style))

    def OnMouseEvent(self, event):
        send_event = False
        vertical = self.IsVertical()

        if event.LeftDown() and self._foldIcons:

            pt = event.GetPosition()
            rect = self.GetRect()

            drw = (rect.GetWidth() - self._iconWidth - self._rightIndent)
            if vertical and pt.x > drw or not vertical and \
               pt.y < (self._iconHeight + self._rightIndent):
                send_event = True

        elif event.LeftDClick():
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
            send_event = True

        elif event.Entering() and self._foldIcons:
            pt = event.GetPosition()
            rect = self.GetRect()

            drw = (rect.GetWidth() - self._iconWidth - self._rightIndent)
            if vertical and pt.x > drw or not vertical and \
               pt.y < (self._iconHeight + self._rightIndent):
                self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
            else:
                self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

        elif event.Leaving():
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

        elif event.Moving():
            pt = event.GetPosition()
            rect = self.GetRect()

            drw = (rect.GetWidth() - self._iconWidth - self._rightIndent)
            if vertical and pt.x > drw or not vertical and \
               pt.y < (self._iconHeight + self._rightIndent):
                self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
            else:
                self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

        if send_event:
            event = CaptionBarEvent(wxEVT_CAPTIONBAR)
            event.SetId(self.GetId())
            event.SetEventObject(self)
            event.SetBar(self)
            self.GetEventHandler().ProcessEvent(event)

    def OnChar(self, event):
        event.Skip()

    def DoGetBestSize(self):
        if self.IsVertical():
            x, y = self.GetTextExtent(self._caption)
        else:
            y, x = self.GetTextExtent(self._caption)

        if x < self._iconWidth:
            x = self._iconWidth

        if y < self._iconHeight:
            y = self._iconHeight

        return wx.Size(x + FPB_EXTRA_X, y + FPB_EXTRA_Y)

    def DrawVerticalGradient(self, dc, rect):
        if rect.height < 1 or rect.width < 1:
            return

        dc.SetPen(wx.TRANSPARENT_PEN)

        col2 = self._style.GetSecondColour()
        col1 = self._style.GetFirstColour()

        r1, g1, b1 = int(col1.Red()), int(col1.Green()), int(col1.Blue())
        r2, g2, b2 = int(col2.Red()), int(col2.Green()), int(col2.Blue())

        flrect = float(rect.height)

        rstep = float((r2 - r1)) / flrect
        gstep = float((g2 - g1)) / flrect
        bstep = float((b2 - b1)) / flrect

        rf, gf, bf = 0, 0, 0

        for y in range(rect.y, rect.y + rect.height):
            currCol = (int(r1 + rf), int(g1 + gf), int(b1 + bf))

            dc.SetBrush(wx.Brush(currCol, wx.BRUSHSTYLE_SOLID))
            dc.DrawRectangle(rect.x, rect.y + (y - rect.y), rect.width, rect.height)
            rf = rf + rstep
            gf = gf + gstep
            bf = bf + bstep

    def DrawHorizontalGradient(self, dc, rect):
        if rect.height < 1 or rect.width < 1:
            return

        dc.SetPen(wx.TRANSPARENT_PEN)

        col2 = self._style.GetSecondColour()
        col1 = self._style.GetFirstColour()

        r1, g1, b1 = int(col1.Red()), int(col1.Green()), int(col1.Blue())
        r2, g2, b2 = int(col2.Red()), int(col2.Green()), int(col2.Blue())

        flrect = float(rect.width)

        rstep = float((r2 - r1)) / flrect
        gstep = float((g2 - g1)) / flrect
        bstep = float((b2 - b1)) / flrect

        rf, gf, bf = 0, 0, 0

        for x in range(rect.x, rect.x + rect.width):
            currCol = (int(r1 + rf), int(g1 + gf), int(b1 + bf))

            dc.SetBrush(wx.Brush(currCol, wx.BRUSHSTYLE_SOLID))
            dc.DrawRectangle(rect.x + (x - rect.x), rect.y, 1, rect.height)
            rf = rf + rstep
            gf = gf + gstep
            bf = bf + bstep

    def DrawSingleColour(self, dc, rect):
        if rect.height < 1 or rect.width < 1:
            return

        dc.SetPen(wx.TRANSPARENT_PEN)

        dc.SetBrush(wx.Brush(self._style.GetFirstColour(), wx.BRUSHSTYLE_SOLID))
        dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)

    def DrawSingleRectangle(self, dc, rect):
        if rect.height < 2 or rect.width < 1:
            return

        if self._style.GetCaptionStyle() == CAPTIONBAR_RECTANGLE:
            colour = self.GetParent().GetBackgroundColour()
            br = wx.Brush(colour, wx.BRUSHSTYLE_SOLID)
        else:
            colour = self._style.GetFirstColour()
            br = wx.Brush(colour, wx.BRUSHSTYLE_SOLID)

        # setup the pen frame

        pen = wx.Pen(self._style.GetSecondColour())
        dc.SetPen(pen)
        dc.SetBrush(br)
        dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height - 1)

        bgpen = wx.Pen(self.GetParent().GetBackgroundColour())
        dc.SetPen(bgpen)
        dc.DrawLine(rect.x, rect.y + rect.height - 1, rect.x + rect.width,
                    rect.y + rect.height - 1)

    def OnSize(self, event):
        if not self._controlCreated:
            event.Skip()
            return

        size = event.GetSize()

        if self._foldIcons:
            rect = wx.Rect(size.GetWidth() - self._iconWidth - self._rightIndent, 0,
                           self._iconWidth + self._rightIndent,
                           self._iconWidth + self._rightIndent)

            diffX = size.GetWidth() - self._oldSize.GetWidth()

            if diffX > 1:
                rect.SetWidth(rect.GetWidth() + diffX + 10)
                rect.SetX(rect.GetX() - diffX - 10)

            self.RefreshRect(rect)

        else:

            rect = self.GetRect()
            self.RefreshRect(rect)

        self._oldSize = size

    def RedrawIconBitmap(self):
        if self._foldIcons:

            rect = self.GetRect()

            rect.SetX(rect.GetWidth() - self._iconWidth - self._rightIndent)
            rect.SetWidth(self._iconWidth + self._rightIndent)
            self.RefreshRect(rect)


class FoldPanelBar(wx.Panel):

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=wx.TAB_TRAVERSAL | wx.NO_BORDER, agwStyle=0):

        self._controlCreated = False

        if not agwStyle & (FPB_HORIZONTAL | FPB_VERTICAL):
            agwStyle = agwStyle | FPB_VERTICAL

        if agwStyle & FPB_HORIZONTAL:
            self._isVertical = False
        else:
            self._isVertical = True

        self._agwStyle = agwStyle

        wx.Panel.__init__(self, parent, id, pos, size, style)

        self._foldPanel = wx.Panel(self, wx.ID_ANY, pos, size,
                                   wx.NO_BORDER | wx.TAB_TRAVERSAL)

        self._controlCreated = True
        self._panels = []

        self.Bind(EVT_CAPTIONBAR, self.OnPressCaption)
        self.Bind(wx.EVT_SIZE, self.OnSizePanel)

    def AddFoldPanel(self, caption="", collapsed=False, foldIcons=None, cbstyle=None):
        if cbstyle is None:
            cbstyle = EmptyCaptionBarStyle

        if foldIcons is None:
            foldIcons = wx.ImageList(16, 16)

            bmp = ExpandedIcon.GetBitmap()
            foldIcons.Add(bmp)
            bmp = CollapsedIcon.GetBitmap()
            foldIcons.Add(bmp)

        item = FoldPanelItem(self._foldPanel, -1, caption=caption,
                             foldIcons=foldIcons,
                             collapsed=collapsed, cbstyle=cbstyle)

        pos = 0
        if len(self._panels) > 0:
            pos = self._panels[-1].GetItemPos() + self._panels[-1].GetPanelLength()

        item.Reposition(pos)
        self._panels.append(item)

        return item

    def AddFoldPanelWindow(self, panel, window, flags=FPB_ALIGN_WIDTH,
                           spacing=FPB_DEFAULT_SPACING,
                           leftSpacing=FPB_DEFAULT_LEFTLINESPACING,
                           rightSpacing=FPB_DEFAULT_RIGHTLINESPACING):

        try:
            self._panels.index(panel)
        except :  # NOQA
            raise Exception("ERROR: Invalid Panel Passed To AddFoldPanelWindow: " + repr(panel))

        panel.AddWindow(window, flags, spacing, leftSpacing, rightSpacing)
        return 0

    def AddFoldPanelSeparator(self, panel, colour=wx.BLACK,
                              spacing=FPB_DEFAULT_SPACING,
                              leftSpacing=FPB_DEFAULT_LEFTLINESPACING,
                              rightSpacing=FPB_DEFAULT_RIGHTLINESPACING):

        try:
            item = self._panels.index(panel)
        except:
            raise Exception("ERROR: Invalid Panel Passed To AddFoldPanelSeparator: " + repr(panel))

        panel.AddSeparator(colour, spacing, leftSpacing, rightSpacing)
        return 0

    def OnSizePanel(self, event):
        if not self._controlCreated:
            event.Skip()
            return

        foldrect = self.GetRect()

        foldrect.SetX(0)
        foldrect.SetY(0)

        self._foldPanel.SetSize(foldrect[2:])

        if self._agwStyle & FPB_COLLAPSE_TO_BOTTOM or self._agwStyle & FPB_EXCLUSIVE_FOLD:
            rect = self.RepositionCollapsedToBottom()
            vertical = self.IsVertical()
            if vertical and rect.GetHeight() > 0 or not vertical and rect.GetWidth() > 0:
                self.RefreshRect(rect)

        self.RedisplayFoldPanelItems()

    def OnPressCaption(self, event):
        if event.GetFoldStatus():
            self.Collapse(event.GetTag())
        else:
            self.Expand(event.GetTag())

    def RefreshPanelsFrom(self, item):
        try:
            i = self._panels.index(item)
        except:
            raise Exception("ERROR: Invalid Panel Passed To RefreshPanelsFrom: " + repr(item))

        self.Freeze()

        if self._agwStyle & FPB_COLLAPSE_TO_BOTTOM or self._agwStyle & FPB_EXCLUSIVE_FOLD:
            offset = 0

            for panels in self._panels:
                if panels.IsExpanded():
                    offset = offset + panels.Reposition(offset)

            self.RepositionCollapsedToBottom()

        else:

            pos = self._panels[i].GetItemPos() + self._panels[i].GetPanelLength()
            for j in range(i+1, len(self._panels)):
                pos = pos + self._panels[j].Reposition(pos)

        self.Thaw()

    def RedisplayFoldPanelItems(self):
        for panels in self._panels:
            panels.ResizePanel()
            panels.Refresh()

    def RepositionCollapsedToBottom(self):
        value = wx.Rect(0,0,0,0)
        vertical = self.IsVertical()

        expanded = 0
        collapsed = 0
        collapsed, expanded, values = self.GetPanelsLength(collapsed, expanded)

        if (vertical and
            [self.GetSize().GetHeight()] or
            [self.GetSize().GetWidth()])[0] - expanded - collapsed < 0:

            offset = expanded
        else:
            value.SetHeight(self.GetSize().GetHeight())
            value.SetWidth(self.GetSize().GetWidth())

            if vertical:
                value.SetY(expanded)
                value.SetHeight(value.GetHeight() - expanded)
            else:
                value.SetX(expanded)
                value.SetWidth(value.GetWidth() - expanded)

            offset = (vertical and [self.GetSize().GetHeight()] or
                      [self.GetSize().GetWidth()])[0] - collapsed

        for panels in self._panels:
            if not panels.IsExpanded():
                offset = offset + panels.Reposition(offset)

        return value

    def GetPanelsLength(self, collapsed, expanded):
        value = 0
        for j in range(0, len(self._panels)):
            offset = self._panels[j].GetPanelLength()
            value = value + offset
            if self._panels[j].IsExpanded():
                expanded = expanded + offset
            else:
                collapsed = collapsed + offset

        return collapsed, expanded, value

    def Collapse(self, foldpanel):
        try:
            item = self._panels.index(foldpanel)
        except:
            raise Exception("ERROR: Invalid Panel Passed To Collapse: " + repr(foldpanel))

        foldpanel.Collapse()
        self.RefreshPanelsFrom(foldpanel)

    def Expand(self, foldpanel):
        fpbextrastyle = 0

        if self._agwStyle & FPB_SINGLE_FOLD or self._agwStyle & FPB_EXCLUSIVE_FOLD:
            fpbextrastyle = 1
            for panel in self._panels:
                panel.Collapse()

        foldpanel.Expand()

        if fpbextrastyle:
            if self._agwStyle & FPB_EXCLUSIVE_FOLD:
                self.RepositionCollapsedToBottom()
            self.RefreshPanelsFrom(self._panels[0])
        else:
            self.RefreshPanelsFrom(foldpanel)

    def ApplyCaptionStyle(self, foldpanel, cbstyle):
        foldpanel.ApplyCaptionStyle(cbstyle)

    def ApplyCaptionStyleAll(self, cbstyle):
        for panels in self._panels:
            self.ApplyCaptionStyle(panels, cbstyle)

    def GetCaptionStyle(self, foldpanel):
        return foldpanel.GetCaptionStyle()

    def IsVertical(self):
        return self._isVertical

    def GetFoldPanel(self, item):
        try:
            ind = self._panels[item]
            return self._panels[item]
        except:
            raise Exception(f"ERROR: List Index Orepr(0)ut Of Range Or Bad Item "
                            f"Passed: {repr(item)}. Item Should Be An Integer "
                            f"Between {repr(0)} And {repr(0)}")

    def GetCount(self):
        try:
            return len(self._panels)
        except:
            raise Exception("ERROR: No Panels Have Been Added To FoldPanelBar")


class FoldPanelItem(wx.Panel):

    def __init__(self, parent, id=wx.ID_ANY, caption="", foldIcons=None,
                 collapsed=False, cbstyle=None):

        wx.Panel.__init__(self, parent, id, wx.Point(0, 0), style=wx.CLIP_CHILDREN)
        self._controlCreated = False
        self._UserSize = 0
        self._PanelSize = 0
        self._LastInsertPos = 0
        self._itemPos = 0
        self._userSized = False

        if foldIcons is None:
            foldIcons = wx.ImageList(16, 16)

            bmp = ExpandedIcon.GetBitmap()
            foldIcons.Add(bmp)
            bmp = CollapsedIcon.GetBitmap()
            foldIcons.Add(bmp)

        self._foldIcons = foldIcons
        if cbstyle is None:
            cbstyle = EmptyCaptionBarStyle

        self._captionBar = CaptionBar(self, wx.ID_ANY, wx.Point(0,0),
                                      size=wx.DefaultSize, caption=caption,
                                      foldIcons=foldIcons, cbstyle=cbstyle)

        if collapsed:
            self._captionBar.Collapse()

        self._controlCreated = True

        size = self._captionBar.GetSize()

        self._PanelSize = (self.IsVertical() and
                           [size.GetHeight()] or [size.GetWidth()])[0]

        self._LastInsertPos = self._PanelSize
        self._items = []

        self.Bind(EVT_CAPTIONBAR, self.OnPressCaption)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def AddWindow(self, window, flags=FPB_ALIGN_WIDTH, spacing=FPB_DEFAULT_SPACING,
                  leftSpacing=FPB_DEFAULT_LEFTLINESPACING,
                  rightSpacing=FPB_DEFAULT_RIGHTLINESPACING):

        wi = FoldWindowItem(self, window, Type="WINDOW", flags=flags, spacing=spacing,
                            leftSpacing=leftSpacing, rightSpacing=rightSpacing)

        self._items.append(wi)

        vertical = self.IsVertical()

        self._spacing = spacing
        self._leftSpacing = leftSpacing
        self._rightSpacing = rightSpacing

        xpos = (vertical and [leftSpacing] or [self._LastInsertPos + spacing])[0]
        ypos = (vertical and [self._LastInsertPos + spacing] or [leftSpacing])[0]

        window.SetSize(xpos, ypos, -1, -1, wx.SIZE_USE_EXISTING)

        self._LastInsertPos = self._LastInsertPos + wi.GetWindowLength(vertical)
        self.ResizePanel()

    def AddSeparator(self, colour=wx.BLACK, spacing=FPB_DEFAULT_SPACING,
                     leftSpacing=FPB_DEFAULT_LEFTSPACING,
                     rightSpacing=FPB_DEFAULT_RIGHTSPACING):

        wi = FoldWindowItem(self, window=None, Type="SEPARATOR",
                            flags=FPB_ALIGN_WIDTH, y=self._LastInsertPos,
                            colour=colour, spacing=spacing, leftSpacing=leftSpacing,
                            rightSpacing=rightSpacing)

        self._items.append(wi)
        self._LastInsertPos = self._LastInsertPos + \
                              wi.GetWindowLength(self.IsVertical())

        self.ResizePanel()

    def Reposition(self, pos):
        self.Freeze()

        vertical = self.IsVertical()
        xpos = (vertical and [-1] or [pos])[0]
        ypos = (vertical and [pos] or [-1])[0]

        self.SetSize(xpos, ypos, -1, -1, wx.SIZE_USE_EXISTING)
        self._itemPos = pos

        self.Thaw()

        return self.GetPanelLength()

    def OnPressCaption(self, event):
        event.SetTag(self)
        event.Skip()

    def ResizePanel(self):
        self.Freeze()

        vertical = self.IsVertical()

        if self._captionBar.IsCollapsed():
            size = self._captionBar.GetSize()
            self._PanelSize = (vertical and [size.GetHeight()] or [size.GetWidth()])[0]
        else:
            size = self.GetBestSize()
            self._PanelSize = (vertical and [size.GetHeight()] or [size.GetWidth()])[0]

            if self._UserSize:
                if vertical:
                    size.SetHeight(self._UserSize)
                else:
                    size.SetWidth(self._UserSize)

        pnlsize = self.GetParent().GetSize()

        if vertical:
            size.SetWidth(pnlsize.GetWidth())
        else:
            size.SetHeight(pnlsize.GetHeight())

        xsize = (vertical and [size.GetWidth()] or [-1])[0]
        ysize = (vertical and [-1] or [size.GetHeight()])[0]

        self._captionBar.SetSize((xsize, ysize))

        self.SetSize(size)

        for items in self._items:
            items.ResizeItem((vertical and
                              [size.GetWidth()] or
                              [size.GetHeight()])[0], vertical)

        self.Thaw()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        vertical = self.IsVertical()

        for item in self._items:

            if item.GetType() == "SEPARATOR":
                pen = wx.Pen(item.GetLineColour(), 1, wx.PENSTYLE_SOLID)
                dc.SetPen(pen)
                a = item.GetLeftSpacing()
                b = item.GetLineY() + item.GetSpacing()
                c = item.GetLineLength()
                d = a + c

                if vertical:
                    dc.DrawLine(a, b, d, b)
                else:
                    dc.DrawLine(b, a, b, d)

        event.Skip()

    def IsVertical(self):
        if isinstance(self.GetGrandParent(), FoldPanelBar):
            return self.GetGrandParent().IsVertical()
        else:
            raise Exception("ERROR: Wrong Parent " + repr(self.GetGrandParent()))

    def IsExpanded(self):
        return not self._captionBar.IsCollapsed()

    def GetItemPos(self):
        return self._itemPos

    def Collapse(self):
        self._captionBar.Collapse()
        self.ResizePanel()

    def Expand(self):
        self._captionBar.Expand()
        self.ResizePanel()

    def GetPanelLength(self):
        """ Returns size of panel. """

        if self._captionBar.IsCollapsed():
            return self.GetCaptionLength()
        elif self._userSized:
            return self._UserSize

        return self._PanelSize

    def GetCaptionLength(self):
        size = self._captionBar.GetSize()
        return (self.IsVertical() and [size.GetHeight()] or [size.GetWidth()])[0]

    def ApplyCaptionStyle(self, cbstyle):
        self._captionBar.SetCaptionStyle(cbstyle)

    def GetCaptionStyle(self):
        return self._captionBar.GetCaptionStyle()


class FoldWindowItem(object):

    def __init__(self, parent, window=None, **kw):
        if "Type" not in kw:
            raise Exception('ERROR: Missing Window Type Information. This Should Be "WINDOW" Or "SEPARATOR"')

        if kw.get("Type") == "WINDOW":
            # Window constructor. This initialises the class as a wx.Window Type

            if "flags" in kw:
                self._flags = kw.get("flags")
            else:
                self._flags = FPB_ALIGN_WIDTH
            if "spacing" in kw:
                self._spacing = kw.get("spacing")
            else:
                self._spacing = FPB_DEFAULT_SPACING
            if "leftSpacing" in kw:
                self._leftSpacing = kw.get("leftSpacing")
            else:
                self._leftSpacing = FPB_DEFAULT_LEFTSPACING
            if "rightSpacing" in kw:
                self._rightSpacing = kw.get("rightSpacing")
            else:
                self._rightSpacing = FPB_DEFAULT_RIGHTSPACING

            self._lineY = 0
            self._sepLineColour = None
            self._wnd = window

        elif kw.get("Type") == "SEPARATOR":
            if "y" in kw:
                self._lineY = kw.get("y")
            else:
                raise Exception("ERROR: Undefined Y Position For The Separator")
            if "lineColour" in kw:
                self._sepLineColour = kw.get("lineColour")
            else:
                self._sepLineColour = wx.BLACK
            if "flags" in kw:
                self._flags = kw.get("flags")
            else:
                self._flags = FPB_ALIGN_WIDTH
            if "spacing" in kw:
                self._spacing = kw.get("spacing")
            else:
                self._spacing = FPB_DEFAULT_SPACING
            if "leftSpacing" in kw:
                self._leftSpacing = kw.get("leftSpacing")
            else:
                self._leftSpacing = FPB_DEFAULT_LEFTSPACING
            if "rightSpacing" in kw:
                self._rightSpacing = kw.get("rightSpacing")
            else:
                self._rightSpacing = FPB_DEFAULT_RIGHTSPACING

            self._wnd = window

        else:
            raise Exception("ERROR: Undefined Window Type Selected: " + repr(kw.get("Type")))

        self._type = kw.get("Type")
        self._lineLength = 0

    def GetType(self):
        return self._type

    def GetLineY(self):
        return self._lineY

    def GetLineLength(self):
        return self._lineLength

    def GetLineColour(self):
        return self._sepLineColour

    def GetLeftSpacing(self):
        return self._leftSpacing

    def GetRightSpacing(self):
        return self._rightSpacing

    def GetSpacing(self):
        return self._spacing

    def GetWindowLength(self, vertical=True):
        value = 0
        if self._type == "WINDOW":
            size = self._wnd.GetSize()
            value = (vertical and [size.GetHeight()] or [size.GetWidth()])[0] + \
                    self._spacing

        elif self._type == "SEPARATOR":
            value = 1 + self._spacing

        return value

    def ResizeItem(self, size, vertical=True):
        if self._flags & FPB_ALIGN_WIDTH:
            # align by taking full width
            mySize = size - self._leftSpacing - self._rightSpacing

            if mySize < 0:
                mySize = 10  # can't have negative width

            if self._type == "SEPARATOR":
                self._lineLength = mySize
            else:
                xsize = (vertical and [mySize] or [-1])[0]
                ysize = (vertical and [-1] or [mySize])[0]

                self._wnd.SetSize((xsize, ysize))


if __name__ == '__main__':

    import wx

    class MyFrame(wx.Frame):

        def __init__(self, parent):

            wx.Frame.__init__(self, parent, -1, "FoldPanelBar Demo")

            text_ctrl = wx.TextCtrl(self, -1, size=(400, 100), style=wx.TE_MULTILINE)

            panel_bar = FoldPanelBar(self, -1, agwStyle=FPB_VERTICAL)

            fold_panel = panel_bar.AddFoldPanel("Thing")
            thing = wx.TextCtrl(fold_panel, -1, size=(400, -1), style=wx.TE_MULTILINE)

            panel_bar.AddFoldPanelWindow(fold_panel, thing)

            main_sizer = wx.BoxSizer(wx.VERTICAL)
            main_sizer.Add(text_ctrl, 1, wx.EXPAND)
            main_sizer.Add(panel_bar, 1, wx.EXPAND)
            self.SetSizer(main_sizer)


    app = wx.App(0)

    frame = MyFrame(None)
    app.SetTopWindow(frame)
    frame.Show()

    app.MainLoop()
