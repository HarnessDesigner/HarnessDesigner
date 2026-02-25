import wx
import wx.dataview as dv

from wx.lib import popupctl
from wx.lib import scrolledpanel
from wx import aui


class PopupContent(scrolledpanel.ScrolledPanel):

    def __init__(self, parent, size, choices):
        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY, size=size)

        self.ctrls = []

        sizer = wx.BoxSizer(wx.VERTICAL)

        def _add(item, tt, sel):
            ctrl = wx.CheckBox(self, wx.ID_ANY, label=item)
            if sel:
                ctrl.SetValue(True)

            ctrl.SetToolTip(tt)

            self.ctrls.append(ctrl)
            sizer.Add(ctrl, 0, wx.ALL, 3)

        for _, name, tooltip, is_selected in choices:
            _add(name, tooltip, is_selected)

        self.SetSizer(sizer)
        self.SetupScrolling()

    def GetValue(self):
        res = []
        for ctrl in self.ctrls:
            if ctrl.GetValue():
                res.append(ctrl.GetLabel())

        return res


class ListChoice(popupctl.PopupControl):

    def __init__(self, parent, pos, size):
        wx.Control.__init__(self, parent=parent, pos=pos, size=size)

        self.textCtrl = wx.TextCtrl(self, wx.ID_ANY, '', pos=(0, 0), style=wx.TE_READONLY)
        self.bCtrl = popupctl.PopButton(self, wx.ID_ANY, style=wx.BORDER_NONE)
        self.pop = None
        self.content = None
        self.align = wx.ALIGN_CENTER

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.bCtrl.Bind(wx.EVT_BUTTON, self.OnButton, self.bCtrl)
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        self.Bind(wx.EVT_MOVE, self.on_move)

        manager = aui.AuiManager.GetManager(parent)
        frame = manager.GetManagedWindow()
        frame.Bind(wx.EVT_MOVE, self.on_move)

        self.SetInitialSize(size)
        self.SendSizeEvent()
        self.value = []

    def GetValue(self):
        return self.value

    def SetChoices(self, choices):
        w = self.GetSize()[0]

        h = self.GetTextExtent('Testing')[1]
        h *= len(choices)

        parent = self.GetParent()
        p_h = parent.GetSize()[1]
        y = self.GetPosition()[1]

        p_h -= y
        if p_h < h:
            h = p_h

        print('SetChoices', w, h)
        self.content = PopupContent(self, (w, h), choices)

        self.value = self.content.GetValue()

        value = str(self.value).replace('"', "'")
        self.textCtrl.SetValue(value[1:-1].replace("'", ''))

        self.content.Bind(wx.EVT_CHECKBOX, self.on_check)
        self.content.Show(False)

        def _on_kill_focus(e):
            def _do():
                self.pop.Hide()
                self.content.Show(False)
                self.content.Reparent(self)
                self.pop.Destroy()
                self.pop = None

            wx.CallAfter(_do)

            e.Skip()

        self.content.Bind(wx.EVT_KILL_FOCUS, _on_kill_focus)

    def on_check(self, evt: wx.CommandEvent):
        obj = evt.GetEventObject()

        if evt.IsChecked():
            self.value.append(obj.GetLabel())  # NOQA
            value = str(self.value).replace('"', "'")
            self.textCtrl.SetValue(value[1:-1].replace("'", ''))
        else:
            label = obj.GetLabel()  # NOQA
            if label in self.value:
                self.value.remove(label)
                value = str(self.value).replace('"', "'")
                self.textCtrl.SetValue(value[1:-1].replace("'", ''))

        evt.Skip()

    def on_move(self, evt):
        evt.Skip()

        if self.pop is not None:
            w = self.GetSize()[0]

            s_h = self.GetTextExtent('Testing')[1]
            h = s_h * len(self.content.ctrls)

            parent = self.GetParent()
            p_h = parent.GetSize()[1]
            e_x, e_y = evt.GetPosition()
            c_w, c_h = self.GetParent().GetClientSize()

            p_h -= e_y

            if p_h < h:
                h = p_h
            elif e_y < 0:
                h += e_y

            print(h)

            if e_x < 0 or e_x > c_w or h < s_h:
                self.pop.Hide()
                return

            self.content.SetSize(w, h)
            self.pop.win.SetClientSize(self.content.GetSize())
            self.pop.SetSize(self.pop.win.GetSize())

            pos = self.pop.ctrl.ClientToScreen((0, 0))
            dSize = wx.GetDisplaySize()
            selfSize = self.pop.GetSize()
            tcSize = self.pop.ctrl.GetSize()

            pos.x -= (selfSize.width - tcSize.width) // 2
            pos.y += tcSize.height
            if pos.y + selfSize.height > dSize.height:
                pos.y = dSize.height - selfSize.height
            if pos.y < 0:
                self.pop.Hide()
                return

            cc_x, cc_y = self.GetParent().ScreenToClient(pos)
            if cc_y < 0:
                pos.y -= cc_y

            self.pop.Move(pos)
            self.pop.ctrl.FormatContent()

            if not self.pop.IsShown():
                self.pop.Show()

    def OnButton(self, evt):
        if not self.pop:
            if self.content:
                self.pop = popupctl.PopupDialog(self)
                self.pop.SetContent(self.content)

                pos = self.pop.ctrl.ClientToScreen((0, 0))
                dSize = wx.GetDisplaySize()
                selfSize = self.pop.GetSize()
                tcSize = self.pop.ctrl.GetSize()

                pos.x -= (selfSize.width - tcSize.width) // 2

                pos.y += tcSize.height
                if pos.y + selfSize.height > dSize.height:
                    pos.y = dSize.height - selfSize.height
                if pos.y < 0:
                    pos.y = 0

                self.pop.Move(pos)
                self.pop.ctrl.FormatContent()
                self.pop.Show()
            else:
                raise RuntimeError('sanity check')
        elif self.pop:
            self.pop.Hide()
            self.content.Show(False)
            self.content.Reparent(self)
            self.pop.Destroy()
            self.pop = None

        evt.Skip()


