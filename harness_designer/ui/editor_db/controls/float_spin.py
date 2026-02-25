
import wx
import wx.dataview as dv


class FloatSpinRenderer(dv.DataViewCustomRenderer):
    def __init__(self, increment, min_val, max_val, *args, **kw):
        self.increment = increment
        self.min_val = min_val
        self.max_val = max_val

        dv.DataViewCustomRenderer.__init__(self, *args, **kw)
        self.value = None
        self.EnableEllipsize(wx.ELLIPSIZE_NONE)

    def SetValue(self, value):
        self.value = float(value)
        return True

    def GetValue(self):
        return float(self.value)

    def GetSize(self):
        size = self.GetTextExtent(str(self.max_val))
        size += (15, 2)
        return size

    def Render(self, rect, dc, state):
        # if not state & dv.DATAVIEW_CELL_SELECTED:
        #     dc.SetBrush(wx.Brush('#ffd0d0'))
        #     dc.SetPen(wx.TRANSPARENT_PEN)
        #     rect.Deflate(1, 1)
        #     dc.DrawRoundedRectangle(rect, 2)

        value = str(self.value)
        self.RenderText(value, 0, rect, dc, state)
        return True

    def ActivateCell(self, rect, model, item, col, mouseEvent):
        return False

    def HasEditorCtrl(self):
        return True

    def CreateEditorCtrl(self, parent, labelRect: wx.Rect, value):
        ctrl = wx.SpinCtrlDouble(parent, value=str(value), initial=float(value),
                                 inc=self.increment, max=self.max_val, min=self.min_val,
                                 pos=labelRect.GetPosition(), size=labelRect.GetSize())
        return ctrl

    def GetValueFromEditorCtrl(self, editor: wx.SpinCtrlDouble):
        value = editor.GetValue()
        return value

    def LeftClick(self, pos, cellRect, model, item, col):
        return False

    def Activate(self, cellRect, model, item, col):
        return False
