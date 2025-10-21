

from wx.lib.agw.aui.aui_utilities import BitmapFromBits, StepColour, GetLabelSize
from wx.lib.agw.aui.aui_utilities import GetBaseColour, MakeDisabledBitmap
from wx.lib.agw.aui.aui_constants import *
import wx


# AuiToolBar events
wxEVT_COMMAND_AUITOOLBAR_TOOL_DROPDOWN = wx.NewEventType()
wxEVT_COMMAND_AUITOOLBAR_OVERFLOW_CLICK = wx.NewEventType()
wxEVT_COMMAND_AUITOOLBAR_RIGHT_CLICK = wx.NewEventType()
wxEVT_COMMAND_AUITOOLBAR_MIDDLE_CLICK = wx.NewEventType()
wxEVT_COMMAND_AUITOOLBAR_BEGIN_DRAG = wx.NewEventType()

EVT_AUITOOLBAR_TOOL_DROPDOWN = wx.PyEventBinder(wxEVT_COMMAND_AUITOOLBAR_TOOL_DROPDOWN, 1)
EVT_AUITOOLBAR_OVERFLOW_CLICK = wx.PyEventBinder(wxEVT_COMMAND_AUITOOLBAR_OVERFLOW_CLICK, 1)
EVT_AUITOOLBAR_RIGHT_CLICK = wx.PyEventBinder(wxEVT_COMMAND_AUITOOLBAR_RIGHT_CLICK, 1)
EVT_AUITOOLBAR_MIDDLE_CLICK = wx.PyEventBinder(wxEVT_COMMAND_AUITOOLBAR_MIDDLE_CLICK, 1)
EVT_AUITOOLBAR_BEGIN_DRAG = wx.PyEventBinder(wxEVT_COMMAND_AUITOOLBAR_BEGIN_DRAG, 1)


class CommandToolBarEvent(wx.PyCommandEvent):

    def __init__(self, command_type, win_id):
        if isinstance(command_type, int):
            wx.PyCommandEvent.__init__(self, command_type, win_id)
        else:
            wx.PyCommandEvent.__init__(self, command_type.GetEventType(), command_type.GetId())

        self.is_dropdown_clicked = False
        self.click_pt = wx.Point(-1, -1)
        self.rect = wx.Rect(-1, -1, 0, 0)
        self.tool_id = -1

    def IsDropDownClicked(self):
        return self.is_dropdown_clicked

    def SetDropDownClicked(self, c):
        self.is_dropdown_clicked = c

    def GetClickPoint(self):
        return self.click_pt

    def SetClickPoint(self, p):
        self.click_pt = p

    def GetItemRect(self):
        return self.rect

    def SetItemRect(self, r):
        self.rect = r

    def GetToolId(self):
        return self.tool_id

    def SetToolId(self, id):
        self.tool_id = id


class AuiToolBarEvent(CommandToolBarEvent):

    def __init__(self, command_type=None, win_id=0):
        CommandToolBarEvent.__init__(self, command_type, win_id)

        if isinstance(command_type, int):
            self.notify = wx.NotifyEvent(command_type, win_id)
        else:
            self.notify = wx.NotifyEvent(command_type.GetEventType(), command_type.GetId())

    def GetNotifyEvent(self):
        return self.notify

    def IsAllowed(self):
        return self.notify.IsAllowed()

    def Veto(self):
        self.notify.Veto()

    def Allow(self):
        self.notify.Allow()


class ToolbarCommandCapture(wx.EvtHandler):

    def __init__(self):
        wx.EvtHandler.__init__(self)
        self._last_id = 0

    def GetCommandId(self):
        return self._last_id

    def ProcessEvent(self, event):
        if event.GetEventType() == wx.wxEVT_COMMAND_MENU_SELECTED:
            self._last_id = event.GetId()
            return True

        if self.GetNextHandler():
            return self.GetNextHandler().ProcessEvent(event)

        return False


class AuiToolBarItem(object):
    def __init__(self, item=None):
        if item:
            self.Assign(item)
            return

        self.window = None
        self.clockwisebmp = wx.NullBitmap
        self.counterclockwisebmp = wx.NullBitmap
        self.clockwisedisbmp = wx.NullBitmap
        self.counterclockwisedisbmp = wx.NullBitmap
        self.sizer_item = None
        self.spacer_pixels = 0
        self.id = 0
        self.kind = ITEM_NORMAL
        self.state = 0   # normal, enabled
        self.proportion = 0
        self.active = True
        self.dropdown = True
        self.sticky = True
        self.user_data = 0

        self.label = ""
        self.bitmap = wx.NullBitmap
        self.disabled_bitmap = wx.NullBitmap
        self.hover_bitmap = wx.NullBitmap
        self.short_help = ""
        self.long_help = ""
        self.target = None
        self.min_size = wx.Size(-1, -1)
        self.alignment = wx.ALIGN_CENTER
        self.orientation = AUI_TBTOOL_HORIZONTAL

    def Assign(self, c):
        self.window = c.window
        self.label = c.label
        self.bitmap = c.bitmap
        self.disabled_bitmap = c.disabled_bitmap
        self.hover_bitmap = c.hover_bitmap
        self.short_help = c.short_help
        self.long_help = c.long_help
        self.sizer_item = c.sizer_item
        self.min_size = c.min_size
        self.spacer_pixels = c.spacer_pixels
        self.id = c.id
        self.kind = c.kind
        self.state = c.state
        self.proportion = c.proportion
        self.active = c.active
        self.dropdown = c.dropdown
        self.sticky = c.sticky
        self.user_data = c.user_data
        self.alignment = c.alignment
        self.orientation = c.orientation
        self.target = c.target

    def SetWindow(self, w):
        self.window = w

    def GetWindow(self):
        return self.window

    def SetId(self, new_id):
        self.id = new_id

    def GetId(self):
        return self.id

    def SetKind(self, new_kind):
        self.kind = new_kind

    def GetKind(self):
        return self.kind

    def SetState(self, new_state):
        self.state = new_state

    def GetState(self):
        return self.state

    def SetSizerItem(self, s):
        self.sizer_item = s

    def GetSizerItem(self):
        return self.sizer_item

    def SetLabel(self, s):
        self.label = s

    def GetLabel(self):
        return self.label

    def SetBitmap(self, bmp):
        self.bitmap = bmp

    def GetBitmap(self):
        return self.GetRotatedBitmap(False)

    def SetDisabledBitmap(self, bmp):
        self.disabled_bitmap = bmp

    def GetDisabledBitmap(self):
        return self.GetRotatedBitmap(True)

    def SetHoverBitmap(self, bmp):
        self.hover_bitmap = bmp

    def SetOrientation(self, a):
        self.orientation = a

    def GetOrientation(self):
        return self.orientation

    def GetHoverBitmap(self):
        return self.hover_bitmap

    def GetRotatedBitmap(self, disabled):
        bitmap_to_rotate = (disabled and [self.disabled_bitmap] or [self.bitmap])[0]
        if not bitmap_to_rotate.IsOk() or self.orientation == AUI_TBTOOL_HORIZONTAL:
            return bitmap_to_rotate

        rotated_bitmap = wx.NullBitmap
        clockwise = True
        if self.orientation == AUI_TBTOOL_VERT_CLOCKWISE:
            rotated_bitmap = (disabled and [self.clockwisedisbmp] or [self.clockwisebmp])[0]

        elif self.orientation == AUI_TBTOOL_VERT_COUNTERCLOCKWISE:
            rotated_bitmap = (disabled and [self.counterclockwisedisbmp] or [self.counterclockwisebmp])[0]
            clockwise = False

        if not rotated_bitmap.IsOk():
            rotated_bitmap = wx.Bitmap(bitmap_to_rotate.ConvertToImage().Rotate90(clockwise))

        return rotated_bitmap

    def SetShortHelp(self, s):
        self.short_help = s

    def GetShortHelp(self):
        return self.short_help

    def SetLongHelp(self, s):
        self.long_help = s

    def GetLongHelp(self):
        return self.long_help

    def SetMinSize(self, s):
        self.min_size = wx.Size(*s)

    def GetMinSize(self):
        return self.min_size

    def SetSpacerPixels(self, s):
        self.spacer_pixels = s

    def GetSpacerPixels(self):
        return self.spacer_pixels

    def SetProportion(self, p):
        self.proportion = p

    def GetProportion(self):
        return self.proportion

    def SetActive(self, b):
        self.active = b

    def IsActive(self):
        return self.active

    def SetHasDropDown(self, b):
        self.dropdown = b

    def HasDropDown(self):
        return self.dropdown

    def SetSticky(self, b):
        self.sticky = b

    def IsSticky(self):
        return self.sticky

    def SetUserData(self, data):
        self.user_data = data

    def GetUserData(self):
        return self.user_data

    def SetAlignment(self, align):
        self.alignment = align

    def GetAlignment(self):
        return self.alignment


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


