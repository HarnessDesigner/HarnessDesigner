import wx
import wx.dataview as dv


class IntSpinRenderer(dv.DataViewCustomRenderer):

    def __init__(self, min_val, max_val, *args, allow_none=False, **kw):
        self.min_val = min_val
        self.max_val = max_val
        self.allow_none = allow_none
        self.old_menu_value = min_val - 1
        self.new_menu_value = min_val - 1

        dv.DataViewCustomRenderer.__init__(self, *args, **kw)
        self.value = None
        self.EnableEllipsize(wx.ELLIPSIZE_NONE)

    def SetValue(self, value):
        if value in ('None', None) and self.allow_none:
            self.value = None
        elif value in ('None', None):
            raise RuntimeError('sanity check ' + self.__class__.__name__)
        else:
            self.value = int(value)

        return True

    def GetValue(self):
        if self.value is None and not self.allow_none:
            raise RuntimeError('sanity check ' + self.__class__.__name__)

        if self.value is None:
            return None

        return int(self.value)

    def GetSize(self):
        if self.allow_none:
            size = self.GetTextExtent('None')
        else:
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

    def CreateEditorCtrl(self, parent, labelRect, value):
        if self.allow_none:

            # TODO: Fix bug where cannot change back to None from an integer value
            class Panel(wx.Panel):
                def __init__(self, p, val, min_val, max_val, size, pos):
                    wx.Panel.__init__(self, p, wx.ID_ANY, size=size, pos=pos, style=wx.BORDER_NONE)
                    self.value = val
                    self.min_val = min_val

                    self.spin_ctrl = wx.SpinCtrl(self, wx.ID_ANY, value=str(min_val), initial=min_val, min=min_val, max=max_val, size=size, pos=(0, 0))
                    self.text_ctrl = wx.TextCtrl(self, wx.ID_ANY, value='None', style=wx.TE_READONLY, size=size, pos=(0, 0))

                    if val in ('None', None):
                        self.spin_ctrl.SetValue(min_val)
                        self.spin_ctrl.Show(False)
                        self.text_ctrl.Show(True)
                    else:
                        self.spin_ctrl.SetValue(val)
                        self.spin_ctrl.Show(True)
                        self.text_ctrl.Show(False)

                    self.none_menu_id = wx.NewIdRef()
                    self.int_menu_id = wx.NewIdRef()
                    self.spin_ctrl.Bind(wx.EVT_RIGHT_DOWN, self.on_context)
                    self.text_ctrl.Bind(wx.EVT_RIGHT_DOWN, self.on_context)
                    self.Bind(wx.EVT_MENU, self.on_none_menu, self.none_menu_id)
                    self.Bind(wx.EVT_MENU, self.on_int_menu, self.int_menu_id)

                def on_none_menu(self, evt):
                    self.spin_ctrl.Show(False)
                    self.text_ctrl.Show(True)
                    self.value = None
                    evt.Skip()

                def on_int_menu(self, evt):
                    self.spin_ctrl.Show(True)
                    self.text_ctrl.Show(False)
                    self.value = self.spin_ctrl.GetValue()
                    evt.Skip()

                def on_context(self, evt):
                    x, y = evt.GetPosition()
                    menu = wx.Menu()

                    if self.spin_ctrl.IsShown():
                        menu.Append(self.none_menu_id, 'Set as None')
                    else:
                        menu.Append(self.int_menu_id, 'Set as Integer')

                    self.PopupMenu(menu, x, y)

                def GetValue(self):
                    if self.value is None:
                        return None
                    else:
                        return self.spin_ctrl.GetValue()

            ctrl = Panel(parent, value, self.min_val, self.max_val, labelRect.GetSize(), labelRect.GetPosition())

        else:
            ctrl = wx.SpinCtrl(parent, value=str(value), initial=int(value),
                               max=self.max_val, min=self.min_val,
                               pos=labelRect.GetPosition(), size=labelRect.GetSize())

        return ctrl

    def GetValueFromEditorCtrl(self, editor):
        value = editor.GetValue()
        return value

    def LeftClick(self, pos, cellRect, model, item, col):
        return False

    def Activate(self, cellRect, model, item, col):
        return False
