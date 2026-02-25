from wx.lib.agw.aui.aui_utilities import BitmapFromBits, StepColour, GetLabelSize
from wx.lib.agw.aui.aui_utilities import GetBaseColour
from wx.lib.agw.aui.aui_constants import *
import wx
from . import buttons as _buttons
from . import events as _events

UpButton = _buttons.UpButton
DownButton = _buttons.DownButton

ToolbarCommandCapture = _events.ToolbarCommandCapture


class AuiDefaultToolBarArt(object):

    def __init__(self):

        self.SetDefaultColours()

        self._agwFlags = 0
        self._text_orientation = AUI_TBTOOL_TEXT_BOTTOM
        highlight_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        highlight_colour = (highlight_colour.GetRed(), highlight_colour.GetGreen(), highlight_colour.GetBlue())

        self._highlight_colour = wx.Colour(*(highlight_colour + (130,)))

        self._separator_size = 7
        self._orientation = AUI_TBTOOL_HORIZONTAL
        self._gripper_size = 7
        self._overflow_size = 16

        button_dropdown_bits = b"\xe0\xf1\xfb"
        overflow_bits = b"\x80\xff\x80\xc1\xe3\xf7"

        self._button_dropdown_bmp = BitmapFromBits(button_dropdown_bits, 5, 3, wx.BLACK)
        self._disabled_button_dropdown_bmp = BitmapFromBits(button_dropdown_bits, 5, 3,
                                                            wx.Colour(128, 128, 128))
        self._overflow_bmp = BitmapFromBits(overflow_bits, 7, 6, wx.BLACK)
        self._disabled_overflow_bmp = BitmapFromBits(overflow_bits, 7, 6, wx.Colour(128, 128, 128))

        self._font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)

    def SetDefaultColours(self, base_colour=None):
        if base_colour is None:
            self._base_colour = GetBaseColour()
        else:
            self._base_colour = base_colour

        darker3_colour = StepColour(self._base_colour, 60)
        darker5_colour = StepColour(self._base_colour, 40)

        self._gripper_pen1 = wx.Pen(darker5_colour)
        self._gripper_pen2 = wx.Pen(darker3_colour)
        self._gripper_pen3 = wx.WHITE_PEN

    def Clone(self):
        return AuiDefaultToolBarArt()

    def SetAGWFlags(self, agwFlags):
        self._agwFlags = agwFlags

    def GetAGWFlags(self):
        return self._agwFlags

    def SetFont(self, font):
        self._font = font

    def SetTextOrientation(self, orientation):
        self._text_orientation = orientation

    def GetFont(self):
        return self._font

    def GetTextOrientation(self):
        return self._text_orientation

    def SetOrientation(self, orientation):
        self._orientation = orientation

    def GetOrientation(self):
        return self._orientation

    def DrawBackground(self, dc, wnd, _rect, horizontal=True):
        rect = wx.Rect(*_rect)

        start_colour = StepColour(self._base_colour, 180)
        end_colour = StepColour(self._base_colour, 85)
        reflex_colour = StepColour(self._base_colour, 95)

        dc.GradientFillLinear(rect, start_colour, end_colour,
                              (horizontal and [wx.SOUTH] or [wx.EAST])[0])

        left = rect.GetLeft()
        right = rect.GetRight()
        top = rect.GetTop()
        bottom = rect.GetBottom()

        dc.SetPen(wx.Pen(reflex_colour))
        if horizontal:
            dc.DrawLine(left, bottom, right+1, bottom)
        else:
            dc.DrawLine(right, top, right, bottom+1)

    def DrawPlainBackground(self, dc, wnd, _rect):
        rect = wx.Rect(*_rect)
        rect.height += 1

        dc.SetBrush(wx.Brush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE)))
        dc.DrawRectangle(rect.x - 1, rect.y - 1, rect.width + 2, rect.height + 1)

    def DrawLabel(self, dc, wnd, item, rect):
        dc.SetFont(self._font)

        if item.state & AUI_BUTTON_STATE_DISABLED:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        else:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNTEXT))

        orient = item.GetOrientation()

        horizontal = orient == AUI_TBTOOL_HORIZONTAL
        # we only care about the text height here since the text
        # will get cropped based on the width of the item
        label_size = GetLabelSize(dc, item.GetLabel(), not horizontal)
        text_width = label_size.GetWidth()
        text_height = label_size.GetHeight()

        if orient == AUI_TBTOOL_HORIZONTAL:
            text_x = rect.x
            text_y = rect.y + (rect.height - text_height) // 2
            dc.DrawText(item.GetLabel(), text_x, text_y)

        elif orient == AUI_TBTOOL_VERT_CLOCKWISE:
            text_x = rect.x + (rect.width + text_width) // 2
            text_y = rect.y
            dc.DrawRotatedText(item.GetLabel(), text_x, text_y, 270)

        elif AUI_TBTOOL_VERT_COUNTERCLOCKWISE:
            text_x = rect.x + (rect.width-text_width) // 2
            text_y = rect.y + text_height
            dc.DrawRotatedText(item.GetLabel(), text_x, text_y, 90)

    def DrawButton(self, dc, wnd, item, rect):
        bmp_rect, text_rect = self.GetToolsPosition(dc, item, rect)
        gc = wx.GraphicsContext.Create(dc)
        item_state = item.GetState()

        if item_state & AUI_BUTTON_STATE_DISABLED:
            bmp = item.GetDisabledBitmap()
        elif item_state & AUI_BUTTON_STATE_HOVER or item_state & AUI_BUTTON_STATE_PRESSED:
            bmp = item.GetHoverBitmap()
            if not bmp:
                bmp = item.GetBitmap()
        else:
            bmp = item.GetBitmap()

        w, h = bmp.GetSize()

        if not item_state & AUI_BUTTON_STATE_DISABLED:
            if item_state & AUI_BUTTON_STATE_PRESSED:
                bmp_ = DownButton.GetImage().Scale(w, h).ConvertToBitmap()
                gc.DrawBitmap(bmp_, bmp_rect.x, bmp_rect.y, w, h)
            elif item_state & AUI_BUTTON_STATE_CHECKED:
                # it's important to put this code in an else statement after the
                # hover, otherwise hovers won't draw properly for checked items
                bmp_ = DownButton.GetImage().Scale(w, h).ConvertToBitmap()
                gc.DrawBitmap(bmp_, bmp_rect.x, bmp_rect.y, w, h)
            else:
                bmp_ = UpButton.GetImage().Scale(w, h).ConvertToBitmap()
                gc.DrawBitmap(bmp_, bmp_rect.x, bmp_rect.y, w, h)

            if item_state & AUI_BUTTON_STATE_HOVER or item.IsSticky():

                # gc.SetPen(wx.Pen(self._highlight_colour))
                gc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 120)))

                # draw an even lighter background for checked item hovers (since
                # the hover background is the same colour as the check background)
                # if item_state & AUI_BUTTON_STATE_CHECKED:
                #     gc.SetBrush(wx.Brush(wx.Colour(*StepColour(self._highlight_colour, 180))))

                hw = w * 0.30
                hh = h * 0.30
                x = bmp_rect.x + (hw / 2.0)
                y = bmp_rect.y + (hh / 2.0)

                gc.DrawEllipse(x, y, w - hw, h - hh)
        else:
            bmp_ = UpButton.GetBitmap()
            gc.DrawBitmap(bmp_, bmp_rect.x, bmp_rect.y, w, h)

        if bmp.IsOk():
            gc.DrawBitmap(bmp, bmp_rect.x, bmp_rect.y, w, h)

        # set the item's text colour based on if it is disabled
        dc.SetTextForeground(wx.BLACK)
        if item_state & AUI_BUTTON_STATE_DISABLED:
            dc.SetTextForeground(DISABLED_TEXT_COLOUR)

        if self._agwFlags & AUI_TB_TEXT and item.GetLabel() != "":
            self.DrawLabel(dc, wnd, item, text_rect)

    def DrawDropDownButton(self, dc, wnd, item, rect):
        # dropbmp_x = dropbmp_y = 0

        # button_rect = wx.Rect(rect.x, rect.y, rect.width-BUTTON_DROPDOWN_WIDTH, rect.height)
        # dropdown_rect = wx.Rect(rect.x+rect.width-BUTTON_DROPDOWN_WIDTH-1, rect.y, BUTTON_DROPDOWN_WIDTH+1, rect.height)

        horizontal = item.GetOrientation() == AUI_TBTOOL_HORIZONTAL

        gc = wx.GraphicsContext.Create(dc)

        if horizontal:
            button_rect = wx.Rect(rect.x, rect.y, rect.width - BUTTON_DROPDOWN_WIDTH, rect.height)
            dropdown_rect = wx.Rect(rect.x + rect.width - BUTTON_DROPDOWN_WIDTH - 1, rect.y, BUTTON_DROPDOWN_WIDTH + 1, rect.height)
        else:
            button_rect = wx.Rect(rect.x, rect.y, rect.width, rect.height-BUTTON_DROPDOWN_WIDTH)
            dropdown_rect = wx.Rect(rect.x, rect.y + rect.height - BUTTON_DROPDOWN_WIDTH - 1, rect.width, BUTTON_DROPDOWN_WIDTH + 1)

        dropbmp_width = self._button_dropdown_bmp.GetWidth()
        dropbmp_height = self._button_dropdown_bmp.GetHeight()
        if not horizontal:
            tmp = dropbmp_width
            dropbmp_width = dropbmp_height
            dropbmp_height = tmp

        dropbmp_x = dropdown_rect.x + (dropdown_rect.width / 2.0) - dropbmp_width / 2.0
        dropbmp_y = dropdown_rect.y + (dropdown_rect.height / 2.0) - dropbmp_height / 2.0

        bmp_rect, text_rect = self.GetToolsPosition(dc, item, button_rect)

        item_state = item.GetState()
        if item_state & AUI_BUTTON_STATE_PRESSED:

            gc.SetPen(wx.Pen(self._highlight_colour))
            gc.SetBrush(wx.Brush(StepColour(self._highlight_colour, 140)))
            gc.DrawRectangle(button_rect.x, button_rect.y, button_rect.width, button_rect.height)
            gc.DrawRectangle(dropdown_rect.x, dropdown_rect.y, dropdown_rect.width, dropdown_rect.height)

        elif item_state & AUI_BUTTON_STATE_HOVER or item.IsSticky():

            gc.SetPen(wx.Pen(self._highlight_colour))
            gc.SetBrush(wx.Brush(StepColour(self._highlight_colour, 170)))
            gc.DrawRectangle(button_rect.x, button_rect.y, button_rect.width, button_rect.height)
            gc.DrawRectangle(dropdown_rect.x, dropdown_rect.y, dropdown_rect.width, dropdown_rect.height)

        elif item_state & AUI_BUTTON_STATE_CHECKED:
            # it's important to put this code in an else statement after the
            # hover, otherwise hovers won't draw properly for checked items
            gc.SetPen(wx.Pen(self._highlight_colour))
            gc.SetBrush(wx.Brush(StepColour(self._highlight_colour, 170)))
            gc.DrawRectangle(button_rect.x, button_rect.y, button_rect.width, button_rect.height)
            gc.DrawRectangle(dropdown_rect.x, dropdown_rect.y, dropdown_rect.width, dropdown_rect.height)

        if item_state & AUI_BUTTON_STATE_DISABLED:
            bmp = item.GetDisabledBitmap()
            dropbmp = self._disabled_button_dropdown_bmp
        else:
            bmp = item.GetBitmap()
            dropbmp = self._button_dropdown_bmp

        if bmp.IsOk():
            w, h = bmp.GetSize()
            gc.DrawBitmap(bmp, bmp_rect.x, bmp_rect.y, w, h)

        if horizontal:
            w, h = dropbmp.GetSize()
            gc.DrawBitmap(dropbmp, dropbmp_x, dropbmp_y, w, h)
        else:
            dbmp = wx.Bitmap(dropbmp.ConvertToImage().Rotate90(item.GetOrientation() == AUI_TBTOOL_VERT_CLOCKWISE))
            w, h = dbmp.GetSize()
            dc.DrawBitmap(dbmp, dropbmp_x, dropbmp_y, w, h)

        # set the item's text colour based on if it is disabled
        dc.SetTextForeground(wx.BLACK)
        if item_state & AUI_BUTTON_STATE_DISABLED:
            dc.SetTextForeground(DISABLED_TEXT_COLOUR)

        if self._agwFlags & AUI_TB_TEXT and item.GetLabel() != "":
            self.DrawLabel(dc, wnd, item, text_rect)

    def DrawControlLabel(self, dc, wnd, item, rect):
        label_size = GetLabelSize(dc, item.GetLabel(), item.GetOrientation() != AUI_TBTOOL_HORIZONTAL)
        text_height = label_size.GetHeight()
        # text_width = label_size.GetWidth()

        dc.SetFont(self._font)

        if self._agwFlags & AUI_TB_TEXT:

            tx, text_height = dc.GetTextExtent("ABCDHgj")

        text_width, ty = dc.GetTextExtent(item.GetLabel())

        # don't draw the label if it is wider than the item width
        if text_width > rect.width:
            return

        # set the label's text colour
        dc.SetTextForeground(wx.BLACK)

        text_x = rect.x + (rect.width // 2) - (text_width // 2) + 1
        text_y = rect.y + rect.height - text_height - 1

        if self._agwFlags & AUI_TB_TEXT and item.GetLabel() != "":
            dc.DrawText(item.GetLabel(), text_x, text_y)

    def GetLabelSize(self, dc, wnd, item):
        dc.SetFont(self._font)
        label_size = GetLabelSize(dc, item.GetLabel(), self._orientation != AUI_TBTOOL_HORIZONTAL)

        return wx.Size(item.GetMinSize().GetWidth(), label_size.GetHeight())

    def GetToolSize(self, dc, wnd, item):
        if not item.GetBitmap().IsOk() and not self._agwFlags & AUI_TB_TEXT:
            return wx.Size(16, 16)

        width = item.GetBitmap().GetWidth()
        height = item.GetBitmap().GetHeight()

        if self._agwFlags & AUI_TB_TEXT:

            dc.SetFont(self._font)
            label_size = GetLabelSize(dc, item.GetLabel(), self.GetOrientation() != AUI_TBTOOL_HORIZONTAL)
            padding = 6

            if self._text_orientation == AUI_TBTOOL_TEXT_BOTTOM:

                if self.GetOrientation() != AUI_TBTOOL_HORIZONTAL:
                    height += 3   # space between top border and bitmap
                    height += 3   # space between bitmap and text
                    padding = 0

                height += label_size.GetHeight()

                if item.GetLabel() != "":
                    width = max(width, label_size.GetWidth()+padding)

            elif self._text_orientation == AUI_TBTOOL_TEXT_RIGHT and item.GetLabel() != "":

                if self.GetOrientation() == AUI_TBTOOL_HORIZONTAL:

                    width += 3  # space between left border and bitmap
                    width += 3  # space between bitmap and text
                    padding = 0

                width += label_size.GetWidth()
                height = max(height, label_size.GetHeight()+padding)

        # if the tool has a dropdown button, add it to the width
        if item.HasDropDown():
            if item.GetOrientation() == AUI_TBTOOL_HORIZONTAL:
                width += BUTTON_DROPDOWN_WIDTH + 4
            else:
                height += BUTTON_DROPDOWN_WIDTH + 4

        return wx.Size(width, height)

    def DrawSeparator(self, dc, wnd, _rect):
        horizontal = True
        if self._agwFlags & AUI_TB_VERTICAL:
            horizontal = False

        rect = wx.Rect(*_rect)

        if horizontal:

            rect.x += (rect.width//2)
            rect.width = 1
            new_height = (rect.height*3)//4
            rect.y += (rect.height//2) - (new_height//2)
            rect.height = new_height

        else:

            rect.y += (rect.height//2)
            rect.height = 1
            new_width = (rect.width*3)//4
            rect.x += (rect.width//2) - (new_width//2)
            rect.width = new_width

        start_colour = StepColour(self._base_colour, 80)
        end_colour = StepColour(self._base_colour, 80)
        dc.GradientFillLinear(rect, start_colour, end_colour, (horizontal and [wx.SOUTH] or [wx.EAST])[0])

    def DrawGripper(self, dc, wnd, rect):
        # local opts
        toolbar_is_vertical = self._agwFlags & AUI_TB_VERTICAL
        rect_x, rect_y, rect_width, rect_height = rect.x, rect.y, rect.GetWidth(), rect.GetHeight()

        i = 0
        while 1:

            if toolbar_is_vertical:

                x = rect_x + (i * 4) + 4
                y = rect_y + 3
                if x > rect_width - 4:
                    break

            else:

                x = rect_x + 3
                y = rect_y + (i * 4) + 4
                if y > rect_height - 4:
                    break

            dc.SetPen(self._gripper_pen1)
            dc.DrawPoint(x, y)
            dc.SetPen(self._gripper_pen2)
            dc.DrawPoint(x, y + 1)
            dc.DrawPoint(x + 1, y)
            dc.SetPen(self._gripper_pen3)
            dc.DrawPoint(x + 2, y + 1)
            dc.DrawPoint(x + 2, y + 2)
            dc.DrawPoint(x + 1, y + 2)

            i += 1

    def DrawOverflowButton(self, dc, wnd, rect, state):
        gc = wx.GraphicsContext.Create(dc)
        if state & AUI_BUTTON_STATE_HOVER or state & AUI_BUTTON_STATE_PRESSED:

            cli_rect = wnd.GetClientRect()
            light_gray_bg = StepColour(self._highlight_colour, 170)

            if self._agwFlags & AUI_TB_VERTICAL:

                gc.SetPen(wx.Pen(self._highlight_colour))
                path = gc.CreatePath()
                path.MoveToPoint((rect.x, rect.y))
                path.AddLineToPoint((rect.x + rect.width, rect.y))
                path.CloseSubpath()
                gc.StrokePath(path)

                gc.SetPen(wx.Pen(light_gray_bg))
                gc.SetBrush(wx.Brush(light_gray_bg))
                gc.DrawRectangle(rect.x, rect.y + 1, rect.width, rect.height)

            else:
                gc.SetPen(wx.Pen(self._highlight_colour))
                path = gc.CreatePath()
                path.MoveToPoint((rect.x, rect.y))
                path.AddLineToPoint((rect.x, rect.y + rect.height))
                path.CloseSubpath()
                gc.StrokePath(path)
                gc.SetPen(wx.Pen(light_gray_bg))
                gc.SetBrush(wx.Brush(light_gray_bg))
                gc.DrawRectangle(rect.x+1, rect.y, rect.width, rect.height)

        x = rect.x + 1 + (rect.width - self._overflow_bmp.GetWidth()) / 2.0
        y = rect.y + 1 + (rect.height - self._overflow_bmp.GetHeight()) / 2.0

        w, h = self._overflow_bmp.GetSize()
        gc.DrawBitmap(self._overflow_bmp, x, y, w, h)

    def GetElementSize(self, element_id):
        if element_id == AUI_TBART_SEPARATOR_SIZE:
            return self._separator_size
        elif element_id == AUI_TBART_GRIPPER_SIZE:
            return self._gripper_size
        elif element_id == AUI_TBART_OVERFLOW_SIZE:
            return self._overflow_size

        return 0

    def SetElementSize(self, element_id, size):
        if element_id == AUI_TBART_SEPARATOR_SIZE:
            self._separator_size = size
        elif element_id == AUI_TBART_GRIPPER_SIZE:
            self._gripper_size = size
        elif element_id == AUI_TBART_OVERFLOW_SIZE:
            self._overflow_size = size

    def ShowDropDown(self, wnd, items):
        menuPopup = wx.Menu()
        items_added = 0

        for item in items:

            if item.GetKind() not in [ITEM_SEPARATOR, ITEM_SPACER, ITEM_CONTROL]:

                text = item.GetShortHelp()
                if text == "":
                    text = item.GetLabel()
                if text == "":
                    text = " "

                kind = item.GetKind()
                m = wx.MenuItem(menuPopup, item.GetId(), text, item.GetShortHelp(), kind)
                orientation = item.GetOrientation()
                item.SetOrientation(AUI_TBTOOL_HORIZONTAL)

                if kind not in [ITEM_CHECK, ITEM_RADIO]:
                    m.SetBitmap(item.GetBitmap())

                item.SetOrientation(orientation)

                menuPopup.Append(m)
                if kind in [ITEM_CHECK, ITEM_RADIO]:
                    state = (item.state & AUI_BUTTON_STATE_CHECKED and [True] or [False])[0]
                    m.Check(state)

                items_added += 1

            else:

                if items_added > 0 and item.GetKind() == ITEM_SEPARATOR:
                    menuPopup.AppendSeparator()

        cc = ToolbarCommandCapture()
        wnd.PushEventHandler(cc)

        wnd.PopupMenu(menuPopup)
        command = cc.GetCommandId()
        wnd.PopEventHandler(True)

        return command

    def GetToolsPosition(self, dc, item, rect):
        text_width = text_height = 0
        horizontal = self._orientation == AUI_TBTOOL_HORIZONTAL
        text_bottom = self._text_orientation == AUI_TBTOOL_TEXT_BOTTOM
        text_right = self._text_orientation == AUI_TBTOOL_TEXT_RIGHT

        bmp_width = item.GetBitmap().GetWidth()
        bmp_height = item.GetBitmap().GetHeight()

        if self._agwFlags & AUI_TB_TEXT:
            dc.SetFont(self._font)
            label_size = GetLabelSize(dc, item.GetLabel(), not horizontal)
            text_height = label_size.GetHeight()
            text_width = label_size.GetWidth()

        bmp_x = bmp_y = text_x = text_y = 0

        if horizontal and text_bottom:
            bmp_x = rect.x + (rect.width//2) - (bmp_width//2)
            bmp_y = rect.y + 3
            text_x = rect.x + (rect.width//2) - (text_width//2)
            text_y = rect.y + ((bmp_y - rect.y) * 2) + bmp_height

        elif horizontal and text_right:
            bmp_x = rect.x + 3
            bmp_y = rect.y + (rect.height//2) - (bmp_height // 2)
            text_x = rect.x + ((bmp_x - rect.x) * 2) + bmp_width
            text_y = rect.y + (rect.height//2) - (text_height//2)

        elif not horizontal and text_bottom:
            bmp_x = rect.x + (rect.width // 2) - (bmp_width // 2)
            bmp_y = rect.y + 3
            text_x = rect.x + (rect.width // 2) - (text_width // 2)
            text_y = rect.y + ((bmp_y - rect.y) * 2) + bmp_height

        bmp_rect = wx.Rect(bmp_x, bmp_y, bmp_width, bmp_height)
        text_rect = wx.Rect(text_x, text_y, text_width, text_height)

        return bmp_rect, text_rect
