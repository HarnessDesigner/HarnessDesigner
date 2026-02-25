import wx
from wx.lib.agw.aui.aui_constants import *


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