class ListRendererBase(dv.DataViewCustomRenderer):
    __table_name__ = ''
    __field_name__ = ''
    __target_table_name__ = ''
    __target_field_name__ = ''
    __tooltip_field_name__ = ''
    __target_type__ = ''

    def __init__(self, table, *args, **kwargs):
        dv.DataViewCustomRenderer.__init__(self, *args, **kwargs)
        self.table = table

        cmd = f'SELECT id, {self.__target_field_name__}, {self.__tooltip_field_name__} FROM {self.__target_table_name__} ORDER BY id ASC;'
        table.execute(cmd)
        self.choices = table.fetchall()
        self.value = '[]'
        self.EnableEllipsize(wx.ELLIPSIZE_END)

    def SetValue(self, value):
        self.value = value
        return True

    def GetValue(self):
        return self.value

    def GetSize(self):
        size = self.GetTextExtent(self.value)
        size += (2, 2)
        return size

    def Render(self, rect, dc, state):
        # if not state & dv.DATAVIEW_CELL_SELECTED:
        #     dc.SetBrush(wx.Brush('#ffd0d0'))
        #     dc.SetPen(wx.TRANSPARENT_PEN)
        #     rect.Deflate(1, 1)
        #     dc.DrawRoundedRectangle(rect, 2)

        self.RenderText(self.value[1:-1].replace("'", ''), 0, rect, dc, state)
        return True

    def ActivateCell(self, rect, model, item, col, mouseEvent):
        return False

    def HasEditorCtrl(self):
        return True

    def CreateEditorCtrl(self, parent, labelRect, value):
        pos = labelRect.GetPosition()
        size = labelRect.GetSize()
        ctrl = ListChoice(parent, pos=pos, size=size)
        value = eval(value)
        value = [item.strip() for item in value]
        print(value)
        print(self.choices)
        print([item + (item[1].strip() in value,) for item in self.choices])

        ctrl.SetChoices([item + (item[1].strip() in value,) for item in self.choices])

        return ctrl

    def GetValueFromEditorCtrl(self, editor: ListChoice):
        self.value = str(editor.GetValue())
        return self.value

    def LeftClick(self, pos, cellRect, model, item, col):
        return False

    def Activate(self, cellRect, model, item, col):
        # TODO: add new dialog
        return False