class AuiToolBar(wx.Control):

    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, agwStyle=AUI_TB_DEFAULT_STYLE):

        wx.Control.__init__(self, parent, id, pos, size, style | wx.BORDER_NONE)

        self._sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self._sizer)
        self._button_width = -1
        self._button_height = -1
        self._sizer_element_count = 0
        self._action_pos = wx.Point(-1, -1)
        self._action_item = None
        self._tip_item = None
        self._art = AuiDefaultToolBarArt()
        self._tool_packing = 2
        self._tool_border_padding = 3
        self._tool_text_orientation = AUI_TBTOOL_TEXT_BOTTOM
        self._tool_orientation = AUI_TBTOOL_HORIZONTAL
        self._tool_alignment = wx.EXPAND
        self._gripper_sizer_item = None
        self._overflow_sizer_item = None
        self._dragging = False

        self._agwStyle = self._originalStyle = agwStyle

        self._gripper_visible = (self._agwStyle & AUI_TB_GRIPPER and [True] or [False])[0]
        self._overflow_visible = (self._agwStyle & AUI_TB_OVERFLOW and [True] or [False])[0]
        self._overflow_state = 0
        self._custom_overflow_prepend = []
        self._custom_overflow_append = []

        self._items = []

        self.SetMargins(5, 5, 2, 2)
        self.SetFont(wx.NORMAL_FONT)
        self._art.SetAGWFlags(self._agwStyle)
        self.SetExtraStyle(wx.WS_EX_PROCESS_IDLE)

        if agwStyle & AUI_TB_HORZ_LAYOUT:
            self.SetToolTextOrientation(AUI_TBTOOL_TEXT_RIGHT)
        elif agwStyle & AUI_TB_VERTICAL:
            if agwStyle & AUI_TB_CLOCKWISE:
                self.SetToolOrientation(AUI_TBTOOL_VERT_CLOCKWISE)
            elif agwStyle & AUI_TB_COUNTERCLOCKWISE:
                self.SetToolOrientation(AUI_TBTOOL_VERT_COUNTERCLOCKWISE)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_DCLICK, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
        self.Bind(wx.EVT_MIDDLE_DCLICK, self.OnMiddleDown)
        self.Bind(wx.EVT_MIDDLE_UP, self.OnMiddleUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        self.Bind(wx.EVT_SET_CURSOR, self.OnSetCursor)

    def SetWindowStyleFlag(self, style):
        wx.Control.SetWindowStyleFlag(self, style | wx.BORDER_NONE)

    def SetAGWWindowStyleFlag(self, agwStyle):
        self._agwStyle = self._originalStyle = agwStyle

        if self._art:
            self._art.SetAGWFlags(self._agwStyle)

        if agwStyle & AUI_TB_GRIPPER:
            self._gripper_visible = True
        else:
            self._gripper_visible = False

        if agwStyle & AUI_TB_OVERFLOW:
            self._overflow_visible = True
        else:
            self._overflow_visible = False

        if agwStyle & AUI_TB_HORZ_LAYOUT:
            self.SetToolTextOrientation(AUI_TBTOOL_TEXT_RIGHT)
        else:
            self.SetToolTextOrientation(AUI_TBTOOL_TEXT_BOTTOM)

        if agwStyle & AUI_TB_VERTICAL:
            if agwStyle & AUI_TB_CLOCKWISE:
                self.SetToolOrientation(AUI_TBTOOL_VERT_CLOCKWISE)
            elif agwStyle & AUI_TB_COUNTERCLOCKWISE:
                self.SetToolOrientation(AUI_TBTOOL_VERT_COUNTERCLOCKWISE)

    def GetAGWWindowStyleFlag(self):
        return self._originalStyle

    def SetArtProvider(self, art):
        del self._art
        self._art = art

        if self._art:
            self._art.SetAGWFlags(self._agwStyle)
            self._art.SetTextOrientation(self._tool_text_orientation)
            self._art.SetOrientation(self._tool_orientation)

    def GetArtProvider(self):
        return self._art

    def AddSimpleTool(self, tool_id, label, bitmap, short_help_string="", kind=ITEM_NORMAL, target=None):
        return self.AddTool(tool_id, label, bitmap, wx.NullBitmap, kind, short_help_string, "", None, target)

    def AddToggleTool(self, tool_id, bitmap, disabled_bitmap, toggle=False, client_data=None, short_help_string="", long_help_string=""):
        kind = (toggle and [ITEM_CHECK] or [ITEM_NORMAL])[0]
        return self.AddTool(tool_id, "", bitmap, disabled_bitmap, kind, short_help_string, long_help_string, client_data)

    def AddTool(self, tool_id, label, bitmap, disabled_bitmap, kind, short_help_string='', long_help_string='', client_data=None, target=None):
        item = AuiToolBarItem()
        item.window = None
        item.label = label
        item.bitmap = bitmap
        item.disabled_bitmap = disabled_bitmap
        item.short_help = short_help_string
        item.long_help = long_help_string
        item.target = target
        item.active = True
        item.dropdown = False
        item.spacer_pixels = 0

        if tool_id == wx.ID_ANY:
            tool_id = wx.NewIdRef()

        item.id = tool_id
        item.state = 0
        item.proportion = 0
        item.kind = kind
        item.sizer_item = None
        item.min_size = wx.Size(-1, -1)
        item.user_data = 0
        item.sticky = False
        item.orientation = self._tool_orientation

        if not item.disabled_bitmap.IsOk():
            # no disabled bitmap specified, we need to make one
            if item.bitmap.IsOk():
                item.disabled_bitmap = MakeDisabledBitmap(item.bitmap)

        self._items.append(item)
        return self._items[-1]

    def AddCheckTool(self, tool_id, label, bitmap, disabled_bitmap, short_help_string="", long_help_string="", client_data=None):
        return self.AddTool(tool_id, label, bitmap, disabled_bitmap, ITEM_CHECK, short_help_string, long_help_string, client_data)

    def AddRadioTool(self, tool_id, label, bitmap, disabled_bitmap, short_help_string="", long_help_string="", client_data=None):
        return self.AddTool(tool_id, label, bitmap, disabled_bitmap, ITEM_RADIO, short_help_string, long_help_string, client_data)

    def AddControl(self, control, label=""):
        item = AuiToolBarItem()
        item.window = control
        item.label = label
        item.bitmap = wx.NullBitmap
        item.disabled_bitmap = wx.NullBitmap
        item.active = True
        item.dropdown = False
        item.spacer_pixels = 0
        item.id = control.GetId()
        item.state = 0
        item.proportion = 0
        item.kind = ITEM_CONTROL
        item.sizer_item = None
        item.min_size = control.GetEffectiveMinSize()
        item.user_data = 0
        item.sticky = False
        item.orientation = self._tool_orientation

        self._items.append(item)
        return self._items[-1]

    def AddLabel(self, tool_id, label="", width=0):
        min_size = wx.Size(-1, -1)

        if width != -1:
            min_size.x = width

        item = AuiToolBarItem()
        item.window = None
        item.label = label
        item.bitmap = wx.NullBitmap
        item.disabled_bitmap = wx.NullBitmap
        item.active = True
        item.dropdown = False
        item.spacer_pixels = 0

        if tool_id == wx.ID_ANY:
            tool_id = wx.NewIdRef()

        item.id = tool_id
        item.state = 0
        item.proportion = 0
        item.kind = ITEM_LABEL
        item.sizer_item = None
        item.min_size = min_size
        item.user_data = 0
        item.sticky = False
        item.orientation = self._tool_orientation

        self._items.append(item)
        return self._items[-1]

    def AddSeparator(self):
        item = AuiToolBarItem()
        item.window = None
        item.label = ""
        item.bitmap = wx.NullBitmap
        item.disabled_bitmap = wx.NullBitmap
        item.active = True
        item.dropdown = False
        item.id = -1
        item.state = 0
        item.proportion = 0
        item.kind = ITEM_SEPARATOR
        item.sizer_item = None
        item.min_size = wx.Size(-1, -1)
        item.user_data = 0
        item.sticky = False
        item.orientation = self._tool_orientation

        self._items.append(item)
        return self._items[-1]

    def AddSpacer(self, pixels):
        item = AuiToolBarItem()
        item.window = None
        item.label = ""
        item.bitmap = wx.NullBitmap
        item.disabled_bitmap = wx.NullBitmap
        item.active = True
        item.dropdown = False
        item.spacer_pixels = pixels
        item.id = -1
        item.state = 0
        item.proportion = 0
        item.kind = ITEM_SPACER
        item.sizer_item = None
        item.min_size = wx.Size(-1, -1)
        item.user_data = 0
        item.sticky = False
        item.orientation = self._tool_orientation

        self._items.append(item)
        return self._items[-1]

    def AddStretchSpacer(self, proportion=1):
        item = AuiToolBarItem()
        item.window = None
        item.label = ""
        item.bitmap = wx.NullBitmap
        item.disabled_bitmap = wx.NullBitmap
        item.active = True
        item.dropdown = False
        item.spacer_pixels = 0
        item.id = -1
        item.state = 0
        item.proportion = proportion
        item.kind = ITEM_SPACER
        item.sizer_item = None
        item.min_size = wx.Size(-1, -1)
        item.user_data = 0
        item.sticky = False
        item.orientation = self._tool_orientation

        self._items.append(item)
        return self._items[-1]

    def Clear(self):
        self._items = []
        self._sizer_element_count = 0

    def ClearTools(self):
        self.Clear()

    def DeleteTool(self, tool):

        if isinstance(tool, AuiToolBarItem):
            try:
                self._items.remove(tool)
                self.Realize()
                return True
            except ValueError:
                return False
        # Assume tool is the id of the tool to be removed
        return self.DeleteToolByPos(self.GetToolIndex(tool))

    def DeleteToolByPos(self, pos):
        if 0 <= pos < len(self._items):

            self._items.pop(pos)
            self.Realize()
            return True

        return False

    def FindControl(self, id):
        wnd = self.FindWindow(id)
        return wnd

    def FindTool(self, tool_id):
        for item in self._items:
            if item.id == tool_id:
                return item

        return None

    def FindToolByLabel(self, label):
        for item in self._items:
            if item.label == label:
                return item

        return None

    def FindToolByUserData(self, userData):
        for item in self._items:
            if item.user_data == userData:
                return item

        return None

    def FindToolForPosition(self, x, y):
        for i, item in enumerate(self._items):
            if not item.sizer_item:
                continue

            rect = item.sizer_item.GetRect()
            if rect.Contains((x, y)):

                # if the item doesn't fit on the toolbar, return None
                if not self.GetToolFitsByIndex(i):
                    return None

                return item

        return None

    def HitTest(self, x, y):
        return self.FindToolForPosition(*self.ScreenToClient((x, y)))

    def FindToolForPositionWithPacking(self, x, y):
        count = len(self._items)

        for i, item in enumerate(self._items):
            if not item.sizer_item:
                continue

            rect = item.sizer_item.GetRect()

            # apply tool packing
            if i+1 < count:
                rect.width += self._tool_packing

            if rect.Contains((x, y)):

                # if the item doesn't fit on the toolbar, return None
                if not self.GetToolFitsByIndex(i):
                    return None

                return item

        return None

    def FindToolByIndex(self, pos):
        if pos < 0 or pos >= len(self._items):
            return None

        return self._items[pos]

    def SetToolBitmapSize(self, size):
        # TODO: wx.ToolBar compatibility
        pass

    def GetToolBitmapSize(self):
        # TODO: wx.ToolBar compatibility
        return wx.Size(16, 15)

    def SetToolProportion(self, tool_id, proportion):
        item = self.FindTool(tool_id)
        if not item:
            return

        item.proportion = proportion

    def GetToolProportion(self, tool_id):

        item = self.FindTool(tool_id)
        if not item:
            return

        return item.proportion

    def SetToolSeparation(self, separation):
        if self._art:
            self._art.SetElementSize(AUI_TBART_SEPARATOR_SIZE, separation)

    def GetToolSeparation(self):
        if self._art:
            return self._art.GetElementSize(AUI_TBART_SEPARATOR_SIZE)

        return 5

    def SetToolDropDown(self, tool_id, dropdown):
        item = self.FindTool(tool_id)
        if not item:
            return

        item.dropdown = dropdown

    def GetToolDropDown(self, tool_id):
        item = self.FindTool(tool_id)
        if not item:
            return

        return item.dropdown

    def SetToolSticky(self, tool_id, sticky):
        # ignore separators
        if tool_id == -1:
            return

        item = self.FindTool(tool_id)
        if not item:
            return

        if item.sticky == sticky:
            return

        item.sticky = sticky

        self.Refresh(False)
        self.Update()

    def GetToolSticky(self, tool_id):
        item = self.FindTool(tool_id)
        if not item:
            return

        return item.sticky

    def SetToolBorderPadding(self, padding):
        self._tool_border_padding = padding

    def GetToolBorderPadding(self):
        return self._tool_border_padding

    def SetToolTextOrientation(self, orientation):
        self._tool_text_orientation = orientation

        if self._art:
            self._art.SetTextOrientation(orientation)

    def GetToolTextOrientation(self):
        return self._tool_text_orientation

    def SetToolOrientation(self, orientation):
        self._tool_orientation = orientation
        if self._art:
            self._art.SetOrientation(orientation)

    def GetToolOrientation(self):
        return self._tool_orientation

    def SetToolPacking(self, packing):
        self._tool_packing = packing

    def GetToolPacking(self):
        return self._tool_packing

    def SetOrientation(self, orientation):
        pass

    def SetMargins(self, left=-1, right=-1, top=-1, bottom=-1):
        if left != -1:
            self._left_padding = left
        if right != -1:
            self._right_padding = right
        if top != -1:
            self._top_padding = top
        if bottom != -1:
            self._bottom_padding = bottom

    def SetMarginsSize(self, size):
        self.SetMargins(size.x, size.x, size.y, size.y)

    def SetMarginsXY(self, x, y):
        self.SetMargins(x, x, y, y)

    def GetGripperVisible(self):
        return self._gripper_visible

    def SetGripperVisible(self, visible):
        self._gripper_visible = visible
        if visible:
            self._agwStyle |= AUI_TB_GRIPPER
        else:
            self._agwStyle &= ~AUI_TB_GRIPPER

        self.Realize()
        self.Refresh(False)

    def GetOverflowVisible(self):
        return self._overflow_visible

    def SetOverflowVisible(self, visible):
        self._overflow_visible = visible
        if visible:
            self._agwStyle |= AUI_TB_OVERFLOW
        else:
            self._agwStyle &= ~AUI_TB_OVERFLOW

        self.Refresh(False)

    def SetFont(self, font):
        res = wx.Control.SetFont(self, font)

        if self._art:
            self._art.SetFont(font)

        return res

    def SetHoverItem(self, pitem):
        former_hover = None

        for item in self._items:

            if item.state & AUI_BUTTON_STATE_HOVER:
                former_hover = item

            item.state &= ~AUI_BUTTON_STATE_HOVER

        if pitem:
            pitem.state |= AUI_BUTTON_STATE_HOVER

        if former_hover != pitem:
            self.Refresh(False)
            self.Update()

    def SetPressedItem(self, pitem):
        former_item = None

        for item in self._items:

            if item.state & AUI_BUTTON_STATE_PRESSED:
                former_item = item

            item.state &= ~AUI_BUTTON_STATE_PRESSED

        if pitem:
            pitem.state &= ~AUI_BUTTON_STATE_HOVER
            pitem.state |= AUI_BUTTON_STATE_PRESSED

        if former_item != pitem:
            self.Refresh(False)
            self.Update()

    def RefreshOverflowState(self):
        if not self.GetOverflowVisible():
            self._overflow_state = 0
            return

        overflow_state = 0
        overflow_rect = self.GetOverflowRect()

        # find out the mouse's current position
        pt = wx.GetMousePosition()
        pt = self.ScreenToClient(pt)

        # find out if the mouse cursor is inside the dropdown rectangle
        if overflow_rect.Contains((pt.x, pt.y)):

            if wx.GetMouseState().LeftIsDown():
                overflow_state = AUI_BUTTON_STATE_PRESSED
            else:
                overflow_state = AUI_BUTTON_STATE_HOVER

        if overflow_state != self._overflow_state:
            self._overflow_state = overflow_state
            self.Refresh(False)
            self.Update()

        self._overflow_state = overflow_state

    def ToggleTool(self, tool_id, state):
        tool = self.FindTool(tool_id)

        if tool:
            if tool.kind not in [ITEM_CHECK, ITEM_RADIO]:
                return

            if tool.kind == ITEM_RADIO:
                idx = self.GetToolIndex(tool_id)
                if 0 <= idx < len(self._items):
                    for i in range(idx, len(self._items)):
                        tool = self.FindToolByIndex(i)
                        if tool.kind != ITEM_RADIO:
                            break
                        tool.state &= ~AUI_BUTTON_STATE_CHECKED

                    for i in range(idx, -1, -1):
                        tool = self.FindToolByIndex(i)
                        if tool.kind != ITEM_RADIO:
                            break
                        tool.state &= ~AUI_BUTTON_STATE_CHECKED

                    tool = self.FindTool(tool_id)
                    tool.state |= AUI_BUTTON_STATE_CHECKED
            else:
                if state:
                    tool.state |= AUI_BUTTON_STATE_CHECKED
                else:
                    tool.state &= ~AUI_BUTTON_STATE_CHECKED

    def GetToolToggled(self, tool_id):
        tool = self.FindTool(tool_id)

        if tool:
            if tool.kind not in [ITEM_CHECK, ITEM_RADIO]:
                return False

            return (tool.state & AUI_BUTTON_STATE_CHECKED and [True] or [False])[0]

        return False

    def EnableTool(self, tool_id, state):
        tool = self.FindTool(tool_id)

        if tool:

            if state:
                tool.state &= ~AUI_BUTTON_STATE_DISABLED
            else:
                tool.state |= AUI_BUTTON_STATE_DISABLED

    def GetToolEnabled(self, tool_id):
        tool = self.FindTool(tool_id)

        if tool:
            return (tool.state & AUI_BUTTON_STATE_DISABLED and [False] or [True])[0]

        return False

    def GetToolLabel(self, tool_id):
        tool = self.FindTool(tool_id)
        if not tool:
            return ""

        return tool.label

    def SetToolLabel(self, tool_id, label):
        tool = self.FindTool(tool_id)
        if tool:
            tool.label = label

    def GetToolBitmap(self, tool_id):
        tool = self.FindTool(tool_id)
        if not tool:
            return wx.NullBitmap

        return tool.bitmap

    def SetToolBitmap(self, tool_id, bitmap):
        tool = self.FindTool(tool_id)
        if tool:
            tool.bitmap = bitmap

    def SetToolNormalBitmap(self, tool_id, bitmap):
        self.SetToolBitmap(tool_id, bitmap)

    def SetToolDisabledBitmap(self, tool_id, bitmap):
        tool = self.FindTool(tool_id)
        if tool:
            tool.disabled_bitmap = bitmap

    def GetToolShortHelp(self, tool_id):
        tool = self.FindTool(tool_id)
        if not tool:
            return ""

        return tool.short_help

    def SetToolShortHelp(self, tool_id, help_string):
        tool = self.FindTool(tool_id)
        if tool:
            tool.short_help = help_string

    def GetToolLongHelp(self, tool_id):
        tool = self.FindTool(tool_id)
        if not tool:
            return ""

        return tool.long_help

    def SetToolAlignment(self, alignment=wx.EXPAND):
        self._tool_alignment = alignment

    def SetToolLongHelp(self, tool_id, help_string):
        tool = self.FindTool(tool_id)
        if tool:
            tool.long_help = help_string

    def SetCustomOverflowItems(self, prepend, append):
        self._custom_overflow_prepend = prepend
        self._custom_overflow_append = append

    def GetToolCount(self):
        return len(self._items)

    def GetToolIndex(self, tool_id):
        # this will prevent us from returning the index of the
        # first separator in the toolbar since its id is equal to -1
        if tool_id == -1:
            return wx.NOT_FOUND

        for i, item in enumerate(self._items):
            if item.id == tool_id:
                return i

        return wx.NOT_FOUND

    def GetToolPos(self, tool_id):
        return self.GetToolIndex(tool_id)

    def GetToolFitsByIndex(self, tool_id):
        if tool_id < 0 or tool_id >= len(self._items):
            return False

        if not self._items[tool_id].sizer_item:
            return False

        cli_w, cli_h = self.GetClientSize()
        rect = self._items[tool_id].sizer_item.GetRect()
        dropdown_size = self._art.GetElementSize(AUI_TBART_OVERFLOW_SIZE)

        if self._agwStyle & AUI_TB_VERTICAL:
            # take the dropdown size into account
            if self._overflow_visible:
                cli_h -= dropdown_size

            if rect.y+rect.height < cli_h:
                return True

        else:

            # take the dropdown size into account
            if self._overflow_visible:
                cli_w -= dropdown_size

            if rect.x+rect.width < cli_w:
                return True

        return False

    def GetToolFits(self, tool_id):
        return self.GetToolFitsByIndex(self.GetToolIndex(tool_id))

    def GetToolRect(self, tool_id):
        tool = self.FindTool(tool_id)
        if tool and tool.sizer_item:
            return tool.sizer_item.GetRect()

        return wx.Rect()

    def GetToolBarFits(self):
        if len(self._items) == 0:
            # empty toolbar always 'fits'
            return True

        # entire toolbar content fits if the last tool fits
        return self.GetToolFitsByIndex(len(self._items) - 1)

    def Realize(self):
        dc = wx.ClientDC(self)

        if not dc.IsOk():
            return False

        horizontal = True
        if self._agwStyle & AUI_TB_VERTICAL:
            horizontal = False

        # create the new sizer to add toolbar elements to
        sizer = wx.BoxSizer((horizontal and [wx.HORIZONTAL] or [wx.VERTICAL])[0])
        # local opts

        # add gripper area
        separator_size = self._art.GetElementSize(AUI_TBART_SEPARATOR_SIZE)
        gripper_size = self._art.GetElementSize(AUI_TBART_GRIPPER_SIZE)

        if gripper_size > 0 and self._gripper_visible:
            if horizontal:
                self._gripper_sizer_item = sizer.Add((gripper_size, 1), 0, wx.EXPAND)
            else:
                self._gripper_sizer_item = sizer.Add((1, gripper_size), 0, wx.EXPAND)
        else:
            self._gripper_sizer_item = None

        # add "left" padding
        if self._left_padding > 0:
            if horizontal:
                sizer.Add((self._left_padding, 1))
            else:
                sizer.Add((1, self._left_padding))

        count = len(self._items)
        for i, item in enumerate(self._items):

            sizer_item = None
            kind = item.kind

            if kind == ITEM_LABEL:

                size = self._art.GetLabelSize(dc, self, item)
                sizer_item = sizer.Add((size.x + (self._tool_border_padding * 2),
                                        size.y + (self._tool_border_padding * 2)),
                                       item.proportion,
                                       item.alignment)
                if i+1 < count:
                    sizer.AddSpacer(self._tool_packing)

            elif kind in [ITEM_CHECK, ITEM_NORMAL, ITEM_RADIO]:

                size = self._art.GetToolSize(dc, self, item)
                sizer_item = sizer.Add((size.x + (self._tool_border_padding * 2),
                                        size.y + (self._tool_border_padding * 2)),
                                       0,
                                       item.alignment)
                # add tool packing
                if i + 1 < count:
                    sizer.AddSpacer(self._tool_packing)

            elif kind == ITEM_SEPARATOR:

                if horizontal:
                    sizer_item = sizer.Add((separator_size, 1), 0, wx.EXPAND)
                else:
                    sizer_item = sizer.Add((1, separator_size), 0, wx.EXPAND)

                # add tool packing
                if i+1 < count:
                    sizer.AddSpacer(self._tool_packing)

            elif kind == ITEM_SPACER:

                if item.proportion > 0:
                    sizer_item = sizer.AddStretchSpacer(item.proportion)
                else:
                    sizer_item = sizer.Add((item.spacer_pixels, 1))

            elif kind == ITEM_CONTROL:
                if item.window and item.window.GetContainingSizer():
                    # Make sure that there is only one sizer to this control
                    item.window.GetContainingSizer().Detach(item.window)

                if item.window and not item.window.IsShown():
                    item.window.Show(True)

                vert_sizer = wx.BoxSizer(wx.VERTICAL)
                vert_sizer.AddStretchSpacer(1)
                vert_sizer.Add(item.window, 0, wx.EXPAND)
                vert_sizer.AddStretchSpacer(1)

                if (
                    self._agwStyle & AUI_TB_TEXT and
                    self._tool_text_orientation == AUI_TBTOOL_TEXT_BOTTOM and
                    item.GetLabel() != ""
                ):

                    s = self.GetLabelSize(item.GetLabel())
                    vert_sizer.Add((1, s.y))

                sizer_item = sizer.Add(vert_sizer, item.proportion, wx.EXPAND)
                min_size = item.min_size

                # proportional items will disappear from the toolbar if
                # their min width is not set to something really small
                if item.proportion != 0:
                    min_size.x = 1

                if min_size.IsFullySpecified():
                    sizer.SetItemMinSize(vert_sizer, min_size)
                    vert_sizer.SetItemMinSize(item.window, min_size)

                # add tool packing
                if i+1 < count:
                    sizer.AddSpacer(self._tool_packing)

            item.sizer_item = sizer_item

        # add "right" padding
        if self._right_padding > 0:
            if horizontal:
                sizer.Add((self._right_padding, 1))
            else:
                sizer.Add((1, self._right_padding))

        # add drop down area
        self._overflow_sizer_item = None

        if self._agwStyle & AUI_TB_OVERFLOW:

            overflow_size = self._art.GetElementSize(AUI_TBART_OVERFLOW_SIZE)
            if (
                overflow_size > 0 and
                (self._custom_overflow_append or self._custom_overflow_prepend)
            ):
                # add drop down area only if there is any custom overflow
                # item; otherwise, the overflow button should not affect the
                # min size.

                if horizontal:
                    self._overflow_sizer_item = sizer.Add((overflow_size, 1), 0, wx.EXPAND)
                else:
                    self._overflow_sizer_item = sizer.Add((1, overflow_size), 0, wx.EXPAND)

            else:

                self._overflow_sizer_item = None

        # the outside sizer helps us apply the "top" and "bottom" padding
        outside_sizer = wx.BoxSizer((horizontal and [wx.VERTICAL] or [wx.HORIZONTAL])[0])

        # add "top" padding
        if self._top_padding > 0:

            if horizontal:
                outside_sizer.Add((1, self._top_padding))
            else:
                outside_sizer.Add((self._top_padding, 1))

        # add the sizer that contains all of the toolbar elements
        outside_sizer.Add(sizer, 1, self._tool_alignment)

        # add "bottom" padding
        if self._bottom_padding > 0:

            if horizontal:
                outside_sizer.Add((1, self._bottom_padding))
            else:
                outside_sizer.Add((self._bottom_padding, 1))

        del self._sizer  # remove old sizer
        self._sizer = outside_sizer
        self.SetSizer(outside_sizer)

        # calculate the rock-bottom minimum size
        for item in self._items:

            if item.sizer_item and item.proportion > 0 and item.min_size.IsFullySpecified():
                item.sizer_item.SetMinSize((0, 0))

        self._absolute_min_size = self._sizer.GetMinSize()

        # reset the min sizes to what they were
        for item in self._items:

            if item.sizer_item and item.proportion > 0 and item.min_size.IsFullySpecified():
                item.sizer_item.SetMinSize(item.min_size)

        # set control size
        size = self._sizer.GetMinSize()
        self.SetMinSize(size)
        self._minWidth = size.x
        self._minHeight = size.y

        if self._agwStyle & AUI_TB_NO_AUTORESIZE == 0:

            cur_size = self.GetClientSize()
            new_size = self.GetMinSize()

            if new_size != cur_size:

                self.SetClientSize(new_size)

            else:

                self._sizer.SetDimension(0, 0, cur_size.x, cur_size.y)

        else:
            cur_size = self.GetClientSize()
            self._sizer.SetDimension(0, 0, cur_size.x, cur_size.y)

        self.Refresh(False)
        return True

    def GetOverflowState(self):
        return self._overflow_state

    def GetOverflowRect(self):
        cli_rect = wx.Rect(wx.Point(0, 0), self.GetClientSize())
        overflow_rect = wx.Rect(0, 0, 0, 0)
        overflow_size = self._art.GetElementSize(AUI_TBART_OVERFLOW_SIZE)

        if self._agwStyle & AUI_TB_VERTICAL:

            overflow_rect.y = cli_rect.height - overflow_size
            overflow_rect.x = 0
            overflow_rect.width = cli_rect.width
            overflow_rect.height = overflow_size

        else:

            overflow_rect.x = cli_rect.width - overflow_size
            overflow_rect.y = 0
            overflow_rect.width = overflow_size
            overflow_rect.height = cli_rect.height

        return overflow_rect

    def GetLabelSize(self, label):
        dc = wx.ClientDC(self)
        dc.SetFont(self._font)

        return GetLabelSize(dc, label, self._tool_orientation != AUI_TBTOOL_HORIZONTAL)

    def GetAuiManager(self):
        try:
            return self._auiManager
        except AttributeError:
            return False

    def SetAuiManager(self, auiManager):
        self._auiManager = auiManager

    def DoIdleUpdate(self):
        if not self:
            return  # The action Destroyed the toolbar!

        handler = self.GetEventHandler()
        if not handler:
            return

        need_refresh = False

        for item in self._items:

            if item.id == -1:
                continue

            evt = wx.UpdateUIEvent(item.id)
            evt.SetEventObject(self)

            if handler.ProcessEvent(evt):

                if evt.GetSetEnabled():

                    if item.window:
                        is_enabled = item.window.IsEnabled()
                    else:
                        is_enabled = (item.state & AUI_BUTTON_STATE_DISABLED and [False] or [True])[0]

                    new_enabled = evt.GetEnabled()
                    if new_enabled != is_enabled:

                        if item.window:
                            item.window.Enable(new_enabled)
                        else:
                            if new_enabled:
                                item.state &= ~AUI_BUTTON_STATE_DISABLED
                            else:
                                item.state |= AUI_BUTTON_STATE_DISABLED

                        need_refresh = True

                if evt.GetSetChecked():

                    # make sure we aren't checking an item that can't be
                    if item.kind != ITEM_CHECK and item.kind != ITEM_RADIO:
                        continue

                    is_checked = (item.state & AUI_BUTTON_STATE_CHECKED and [True] or [False])[0]
                    new_checked = evt.GetChecked()

                    if new_checked != is_checked:

                        if new_checked:
                            item.state |= AUI_BUTTON_STATE_CHECKED
                        else:
                            item.state &= ~AUI_BUTTON_STATE_CHECKED

                        need_refresh = True

        if need_refresh:
            self.Refresh(False)

    def OnSize(self, event):
        x, y = self.GetClientSize()
        realize = False

        if x > y:
            self.SetOrientation(wx.HORIZONTAL)
        else:
            self.SetOrientation(wx.VERTICAL)

        horizontal = True
        if self._agwStyle & AUI_TB_VERTICAL:
            horizontal = False

        if (
            (horizontal and self._absolute_min_size.x > x) or
            (not horizontal and self._absolute_min_size.y > y)
        ):

            if self._originalStyle & AUI_TB_OVERFLOW:
                if not self.GetOverflowVisible():
                    self.SetOverflowVisible(True)

            # hide all flexible items and items that do not fit into toolbar
            self_GetToolFitsByIndex = self.GetToolFitsByIndex
            for i, item in enumerate(self._items):
                sizer_item = item.sizer_item
                if not sizer_item:
                    continue

                if item.proportion > 0:
                    if sizer_item.IsShown():
                        sizer_item.Show(False)
                        sizer_item.SetProportion(0)
                elif self_GetToolFitsByIndex(i):
                    if not sizer_item.IsShown():
                        sizer_item.Show(True)
                else:
                    if sizer_item.IsShown():
                        sizer_item.Show(False)

        else:

            if (
                self._originalStyle & AUI_TB_OVERFLOW and
                not self._custom_overflow_append and
                not self._custom_overflow_prepend
            ):
                if self.GetOverflowVisible():
                    self.SetOverflowVisible(False)

            # show all items
            for item in self._items:
                sizer_item = item.sizer_item
                if not sizer_item:
                    continue

                if not sizer_item.IsShown():
                    sizer_item.Show(True)
                    if item.proportion > 0:
                        sizer_item.SetProportion(item.proportion)

        self._sizer.SetDimension(0, 0, x, y)

        self.Refresh(False)

        self.Update()

    def DoSetSize(self, x, y, width, height, sizeFlags=wx.SIZE_AUTO):
        parent_size = self.GetParent().GetClientSize()
        if x + width > parent_size.x:
            width = max(0, parent_size.x - x)
        if y + height > parent_size.y:
            height = max(0, parent_size.y - y)

        wx.Control.DoSetSize(self, x, y, width, height, sizeFlags)

    def OnIdle(self, event):
        self.DoIdleUpdate()
        event.Skip()

    def DoGetBestSize(self):
        return self._absolute_min_size

    def OnPaint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        cli_rect = wx.Rect(wx.Point(0, 0), self.GetClientSize())

        horizontal = True
        if self._agwStyle & AUI_TB_VERTICAL:
            horizontal = False

        if self._agwStyle & AUI_TB_PLAIN_BACKGROUND:
            self._art.DrawPlainBackground(dc, self, cli_rect)
        else:
            self._art.DrawBackground(dc, self, cli_rect, horizontal)

        gripper_size = self._art.GetElementSize(AUI_TBART_GRIPPER_SIZE)
        dropdown_size = self._art.GetElementSize(AUI_TBART_OVERFLOW_SIZE)

        # paint the gripper
        if (
            self._agwStyle & AUI_TB_GRIPPER and
            gripper_size > 0 and
            self._gripper_sizer_item
        ):
            gripper_rect = wx.Rect(*self._gripper_sizer_item.GetRect())
            if horizontal:
                gripper_rect.width = gripper_size
            else:
                gripper_rect.height = gripper_size

            self._art.DrawGripper(dc, self, gripper_rect)

        # calculated how far we can draw items
        if horizontal:
            last_extent = cli_rect.width
        else:
            last_extent = cli_rect.height

        if self._overflow_visible:
            last_extent -= dropdown_size

        # paint each individual tool
        # local opts
        for item in self._items:

            if not item.sizer_item:
                continue

            item_rect = wx.Rect(*item.sizer_item.GetRect())

            if (
                (horizontal and item_rect.x + item_rect.width >= last_extent) or
                (not horizontal and item_rect.y + item_rect.height >= last_extent)
            ):

                break

            item_kind = item.kind
            if item_kind == ITEM_SEPARATOR:
                # draw a separator
                self._art.DrawSeparator(dc, self, item_rect)

            elif item_kind == ITEM_LABEL:
                # draw a text label only
                self._art.DrawLabel(dc, self, item, item_rect)

            elif item_kind == ITEM_NORMAL:
                # draw a regular button or dropdown button
                if not item.dropdown:
                    self._art.DrawButton(dc, self, item, item_rect)
                else:
                    self._art.DrawDropDownButton(dc, self, item, item_rect)

            elif item_kind == ITEM_CHECK:
                # draw a regular toggle button or a dropdown one
                if not item.dropdown:
                    self._art.DrawButton(dc, self, item, item_rect)
                else:
                    self._art.DrawDropDownButton(dc, self, item, item_rect)

            elif item_kind == ITEM_RADIO:
                # draw a toggle button
                self._art.DrawButton(dc, self, item, item_rect)

            elif item_kind == ITEM_CONTROL:
                # draw the control's label
                self._art.DrawControlLabel(dc, self, item, item_rect)

            # fire a signal to see if the item wants to be custom-rendered
            self.OnCustomRender(dc, item, item_rect)

        # paint the overflow button
        if dropdown_size > 0 and self.GetOverflowVisible():
            dropdown_rect = self.GetOverflowRect()
            self._art.DrawOverflowButton(dc, self, dropdown_rect, self._overflow_state)

    def OnEraseBackground(self, event):
        pass

    def OnLeftDown(self, event):
        cli_rect = wx.Rect(wx.Point(0, 0), self.GetClientSize())
        self.StopPreviewTimer()

        if self._gripper_sizer_item:

            gripper_rect = wx.Rect(*self._gripper_sizer_item.GetRect())
            if gripper_rect.Contains(event.GetPosition()):

                # find aui manager
                manager = self.GetAuiManager()
                if not manager:
                    return

                x_drag_offset = event.GetX() - gripper_rect.GetX()
                y_drag_offset = event.GetY() - gripper_rect.GetY()

                clientPt = wx.Point(*event.GetPosition())
                screenPt = self.ClientToScreen(clientPt)
                managedWindow = manager.GetManagedWindow()
                managerClientPt = managedWindow.ScreenToClient(screenPt)

                # gripper was clicked
                manager.OnGripperClicked(self, managerClientPt, wx.Point(x_drag_offset, y_drag_offset))
                return

        if self.GetOverflowVisible():
            overflow_rect = self.GetOverflowRect()

            if self._art and self._overflow_visible and overflow_rect.Contains(event.GetPosition()):

                e = AuiToolBarEvent(wxEVT_COMMAND_AUITOOLBAR_OVERFLOW_CLICK, -1)
                e.SetEventObject(self)
                e.SetToolId(-1)
                e.SetClickPoint(event.GetPosition())
                processed = self.ProcessEvent(e)

                if processed:
                    self.DoIdleUpdate()
                else:
                    overflow_items = []

                    # add custom overflow prepend items, if any
                    count = len(self._custom_overflow_prepend)
                    for i in range(count):
                        overflow_items.append(self._custom_overflow_prepend[i])

                    # only show items that don't fit in the dropdown
                    count = len(self._items)
                    for i in range(count):

                        if not self.GetToolFitsByIndex(i):
                            overflow_items.append(self._items[i])

                    # add custom overflow append items, if any
                    count = len(self._custom_overflow_append)
                    for i in range(count):
                        overflow_items.append(self._custom_overflow_append[i])

                    res = self._art.ShowDropDown(self, overflow_items)
                    self._overflow_state = 0
                    self.Refresh(False)
                    if res != -1:
                        e = wx.CommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, res)
                        e.SetEventObject(self)
                        if not self.GetParent().ProcessEvent(e):
                            tool = self.FindTool(res)
                            if tool:
                                state = (tool.state & AUI_BUTTON_STATE_CHECKED and [True] or [False])[0]
                                self.ToggleTool(res, not state)

                return

        self._dragging = False
        self._action_pos = wx.Point(*event.GetPosition())
        self._action_item = self.FindToolForPosition(*event.GetPosition())

        if self._action_item:

            if self._action_item.state & AUI_BUTTON_STATE_DISABLED:

                self._action_pos = wx.Point(-1, -1)
                self._action_item = None
                return

            self.SetPressedItem(self._action_item)

            # fire the tool dropdown event
            e = AuiToolBarEvent(wxEVT_COMMAND_AUITOOLBAR_TOOL_DROPDOWN, self._action_item.id)
            e.SetEventObject(self)
            e.SetToolId(self._action_item.id)
            e.SetDropDownClicked(False)

            mouse_x, mouse_y = event.GetX(), event.GetY()
            rect = wx.Rect(*self._action_item.sizer_item.GetRect())

            if self._action_item.dropdown:
                if (
                    (
                        self._action_item.orientation == AUI_TBTOOL_HORIZONTAL and (
                        rect.x + rect.width - BUTTON_DROPDOWN_WIDTH - 1) <= mouse_x < rect.x + rect.width) or
                    (
                        self._action_item.orientation != AUI_TBTOOL_HORIZONTAL and (
                        rect.y + rect.height - BUTTON_DROPDOWN_WIDTH - 1) <= mouse_y < rect.y + rect.height)
                ):
                    e.SetDropDownClicked(True)

            e.SetClickPoint(event.GetPosition())
            e.SetItemRect(rect)
            self.ProcessEvent(e)
            self.DoIdleUpdate()

    def OnLeftUp(self, event):
        self.SetPressedItem(None)

        hit_item = self.FindToolForPosition(*event.GetPosition())

        if hit_item and not hit_item.state & AUI_BUTTON_STATE_DISABLED:
            self.SetHoverItem(hit_item)

        if self._dragging:
            # reset drag and drop member variables
            self._dragging = False
            self._action_pos = wx.Point(-1, -1)
            self._action_item = None

        else:

            if self._action_item and hit_item == self._action_item:
                self.SetToolTip("")

                if hit_item.kind in [ITEM_CHECK, ITEM_RADIO]:
                    toggle = not (self._action_item.state & AUI_BUTTON_STATE_CHECKED)
                    self.ToggleTool(self._action_item.id, toggle)

                    # repaint immediately
                    self.Refresh(False)
                    self.Update()

                    e = wx.CommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, self._action_item.id)
                    e.SetEventObject(self)
                    e.SetInt(toggle)
                    self._action_pos = wx.Point(-1, -1)
                    self._action_item = None

                    self.ProcessEvent(e)
                    self.DoIdleUpdate()

                else:

                    if self._action_item.id == ID_RESTORE_FRAME:
                        # find aui manager
                        manager = self.GetAuiManager()

                        if not manager:
                            return

                        if self._action_item.target:
                            pane = manager.GetPane(self._action_item.target)
                        else:
                            pane = manager.GetPane(self)

                        from wx.lib.agw.aui import framemanager
                        e = framemanager.AuiManagerEvent(framemanager.wxEVT_AUI_PANE_MIN_RESTORE)

                        e.SetManager(manager)
                        e.SetPane(pane)

                        manager.ProcessEvent(e)
                        self.DoIdleUpdate()

                    else:

                        e = wx.CommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, self._action_item.id)
                        e.SetEventObject(self)
                        self.ProcessEvent(e)
                        self.DoIdleUpdate()

        # reset drag and drop member variables
        self._dragging = False
        self._action_pos = wx.Point(-1, -1)
        self._action_item = None

    def OnRightDown(self, event):
        cli_rect = wx.Rect(wx.Point(0, 0), self.GetClientSize())

        if self._gripper_sizer_item:
            gripper_rect = self._gripper_sizer_item.GetRect()
            if gripper_rect.Contains(event.GetPosition()):
                return

        if self.GetOverflowVisible():

            dropdown_size = self._art.GetElementSize(AUI_TBART_OVERFLOW_SIZE)
            if (
                dropdown_size > 0 and
                event.GetX() > cli_rect.width - dropdown_size and
                0 <= event.GetY() < cli_rect.height and
                self._art
            ):
                return

        self._action_pos = wx.Point(*event.GetPosition())
        self._action_item = self.FindToolForPosition(*event.GetPosition())

        if self._action_item:
            if self._action_item.state & AUI_BUTTON_STATE_DISABLED:

                self._action_pos = wx.Point(-1, -1)
                self._action_item = None
                return

    def OnRightUp(self, event):
        hit_item = self.FindToolForPosition(*event.GetPosition())

        if self._action_item and hit_item == self._action_item:

            e = AuiToolBarEvent(wxEVT_COMMAND_AUITOOLBAR_RIGHT_CLICK, self._action_item.id)
            e.SetEventObject(self)
            e.SetToolId(self._action_item.id)
            e.SetClickPoint(self._action_pos)
            self.ProcessEvent(e)
            self.DoIdleUpdate()

        else:

            # right-clicked on the invalid area of the toolbar
            e = AuiToolBarEvent(wxEVT_COMMAND_AUITOOLBAR_RIGHT_CLICK, -1)
            e.SetEventObject(self)
            e.SetToolId(-1)
            e.SetClickPoint(self._action_pos)
            self.ProcessEvent(e)
            self.DoIdleUpdate()

        # reset member variables
        self._action_pos = wx.Point(-1, -1)
        self._action_item = None

    def OnMiddleDown(self, event):
        cli_rect = wx.Rect(wx.Point(0, 0), self.GetClientSize())

        if self._gripper_sizer_item:

            gripper_rect = self._gripper_sizer_item.GetRect()
            if gripper_rect.Contains(event.GetPosition()):
                return

        if self.GetOverflowVisible():

            dropdown_size = self._art.GetElementSize(AUI_TBART_OVERFLOW_SIZE)
            if (
                dropdown_size > 0 and
                event.GetX() > cli_rect.width - dropdown_size and
                0 <= event.GetY() < cli_rect.height and
                self._art
            ):
                return

        self._action_pos = wx.Point(*event.GetPosition())
        self._action_item = self.FindToolForPosition(*event.GetPosition())

        if self._action_item:
            if self._action_item.state & AUI_BUTTON_STATE_DISABLED:

                self._action_pos = wx.Point(-1, -1)
                self._action_item = None
                return

    def OnMiddleUp(self, event):
        hit_item = self.FindToolForPosition(*event.GetPosition())

        if self._action_item and hit_item == self._action_item:
            if hit_item.kind == ITEM_NORMAL:

                e = AuiToolBarEvent(wxEVT_COMMAND_AUITOOLBAR_MIDDLE_CLICK, self._action_item.id)
                e.SetEventObject(self)
                e.SetToolId(self._action_item.id)
                e.SetClickPoint(self._action_pos)
                self.ProcessEvent(e)
                self.DoIdleUpdate()

        # reset member variables
        self._action_pos = wx.Point(-1, -1)
        self._action_item = None

    def OnMotion(self, event):
        # start a drag event
        if not self._dragging and self._action_item is not None and self._action_pos != wx.Point(-1, -1) and \
           abs(event.GetX() - self._action_pos.x) + abs(event.GetY() - self._action_pos.y) > 5:

            self.SetToolTip("")
            self._dragging = True

            e = AuiToolBarEvent(wxEVT_COMMAND_AUITOOLBAR_BEGIN_DRAG, self.GetId())
            e.SetEventObject(self)
            e.SetToolId(self._action_item.id)
            self.ProcessEvent(e)
            self.DoIdleUpdate()
            return

        hit_item = self.FindToolForPosition(*event.GetPosition())

        if hit_item:
            if not hit_item.state & AUI_BUTTON_STATE_DISABLED:
                self.SetHoverItem(hit_item)
            else:
                self.SetHoverItem(None)

        else:
            # no hit item, remove any hit item
            self.SetHoverItem(hit_item)

        # figure out tooltips
        packing_hit_item = self.FindToolForPositionWithPacking(*event.GetPosition())

        if packing_hit_item:

            if packing_hit_item != self._tip_item:
                self._tip_item = packing_hit_item

                if packing_hit_item.short_help != "":
                    self.StartPreviewTimer()
                    self.SetToolTip(packing_hit_item.short_help)
                else:
                    self.SetToolTip("")
                    self.StopPreviewTimer()

        else:

            self.SetToolTip("")
            self._tip_item = None
            self.StopPreviewTimer()

        # if we've pressed down an item and we're hovering
        # over it, make sure it's state is set to pressed
        if self._action_item:

            if self._action_item == hit_item:
                self.SetPressedItem(self._action_item)
            else:
                self.SetPressedItem(None)

        # figure out the dropdown button state (are we hovering or pressing it?)
        self.RefreshOverflowState()

    def OnLeaveWindow(self, event):
        self.RefreshOverflowState()
        self.SetHoverItem(None)
        self.SetPressedItem(None)

        self._tip_item = None
        self.StopPreviewTimer()

    def OnSetCursor(self, event):
        cursor = wx.NullCursor

        if self._gripper_sizer_item:

            gripper_rect = self._gripper_sizer_item.GetRect()
            if gripper_rect.Contains((event.GetX(), event.GetY())):
                cursor = wx.Cursor(wx.CURSOR_SIZING)

        event.SetCursor(cursor)

    def OnCustomRender(self, dc, item, rect):
        pass

    def IsPaneMinimized(self):
        manager = self.GetAuiManager()
        if not manager:
            return False

        if manager.GetAGWFlags() & AUI_MGR_PREVIEW_MINIMIZED_PANES == 0:
            # No previews here
            return False

        self_name = manager.GetPane(self).name

        if not self_name.endswith("_min"):
            # Wrong tool name
            return False

        return self_name[0:-4]

    def StartPreviewTimer(self):
        self_name = self.IsPaneMinimized()
        if not self_name:
            return

        manager = self.GetAuiManager()
        manager.StartPreviewTimer(self)

    def StopPreviewTimer(self):
        self_name = self.IsPaneMinimized()
        if not self_name:
            return

        manager = self.GetAuiManager()
        manager.StopPreviewTimer()