class AdhesiveListRenderer(ListRendererBase):
    __target_table_name__ = 'adhesives'
    __target_field_name__ = 'code'
    __tooltip_field_name__ = 'description'
    __target_type__ = 'id'


class AccessoryListRenderer(ListRendererBase):
    __target_table_name__ = 'accessories'
    __target_field_name__ = 'part_number'
    __tooltip_field_name__ = 'description'
    __target_type__ = 'str'


class CPAListRenderer(ListRendererBase):
    __target_table_name__ = 'cpa_locks'
    __target_field_name__ = 'part_number'
    __tooltip_field_name__ = 'description'
    __target_type__ = 'str'


class TPAListRenderer(ListRendererBase):
    __target_table_name__ = 'tpa_locks'
    __target_field_name__ = 'part_number'
    __tooltip_field_name__ = 'description'
    __target_type__ = 'str'


class CoverListRenderer(ListRendererBase):
    __target_table_name__ = 'covers'
    __target_field_name__ = 'part_number'
    __tooltip_field_name__ = 'description'
    __target_type__ = 'str'


class TerminalListRenderer(ListRendererBase):
    __target_table_name__ = 'terminals'
    __target_field_name__ = 'part_number'
    __tooltip_field_name__ = 'description'
    __target_type__ = 'str'


class SealListRenderer(ListRendererBase):
    __target_table_name__ = 'seals'
    __target_field_name__ = 'part_number'
    __tooltip_field_name__ = 'description'
    __target_type__ = 'str'


class HousingListRenderer(ListRendererBase):
    __target_table_name__ = 'housings'
    __target_field_name__ = 'part_number'
    __tooltip_field_name__ = 'description'
    __target_type__ = 'str'


class TerminalSizeListRenderer(dv.DataViewCustomRenderer):

    def __init__(self, *args, **kwargs):
        dv.DataViewCustomRenderer.__init__(self, *args, **kwargs)
        self.value = '[]'
        self.ctrls = []
        self.popup_window = None
        self.EnableEllipsize(wx.ELLIPSIZE_END)

    def SetValue(self, value):
        self.value = value
        return True

    def GetValue(self):
        return self.value

    def GetSize(self):
        size = self.GetTextExtent(self.value[1:-1])
        size += (2, 2)
        return size

    def Render(self, rect, dc, state):
        if not state & dv.DATAVIEW_CELL_SELECTED:
            dc.SetBrush(wx.Brush('#ffd0d0'))
            dc.SetPen(wx.TRANSPARENT_PEN)
            rect.Deflate(1, 1)
            dc.DrawRoundedRectangle(rect, 2)

        self.RenderText(self.value[1:-1], 0, rect, dc, state)
        return True

    def ActivateCell(self, rect, model, item, col, mouseEvent):
        return False

    def HasEditorCtrl(self):
        return True

    def CreateEditorCtrl(self, parent, labelRect, value):
        ctrl = wx.TextCtrl(parent, wx.ID_ANY, value=value[1:-1],
                           pos=labelRect.GetPosition(), size=labelRect.GetSize())
        return ctrl

    def GetValueFromEditorCtrl(self, editor):
        return self.value

    def LeftClick(self, pos, cellRect, model, item, col):
        return False

    def Activate(self, cellRect, model, item, col):
        # TODO: add new dialog
        return False