from wx.lib.embeddedimage import PyEmbeddedImage

UpButton = PyEmbeddedImage(
    b'iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAAHaX54IAAAAAXNSR0IArs4c6QAAAARnQU1BAA'
    b'Cxjwv8YQUAAAAJcEhZcwAADsIAAA7CARUoSoAAAEdSSURBVHhe7Z3ZsqZleffbTAY1SWPMtIEB'
    b'N7ITaRrBAUfIBhthQ6zKRjZS9cERBI7AeASSI4AcwYe72WBUUFDppGKlKKuAz7YSQ4h2TKKZ+e'
    b'7fw/tb/te17vsZ3rVWD9C/qqvvebqG53neod915nLwrl06yyuvvPLmL/7iL+5Kb/Ff//Vfk/z3'
    b'f//3md///d+fnWe28eLFi2/+yq/8yq50ZpoQgZ/85CdT6kLIbbfd1p2vW8nO3//+959597vffe'
    b'Z//ud/zvz7v//7mZ/+9KcHu0/+93//d1qAfrsNXLjzzjtvnxp3HFmE3d94441nfv7nf/7Mf/zH'
    b'f5z5l3/5lzM//vGPp4WYhEnhXe961xlUSPpzP/dz0yL/+Z//ObVR/vjHP34w96FFOMFv/uZvTg'
    b'v827/925l/+qd/mhZgMJMkv/ALvzClTEh/FmMTbGy3gcfuuuuuB6c+U88dv/qrv3qwwD/+4z9O'
    b'i6AmBr/55pu7Xm9NnGU2gFDPAjv1PrBr/tkiqOmXf/mXp50w+Y9+9KNJ/zlZwmSImNcL0cDTTz'
    b'89DT5Y5IYbbphSbVANDC7ohKaeQNWhSk7PRqd2/sEWNHBMFuA0SzApoj1ywV/6pV86WOiJJ554'
    b'c1rEI6J/pBo5SfUxMWUXcDGdQtc/UBeroiIWyEEVdpriScwj5Nm4cx5ZJOPANPNMYGreie2LuA'
    b'hysEg1NAMzRQUKEyDuHJg4HUOtwLSIC3AKBzKACd0VO6XeFKEtT6QwT276YBHEAU6UkzgxC1LP'
    b'JqjPyRFARf/6r/86zclGp0XSHnTMwWA5yXL2Yw68iqsGtE09NS3C/UAjsdvULQN7efsIdSxAjP'
    b'3whz+cNv2+973vzH333XfPW6MansaFckLFusTFtMMbb7xx5gc/+MGUP3v27NR2MIobDh1ZhFSd'
    b'J9R7CoUyXsSkXPP+/u//fsr/xm/8xpn7779/0uOhWdqgCwxEp1zeWVA8iRMjbor+7P573/vedO'
    b'3jbvonf/InB0Y7tMhHP/rR25mICbgcMABxUYUyuse46L9dwc98//vfP1jgd37ndx7bTTlx2GV2'
    b'PP/8849yP2Ahjg4GIFCHsBiuSgoY+oEHHjgyZ3cReeaZZ95kdyzmRDVlYZ4FMLI2qMwuItx8DK'
    b'60E4H2nve856l77733nl3VlWPxJO2G9lJTyfldcUI7YfyWf/DcuXOHDF0ZLsLdsqniDPd9UE2k'
    b'LkK6Wwh3vnT+/Pkbp4ZCd5Hm89NDBTo3DvKJMXFRApIYag92R+Y8UsECv/ZrvzYNwtj//M//PC'
    b'2SwWkwsgkuQUC7d9VPfOITh+Y9VGjXnTff+973Tp150iDQOAGTs0thYiYzcL2oojrGUv70pz99'
    b'MPdBxPvc5QKvv/76wdMjl4+EicFrHGNImZw8G3v22WcPdnWwiE/vLMDTI5eMnNyTsIB5L6Auyi'
    b'IINiKAZerFKdAvuscGdHCiHkzqxKoMIc8zF3AanrmmPvzD0yN6Rz0swJFH5OJOrgALcalhw57m'
    b'QF26YjVyQn2d2MmBPItwLYODRV5++eU3mRhh9Zyoh3YgRf9OjGQemK+p7O6Dk3AKFqincDFSJy'
    b'V1Uie2jlR2m39yWqRGMbgjJjHoEPRNmdQ6+oApqB34ORcwdVJSJiDPYrkQ4ibciALadsc9P/fh'
    b'D3/4XVS6CBMAg8WJSGl3MlPbwfs+0c/G2r3mrecuKsAT5OBcAAHbgXw6C5slFIgT5oNplPpjF+'
    b'4UyQUSJxXy1BFfXCkuXbo02Yx7Pkyjb7311kllXKfonJOaJ0X0Pi85llmAqzbXPJ4LWODIcxeD'
    b'1KcLudvcNdDu7oExqIdnLx7uOIVPj3CwyEc+8pFpJo3GydwtOCGTuwDtnJ7r3d/93d9Ni8AHPv'
    b'CBQ08uh7fYeO65594kUlkMuEQYE3kiFmEzqIarNldv+rHAH//xHx+a98gi8NWvfvVNjo8AgzPl'
    b'lFyXsAEL0Y/ngV//9V8/80d/9EdH5uwuAm2hR9vgB5jAkykY2bhiYW7X7X50Y3uZcGmqLAwXSf'
    b'7yL//yTSZFVKMxMHpqTFYtspV2ZX+yJXe/VfoZOApaaPZ8pIXNw7vqE+FYB+H5D5PoD2owUbua'
    b'EMybGp6kozf/ltg0qG38y23TD/FE4KZN3TBpb/PQOwxwgLDWJOTvuOOO1ftb1ZHnJTbvk7c3HB'
    b'YzgNiYkUuZNjY3wgujlxAPkweynj75hmaP2cY8gJsH7hdcUtg8l5S8mKZW8zoHlk3zMOSBcR4I'
    b'hXgQ1qdPfZCXbiUu1K51D3HPqdr3mkjKAVhIVxA3mrhZ27KPeQ8DHgYF5dy48mc/+9kjCxypII'
    b'B5Zzit4B2DA2AND4DMkZvOTZrPwwDlrGN+DsF6ui/gJe2R/rH26md6WxsOzeSrUB8vGIzwbMOj'
    b'BxP1Xg2NyE2xeUSXy4OBh3CM/bQK6+rOXinbgR77zGc+c/g9+naIl+pLaVzJt9LRipZYgxsCNk'
    b'2ZzZkX8taZ1jrcCe/wMs+BuLC09OjnAK3T+byUcghfVWtWNrKW7NuzQt1stoltHoL9kbo/DsMT'
    b'AX2n0bs78QSd3Dip/glMvBb7eiBTN43Qx345N3nbwcOoaPAw7BOmnrxYxK00HY07002dCbi8cv'
    b'RIC+Sm2IAbgzyEkGe8F5cK7qxSiVcuPOwLeNBue3/rhY94uiQ3CLkB2tyUm7VMysZMU/R5xT7g'
    b'XJl3XuFQKY23XlV7ZQDTGtRMmIsibIiybdalWI+1eReE1I25ydws+Z5AKhUPYf4dj00HaZWPkH'
    b'IIRVwAkboAG81NkPcACAvaN8c5JucW69g8ovZ1d9hZg9fUD06924v3h/G/PIiLsAk3ZuriKblx'
    b'+4L9wTogT73iPJbBlA2zJw7BTdkg1+pwMHNreJABuJTBlRtz0sQNmK99cuNQ3bWC5nMeyt7ZCX'
    b'LuZxyEQ+Ci3ZftvCntybmLkmo6J/dAKdmOpFY9SPo26C4pwBjgwByAfXCF4qmCF9Q+XXCF5WVp'
    b'e5S6ZRrQOKzCxoULF/ig+SwTMaGLVNxskmUOLb2+eUja8lAoECugfSzB04UvETxEfW195CDyzW'
    b'9+800144FS27k5N9Wrk1oG+zq/B+DBlANwEF0JeKOa+8amdx/ghRdemA7DRB5KCDK0zgbrAcH6'
    b'Odg485ISwGyelM3jUhJWeLBZofu5zOxB5Otf//qbHEKNqSHxicDDQR4qUSHMxTxeThXnZk4eYA'
    b'nouQPIqoMkfDjBYm7EfI+sN0+KcBg3Taoy3DzpmreBZPNBknaoR9smHmBjeSgFTIWy137vA0o7'
    b'zC1N869NjRs51kHm4FOFlnyxbTzf38I9/oJ3t98qXucIJ26R9pLgoZZ8+a3SYXZXqEvvfe97v/'
    b'ChD33oRK1y7IO0S+XZ119//UcG6wgDG8hzKCBm+NRhKhyDvSdor/H/b9v8/eQ5hAGcGOj1EJl6'
    b'OSZtcs/58+f3stTmg7QDPNQ2zlunB1ebigeYOwiQT8twd6fcDrN5X5sG8M4jB/CdljxEbr53AO'
    b'iV8yDkPQzS+x7CiFUdiYP2CP0j37xGuIP7yMIdOTfvhuvGKx6CeZA8hKw9zGKn5kqPtmedB7CC'
    b'BwAWVvs8ZngANmHbHPko4wF8cPQgpLQvvYENsx16h0greACev9iAB1HYmLAhHiKpZy6fwzwQ0K'
    b'Z1yNNH2fvd+DfeeINHj0c5hF82ADbNIXh9wMZ1KzWpdt2ouCHaORAph6DOp2TqHI8wJ/gkfddd'
    b'dw33O2zwy0IeQnfxELxm8JWkGmQTc2AJ8WDAJrPsfMztnB7mU5/6VHfP3cre5yJYgtcITE7q47'
    b'wazEO4oYS6jAsxT2reOVEcawjjkfwOkhx55dPi4uASWw+BJUixCtZYawlgLvuR1jHWIR4KCwiH'
    b'Yh+s+9xzzx35oPXIQeoh2KzuRHAjTOYB6oag1rsh69yoFpCsI2UP7EfLILv8wXvVcuggupS+nI'
    b'FNijDR6ABJ3SQHr3VJbaOMoAT342FQ7jPPPHPoMEcs4iA6AxbgQAh1yNIhIPtwiHQTyI27abCf'
    b'h0D0DuAg7Kkp9JB7HcxubAiaT5fiAGxoH9xkbliyjhQFsHnrPEzuzcM8/fTT00MrHByEjnl55C'
    b'AcgnjIwF5LbpiNjMbmIRSxzHj2ZrwgOxf7v7uuh13Lg5TOB5KLLFFdKzdpPmUEbbhWuhd7A6wi'
    b'00H4oKe6FYcwdVNrYqNHuorkATIv1iE998LtobnXzaTTQbIDeAAPs+8BeuN6m6702jkI4DXsyT'
    b'02T3l1ap9ad2SHXaeDzazZQNLrb531NYVeHy2SMQzsVQ4dBGzErzkI5EKQC41QAWwg+5t3cwiY'
    b'tw0yNhwvKt39HjmIeAhIF8kJ3VRdxHK2p9iWqQfxEKZgn8RD4Dlw6CCezkbgEL2JYHRAyE0B7Z'
    b'RJ0TKpY/KKlPXmaz/3mUwr5cYz38NJxc1S7+bNg+6R9VUqqTzyvT6Vgx71AKltyY0AqQuCbdZn'
    b'mcMQrKS0pUjmK7Th7rqUeTl01HqYXMwNSWp5TuM53jwCprVvFegpNq9iQ4sIC4CTanYXgNyIZf'
    b'KmHBRyXPZZA+tqDTliEZ+DOMxcjNRDmCajjfb6jnCMVsCN2CN7063IH7FIXmqBTm4ixTpSN0bZ'
    b'NCXb7Y+wuawDUurMewDz3tM8SFH2Bf6ZRrfOr9GoAJP0AhOx3cXrZhXrk17ZujxM1hvYCK+LwK'
    b'f1++67b/rv7tPIW2+99Rbda19c1BTcWEWNJ1nnHNRxCIQnXR4UVTRK7gY7nTmMwiRM2NOq2C69'
    b'fm6QNDfbwzXtq0thBQ6QB+EQ3YO0Qa95GFIXZWI3mOmo3nTUBpmXHOPauBIv6rAGH1n76A4cIj'
    b'8sPTjIuXPnJvfiEB7ICdG6InUzlnND4BymQD4lsY71fXXKQXhDEGsQG37qm/xsZw03jxhc1IGb'
    b'y8MA9bUuyQOCG8/Digcg9R0cvwHBy24wyG+44YZD/zX10A74gMWFnFSxHtw4aW4o83OHSxjD3K'
    b'5HihU4hC6FAIfgLVws0q5Whz7ZOrJac6tHnLAeRIHcwIjsU/uat964xAs4BJvnXU1dCjgILtX7'
    b'IsGRg9xxxx0Ps3Ehz+RMZuz0DiZpFduoUyDHOB9zcwA2zgEQvq6rS/F9FP7/ajvIdAOsHDmZvP'
    b'jii9P3TxQWZyO4jGLZDeZmda1skzwIea2ASxkTHCjjgm8FYY3eN4OgWynf+MY3pv9zyUFIhZuR'
    b'T7x5IPAwWddDKyAcAAtgdQ7hF8zAqxQyOgTMHgSef/756TBMnIcBrh4eyo3nQUZ4AISrE5o3Lk'
    b'i3HgIWDwIcxoN4KGEx8C7LoWBkDechRdg44t3buYkJr1BLh4BVBwH+Yx+L1AWFA1HnwUzFMSoD'
    b'4QBYJedjHLGAcIi1X3VafRD46le/+mpb+OY8DBsS8lgmUyGvsHmoB0C0Aje8eq+YY9NBhF+fcF'
    b'P4NylYV/Pg5sHNA5vHHbUCCtjyhTPZ6yDif473zWQtlCLmjaVMOQAHahbYez/HOog8/fTTDzWN'
    b'f5nNprtAHkY8xM6dbrn33nv3+tZcciIH6dGs9WftEJ9rWT9Zwt+fbpv+s7eK13lbc2qedRxefv'
    b'nlR1vyACG0lryKZ4jyJJT4jNoe8V5r8vBtt932+K7pquCKGuSVV14h7L9Ivip/izEgjVCpbbXM'
    b'dZVn8J28duONN95+0003df9r/mlzWQ3SDMBnyferbFNvKpB5yLtovSH1blA9w4yMZb1RtIucI9'
    b'K45fz588e+0a3hVA3SDnP21VdfPfg+MCmKrQZAsT2FJ9mWeZTq/GuNUevyshaXtKkcRrH+Ed4K'
    b'mCpOgVMxyMWLF6f/2aQBoKY9VPSc8qWn6GSpXaoxUH41CPTqGg/eeeeds/+lZSsnZhC+xtke5L'
    b'kZT/9lHlB+GsAXwOKrE5SugMqsSrWsElWSCvIdglpORu8i5DypfGCf2V5p9Zc+9rGPdX9XbivH'
    b'NghfCm6RMD0RaQCkKl84nIrnxTqgaEXoUxWhotIQc2/T0OZY8rwTUvfl+OwL5llLcU3JuYH5m2'
    b'GOpdO9B2sI8n7/cWSINAJpviRGOCx9NABpKiCFeg5OfgQKUrKfe6POdvB9uIpj3UvdE5DmW17O'
    b'M/cl6zk2D/rX3X9YWBMRGkLJSOBwNa2HBlMwn8ocsdSnKjGFdXKs+0nRgSD7ktfATS41w2y6lG'
    b'0ySIsKDDHdrH3nqRpCI0BGA+96qXwN5MHyoJB5yUOvgX2NxuyUtSv9jKzPdvLsJ52FvHvXMKJO'
    b'GIdxmtz+yU9+svshSGXVKduiZ7///e8vRoXGUDCCBjClD+LhoKY9UkFzqATzSZZZy3Jv7t5Y95'
    b'eG8UxAHtBNgp6avPbpT3/64D/djzi6k0KLiiP/s60ao2cIIDoo8+ENhyDPITxQVdAcPaX12Hnk'
    b'lHfO0Vjq59qSLLN/YH4drBoFcEL1tjNK97+JJLONvLJuE06vrNcYAwOwiTSEm82IgCUDLNFTWA'
    b'rzI1mX1HKlN0bcO6nn4rzqAh1UfCmA7j73uc8NFx82pDG4X4DGSG9QiAo+8sEIiJtkwxkRHmZf'
    b'RkqyPtPaN8u1LaljyY/27fl0OnQAGCUNgx5N0eMf/MEfdDfQ/YiyGePPNAaDwbQag2jwXoEhSP'
    b'UUDqEx4LjGAObozZP1XLJUYu1blS3W1/Za3xPWw1FJ1VNFAyHoxj86UjmyMx5r+f/ofBzM5NUg'
    b'wIR+/o3gFUYHUKfnnBYoIlExku2jvFBX60f9Eg2OeF50o0PiqKQJesTRR5FyJEJGPw7AxIrG8D'
    b'KFaHlSNlQ986ToKQ+yTiVBr29iNCWuUaVS2+tceYXRMOpIfT3xxBP8ksQBhwzCB0NaDzIqJCdM'
    b'j0hPWauMfUhlJ3oooJglRWefKlugv3MhRoBpgq4Uddg49LMehwzSJjj4tcaRMXKyFA2hskaKOy'
    b'1QBtfxNQrNPu5RYyhz9Pr26nqgP64w6pG03U+mN2XhwCC7H2E5AgNMnQT0SKLD/OU0gmu5Hql7'
    b'qKxV1hJz43N+nQOMFlCXkPpsOjz6s6WNI7+I4wQ5GLQskgqB3Bhy0tT5XYMURViGrKtCvULZ/j'
    b'3Jfj3JubLf6Cpjqk6tgyM3dclODlQoe9/AK8FNjLB9qd8SrKkACvCRE3rzU05FjURG9SpcLCO5'
    b'J8Zkvwr6S/0CXzciHY/aUQdiEBc2hdxQUg8l1lcZUfupiBzTa89+KUltq2MVqWVIp4CeLiCNYX'
    b'7n5Hz367BBaMjUgZZ7pCHqQedYMmAVIa9CrM9+2V77cAlBcVWyP1LJuZ0PRnXC3D5pqfwZpi/i'
    b'HV29wSQYQdkXNuchextHVEptSwVVsW+OT7GP82gIxyhSy9DrpxP16iH3BlzW0V81BPUjAx0xSB'
    b'ohn6OtzyeZXLwH7SoxlWS9SpJsz349qYrP/hggoyHbk1o36idzbcmoDwbAGOAeg+kr2QcGSWtp'
    b'kJqmgYTFUzEqi8XI5yMxpJLAcdYjjFNy3ixnXZWc9yRFem0IcE7PjE7RXS8aOnVP88+BQdpEB9'
    b'/U23LJQgG5odwYYlsqC3IMWF6qdx7Feg2Z5DhEar2yRO3nGc2n8xkJoOKzDjJC/PL2wQne8573'
    b'fIGBc0ao9XmYJZG15SrZpiHAS5PUdpWGOH6E7aN+tb6WNYj3CPTlN2tGb8uXy9bPDMLPoDIZ1E'
    b'FZ1jMzrwJSZG19lTpvlqXmLaN8sG5JKr0+iIZNrMMIGgRRZxgmv+4EXIHSEK188CdfDsV4m/gL'
    b'GgXSEGJ7XiLcZO8QihynvpazLsm2pCpT7F/H1Tmqk9iOTowKxHe/MQRCW9UjBvF/+LTL1cG3Hw'
    b'8Z5Ny5c487qZaWWs5N1Y1uoY7pzZHlNH51CKHMXkcGWIJxivtBsh5xDVKUjiwZAwPgzBgEaeVD'
    b'X3w4ZBDgx45dgFSBrGcjoDE0iPUeQiwrOSZFsl3IZ537qn0UGO1njjoHMI+SZZwXhfPhnJ+e+l'
    b'OVGgdM0xiNx+t/H+vu8OLFi9OX4XJD5HsbAg1EqpLEPuKcOXdC/Zo2DJP0xszNlSz18ax5FvIq'
    b'3MjAGEaGbRqCyOASpfClh95/Rhzu5Nvf/vbd7dBPutncTEaIWK4pkLc8UpJ1tW1UXw0C9Kn9kr'
    b'k26LW79zwDUeGliMigrDHqf+8GjIHwf3M1yOi/ts7usBnl5nbw6Rf1RGPkBpNeHVjvoWta6dVT'
    b'NzKEjOYD2rK97inxfAp4ucYAGMIo4FKFIagfGYOfcPBGPvf/jMe7D5phDrS8ZJA5hYDta/tJlj'
    b'WKdbmP3rzU9eoh56hnyryRgLIxjN9BMyIQqMYwIpBmkAvNGNPvMY3o77LDt771rWl3ufG8dJHm'
    b'oasCLI8UUz1/1L8XIULf0fzSa88zmOdsKRpEQ2iEeq8Ao4IbuMZY+xMC87svvPjii3zUOH3+y8'
    b'Y1iKmHgfRilWCeftXLTWVU3zNI9qn9E/dHH/u5b0TlEwFenjAEYAgEI2CYniHAqPDyhGz5KYTV'
    b'HZMXXnhh+i9reQjEg3GYfDsDUADKzDQVk6l55qp5pBrFPj2yjTkyhdw7KcpW4eB3q9YYAvHGvX'
    b'u0vb0ZY9W33mV8khXwd7g4iN7kwSgLhwA2KBorDWQZVLz5XgqZl1Q2uFbuD8my+VS2htEQpLDG'
    b'EO3y9Fi7PB28HbKFoyfaA/6eGKkHM+RBg+RBOABlUtBYKg9Fp0ivbg2pdPcH7E0DWEbxiH2IkI'
    b'pG8B6xi4ZjGUJOxCDy/PPP/6gd/qwH1xgeXNIYlV59RpfUS2Iy5wypfCXLc5FgmoYgbXW3N0Ns'
    b'ujSNOFGDSDPM+WaQl1AM3knKYXuKAdpUeub3hTnEfKaIRgP3kntKxyDPJYl9hSw+wu7DqRgk4c'
    b'9/NOM8iQJGnsvTS2J7pdaP+kkqnrVQbCq9hxGgUxABpq3tQouEEzdCcuoGqTz77LNPNqVM37BA'
    b'YSooFaWiawqZh1qGNALo7ZTNSypf7wcN0fpv+gmy43LZDVLhj4I0BU5/T0PlrjGS9AwyhwqHNA'
    b'Q05T/elP+FqXCFuOIGGbH78xpfbMY6+N5rVX4abA276ODm++f5odB1rnOd61xnL67ae4hcvHjx'
    b'7vZq+fMty73k7FS5AC9KTXf5p9qr+698+MMffmRquIq56gzy8ssv86fY+KGC6W9mbaXe6DUOaC'
    b'BerDZ57LbbbjvW2xynwVVhkFdeeeXgbX2orxW2MHrysr4aaPc+14UPfvCD95w9e/aK/M5icsUM'
    b'8oMf/OBsuxS91LI3VwPsY5AlQ0CvD0bxheTOWF86d+7cFftN3stukBYNvEqf/m4niu8pP1+8jR'
    b'i9IKxK7xmh1mEIBXaXtMfbJe2yv0i8bAZphuCe8GoagHzvlXOC4qlf8wpdRTOv+Z5BxDYNYaTs'
    b'DGL94+fPn79shrksBmnGmH5na1c8ZIilaBhFwpxBEuqqgSibBw1CqjEU2Bnn4Y985COn/pR2qg'
    b'ZphuBpafrv1nNGqOVU9pxBegaQLW1pEPPVIEAENaPc2B6hT+3mf2oGacaY/kxtNQSCMqsRpBrA'
    b'ctb3lE2dng8jg4yMARokDWEeMMiu/Midd955Kr/de+IGaYbgF0qnR1iNkQYZkQrv5VORI2X3sC'
    b'97WTIGyrauGsP2qLvUjHIiPw2bnKhBmjFeagc/T94f7Epj5Meu3kChRsGSEbYYZEQaAyin0tMY'
    b'ERlHuPnmm2/8wAc+cGKXsBMzSP016xoV9TNwDYLye4YYGUBFVo/1iw+U574EMWpzrhRIQ/Wgvh'
    b'nkwQ996EMn8nb+iRik3i/SIGsNodJrmgpB5pSzBMYYfafL+Z071zKlr+3UgeNb+tjHPvaxY78V'
    b'c2yDtMiYdsglKqOiGgIwRhpBQ1QjUM+BU/lVOSqoR9bbr34HTOoc9s+1vGQhYt7xu3mPbZRjGS'
    b'Qjw8+g54wBfs3GLzakQVAA/VRAKkKx3wgUpAB9UZYGSShXAyWur2FMcx7zUffYxz/+8b2NcniH'
    b'G6iRsfYSlVGBaARSxbIGIFUhVakV2hVQgSrecu1nmuS6mSK2V4Pu5nnsrrvu2sso86cbQGTkbz'
    b'KOogJQ7pwxTFM8dBXoKS6pCmYcecQ5Mlpss5zkuqTuLVNgrIZxrt/6rd/a60Y/f7oOPk1lZMzd'
    b'L5YMQVse0LyYNx0przLXL9vM176Wc/26TwRyrMZGfu/3fm/zI/H4AtqhRQYv+KZHW9lqDMscxj'
    b'L98zKVh7YsVSE9yf6Vqvi6VqX278E4xXmQ7373uzjvJpZX29GMcb4Zghd+s5eqkTH4ZrnKN01F'
    b'KGAqa5SS0D8vS4l1o7baTure3KspZwBTQSeM2+3h0qc+9anVr+hXRwjGIN3HGEoaA/Fg4sH3BS'
    b'WEIna1b2Gb9NayLiUdxjmcJ+dLOJtjm5z92te+duTnE0esMkiLjulzjLn7xsgYRAaPuvxPJCSN'
    b'42F3G9/NdDxGkbEWlZ/So66TZ0fUx+5sD7V5Vn1BY9EgzRh3N2McfOEAY1RGxkDcnH1IYc2ht5'
    b'LeW+fNtbJ+DfR37pSk6oWzAudl/HPPPbfqfrJokGaMJ/O+ARkdKtgNaAgiAzEqaDcSkK1KuZrQ'
    b'GHPR6JmBs3Lmdunq/hRvMmuQ3VPVIiysaBCFOr1EI2Rqfg77jfqjlFRO7Uv9SObo9TNvyrrCeW'
    b'vq+XeOuHgvWYqQI399LWGhNAT//YvU/6vnZmJDu5HXNmkMpN5PK2mUZ599dvqm/4ihQVp0TJeq'
    b'iouzAGgQwAiIykeqV2d+K9VbK8yt0bPvljUdN7fOqD31pS4Q0ChtL3wRcMjQIG1ybubd6GBiDY'
    b'GwqNHh01RGxXGMsJa6xpJS1zKahzovk0ZJvYKIhlFfzzzzzDBKugbJe0fvMiUaA4GdBxwRMD0O'
    b'OV+S9Spp1HdOwSm1TrIuZS3orO1rGCWjCDm4d0DP8lpbgyAYJCMDekq5FqmKN0/qvQSqrlI/CK'
    b'Cjp59+uvvtyCMGadFx8Oe1R1RjoPyd5Q8kjXLaqKyqsF59ZdTPvOfp9atlQX89HaZRGtPfka/0'
    b'ImS6vmHpNZEBpNTlJQtjkF4u9FDXv9x4H6moL0TU1RtvvHHk1fvoktWlTq4hXEA5rcjoeWMlDb'
    b'LU1/myX9al9Fhqr6AnHZn8d77znek7zskhg/BHXUbhphHASUEDpFwJD73SEB1GSe/KUkF/TXfT'
    b'V6aSQwZphjh4JZmTagzSNEwqX89c6537kPMn1LkX1kUxdX09eUm2kuN660rqEHD61KUcuWT1og'
    b'McbHQgKoEURgq7nKxV7Jo+a3FNDGKUpB6rMdQf5N+fggODtMvVof9C1rNeghG8Z1RDXG7DqIwl'
    b'Jau4Xr9s67VL7ZfSo16+0CuiQZr+Dv4fPmSEdB/DEidCvHdokCtJVcqV2g/r4xhilGiU6uQaJU'
    b'mDTC8GoWfVCofWKEbE5VJEXa+Wk2qsfVkzh8aY62eEjEiDHCEHk6ZFUwk9RVxuruQe0lheOpec'
    b'Wn2StvvIweckswbpwSRERY0MFeLm3OBJknPX+bOu5jOV7AO1LNZXSbKu117BCGmgdqXh/+FPHB'
    b'hk9HQFWlM0yJVmSQnZbjoS6bUhlV4fJCO1p9M0ROSnn6uCySDtCeugAnJQolE0iEbJDfXI9rl+'
    b'S/SisT5d1fxakVE96+QN2zKSe7Ku9zZKoo7T0cEVDhkkqca5WqJDquJ6LLWfBKyhUUaoy5HDgw'
    b'b5XLVUYhtpzxh6SN3QnLJsSxlR+9QyZF1PZKmcnp8itQzOYb166Om0Z4ysOzRzncCOXgtJl7zg'
    b'tPHwqcRK9rFf5nsstc9RDSFz92XoGUeDTB/XgkbJztQpSUbFlgPluGRpDttH/Wp79tGzl9oro/'
    b'6juh7qsqY9DnaAspcsCqNFT5I8bF0v67JPT4S8Ch/JSZPrb2FxJzUqtlKVk6ioxP49sT2jsirW'
    b'fmD70hPPGoxq5sw1pK5drwA1KkZRMjRI7xK1FTdfD1Hrsw167cpSexUUlVgvtSyj+uPC201zdA'
    b'3i5at3Cetd+0d4qN7henWSY7aKkeIHRrVdavmkcM4lxY/QINMPBY8iYp9I8cB56Kzbp74nFQ2y'
    b'laV5R/VzqDcvT2uMNO28vbY49KfbgMmccHSz722ScirFay9km2OVUf1WkV4bIqPySKTXhkiedw'
    b'3V2TXI/yPdGgm9jaVAbq62SdanSK3LcopOMId9pZaPg8bIF89rHnWT6QRtkoO/g7uF3mF6h7Nf'
    b'ttV8r09i/ahfNUb2y761XjkOOl2mIwMsOf10ig9/+MMHPzbvANKUSh6idzA312vbQo7Nuaoklm'
    b'v9cajrcD4FcOgsA3rDMAj3D8r18r8rH/xP3QO3ygjpGWCJNYdf6jNq95AqxX7mjY7afpIszasx'
    b'0iAb6P9x4jmqkfLwbrTWKUnWzbXPiZDvXaoklVTHVmxf6ie1X65lNBgdeflSj3yi6KeKN95441'
    b'emTCMj5AJRshQduQk3ZV3mIduzXnptWdeTHr22XrknlVpvWWX3yMsVeQ2gMTTQiI9+9KMHt4wD'
    b'g7TJ/nyXPUJO5qNpXib2oY7LMnkly0ktSyrNcaO+c6wdpyEUL/0jA3DPqJ+3JwcGOXfu3MF1jM'
    b'lSKm60bthDVEn2re/lM5VaXsI5FRmVU0QnMFLQmdGB9HQYl6xDrwEPXYCZUAv3sD035GZyg/uy'
    b'dg771fvHHHrwvuSZJQ2h+Go8L1dztIg59GOah07UFphejyAjvGS5OfMpx6GOp+zBTambM8ZxFM'
    b'/YNePth67MI0aEBpGMkrxk3XvvvY/vshM1Qh50kTRKLUsapypyDaOxlmvag/0mllXQvjje/VlO'
    b'yX7oJ5+uoHcz96MAjNJ7S+qQQdp95LVcrGcIyraDG55TWiXH9MbO1V8p8syifhAjYi46NEDcP4'
    b'78yNmRuG8LP87i1RCgMXoGEdpqneUqyZpyjnN/o36JdbW+R/at/T23OkDYB5GQ0ZHGQTBEGkPu'
    b'u+++Iz9wdsQgLUqmH553sZTcyJVmyw39uIzOWw2RBvG3JQWDcLkyOlr5yDvs0D2VSu8ZIqUy51'
    b'1rWBrnmmmMupfe3qzryRLZL8epeAxSjYEAdYnGQG666abuXwwdGeSWXFxPQNJASRqiJ9lnRK/N'
    b'MXPjlqh7TXpnGWHf1AdKR/zj90o1RokOrkTdn/7rGuS22257rRcZQpsbqm2puC2KnOtn25q56p'
    b'q5t+PgPJ4bHRgVpghtFQyQ0dHK9+yajjC8ELcF7+kdZs5QW1F5VYkjuFTVe8fasbBlLajn1BBp'
    b'BFKjwh/dQaRz7+C1x/Bv6w4N8pGPfGQaNKfwumGlRyohFaMktX4050nQWx9YM53PPCmG0Rhcqo'
    b'yOagyo0dG4ZWoYMDQItMUP/XhjbrAnc+TBR0q40vTOhOQlih/WwQjK3H2jEx2X2qNu9+lKZg3S'
    b'ouRS28z0tvySMZARqfx9DOEY9wEatbePFPtCrU+sz7MK5YwAxcjAGBWMwc+vZ3Q0Yyz+OumsQe'
    b'COO+449HjmxrdIZal9jpN+/dHbh2UvTSlEBcYwKrhvAHWCMbxUYZTdH8df9ferVp2uba57gwfq'
    b'9aj0rp7YvyeJZaNA5l5/2LcK2Df7S7ZlO+dIg3CpItUY5HvGkHojb9Gx6k8krb5+fPOb3+R3e8'
    b'/n5qvyRcWpkFQQ/awX25Je3Vx02LeOqdT2un+dCtEYSI0M6kirMbxUebkivf/+++c3FayO/zvv'
    b'vPP2VLrkgZRqqJ6ASl9S4hxrx9e1E+o0QEYFyu4Zg8gYGcNLlcZo5U1/JWGzJl588cW2/7cOpi'
    b'eZJ5VUFJ6dZfM1kpLsz7zma5TUsb25IPeW5DnyaYp6X1dgECOi91oDNMa73/3ug+i44YYbLrRL'
    b'VfctkhGrI0TaRqcFOLiK7lEP6mGpV2oZnC/rU5ZY6p9t7su9kRodKJ7fkcxHW41R0Rh532jCI+'
    b'4mY0Bfmwu88MIL01939lAq3nIPNouyU0aRI728aY2UtbA/9gm5ZwRle6lCMIKRYXvPIPwtFc7n'
    b'vYOfZG/G+NnmN7DXIGhGwSAPaAwPSiocBm9J2Dig2DRIFftkCr26RGUDfVgjHUax7N4RjeElSm'
    b'MgUI2RlynO6aVqy028svdA+MY3vvFoO9ADHsxDahQONEJD9SInBWq6lTRA7jWNgGgEZXS/gLxM'
    b've9975vOc1xjwLEGw9e//nV+7+lQpFSD9DxL0jCQxkgD9OqWoK/7SqO4PyIB0hhepuizZIyTjA'
    b'w59gTQIgWDHLqnkI4MkvSMIxpJthrEiEgHcS9pBPe5dK9wrxrA9KSMAScyCbRI4UXjSxwIJaRR'
    b'6uEspzGSOSNBNVSi8qWuT14DaAxFY0DdM3tCWFsj7AxyqRnjxP4m7okZRJ577rlmj7e80pTDVq'
    b'WM0Bj0WWOwpM5rmfVrqsDIEK5j6iVKY7T6x9rT1LH+kGTlxA0CX/va115qEXK+d+lCOGBVlnDY'
    b'ETluRJ0vFZ9pGgHqvGkMDAF5iWr1tzdjXJgaTpBTMQg0o9zdDPLk6H4yMohkPQqgbDqitlk2ZR'
    b'/QM6p1aQgvT8UQrzVDzH7IdBxOzSDy1a9+dYoWL1+AgkaGqSlKAMuS7aM214OeEXpkRGgEpbXd'
    b'04wx/Pj1JDh1g0CLlrNNOT/CKGDEzBmlKhmyrtcOaQRJY6DwWoa8WSNAZEDrc+L3ihGXxSDy7L'
    b'PPTpcxDQJzRslUslzboGeQOXqGMN8M8VQzxPAbIqfBZTWINMPc3AzwKvlUKkZJ7+0ZhXzPEEIb'
    b'yrSPSk6yTuWb30XMZYuIyhUxSPLEE0/w1ximP3CiEpeiRmp5iWqcNMbOEF9ohjj03wMuN1fcIP'
    b'L000/zy9qPtkvO3anoapxkrUGqIcB7R0sfvvfee1d93n05uGoMUmkG4i3+P20Gmv6CQFV+z0Bz'
    b'aIAG3zj/UjPC7NdxrhRXrUF6tMsbP9aJ/G4zEBHV+/FOH0ufbvLU3LcEr3Od61znOsfhmrqFXG'
    b'vED4ab/m6T/DMtvVtgj+k2yNuCDZ5Fpl/TauWnePMjfzvoOifL9QDZyO7vEOHYn2vCA/mRP+sV'
    b'D9gHD+fUkc+2xLZM17ALmi67Nr4qz4cET7dgeor/Z03lddZxPUA6vPLKKwQB7+V8vjnqwU9+V9'
    b'Y4dO0zmgtGc8yxZoxBZMpdhy8m7N565y70lSaPXw+eo7zjA4S/+9uS/9NkenNzzoFtW3L0Lejg'
    b'BtBa1vad65d3H/K7gJlSAqbJX9x2221X9I3WK807KkB4PGqOyF8GnP5s4JpgmKP3BvIcWz8pWB'
    b'MEJ9Gnd4dRwLtNk8eafOn8+fPvmDvN2zpA2t2B1wpfbM5+5MVwBgCOjvOOHH5Uv9XhkzVje47N'
    b'vmu9Zc+0T9Dk3QTyjgLmM23CmwMEzNv2TYK3VYC0gOAvxX+5OcqhPywLGRDQc/qlQJljS7Cs7b'
    b's1QEbQ3huX1ACBekcxL9Z7h2n9+dTvYf4f/Vs9rn2u+QDZ3SUIioN3k0bBsNXxDZg1nES/NY4s'
    b'9lnTf828+waIZB7a2Aut7uE77rjjmr67XJMBsguKR5vRDz5TyKCogZBlnX4pWOyzxvFrn6Uxaw'
    b'KgxxpH77E0rhccYH0GiswFBzDG+pbymuXBO++885oLlmsmQFpQcIcgKKY7RS8gqtMvBcEcc06+'
    b'FBA64pxT6rQy6tejjq3YvnbOkw6Q2r+085kMwXLi/4HjNLjqA6QFBkFx8JpCx0jnXwqM/H9vc9'
    b'/A7jk+c80FxJwTjtrWOu5pMQqIhD7p4IoUp5/oBRL0+u54rAXKFfni9FquygDhbtEC4cmW5UX3'
    b'kaDYEhCVXoCkw5uvQZFOvU9QpFNWB60OVP93se2+GK7tc/R+5aKun31qYJjWugrjEPZmCvQfnU'
    b'damRf193zsYx+76u4qV1WAtMCYfjbFgBgFRg0IOImgAPPV0dcESHU818Uh0imqg5w06ZDkq4Mm'
    b'tHUcdpd7izxXttV627JPnatH6fPgxz/+8SO/un6luCoCZOkxijSDYi4YkgyMXhBk3VwAZBmnQH'
    b'oOUQPEcu1nOue4c+Q45wLrTb0zzK2zZg+5RubzfIplyfq17Pb9WLujXPHHr2XtnCIERkse6N0x'
    b'MiDMrw0MMDh6wWBex58LDp2A1LxzLwVAOsYov4bq+OnUOVdt7z1eJb12xq7dX71DOq7ml8jzQC'
    b'k/1u4oVyxQDu/sMnHx4sUpMN4qvRUYNSC2BMXoTgGUs44A6AVEBoAGToEMjKxfSmGL41V0mJpC'
    b'XQOWAiPnYXz2z7nnyHXJK6NyppW65mAPj911112XPVDWaeOE4DVGCwaCY/b1xZY7BeC4vTuEqU'
    b'FQA8OAoF81agYBYl/IfqbQq4O1TjdizoFyLetH643aa/1ofNI7N6QOMg/qFEwl1+zlI33wE5/4'
    b'xGV7jbKsiROAd6Va8mQLirN5t6jpSb62qMGQZQzFHKMAGUmPrDdf+1YjHweu9sy/z1yMUcB9Wq'
    b'4pZH7ESAeZh3rRsR5Ga9Y97dJLLb2n3VFO/V2vn+3klGjB8VILikMf7vmTOmBwwFKAGBgZFEA5'
    b'6/i144TgyCBwnkzTYHP5OZba0/D74uPQlrmy79w42+Ye0ebGV51lGeYCZATrKZZNm1xoQbL5l6'
    b'm3MD7tMVl6nDpuYJgnHd0tMIh3C4zhGPLOCeY1WDVe1lc02OWAtU4zQKC2U147vuqv6m0pQNIm'
    b'kr7h2qahiwc/+clPnspj1/i0xyDvGsDPnkMGCKwNDMjgqL/yXVP+zgpoEOYxn0aCmkK2A3mMkn'
    b'U95pznOIwcY8TWffT6Z90oX1E/VXemVbCF9IKjR/pMXiyaXPjUpz514neTbZpcoAUGXyLktcZU'
    b'Hj1S7XvHsNwLDJRNO4q3XgOQKqCBBAVbzvrMr2HOefbB+UbpiK372DLfmrl7OiSteexh3ShAtH'
    b'k+cUi9uyAtaO5pgXJiX4rcpskZWnB8uSUPERS9R6pMlwKEPz8gKoi0FximGQSOUekaw3ymGrzW'
    b'78Ma59lCfZwiZX+msnXd7H+csT1qe+oVG9BO3rL5vCjqJ9oxmQsU5kaa3h5pQbLqr60tsU07Ay'
    b'5evDj9pTbyBMcoMKQGSFUOqcohHQUE41QuosIdq/LNZ9pjrm0NS86zFQPEVOo+t66b/Y8ztkev'
    b'nf0qQl57kYJ+INpxCf1Lv0JfTU7kkWubdgrtrsGXCV9tQXHkS4UZFP5C94gMEFPzBEMNEF5jpH'
    b'LpmwqviqYu0yvFVucyMKzvnYM225fml7X9emxdS9hz7pu8gaHdakBQ1uaAf9VykoHC/prwdvAt'
    b'n/70p/f+H457a6oFB/9ZieA48kgF5nPTPXBmFZNpBgWSgWBZxVZFg2nSq7ucLDmV7aO0dzbaar'
    b'851vSZY8taSe7ZvHajjHhh8xEbO9eg6JGBkj5ooLQLDUGy1w9N7KWt0YtxNqcko0cqwOlrgBgU'
    b'5qlnjAqlzjlQbA0U0RBXiq1OVJ1vzfjss7X/PtTHvX3ATuyjBoj217bpD0kt438ZJIIfxt3kns'
    b'985jObX7xv1hbB0TbD/9WYYGMGRE0hg6MGhmlVBCmCAmljHKLDU2dQWJd5qeXLzVZntP9o3FK7'
    b'zLUvje2RY/YZX6k2U/KiB5SrbyRZZ4BkoOiH+mDb+z2f/exnNwXJptPmYxWYupF8O3cOD11TAw'
    b'MxCAwO8ggGMlh6AhrR8pViX2dyXC/lTDlvLUOWa9s+jO4ao7l7eq97Nk3BvmCgZIBADZJegCTV'
    b'P3d3k1takKx+3Fp9v/zBD34wvSB/q3R4cWUJDptBoXBQvh5icGRg0G7eIEGqchGp5StF7m3Lfm'
    b'p/nEsHI91nzi24Xq47x1LfWp/95wTW+BXoOxXq9DN8qOns1b/927+d3lRaw+oAaQ7MW7lTYNTI'
    b'XAMbFDfsoRRenFHvu1S7Ax2SUaC8HdApeo6S1Prsm/VrqeOrJL36tA9kn5Gs6Sf6mX6nv/RIf7'
    b'JP5vGf119/ffLlNawKkPZoxR/m4mc7jwTH2juHaQYHuHmcvbb3AqQnbyd6DjJibb8tnMR87mvt'
    b'/mp/JV+/pp/pgz30H9C3xPrmVzfv/tjcIosB8vLLL/Mfm6YfdpZ9g8PUTXsA6hACQsm7RJVrJT'
    b'CqwdfQ6+95PbtsmXeO3ppJtq+RNfTGKbzmIYUMkhH6DyKZz0CJfvfv/q7cLLOn2f0tjFff8573'
    b'TOU1d4+sc5OZ5mZNfaSiHQcw1RlqUJhe7WjktaSTJHnebK/9esz1WTtPtq9ZcwtpU+xsHtEPuG'
    b'CCflT9x/oR+qT+m37cAvCWz33uc8MX7bN3kDbRwS+MVHrBAWxWEcseCMyjlAyAFNtsF4x00oa6'
    b'Gqjn98ye1yvr0vmzvfazbSSXm94eEM6qcBdBRj4n6XuIZB7SD1vwTf8lY8QwQNrdg8eq6VfRCZ'
    b'KMOqiL9qgbZWMK4PhcHXCEUZCkXGvss/9e/+o8a7FvHa/YltQ+tf206K2bQUIZ8L/0xzlqkKTv'
    b'ke7a726PWodeQiTDAGkb4Nu53Y2wybloHgWGeYLBPt4hegEC6Shvd6pjWN4XxzrPmrmyb0/2oT'
    b'dPlTX9Rq9HlnzR1HwNknaRnny9RzdAeGHeBh/8MLQTbsVN5YbAgPDFOKn5uYDI4Hk7Bk7PKZLT'
    b'OPPVrMc5XcDcnUTfU8R88embRy/YR3eQP82Fzc9FaoWNsIkaHGCAZJAYHAjK0HBXswG34vmqVE'
    b'b171Tybrr2Xa3EILE+2/XL5od/OmUKRwLk4sWLvO44+O+yI+Y2UduSDAQDI+usB/LvJFIHKUvo'
    b'PFVsu9z09rGGOi4DQ4HehXrpsV/SNw2OXd35CxcuTK+5kyMB8pOf/OTz3jHmbl+mSiXvGEA5A6'
    b'IGBdQyVAWlXO309pwyYtTHcrbV1yrms5xku1JZaq/U/kvSY9TPfD1nLxiqH875Z6/uhz/84ed3'
    b'2QN6j1iLH56McDMZHOSzjPMbIO900uBgOeuzvVLbRmXStdKj129OluiNmZN60ZTRBVwMIlODIo'
    b'ND39zVHfH9QwHSXpxzixl+kcsAWEsGBgHBWF9zwJq7xRZ646tcTjxfFXFPXB3rFVK27Nm5nGcf'
    b'6bHUXvE8SqW2K+qHdUwh10fWvA5J0m8zNR9+evaJJ5449JhVd3/kGawyes5zsR69gDBv+Z1KNT'
    b'5Smas3HfXZytIcuZZy0ugT+o1rnNR6c77amA2Q392lm8gFjcZMOShy0sGgwrYoro6Zk60sja/t'
    b'yojanmPmZCtL43tX+zmpLLVLrt/bx1b0S9IU65K4ixyKgbrb6bOP6uQjckGo/S337hS9YLFfyr'
    b'WMBh/JiNqeY+ZEem3KGvYZcxIYQKO1l3win270zfRP85nW9iYHn//B7CNW70VQnXSOpRdRl5tU'
    b'7uUMvjR4yhL2qeOUEb2+c1LJqz2yRG/OlEqvD7KFra9DYPTyoDD7iHWIvJMokkGS9VDLo8N7RV'
    b'BkX6Wtoa41R+5jjVR6fRAxX9u3iljGeZTq7GvkaqGeT7IuL8JrL9xb2KSN3h3BYKhBAb26k0Yl'
    b'jpQ5oo5bM7Y3Zk4cM6L2X5KK9Tr2qN+1hkHqeeoFLctbfGyfALp6LhcbUXlzUqltpDrXnINZf1'
    b'yRrMv1R5L9e1L7J73+laX2pPbt9fcurSz1h3R6yHP0xvBxQY/eSwD62t+2tcGyKUCI1ipXkqp4'
    b'ZY4tfZeoc5224DS1XOuQdyIjhx8FUjLnxzVAVv1mEI9aSpILmfft3XqFOI4hq0Moc21V6pUWqD'
    b'c9LakOvQR98vVEvq6wvbI0f7b3+tT2lDXsM2aOOo9OP+fYBEwvOOqn61D8+FAMHPISP68AF+9t'
    b'gjolYaFe/x5rb721T8oSW8f0+i9Jsk/7klTW9Hk74kW2XmiTtY9NW6iX0ad36V4QHPWuMiKNm8'
    b'YeiVdNhTowqHt3qtE4x5rfV/aZY8sY97xEb+yVlEqvz5yI9kzbpn33ofcapFzUD8XAIe23W9JT'
    b'3Ja8i6zBO8naO0clFbKGNf2rotfCmAymtQ6a1HXdS096UL923dEcbxdqQGReB8fvyKfjp/Pvwa'
    b'FHrCMa/pu/+Zs3fc6FvCNseYSyH8FG0HE4rwQZhNabNzW/heM6zD7jc0xvfK+99sv6ucCo4+s8'
    b'UnU36jdiH91vYTS/9foDjk4dQh0+he8YAP6xVv8kn2n9dXjz/jSurz8ok0foh9x7772HlNWzxl'
    b'Nsxk0mLphyGmw16IjjznMS43sitb4GR21HrgWOu2eDokriBTjvHJkK/eybDF6kH3mT6kiAtI18'
    b'hdQAqZO74GjhXl2lKrDKmj496THXZ65Nap85kVpX24W6+q5UjzqXVAdS7J/jtlDHVzkuS/P1zo'
    b'Q/cvcAfWwuOKof5sXc4PDuEUy+nxyxyq233vqImxKDYcn5aWcjtV9PEZZtq+1XI7nX3p6X2pfY'
    b'2r/Hcda/khgEiP5XBQwCfSyDgwBC9MMeJSAO0R6vHtllD+hettomH2ND3kVGsJEU6xKvjmmwLP'
    b'cERvVJr09Kj16/kWztX8XxlWyv2Jbt6SCQfapUen2qLNEbMyfut+67R/bJMdaBQUMQpK9RToGe'
    b'H/aCpQZK69P9O+vdAGmb+dIueyRIagBsAeX5KDH3SHG1wH63oIO801EPW/WRwYHge76h451Ban'
    b'D4+DXH3N2jceDzSddLb7vtttfaBh8b3UHY6JpAYbwCVWmmKkSy3xbp0eun9Oj1U3rMtWdbT7xI'
    b'WB6R7XP9RH2mTudw/pFU5tog2+ck94eP5J7Td9L58btRcKzxyXzdQcrdhbtHe7zq/j7vrLZ5y5'
    b'eD1Kv92qu/gWEKKCAPT9kDpsIyL7WOvSW9MbXPEtl/zdi5/qPx1meAzLF23h5b+u7DGp33+gB2'
    b'py/t+IIOrm/o/KTA27oZGL6tOxcgPl7xZohv8+bbvbTfd999QyXNenrb+MNuPvEAFetrey+gUA'
    b'z1pGvkNFizzly75V4boLt0Dvtx7tRJ7VexvSeXg966imdK6fXriXPjK72yjg/1zgG0I7QZHDVI'
    b'KBMc0rl7PDxVDFj0vL/+679+qR36PAcHUo1bHT+DomJbKkClqAjLqTDJ/uKepLZD7ZPMtQHtc2'
    b'vYtmaeTKveZGkeyX5r1z4OPb1Kb/7av1dG9AntjeOTxx8o84FfOj53jAyQbAfz3jXy7kFA5AeD'
    b'0NovtLvH7VNhwKL2Ll26dPZ73/vejzAqm0YhGZFLqATGQpZ7daDCss++bHGmHvuMt99SfwNlrt'
    b'+aNdeudzmYsxn17NE+BgL2RgwQA+CnP/3p5PSWa4D4iCWjAHn3u989pTVAPvGJT9z427/925em'
    b'woD+pSw4e/YsE3whD80hOJwH6wnt2UdFXA1GvM6VQ18wGPQTxQDI4EAyOOwr9EMICIMCuJATHA'
    b'aFsuv3haXggMUAgXPnzj3eDjW9DcbhDBbzPbG90qvrQSDVYLKu13YauMa+69WzcsdIEXU20leV'
    b'JPfV67tGjktvvloG8wZJBgbiH3H1TkC+pvQzIJSKgeKdogZH40vt0erxqXGBTVb/q7/6K/4azw'
    b'NrnSWVA7UsKAxSgUB5NAbm2iT3utXJ7b/vOMh8BsWINWuN5t+X486hHdIevTzOTR4xKHR64K4B'
    b'OD31VTI4ehgY4LtWBgbccMMNJI+14HhwqljBZs1cuHCBvw56P0qtik2lQC2Dzt+jti3N15s/69'
    b'zfFgfIvmvG9fqMxq0JENi6h8o+Y5Kt49G5eidlfNYBtkWoI9XZDQ4CwG/nGhC+xshv564Njrxr'
    b'KK398RYcX5g6rWQvTX77299+shl7+v2gVGYqRHR623p9RtS+c2N787u3kcGXHGGpHbLPUv+3W4'
    b'Cga4T+5q2HDAhSgoG8Uh3fwFDyXapRYICBUe8Yft6xu3M81YLjnqliA3tr0jvJW6UxKAKq8nrU'
    b'trm+PXr955xtqyOt7W+/fQKisnWP4JjR2KqnLWvk2JrPskFAnXkDBOeH0SOVdw7TpeAwQPIFOR'
    b'gg+9w5ZLv2g3YnebQ5weyfS/AWqvJqmlRD9frMsTRnnX+LY8Da/vZ7OwTIyAbU4+yMtQ9lU+qw'
    b'vWkGBilOPwoM+hsUS8EBBsJJvOaobNd+oQXJQy35cnUGlYSgRJWnMk3njHMS5PzHXWtp/Fx76q'
    b'f2Uxc91uzZPmv6Vpb2Mtob9bUNJ7fegDCP01M2MMCAMEDykSvTioFB6usNqAHS2h9uwXHkK+xb'
    b'2K7RDt/61rd4PfJkT9kqcSntUeejnP3XOET2WdN/jqXxc+3XWoBkitCv7tOLnmkGBKKD18AwIF'
    b'LW3DUyMMAPAA0KZdd+TwuOVT9jNcd2jQ5oijnb7iYvteyhX8dWweZNM6+RrJMlg9f2Xv+cu7b3'
    b'1uvNkWT7Ut/RI5bj6vqyZY0llsbTXveRZfO1j49PCuDY5GnzjmE9UoMCoV/2mSMDZPROVeO1z3'
    b'/+87e3cy1+CLiG42m/Q7ub8DeneeyaSAVmOsrPUY2dZfJz7WvozVHJ9qW+a1+DVLasscSa8VX/'
    b'PTtwR7DeO4R15nF4IE2HNxjykSrvGDAXHL3AAF97GByt/ZF215j98uFWjqf9Ad/85jf5K7lPNj'
    b'mbyk4DKIByIdt7VIejbN+eUy05Wq3r9akszZmsDZC5edbsqZL6Y/zcHFXnOdYAyLxC2btIDQwg'
    b'zYAAy6YwFxiQwdF7pNqVL7V2HqkuTBUnyHbtb+DFF1+cPnl/q3TYCArUALEM1GFg0zT2XH7Ut1'
    b'cntdxjbnzlaggQ6M1hn+ybQWAZrMPRzSO+qAYcHaFPDQjKW+4YkIHRe5wC0tZ+rHepltiu/Y28'
    b'8cYbZ1955ZVXW/bQHwdNRY8CxPIcGj+dgLySZfNivetkG9Qx9Kt9emSfNUGyZs4RvbEjvY3qa2'
    b'CYeoegXfE1A06vk5tmQCj2r31H1MCAGhxI49Idd9xxy0033XQirzVG7G+ZjbQgeaAFC3eUCY2Q'
    b'xkkBU5W8FhWr85Bm3rSXB/KsveTcOSapcyVr7yonCfpjH+haqp6zrE3UO2kGBJCnDmpgbA0KIC'
    b'AMjrxjQL7WoM8HP/jBB2+99dbujyycNH0LnyIvvPDCwWNXGigDRUPavhQgGEVl9kDh6fSklHVe'
    b'UutBJ7ZdjluWUX0P99SDeTLg1Jup6zgHaQr09K7jm+LgOnm2mTdAsNOWoIB6xxgFBrQ+p/o41W'
    b'O9pU4YAqUZZQoUjSRpNCCtQaJx1jAKHu80kE6r47m+bTVwcgzUsnNY73ynhfPr6JYzrZJ6zYDI'
    b'1GBInVveJyjgag8MOWzRK8DXv/71I3eUNHAGT8+YgGFQdE1H9AKmFyxLgbC13XNspc5f6elNqe'
    b'U1AQEGQM3D2k+8k2oPygYGkF5NgSHzmr+M1EBJ49Y7SjVyBsQaY0EvgDAM8/UCCDKIYOS4owA5'
    b'adSJehnpR6puLNunl5rPO4Ws0XXq2aAAdKxkGa6GwJCrJkCEF/P/8A//wIeN02co1QEIlnQA0I'
    b'gwMhr1GUS9ABHanGeuH2jUHjWgjks9t+T5oerAcu2XAQDmTV0v56tz91Bnqbt6t0iB1vdSe/H9'
    b'8OV68b2Wqy5AhLeHv/vd7z7ZgoIPHQ8FSn3sqobvGXGNYSUDBJaCpLK1/xbWnm3O8aFX1wsIWN'
    b'Kd+iL17DUgaors+l44d+7cPaf9du2+XLUBkjz//PMPtID4cpPps5TRI5fG1lhbDc14DFfTNfTW'
    b'01m2Mtp/ko6deRi1mc9AcJ1cb27dxPOZ5uOTaS/f4JNvvml7Vd0telwTAZI899xzX24B8pDBMR'
    b'co0DN2r6462ZWEveBMc3vKttrPsvqQkeNT3wsUMQAS6noBUVPz0Mac+HelTptrLkCkBcXZFixf'
    b'bNmHuKOAaXWM6kA6QDrCyBlH9WtgLA6S6RrW9M+2el4ZObxkey8IxLZ8TZXO714770KRPPKHf/'
    b'iHX3rXCX279nJzzQZI5Wtf+xp3lS8SON5RSHkHiTSdSOfScaoD9RxzbV2P2q+Wl4JhawD06kbY'
    b'1yBI8g6h00vWme7m4PHpS72/tXEt8rYJkKQFy80tKHjNMv2f+VEA9JyoVzfn4HOODb32pTGV3q'
    b'NSz7F7e+85flLvCkkNgGwnH3PzG1O8puj+Qvq1zNsyQCrPPPPM3S1Y/rRlp4CZewRbEzTVwUcO'
    b'v7afLLXvQ3X6pLbVAKjtGRAt/+ftLnHs/7F3tfOOCJDKyy+/fPb111/ntcv/acWbe49fshQwPa'
    b'ceOfppB8hcMMBcQECWIxi4K/zFTTfd9Mi5c+euydcRx+EdGSA9+NzlO9/5DncY7jTnj3uXgdMO'
    b'iBFzgVLbyiMY/+Hoz++4447H1/xu7TuB6wGygvaIdn97RPt8C5q72zP7oTsO4Og43sjhe8FzXJ'
    b'gT5zZdw67/ay3l0egr7RFp1e/TvpO5HiAnwIULF+7+8Y9/fL4F0e+2Ip/8I2drIMkp3Tm44nMH'
    b'QP7f+9///gt33nnn2/41wnWuc53rXOc6VyNnzvx/mypu52oakVMAAAAASUVORK5CYII=')

#----------------------------------------------------------------------
DownButton = PyEmbeddedImage(
    b'iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAAHaX54IAAAAAXNSR0IArs4c6QAAAARnQU1BAA'
    b'Cxjwv8YQUAAAAJcEhZcwAADsIAAA7CARUoSoAAAEYjSURBVHhe7Z3bsm5Vde+X5iiauCAhVBmT'
    b'sJILqlIxgqIcCgnrItc7PsGGJ9j4BG6fAPIErFzkIhcpSZUpLrjAGAuPwBLQm6QC29JUmRhAjS'
    b'ZqEnb/Db7fx3+22fs4fHPOtRawflVt9vOptd5GH+Ob3+HcleBdu3CWz33uc6//9Kc/Pfdf//Vf'
    b'U/oXf/EXz/3CL/zCuV/5lV8596u/+qvnLl68ONvPbOFf//Vfv/7aa6/tOwcGMEQY5IYbbpgdrJ'
    b'vJzL/3ve+d++EPfzh1RCfve9/7zr33ve+dZi8M/t///d9T6KqaXL7nnnvu2FWZODbI448/Pg3w'
    b'k5/8ZOr8lltuOff+97//3Hve855zv/RLv3TuXe96o8n//M//TAMQ/vznPz+HOoGBGPDjH//4vu'
    b'8jg7CCl156aZrZTTfddO4DH/jAufPnz5/75V/+5XPvfve7z73++uu7muemOIOAA5Emn/rNZpfu'
    b'vPPOhyh/91RrBytwgN/93d8995u/+ZvTzFAZK3AVdISYZgJ07Cp2eQ9OkcZ+EIyMDVCRK7BzIH'
    b'Qlxk0bR9h1rvwb3/jGVGE/CLuITrEBA6B/KmaHpAH1ZD5pJOvRHoGpFbbQ0BjZQhr0YAA6rTgg'
    b'IXVY1QsvvPD6NIg7g23KQKwIqGhoXJy1q7Bz46ptUh0NMDYJ/IABqAQ2VMS4W9i09dx1sB8E6J'
    b'yd4axzACB0cCaFgHUsyzZHbAKqCLIijR2QUH8wzmCk9REHgyOD5KXCDm2AOPPskAGsp1BOiCZQ'
    b'07FBWAmV6iCE4IAOApbZMYLB6csBYBqETLzVDpDs3DRxoUPIgYwzaXbpjs9Pg/zpn/7pu1RZqi'
    b'E7NW5HPRiYyf76r//6tCK4cOHCxb3hLagrcTAHHqEdcINf+7Vfm/rCwWE/yP333/8uZgGsBkad'
    b'qypDLiMMwOXo5ptvnuI/+9nPzn3wgx+cKuwHgabHy8yATlkNcTqyM6HcfOyJ/h2Ac4cB2pV83+'
    b'ho68ZXvvKVadp0wA7xoljVaDmdqiJW8B//8R/nfvCDH1xqtpjOEjg2CDzzzDOPteBBZslqcjuK'
    b'fsAqiMOPf/xjruLH+uwOIpcvX36djhjMjkgrgg0RbVCZHURefPHFaTAHKnyebbqLXz0WV/LEE0'
    b'88186b2z1zAPXhvDt5qG3/S7uiLsNBOC3/7d/+7dx//ud/TltSVTFAivdiLXzt3nvvvXGqVOgO'
    b'8ld/9Vev/8u//Mt0wWT35I0dHYNXZKGM7Xzfffcd6/NYxl/+5V9OA9AZt0a/9Vu/NQ2A4dnOgK'
    b'9wNUDcWQxKGwZrKzrS75FEDvA7v/M7030XA+j5OiKhAxG6Kq8STOhjH/vYvu99hPuuf/7nf57i'
    b'bUvuLxF6fG+ATIOrow2DfeQjH5n631+7vv/9708zQj2/8Ru/MQ3gCqC3khQ691JDO0SmQVgFl2'
    b'Uu9wziCmicOCA4aG8gdiIq556LutMg//7v/z5lsgJ2EvHaYVI7zzx3HH247adBUBMZ7iLIxj3s'
    b'1I4zDvS3H+TJJ5+ceuHAQlINYpwyjZuSUDfzvvWtbz2wNzwDaKwchAY2dMYZN51i290meGo/CF'
    b'Td0wBsRJrOUa8dGicfoQ+EAVT9uzGQZ3udmQ3pCK8mbqgAdYX2aMQBGhffzRMrgzCYDR0MjCMM'
    b'lmkEUgNsffpykNtuu+2N+y6uN1A7cUWKnYIdZ31gAC9FMg1iJoPUgcBB6JhwBH1wQ+Hd45H7Ll'
    b'TGQOrezgmz07qaBDV5a4R/oPZ2DZyWe2QLs1RX4+xzRaxENZCnymjHlcKrNrTboimEI3v26aef'
    b'fp0Z0JF2Iu1q6JgJCINgYDpmBQhteYrOW6MjgwA3d3RGZS8LDFJ3neU+Z3JxpQ5P0fXW6Ngg8O'
    b'yzz76ualAFYULnOptXCgb40Y9+1L336g4CbaDHWicP0gGXfrBj48Iuahvmxmbo13ZZRxgOkrSL'
    b'3Ouqp+IOmmPVIFtpV/anWvDAG6mj7NT/aLtX+9Qu61Q40ULyVUPuAXUxYMKJaUP3i/vKNM9iU4'
    b'WNbGrU7oofafvoYSbNXQE3r8DkmZDbgjgTMy4ZB9uBi/IetXeLOMeqimieCxGT97IKDOiNMgMj'
    b'LoCJccVEKl4QtV6GXtPo2wWRvuuuu2bnOlvIq6o8A77yyiv7wZw8F0JCJs5geD9lwOWod2MIXv'
    b'u84Loowrw+EoKLUjF5f510M9lC7Ur9MBdTLUBnXGR55ZCrOlZgK5HPAB4r4GTNI25o3IVALUdc'
    b'mLgQQu/hk2MZbiOtoAW4Q2YRxDV3Tr6HkwImZX3i5htKtsn+iZPPuDsu3XHHHf2XIuoi3P8sgG'
    b'c6LIC473MgBnEw06MwNQ2ZNp4TZ7wc03Fb3Usf/vCHj75Gz3O6Du0i8AMehnytHkvYITi5JBcH'
    b'dXHZxnSK+VrNENgd+gsK5cSeChr7WTVfuJ0FcEnVEvgE/qAv1EmCg4hp62Y5cdPGdW5w0imUK6'
    b'RZhNuLkDsC4tNCOIlZBOKkWYCL0Lx2Drko8wjJ1wrGrUsek0WcmHVNI5VaxpwUF6VF9rcTLMJz'
    b'Ia1gR6SdjHkOAMQpc4JIatTyXr4CtX/TTB688SPdrHL0OTFhEZALAToE0zmQkmkmaqjVcwGUkW'
    b'c/1mNc6zkOsPVdBALNKm8+VTNxRao1FPOctHEHdjK+KqVkuXUIaU+Y/VFmHAHmgwVcQHBpWkjb'
    b'Ro+ylbgy5WKyc7BTB8/J10UxEcstq/1VssyQySP4gv4AuZj2TP3QtBBuqVmIfgHc1dYJOUkgNG'
    b'5+Lsq05caBdE+ASRN3N3CRYQFMnAcjrqgoPBcF+63VFvEQVykWAyzAxbgIByN0EYS1zEkzGRcl'
    b'anhE9kM9JszEfT2AODAGW9eHriM9fuELX5ieL3zx2k60VNWCC1DEOAtgMqTTOku4AMZk8ijYEO'
    b'iLR4l29rV1XHh5ajOVBE8//fSrbSHnsYiwEExL557sTh5xsnWS5mm1Si+PyTMGYzp5/90DXLV4'
    b'cK/P1kMbf/GLX3ydCahJBlCYOOKWccJOLONgH2A+7UULIEwYX9AKpMmnDxbB3fimVx+A11RyEq'
    b'BVCNMSCAtzcVLTQh+0Vzk9Z3YByM4KDzUrdP8vM7sQ+drXvnZkDzAJF0Moarm3IKA823omKE4e'
    b'QfssAIduVhguQFYtJHnuuedeZyJMyokRMji4l4HJMRFCcdJgG3HiwBZqk189v80LSZ5//vnH2k'
    b'IeZCFsD3AhOXmo6YTJ7xbQ5v7GVWgrJ1rIHN/85jcfaAv8dNN6vr7F9vgLXt1+I3mdY5y6Rdqz'
    b'zcMteOSN1FF22++19uT5yfa8fapWOfFCvve9751vV7VXOUBx1jxIE30IByfurRDxpfcxruHgDt'
    b'oz/mfbHcCfcTvD5LllABfixIW0ecZZlLc/SLsgXLzvvvsOstTmhbQFPNwm/wgL8IUKrvmSl19w'
    b'8uCEhXjex5k+5PXfTQ14uYhXHutLp8IinCwChpBxQAnmudUIXdypv/b7ne9853y7XXmVBezuOn'
    b'clb0yOBXBbgZB2Umq54vZLn7IebbxF2bKYxUptKz32wx/+8EGtkAOzAF6o8FZfTTKJPPmFNPdk'
    b'LMCQ/nJhLiDlnnvuWZznbIVcBP+1EzrnNS8WkTd5LIyJ5y1M4v0XYd5ospDeFY9xuCMgvPvuu2'
    b'fnOix88cUXH2yn82P5QjYwcV9GxQIsQt9Q+y6EiVacvCEQIizGUOgXQVH5XunKsIA3C/UWwcuo'
    b'+QpkWgG0Qm8RTJJyQssJFS1C3MVQn0UgjHHnnXd25/zmBg74vwhOnZfVXERuKbXlYnI7ZVxcQE'
    b'I92toXkv1Sbjv+HTxFCscW4iWWhaghJs0L2bwi778W2LsM5CTqpGtaazghywmN008uxMWI9dpi'
    b'jv2j9dhC6jnBpLGA2wm/YBFOHmFyqenMh1pm/RQgdNtRz4Wl0nbCf42PcGQhWCO3FBph+2CFdG'
    b'oHIQQHMO6ExPKcNNgGMl8oZxwl05cvXz6ymCML4bbDLcWEsQaLwBJeYtWMAzsZ0uYTKmJ+D/si'
    b'NJ4XBHBsF9LiR7bXfiHVGmifLcUieFHAjsRJJ5nO8hoC8cyvaUPj9OdCDNsT6p9NhY39QrACCw'
    b'EdTUu4R2ksDpAwmFqn3Di4sNqul+6JfSPMZRd+dtfszYV4Ow5aQ8eui6CTEQwKWYe4+ZATND/L'
    b'hTy3mOXMxTDHmGbXbkVedxGANfLeqU48B+1NoEKduhggvUUSlM1iXnjhhVtJv6nmHV6ZFCyB1M'
    b'WYdoKZrlgHehPr5UnNZ36I8db3S8SnhdQbNq9QLsKOeoONyojXRVkn62Z8BOV5OU/c8scsUq0h'
    b'dqR2Rx07KetZ13wY5Yt5GeZ4+K3oM92FUEioRgmdGGSoJL16TtpQkUyP4gmLyQUdWwi4GBeSpG'
    b'ZS62AcSW3nIrI9ZBvrSOabrugvRxbilqpkZ2Ke+U621vN23EVQbhyhPPuwPnnGe6Q1oGuROXKi'
    b'ddLiJJCcNPkKaetmuaxZxLGtpU9ojbyC5eA5UKYJmYiTrwswnfWM296+gHKxDtuY+eXkfeUepo'
    b'XkIjJuJ+KAOamUXrkhuCChLDFd81lEXkGBBR2zCOQCQK0pSaZ75WD+3MTXwAJYSF54cgHe5O4t'
    b'4vZKnEwVyAkKZWmFrItinIz9WG7c8l7IgrhC5SJ2XOaPPvJyWgQfQZhATgwcHDIv6yqWzVHLa9'
    b'pFoGi3E3G57bbbpo+7Twu5//77L1CYVnEhdJwThByslgF5QJ5alZpOev27CJ6J6iKOOTukRYQJ'
    b'Oak6AfMrNT8ntRUX4eNEbqv4d93EfiGt8staBdjTXmWYTBUwBOLWPSkqDcXiF9UazAvyn6X7hb'
    b'C9uOv1GQTYXrmYxMFcgKTlKKuWXLNQ2jBp5pHWSEWnNWC/EKAyjbNB+ooCGYfMr2HWqwursJ0Q'
    b'5sIisAgvgnhPhWJ32+rIR1OPLITPRaZFRKuoeSbm4tIaownXyY8Wk4vwXRBIKtaFtG115D9bRx'
    b'YCbRH7N6FJLgKYMJPJMBcBmWZyie2EOHWYrD7BCx8sgnmQxwIQXjjsvRfl2ELuvffeT2ERRXKy'
    b'Dow4oZxY1gUmIL1FsADGYsJMnEVgFZ9UgT54ladZYzoAK8dWJl/+8penFySwhIMxcQbMiWgpwp'
    b'y8i8n8bAcqQ0vkltISwCK4FRlZA4YLARbjRJlELsh0LsS4Ws9FAHmWIVqCBSBpiS2LgNmFgN8N'
    b'AEyCwZWEMieeUkkrIEycSWMF4/bNAnbbaXYRsLgQyLc5qUknRFrUeLUEaAXa6A+gNfQHBCuETy'
    b'wuAlYtBJ555pnp83bgIlwIohbnqJM37gLARbAAttPatzqtXgg8++yzL7XJ36pmXYiTcKLiZJNc'
    b'RF28C9jJxXpWzLFpIcKbz9TiaCGpcektTGIBm95wJgctRKYvJAqr9BYCSwswPGQBcqKFyIsvvv'
    b'hwW8wjHqB1i83RrkwX2sPRQe+aS05lIT2+9a1v/d8W/EmzlP9ZYr//XZs0+dd5u3NmO+skPPnk'
    b'k4+127z958C4Km/FC6luK6ZbOW75qfY8+fiUcY1wVQ3yxBNP/N+m7E8T96Ga0HSGa0kD9OIYKu'
    b'NAOvJevuWWW+5ol6TuR/PPmitqkM997nP8L3n/bk5Fappb37UHUipfMq8XJ0yj9Ay0y7/QnjZP'
    b'fNCt4UwN0m7jz//t3/7t/v3A3JKrdBWP0udIg6gkyDiQts9aBr08sWzOOKR3t2GP8lLAVHgGnI'
    b'lBmidghPPpCb4zBAOoOFEhVfnmZ2gcUmn0aWheUseUej5ln0DaOCFpn16aPHT33XfPfqRlK6dm'
    b'EN7G+Y//+I+PpSdoBN++VmGBGoGH3Fw4witrkEqBjKvAOarSIQ1kvFcPqlFAw+zC1+66667u98'
    b'pt5cQG4U3BzRMezHeraYC6K10MRiCuERCU78KtR0gelwogTOm9PFPLMkyRfP1Kg1RjMQ9DMNQo'
    b'CuMufU3IEgc3roZAepcjYAFpBF/yIe2L5aZZlEZgkaCSEcl4ksqu8WqMzEsBjEM8vSbXxlzBud'
    b'Zw9HUnS2xuxAcWvv71r/Pp1yOGgGoMJo0hNILK5xVRyxEWUXcagkIyNA6GQH7FctukSI2bNp6v'
    b'L6YnAYZi3sAYGiLn3+S1O++8c9OlbJNBOKybIc5riN6lSSMARvAdkUyYNOW8KMTEyXMhCBiK6V'
    b'TWGlRqtlcq5lnfehjAtOVKD+oWg0zSuOOjH/1o958glaOrH9AmMN2+8h5zlM/7zEd3S/5Dgzie'
    b'oFdgBIR4GmE34WNhXbRpQ+vBUl0hXfOgl5dkf9lHr53z0jCEO17+yEc+cmEXH/Lmqga0s+Lh5g'
    b'mPoPy8RPW8wktTGsJQQ4CTzQWRXqPkSq8eYl+me5wkP+dfQ6DcdQrxO+64Y1bns4XNGNPnJPMj'
    b'JGkMlAx6hYYgjjdgJC9LObmc5KGw+FQAZF6OYX6v/hyW13p1/nqB+VmfvPCSiQ9/+MNDBQwLeJ'
    b'kDY6B8LlGE+TzR8woE5WMUJpHGSDLt5Osiaz5pZYmsV8MetSzTc+2qIQhzHaYzD+jzj//4j49m'
    b'7uhm8qJfM8an651UegbG4MDGGBgA4Z/iegWTqJ6R9PJABVg+Uoj5tZw0ku2VEaPyml/n5NqUUZ'
    b'5hwg3Dhz70oWMFxzL8PLqXKY2R6BneQXmpyrunnFhi2kXV8p5ielRlQS8PzBuVQ69sVFdcH8J6'
    b'wXWP1i+O90d/9EdHKhy9ljQwBp6BN4yMgSEQzo48wD245ybTW3gP29d+sn2WjfJ8lsjySpb3sH'
    b'wkPqMQB+fgWOikCrpCTy+88ALfJLHniEF2/xiaDOHlSTCEnuFlSiNoiJyIk5Fe3hpctNR+qhKg'
    b'thHy0kApSS+vB3Vqf9U46KWCHmGnsyNf63HEIM0ID/ZezxGNQUd5ZmjtqqzECVdG+VvJftIwlZ'
    b'wf5SMDqdhReZWs28MNrTGMc5lvXsIvpEzsDcKXsPSMYcP0Br0Dw6QhiJseYV0x7cJG5UtkvVSK'
    b'/SqpYMi+s3wL2V8PjTCi6fH415Y2JtfpeQaMjJEGcWI9kbXpmp/KRhyz5ovptXKIIRL7QNjYhG'
    b'vAWOhSjh3qPbhMaRAaE448wQWKSjO/li9R2/SMkKJSiMOorvWy7hK2lZqGXh5waTJMkd3bjZYN'
    b'gvINtaTe4WJFZSFOrIr0ypARtV5VpHnmm2a3umOtn+0q2Y9if4r5kmWVvFylASpNp39COGuQNI'
    b'ahcVD50ptYLw3Z1jopqRCkV2ckW9vWuhUMan7OW2NnX9YzXh8bZpjeiLfaQ04TJjpSggsZkeWE'
    b'1QNqvzUv85XsI8V8+6hjEpfcmFDTkJcqBdKLjhjE86F6Qo/egD1c9Fqs35NUFDcfhOZleQr5Ql'
    b'plEjdvDdl/9jkHOpq7w/INwTumt2TvDaIBPCegGqXegTGxkTh5qfnKKF/FKWmAbGPceuZB7cd8'
    b'sE3NS6n08knnmBjBu091md6QlLy/4096yGsaID2kxqVOZATlKVLz6cv+kB69eqN2aZzMX4vtsm'
    b'2vLw2QoXFIpWuYahzOGd+8vTfIjTfe+EmVnyLE2aXuVASYoEpJBdTJL+VXsm5PemOCeZVsm5LU'
    b'fJW7hfQOL1c9I4zYG+T222+frmE8+K05S5h0TyEZh6ogy2s9qeV1DPMIIRWW9WCNMq1vG8m2ll'
    b'cDEdcr0FkKxkiPyDKJM2T/ky95yaLyJwkxik/k1Sh4RnpJKsx4VQyM0kq2nWtvXqbNO016fY/G'
    b'0lAaJvVVPcMrS9IuV/t3Px4xCG/N1wB0rLdUvHSNJsvERtRF1XQP64zqzY2XyjoL6BcvQWd6BS'
    b'H/mkDQX0+Hekc7P4688aE7y6eeemr6GK6eQJhU72FAr5uEc6xVvswZwjI8SkZ1Ya5sLRrWtbp+'
    b'jECc/w8BxoBqDP61ARikyeMXLlyYrkrS1d4HPvCBG1PZhGCeRlKgp5wedbfaLiXzobe7Ladsbi'
    b'NYz74OhXEYI8dTHxpDD9EzSBMi4OVqZww+jHjEGNBdBR9WaR1fxBP8ZxQiDiB6ElLPgKqMQ/Ol'
    b'1jHumBUUqByK7TGCggG8PBHHMzAEeWkEUDcQxuhOaHaWTz/99K1N2S/RmZ5gyCSEOBMgdMIqoI'
    b'apTKhKNN1TLvTajowxYm3dNIRp1oigeA1C6CVKrwANgWiIOWPArEEkf/hFgyQaR6PkQlyMSqhh'
    b'Za2yqNerOzKOecxLar0sc/5AqCHc/fy3FKpXIICuwBcXeQtVM8blZozp+5hGrDIIYBQWgDgYYK'
    b'A0CJMnrAapVGXYt/TKM6wsGQJS4dArc945f9aH0on3DAHVGEp4xqqvEFhtEPjSl770YFvE9P9f'
    b'BmNBGkcjGAcXhIyUsRRWyK9lWy9ZiYoH5+paCPUMLkUw8ghJY+y8YtM3CWwyiHz1q199tQ14Hi'
    b'WkMlR6LtAFE1oOxmkP9pGh8RHWsY+K87DctOS8kFQyStcIxJWsk6QhwivuaMZY9a53OcggwpfT'
    b'jJQBLlRFEFalVFRyivlJlq0h50IIzieVXI1g3Pw0BMo3LIa41AyxfzlkCycyiPBFOyPFqYBqGJ'
    b'UyR/aZshbHTcn5VAMYGtdIxiGNYHgahpBTMYjwyaoWnH8j9SapDKghZZLxpBoi07025OVuBpUP'
    b'aYAMqwESPQEwgGGTzZemEadqEHnmmWdubwp5jjiKUTIN1SAjBXLrmMpci0qGjEM1AGRcxUPPCI'
    b'3LH/zgB2dvYQ/hTAyS8PMfTeH7H5vIS8acQdYYYKTkhDwUWMt6HgBpiDSARmiecOpGSM7cIBV+'
    b'CaQZ4gENI8TXGmSk+Eovb0QqX3bxTV9BdlKuuEEq/ChIM870exp6TN29vWv/Er16qezKruzYq6'
    b'9XmqtukBG7n9f4dPOc6TdGoXqRpMGW3gfV6l5udf48/yl0netc5zrXOYhr9gyR9rD5wKuvvvq/'
    b'WpTPUBx76BzhK9DQzh3ukv7m/vvvf/SNnGuXa84gTz75JD/FxhcVTL+ZBflssIY8+NMwxnfll5'
    b'qBTvQyx1lwTRjkiSee4KN0+4918T+WNELvn2I9UvmgYYoh9unIv9zuui7ecsstV+V7FpOrZpD2'
    b'/HH+29/+Ni+v8G/iyQAqPg2w1hhQDZJp4j0DGY/yzzTPuWrfyXvFDdK84YGm/Kd6Rsi4ZBxSyZ'
    b'ValsoW42mMfAMHeZS1h9TH77vvviv+kHjFDNIMcWszwEsoWEOkSMbXvKiYypalPOKmNczOO/b5'
    b'1mkPo1fUMFfEIM0Y0/dspSF8w1gaAOqT9pxBVF6l5o/ShGmInlF23oJ86t577z3zu7QzNUgzxC'
    b'PNENPHrf0yAgVWvMyxi71JKkuI22fmJ+ZTr9fHyDDWIY/4Pffcc2PzmjM7/M/MIPz6MYv3azoQ'
    b'vSINkQqSNIRlNYTaLpkrg9641UM8W0wT7jzm0bvvvvtMvrv31A3SDPFgW+yRr4tFel8HCKkUDZ'
    b'EK6MUhlZfKtf+sW8dMmKfYJ9C+ZyBf4MRL8Jap4BQ5VYM0YzzXFn/7yCt6imGxaQgl01UxQF6m'
    b'56jjphHEOnUMMM+5hFHO/f7v//6Np/n8cmoG8QsyNcKSIYAFYgzCKiq8Kj7jKmyOOeUL6V49cA'
    b'znJc6NA78Z5KELFy6cysv5p2IQzgu9QmPMeQSkIfymiDQCWA7msSsRQBkjqOMbIXzvmOmq/Jyn'
    b'cevkXDJ0royzm8elu+6668QvxZzYII8//vjrTF5DsKClyxMhUg2Rhyh5LBTRCMoIy1V8hsbzfW'
    b'RpqDQSc6/zZ04Z5vx2BiG89PGPf/zqvQ1Iz9hqDA2BAQg1SMbTAGkUyXglDQCZzlDpeVBvDcL8'
    b'oBplN89LH/vYxw42ysEG0TPqF2T2dlbPKzBGGgQFE+YiQUNUA9Q0qFCocdMZ9gQwEJJeI6yPOQ'
    b'NzBdJlzgcb5SCDrPUMJooxgK8E1BAZsqhckJIKT4MYqrwlqrJT6Qn55hlqEMp6xsmNRBgGOXfz'
    b'zTcfdNBvNoh3UxpjjWfgFUj1CsNqCJVOiDIyryrW/MQyIa3IXJ1qGELLAOMwb2D8nkGQP/iDP7'
    b'jxpptu2nRL/EYPK2nG4BcR9re2GmFkDIxQv0qWMoS36RjXKC4kxfyK5SNSgT167c0z3zjzyzky'
    b'Z8sQ6I31T//0T7y1dhPjFRWaMW5vin/O73/HIHOXqeoVxFkUhmBhLjIXlXHIuAueU7KkMejDdK'
    b'+teYS9uhlmfg/WA65jJ6999KMfXf1Ev8VDnvM6umQMQgxAWC9RShpjJJVUxqhOpbYZYZn99oSN'
    b'NOexvfk1Of/ss88e+ebROVYZpHnHS3mIL3mGX7DMp43SUzQW4uKq9Ba7hbkdvBbm0JvbnCzwcJ'
    b'vXqjdoLPbUjPFAU/6tnhnVEJDGUPleprhEIfUSxSJS+WsMYdtRXYyhWMe01Pama77U8mqILEtq'
    b'3nPPPbfqPFk0SDPAU1yqMETPOzSGO79nDIQyDJKLeKvC3KthlLm1NaMc+RbrHrMGeeKJJ6aX0U'
    b'eeISg7vYN0GqF3XkDGc3f3qG1r3V7bUf9zIqa55a23vYljuM40ClKMtHiWzBqkGYP/bUyeQdjz'
    b'Ds4JDaIxCDUI4qTejugZVZLMb14yvdN/xNAg7ex4ioM8vaMaI++oMAI7RKM4gWoId8ua/EzX3V'
    b'qhnuMh7uheXci+k7k2yaj9Eq0NbwQcMjRIUz6H+d4geIf0jIHwfR/1vEglvR1YMphrnpNvfOMb'
    b'Qy/pGqSeHWmMBMWn5KCJBqlGqfkutuZB1qV/yxPbj/qYw3Zieik/yxwTcY7OQXZ5Qy/pGsSzQw'
    b'FDFN+7xcUjKEvPqIY5Kb0FXi3SEJVc/0heeOGF7rsjj2msecf0u1NK71JlXAMYZyAU5qBVgabr'
    b'zhLrWj5adK+s5mU852C9rF/zUmQubf+ur0qWBdPvyFeOGaR5x2e9XCUoXPAMjWFcg6SUCVxxUo'
    b'FXgzSGEFc3r7zyyrGn92MG0TOMV1R+XqryMsVAOYGk7rJKltlP9pftaz7UvLnnB5krA9uvFch5'
    b'iHpCgPLvfve7+4+LyxGDtMtV90ddJJ/IFYxQDfJOIg0xQiMIafTU9HX7LmtP9ZDhj7r0zg5IIx'
    b'AqSS9vjqzb23mW93ZkrS/mj0Rqeo5R28yvxljiiEHyVrdnlDw70kPeiZ6RpAHWGkMvef755/cf'
    b'VIK9QZ588sn9R8ikPn9oBIWHQDquBnFCkpNMav5Wo1o/+yEPqX1XLD8N6b3eNVoLVxqvNjuj7H'
    b'9/CvYGaR7x6ZFneHYAnVR5O3pIKncO6y3VT0MkVW95yTpiKbETvSLJzoin9KhlpnNBtW1tk6iA'
    b'rGM/YrpKZan8UEaGMK+urR7qE3pJryMN49mRzCnvOn3QV/7a5xGNestb0QgIlygNAj0DrN1tvf'
    b'K5dlmWxl+q2xMZ5W+h9qEswYZHn20dfA5/Ym+QkTEkjbHr5IhSZG4iayd6CL1+r/Rc7HNrv02H'
    b'0w+CwWSQdoe1z6joGcZFYzh4bzJZp1e+RG1jf7VPyLR51INa1pMlar1R214ecEdqaFycJ+ghQ4'
    b'NINUp2cq0wUlKPtfVOkzRENYpokD/hMgS92970DKi3ucRT6mJH6Spz1PJMZx8p9fkgpcdcvVE+'
    b'jPIPYX+GjEhjaLR6dzXitCYpcwuv+Vk385eo7RSp6TWMvMF89QrdSxZGUCQbiR4xYm4xtjMv60'
    b'HmjyTplaeMWKpTy3rzTpGMz1EfLVZt9XrJ6tGb1Fayjyo9euWZN5c/koqXvR6j/JPQNUjvHDlN'
    b'Roqo6SWo5xkh2ccagZ5iNYR1JNvUsjVwmVJ6rDsMzoBUyBZstyQyyhcVqwGUUX2wfCsjIyTHDF'
    b'LPDkiP6Z0lI+YWlcydQ0I/VWkqZiSVbCe9epWs45hbWWMM0CDTFwWnstMoa86Q00JlnpZIGu8Q'
    b'NOTa9kubbPQdwhrkZZWeHmJ8zZniYlMqo/Ka7+Kr1HopWUdqW8n6Yj9KZZRvH1nmc1rvxVmZPU'
    b'Oa0v/fLiQ4xijfSdaJ1rysd1LJ/qSWg0ao+TLKPykYAvFqs/ZSJUcuWZWeIXgRsi52tLBRnZpf'
    b'pdKr0xNZO785artRP/mq9+gypVEIlww09Xbx4sVNXzY/mtyh2N9Sn7XOXLte3lmhMVI2sv+krh'
    b'6yB69QRvSUMKeAXn0Y5S9hu5Skps+SPIfmDLLgGcd/nBgDcN3z2jcySB7wVSlVKqP8SvaRUst6'
    b'pIKSbJciNf+QnZ4G4UD3ElWNUdOt7t/sokc85HLPOzJe/4nl5EfU8qX6PXrte31gCM8OOEShc/'
    b'T6I+0dVca3PKtB/j7J3iCtkz/fRRe9BFI5KiHjUNMyygfL5mTEXNmINX2OyvNA1xjmQXpCXn3m'
    b'fsdk3/r++++/hAF6xqiG0VPqZOcmn/TqmVclqWno5V0N0ku8XAGhOh3w8i6cyEvWBMrXMNUQCU'
    b'ZRGSqvitS0ZF0kLzmJ5Ukv7zSp/Y/G0xApa8BLkJ/97GdHvkyzGmT2JRTgUEfqZDNci4tc025U'
    b'Z0kBW5R0CPSNVyjqDs9Y4R38VPrju+jEEYO0xtN3PKWXJKOXULYoda5eT3Fr+77SOFcNgq4wQF'
    b'6uKkvv7IEjBmnnyP41rRF2Soh4mVmjNOutVfCa+ll2lp6QaARDxdeu5rzDS9WOY19yduwMaZ08'
    b'rncY1o71FJRRbzdBJVZJahpqfWUEZY5/JdEY6gYhDzTGEhil9wVnxwzSvGT64vneJat6zxoXPI'
    b'QlQyTuzisBRtALHRfRKGkMdZc6DM+AI3dX0l0JnaD8KolekpesJUW6IBe1pl3Wl6yfZb0+5vre'
    b'gvPAAIYaAvFyJeZLbl4Mc8MNN3R/MbRrkDbghV10/znCES52y8J79U7a/ixJY4CewSbVGHoHMq'
    b'cvvWT0bdhdg3ziE594mU6rV/RAOR7uPW9BklE+zNWXXnmGFZV5EjRGGkZJ5dfLlXQu7Rd34TGG'
    b'F9822EWN4k5QhMsWg42UcaU460MdxQPGSJ0gegdfwlP1AxoDz1DytavK0CD33XffvpGDz7HmLK'
    b'n5ta47ueZXrAeOu4S7ey3W1xhAHD2o+LzNlZ5RZHe52h8HPYYGgTb4jU5AoyAVvaRK0itPWUtV'
    b'KkpSebXsULI/+tcQCMr3XNUzCDVEGgO9IHpG47XmHd27K5k1yL333vtaG+DYL+n3jIJSPUe8hK'
    b'joqviMS62zBZWGjLDvkeHSCIj9EUfJGoQ4npEHuYZAwMsUhDG4VC1+O+msQaAZ5Q4mlpMasUah'
    b'LFBc/FqW+ncjHIpz0bC5ZgTPeM973rPoGaB3SDPKqt+vWjQItAledKfAkmF60N4dR2hckYwnGm'
    b'NkFBbfy7d+HWeEdZhfKnvtejUEoncgzTtW/UTS8gx3PP300/wI5O0unDBh0izGMJUuxlWS9NKV'
    b'WieZO9jNz3kA+XVuzpc1EMcIGgTPAL3DfDBUJ4R8LWIYY7WeV3kIcOlysoaScZWTQn1Eahp6ec'
    b'mofM4YMGqn8hHmr6BwrwAaJI1RL1NIgjHKZt30KwljDQz48pe//DpKSMWDiybUO1w0YQ/6AI1m'
    b'f/ZZyXzjI4M4H6A80+CcnJ9hegWShzfw9SJzhkDiUnW5eUf3JZIRqz1E2qSnQx5hUizExbooUV'
    b'FVYbZJqfk9sjzr1HzEOVpuWiGP+ZsmPmcMRGNUBsbgFneTMaC/8gW++tWvPth25mMourc7wUUT'
    b'ZhoMa3vTKdQlFNPKiF47xzWuMZBqCOCsAIyR5YIBDIsxNp0byUGN4Ctf+QoGeXBOKRohFw+ke+'
    b'3Iq2J+kmVrYDxwPs7DOXleaAgvT3pGzxigIU7LGHBwQ2ieMhlll9yjsjSGSlAhlvVQ2fZR45Lx'
    b'ETk+OL6hSk5DaAzgEgXVGBjA8DSNASdqDF/72tf2RqlKUhkqoMocaYSUtdSxaItSiTOfaoheaP'
    b'mVMgacuANoRsEgR76IKxkZhPwelMlWg9g2xzFPxS4ZgnrWNayGgNM2BpxKJ/D1r3+d7w/k4XEP'
    b'CkQZI4MokvGkGiLTvTbk5a4GjQBzhsiwkl4BO2NwN3Vqv4l7agaRZ5555nWVpOLSIGA8BUaK2E'
    b'oqH1A4yhsZAuaM0fOKXfxSM8bBv1nY49QNAs8+++z0MgvxnuJ7eTAySFXwGlLZ0EvneHVsDZCG'
    b'MNzF72jGOPZK+Ek5E4NAMwrfDvFUKt0zI41hGaRSloxQFVzplWfeyPiSlyYIQ7zcDDH7T6aTcG'
    b'YGEbylKX3yFg1SzxQ4qTHmDNQrGxlEjwANEsa42Gyx6dNmWzlzg0AzCl+p/aqGOIlBqnK3GmKJ'
    b'NEKEp35WjLgiBpHLly8/0AzwFMrXEGdpEFhjFJUvpHd5n2+GGL5D5Cy4ogaR559//tZmiJfSKE'
    b'i9jPQM01MweShwjfKTniF2XDGPqFwVgyQvvPDCZ5sx/qxnlJGnbFF81q0GEPN/9rOffbJ+POBK'
    b'c9UNIs0weA1P+w94+K+9jJ0EPjDTjLDq/91XgmvGIJVmoAebgf5Pi96u90C9rB0A7zj/TDPC7N'
    b'txrhbXrEF6vPjii3gPzze/1+TWZpzel3d6W/p3TT7fFH+mt6nXuc51rvPO5S11hLzViC8MN5yO'
    b'vjeiE70jsEceg3wMdPo2rcaUv/W7g66znusOspHd7xDxo7R/0kJeMj32s1758uQhLN3Y83YMPp'
    b'lDmNT0Dv5BcLn1Od1z8jnrKfc6q7juIB2eeOIJnIAfq+VHPaarfG56P+2anNQp5phzmOoUWbfn'
    b'MJ36nD58N9Tj153nOO94B+F3f9vm/t8tOv3+r8w5RM9BYJSfDK7y+xPBcMTaMh2llydZVvttdX'
    b'mB9S+a01zVF1qvNu8oB9mdDJ9um396T58beuQMo7j08k7C3OaXUZ1efuaNnCPzs37tb1fv0rve'
    b'9a7P8In5KfMdwNvaQT73uc9xe8RPZR65TXJj11CW0mdBb4P3mKtXy0gz914+jJzD/MzrlTdn+T'
    b'wOkx+ef7vxtnKQdkLwtpZHOCHc1OkU5tUQMl6pPwZc8d+Y1lv7b826cZegPvOcazcqq/mZ7jkE'
    b'jPJNh6MYXnr3u9/9KT5HP2W8DXjLO0hzigeaEzzSNs70ahIOUR2A0DhkHNjYbOolRxix5BBsKM'
    b'asG01G+ZWlfirWN96j5rvpIct6+aO2OEyTyztneUufLm9JB9k5BW9MuZUNkE4BfDQczMsyGDkC'
    b'9UYbqdJzitp21NfSGKPyLfNbC/31+k2HgF55zTNtW940tHvj0MvNYR6655573nLO8pZxkOYUfH'
    b'cETnH7T3/60ykvHaAXr45Avhsiybxq9CVHMF7b1TT08qBuxrOCC8kW1jiJZJlxynenyf5d3I3L'
    b'OMvdd9996h/gOAuueQdpD9qPtc07veqkgesJYRp6TrFENXx1CstHIWS8t7GYR9aBkWNkvTXzr2'
    b'x1BJgbx/kblzkH6tXbnSYZXmqOclXeOL2Wa9JBmlPwPPFUM8p5b580kHHTkE6R+XOkAXWIamDT'
    b'GdI/oUa3DHLDZH4yyj9N1uqg1jvpCSOusa7V+vVUafJak4t33XXXNXeqXFMO0hxj+og7htMxgD'
    b'AFtjpFGqueEH5JQzWsYXWGJUeoeXUjsSnWYD2vuJX8AqWkppc2fk9/vby5fno66emGejunSAeZ'
    b'ynbrfOjjH//4sW9dv1pcEw7ibZQGwDhVQKcwvQaNlE4x5xDpDBnPEHJDpMETDV9DqRu5Mmonth'
    b'85SM2vDpXldfPP6XhUhn4oSz1BTas79JU6M856m1xqjnLVb7/6mr9CtAfvx5phHqwP3TxTGCc8'
    b'1DHSKUhrKOOm55wCjNf6sDPmXszrkXWgbuBK7afWH6UzvzdGrefX8NW6W5xmjtQlqL/UF86Raa'
    b'VxVR3lqAWuEPXEyIduBdY6RhognydyY2ea79uF6gyG5OfVTWOZNpRi0H142tSNXemV9+rWPNKK'
    b'6Up1ouo8ifZCn8TVa6U6iumq551uL915551X3FGuqIO0EwOneMwTQ8eor0rhGEtOISi/90xBvo'
    b'YhRPmmNUR+QRxoENI7o3QFDNkwNc/wtOltXDC/hpU15VnHOOvx9gzWnjhLqHf1VdPFQaZ446GP'
    b'fexjV+wZ5WwsWfBVqeYYvBVk1jFgyTnc6IBzVGdQVDgnRpYDZRgA0QAaJPM0TA17zJVJ3VSngX'
    b'3WsLJm7Owj62e6loFOA1k2chptA+pt5CBQ9D+96tVOlDN/1WvZoiekOcdzzTGmt4Gw8avA2hPD'
    b'zQ06BuRDN4KiM7RMA5hHGoVXgZoW02yCWgY1r26kk7DUV92ga8eu9Ub9ZGhcanrkMNLTnfYBym'
    b'ccxPByc5LN30y9heOzPCV4ybZteh7CjzmEJ8fWE6M+X6SMnAL4spk8FZYco4Y9A4N15hi1PYTe'
    b'hss51PK1Y9d6a9Kjvs2fqwN5yybVIVY4iDzUHOVMbruWLXwAnBpt008/K5LOoegYQHqEG3yrY/'
    b'gQbpoQharUdJZUdMbBcg2dcaj1Ict7G2SpzRzWW6q/NIfKmv5y7bX+KN2rX+uO0DlSX8QV08Hl'
    b'j370o6d+mhy31glojsHnLnjWmNI6BCfGFscANrWOUW+h0gFwjPqwzYmB8jwp0iGgxjVazTO9ha'
    b'XN0Otz7aax3lL9pTlU1o4vh4xfwzmok7YQ4kqmCxc/8pGPnNqbIo9b60Cac/CW84eJ4yA6B2y5'
    b'pUrH0CFS6olhHEUZkkfoVUgHgQzTEFDrVNYaV2r/Peb6rGW1P8vn+uhxJevXtr2+luqwZvK0Y+'
    b'90KTzanGTVr60tMW+9lTz++OP7X2rTMZC1jsGGhpFjzJ0YKIt8lEXafNKpQOMzSl2s0zNuZU2d'
    b'ZK6+ZVkn59YrX8PVrr+13DRrR1Y4CFxuTnLiW67ZEZZ44okneDPhS23jH3lTYb58i3OMHAPY3K'
    b'BzAA6gcyA4CJvetI6hI2QIXmkS0wtKPVM09NoN0qvXm3+tv7b/Qzlp+604nmvHvuQZztiUTzZe'
    b'uOOOOw7+hOPBu6U5x6075zj4lorNDjiHmz/Fk4OQtI7gM4aOYD5p6Smtl3cl0dBLG2yuXm8Ntf'
    b'7a/g+ltl/qb0nvtbyma/+W13BEa4+THPRFE/M9D/BhnI3PyeFDuI7wk5/8ZAp7jsFGT3AOb5kM'
    b'0yF0FtNQHUTHSEX14pkHPcPWOsnIUGJ5r18Y5Y/o1V/K2zoGLLU5aXnV09Z0r3/r1LDHrv3F22'
    b'+/ffPD+7jXAe3keKCdGE8R99Wq6iBzt1Vs9LydIp0OghPoIAiQRgE6hPnEza+kwqxXmVN8j1q/'
    b'1rW8hicl+6l9LqXXsNTmpOVVT1vTPaxTwx7Or4WbnWR5JoG3VekYhmudA+otVZ4chpbhMN5CKT'
    b'pKpivkqxjiGa6F9lvahCGmsEf2OVcvmauX/3Bb218l2+X8ZK5fymr5ks4ozzpb40DaudayEbu5'
    b'Xvjwhz+8+nZrXc+N559//vy3v/3tV9n8+UCOLD1zsNHBk0OH0Ane+973Tul6S4Ww+dMhoDpIls'
    b'2xpk6yxvC1zhJZf6mt5VmvzoGyXr0tZLs1fSzV780xodw6oxB69SDjUNMjmAdy00033fjBD35w'
    b'1YP78UvvgO9+97vT76ZW59AZdI4ROocbHydBiNfbKuM6h0K9mpdKrFimqCBlidpvbb+mjx5Lbb'
    b'P/Wm+unetMal89EeO1fE4OYdS+zt10hil1D9T8Ufmrr7565DeA51jlIO2h/LPNMW7NV6uqg0im'
    b'3fB5cpiH9ByDB3BPkrnFZ95bhUM3VGW0wa4Vcn5Lc7R8qR6kzeek0qlzKz82tyueZXF3+RkONr'
    b'6nR++hXMhjc4vPG5AOohMQkm+aBRDiBEA6HQIsW8L6Uo1Qy3ssGW5ujFFb821rutY/aT2p6RHU'
    b'W1P30P4T55q2TJtDppFaPoK9VGHvivNtz28PfehDH5p9k+PsSPwWRtvw00N53lr5zNFzkKR3Ww'
    b'WeGjqFDoICWDx5KgXMN214Upb66Rl+S5u1G8d6S/Vrva39j8jyNX3WOmvnkfRs2XMQ4spJHETS'
    b'UXZvyb/QnGT40P7GiAOaA0xvV0/n0CkMR6Rz5MmBcyjmsSAVUJXSkxFr6x3KSftcap9z79U9ZC'
    b'Me0uZK4vxG8yQ/pQf7J2WOLN/pmC8jHDJ0kHZ68LsZ/JLSLqdP7/SoJ0c6gvEsZ6JzjnEtM2fA'
    b'pXX02vTIell/pBvrHyI91tTZSq/PmjcnsMYhethuZ5cHnn/+eX4sqcvQQZpjPLKLDk+PLc6hpJ'
    b'OYRjw90lEgN4GKOS16Sk9y7LOg9j+aj/qwfi2fo7eGHKMnlV6dsxA/hWiYshb3X0KekoST7Pd6'
    b'pesg7fTgC9z2Xwyd6BxzpAOkEyCkraNjGFbn2MqhSn2rchpr7PWROqzltayWH4J91H7Nr6zZHy'
    b'OnqHm7/carWtPX21a6DtKcgF+M31NPDqmDGU8nMFRAZ0mHWCtbWGq7VA5bykd11nKafclok61l'
    b'zYY9Dez70DFyL+aeHGEd9uFO30f2vBxzkK9//eu8EXH6bEfSOzm4xUJycj3nACYCpDV+bgRDsS'
    b'zrnDW5EZSzZG3/c/PJsrWS9HQ7V//tyG6P3f7SSy9Nv0SWHHOQV199lV92nchXr3qkY0A6heJp'
    b'YRry9Ki3VYZruBYNmfOv80Nca8qh1L57jPJHrOnzLHHMOo+USu7BLdjOU+THP/7xfu9L7xZr/4'
    b'2Hh6ATQJ4a4mSqVFREVU7KEkv1l8qh1kk5bdb0P1enllney5+Tq4Vj1/kg9cH9tChOcuw55IiD'
    b'tIdzjpjpy922kidEjRv2nKOHCkiFHKKUk7a/2tT51zXM6VBqm9pflWuNk8yPty2lrOD8N7/5zS'
    b'O3WfUEOXYPtgadAEZx6Rn1UMPYl3ISZR5CHU+ROj8Eem2QubKUEaO6vfyU02ap/1req3NSeg6x'
    b'5Cg7G806yO/tws3gDDoEobdXhOYzAZ85llhTp7JG6UvlZ82acXOOvfq1vMpp0xsjpUevnnKWrD'
    b'ktFuoc8YHqIPzQ/n5zr6GeEpnOfohnuucA5mWY0lN2yhK1Tm1f5RB6/Yyk0qszJ9yXp/Tq1H63'
    b'kO22SjJXJrWOclJ0hgWnmJ5Fdnt08gE56BZrzimAgcyrZaITnITTViYs9Zfla6TSy6vU9pmek0'
    b'Pp9YWsZWu7Wt82o/ykl7eGn//855OkkxjHOeJdIbO3WF16m534XHoNeTokVUnKVnpte2P26kHm'
    b'r5VKr7zmVUl65VWkV3YaskSeYpWevqG2GY3Tyx/Nq3dC4BRJTS+xykHeTqjckSQ1fdrUsZVkrr'
    b'xXtiRJL28LbvDsxw2f1HFqm9Oibv56W9VzoCU2OcjoH4Y9ttS9EmiQnsyxpW6PXvtMu8ly06wV'
    b'6ZWlJL18xuZ/X0rOqSfW6/VfsTzbzrWpJ01lrlwHqI4BWZbhEqsdZM0t1LXmFFcLN05P2CS9fG'
    b'Wpfcoa3JhKxfmcFr2+HOM0xzkJOEc9bUb/ja8Osv/OIF91qk5RHWXkNJlPP7J0hdiCSj8t5ffm'
    b'VsfYIm4MN2dPaptDpGLfeZW3HvlnRY6R0pvjScBO2mq0sedYeA458r1ZRxzEzV83/ZITjMpPmz'
    b'T2GqXX+lV69OptETfEWkl65SlL5IYc1SffeshZ4RxG89iKTjFyji23Tmtvr6CeIH+3CyfY+F79'
    b'iSumK5m3dLuVCjxUKr06WyQ3V09yY60R24nxzDeu9PqoWOazgGIfIyyz3qh+La+yxJo6Ql3XYz'
    b'rbp1P4T2bvbipbNr502hzxgeEtVs8BKmvqAMYDDV6VcKXIsXvj1/IqS1intlMqvTopPaoOq7wd'
    b'SKeo9PLmHCPLVjrQkVusY6M99dRTr3v193uw/KrRPBWMp5MQR3x2MTSu99e3uufbT2qYnHQDLL'
    b'U/rf5rWBnVW2qXzjGip7fTpDd2HbPWmZsTZdjfuKH5hgj7iNDTw1ssNv5aR8jnD+OE/qPwtttu'
    b'OzLZeoIw+OeZiLjBUzJfMp7oSN4CaOSKeYTK24FcR65tJNd5Ex0lpbLyVFjLsS+2PuYgjb/ZhX'
    b'tPNRzRc448bZLcBHVzbJVKr05KZam8UusvifTKEMuSmuaCotSyHva9Vnr06imwtGm3wtp61L5J'
    b'19OjstZh8vQI9ntfuqvjNovQL4jj6s+G91mCeO8WC0i7COOExlkk8TxWPUpTITUNGui02Npfr/'
    b'5cXi9kTdlmFAedQj1YXuudhKpjWOq/1yap7Uf1M9/bKCAfYZ8QWqZT5K1VL5yjOoYht1j19gp6'
    b'JwhMX8fIBJM8SWrZWlDeksgoX7aWV1lDr92hYn9Jb/PUEyPbgxuo13Yr9p0yR2/M2j7nN5oj+W'
    b'58pLbpSY+eU7BPU6ScFpXuV5B2HaR1+hk6xgkQ47uyfb55UtOQp45xcAOkJLWslp8VvXGVrRzS'
    b'5lrnrNeEI+gw6UAIJweCUyhgnL2JLFEdZfeA/pkpUeg6yP333893lR7xqHSSHnNlCU6SV0gVbn'
    b'yLVLaWL0nPiaskvbKlOilvFZbmvVReyVMCSXSUNRu/R16URccKR7nUbq+63887e0bnS76GDJjx'
    b'Hi5Gp9G5Mu1VAQVYvyoJ5RqHjB/CGmNlnTX1E+vXMFmTh2NCr25lTZ2rTc9u5GF/4wj7wHxCNn'
    b'I6R54eYGh5j9yj9bnD8MKFC8ONNXoGkU+5qXNzr0VHAuKZHhmWfCVBYVvJvmp/UMtrnbVj9vpB'
    b'1sI4h6wPbJtyrVPn6Ly9aKaw3/LWagu9C3i9vWp8ahd2WdRmO0X4NZ7bibvB6z8O60R0Ip0KyE'
    b'tnI51KEJWlEmu4haVNumYTz9WxrNZZ00Z6dbecID0ObXdWVNtpb+3sPmBfkKackDSOAVtPDlhx'
    b'elxup8cdU8aApRPk3B/+4R9e3EX3MDGEBbjZJeN5YvTwWUTBsClJLTsNWcI6td2SzJGbxbpVD5'
    b'J136rkGoibJvTiqJjWWdI5ZOspklQnufnmm4/t7cqig9xyyy2vtUl/kokzaaiOYdz0iHQYvBtZ'
    b'cozrvH3wpFDcMwr7CAcgns8bKWB9yXiCIygS8U++733vW/whz0UHgfvvv//xFkwvg+kk4uR0mh'
    b'F53OEovdOlOkrKIXjFSkl646RYR3rlMOq/0mtPm7pxJMcYUftc0+ZKwDpSL+qmrjfT7iVPDtAp'
    b'0jmEuOnMB/ZbOlVxlM+0Wyv29CLzFi184Qtf4Nd49l9N6iY3TCfo4SJ0pAxVFKg4lWr6NMgNtG'
    b'YznaR+xbKsk+sy39usk453Nah2S7Qj+4C4dnej11uqkXMYVtx/hvXk2KUvNed4aMpcweZd9/d/'
    b'//efbQ5x5Bd51jqKC6sOYj5KU4k9WaJXp26gpQ2V5aexQdf057wp95bzJJy0/SG4hrSBDmIedi'
    b'ZOmA7iPqgP5DqG0M690oN9l3uvnBrEH2/O8cldchXHd9QKmpM81YIHMEROqDrKCBUCGU8FEipV'
    b'0SN65blZ1myck9TvsaW/LSfHHCdtfwjaCrRXhpSlfcnTAapjiD/6CkuOkaFOUcLPN+dYfCivHD'
    b'0DV/KJT3ziYlvodA+XE3ezE+bGT2r+nDNhaI2dRs/8ObJtr775KYkGl6X6S9Bf7RNwjHyx4qQ4'
    b'zmi8k5J95jhsep0CzGOPKNif0Ho958i47WpcRs4huzQnx2bngBNp74tf/OL0TOKVz0kunSCVdB'
    b'oUgGJVhEo23gulppkXeaNNt2YzZp1DNm+vTc3LkyPXcMh4PU6rH2GOzrM6BJBHPG1JqHNA73kj'
    b'naIXSnWK6hwl3PTMUTm6ow7gS1/60sPNAI94FYStjlJPFRWqYuYcxLjkZqgb45CNcpqby7629I'
    b'lOt9Svdat+YOua6IM2qfd0DCAv7YWkHQ11DEjnAG+p7Acy7r4S0gvO8anmHI9OGQdyXHsH0JyE'
    b'55GnNGZ1jC3PJKBSVHQaBjQOafMkjV83Qk2v4ZA2I+xrS59Xw0F6bYD8nu6NY0frINrRsHdqZG'
    b'h5OkWiM9Rw4BwXm3Mc+4TgVvqaOICm9PPNUZ5rBr3VkwRcRCWdZuQgKl4nQWDOQZK6EdZutFG9'
    b'Ne2zjnHnuHb81N9Sm175nE5gqU/b136q3rETfRGa1jlMj04M49oajGcebHSMl2+99dY72viL/w'
    b'Rcw7wmD+Dpp5/mN6cffiP1xmLSICOHSVSQhjjUQXrMbQ7LRnXm2krWWVM/0TG2tOvVXdKJbXr1'
    b'qo5BPVfJDW3avHpaQM8xDCHj0nOOgWPAo+3UmH3z4Va27a6VfPnLX769GYGXgs9jjDS8xhk5ik'
    b'pC4UJcJ4Geg2R8hGPLKG1If1mn1l8iT4I1rLl4VHpzWtKD1Ho9pwB1X/WOrcw3Dekc1UGAetY1'
    b'7NFzDug4CKcFt1SXp4xTZJ0mD+QrX/nKY82AD2pEQxc6t+FQuGgEMV4Nlm1G5Jh1/N585uovYf'
    b'2ldoecHCehtylTf6lPhPqEqXfSeWu8dCsFZ+AYBCd6lWqJM3UQeOWVV87/wz/8w0ster5uhDUb'
    b'A0NAz0FqmWnDCvk5lvHR+LV8VG+Jpf7dAEv0dAH1pKK8d3plO/pKPWWaeqYR0zqKm3vkFEI8HW'
    b'HJOVIPxDONMxTHeO3mm2++sOYNhyehv5POgJdeeunBf/3Xf+VEObLhRptnDg2NsaCmDSuj/NEc'
    b'cp5z4VZO2n6JpfUTjgS2OARU5xg5Qk3XC4Npw+IQ+/CGG2546JZbbul+ycJp09fkGcJtVwuO3X'
    b'atwbrVoBmHtQ4joznUOY7CtfTabe0DltaT+si66IXxLE/RKYwDG3rkFLDkGNUhknSO6hiAM+gQ'
    b'sIuf6e1Uj3lNnyE4SjPG3lFGjDaTxqxx0MDVUSqjfHG8pVBqujJqd1JSD0LcTW96VI64mdc4hG'
    b'x1jHQAqI5RT4pwkCvuGDK/Q64AX/3qV6cThfghG0ej6wxQHcNNUOnlJaP51Py68Wt4mtBnrqsX'
    b'AvEqmQ9bnaKWnZZjAM4QDjHR0lfNMeRNjV5lvva1r02veO2SXTQsuPl6hs841DLJONT0WqpD1P'
    b'A06a2lhmC8btp0BphzgJFDSKZrWW7+kYPUkyIc5Ko7hryp0WsEHua///3v88/G82nwHrkBqcvJ'
    b'QZ63DpabFuO1/6X0iOoII8cY5a8dh3pZd3TFljlngKU0zDnBEr2TAgaO8Vp7+P7UlXr4Xss6y1'
    b'wFeHm4OQv/bJy+UaVHbrjcPHUjrUlnWNm6MUbUjSJb+q+bfkRvs48cgg2aZdUpmPfSHOvaek6h'
    b'Q8guffmmm266+P73v/9MX649lP6OuMZ45plnuPV6pG3g82/kvAEOkpu7bnRDqPFRWbLVMerm5S'
    b'styTM0r7J201fY1HVzJ738mtdb49p1j5xi4Ah7Whpn4J2219Rp0aO/M65hnn322SPv9XJz1xDm'
    b'4qMyGW2S3My58U+TpY3fY85Jal9LDlDLqyNAL09H6DjELnb675U6a47vjLcI7fQ4/9xzz326be'
    b'69swCb3ZPFjZ9x6KWTOec4xCnqJnXDjDb1HL02tf851p4OPdIpqhOAec5ll3701ltv/UzT8TV5'
    b'C7XEW9ZBKu1kwVE+3WS6DUsnMF7TknGY20SHnBhLG3jLBhfrbm2Xa+udAj12G/0ImVfKX2sXkc'
    b'/cdtttJ/qg0rXC28ZBkuYst7ZNzzPL9O0rOkT9/4jU9Fk4yBxbHCTrbHWOOXpOIKOyyOf7CXim'
    b'6H5D+luZt6WDVL7xjW880Jzg/zTZO0yGkumlW5EtjrJ2E29xlB62s4+5TV+Zq9spwyH+vDnEiT'
    b'+xd63zjnCQyne+853zr7zyysPNIf53S3LaTPkjx+k5y5bnkUM2/qFOMmLJWWbKORX+4oYbbniU'
    b'r6F9I+udwzvSQXr84Ac/OP/tb3+bE4aT5vZ0EuMnvfWqV/VMpxMZnhUzznC5Of2f//Zv//bjZ/'
    b'028rcK1x1kBc8///yfNSf5X00eaMlbyes5kCzdnkk6ladRDU9C9hVwInBr9DftQXrV99O+k7nu'
    b'IKfASy+99MCPfvQj/uP/e004fYhPb5VReqx1pJVwxecjp8j/a47Bb1+87Z8RrnOd61znOte5Fj'
    b'l37v8DZpJYginxCnYAAAAASUVORK5CYII=')
