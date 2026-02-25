from typing import TYPE_CHECKING

import wx

from wx import aui
from ..widgets import aui_toolbar
from .. import image as _image
import wxOpenGL
from ..geometry import point as _point
from ..wrappers.decimal import Decimal as _decimal

from . import axis_indicators as _axis_indicators


if TYPE_CHECKING:
    from .. import ui as _ui
    from .. import objects as _objects


class Editor3D(wx.Panel):

    ID_POINTER = wx.NewIdRef()
    ID_TRANSITION = wx.NewIdRef()
    ID_CONNECTOR = wx.NewIdRef()
    ID_TERMINAL = wx.NewIdRef()
    ID_SEAL = wx.NewIdRef()
    ID_WIRE = wx.NewIdRef()
    ID_SPLICE = wx.NewIdRef()
    ID_BUNDLE_COVER = wx.NewIdRef()
    ID_TPA_LOCK = wx.NewIdRef()
    ID_CPA_LOCK = wx.NewIdRef()

    ID_MOVE = wx.NewIdRef()
    ID_SET_ANGLE = wx.NewIdRef()

    def __init__(self, parent, mainframe: "_ui.MainFrame"):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.mainframe = mainframe

        self.mode = self.ID_POINTER

        self.global_db = self.mainframe.global_db

        self._selected_obj: "_objects.ObjectBase" = None
        self._mouse_click_location = None
        self.bundle_dialog = None
        self._right_motion = None

        self.editor3d_toolbar = aui_toolbar.AuiToolBar(self.mainframe,
                                                       style=aui.AUI_TB_GRIPPER | aui.AUI_TB_TEXT)

        self.editor3d_toolbar.SetToolBitmapSize((32, 32))

        pointer = _image.icons.pointer.resize(32, 32)
        transition = _image.icons.transition.resize(32, 32)
        connector = _image.icons.connector.resize(32, 32)
        terminal = _image.icons.terminal.resize(32, 32)
        seal = _image.icons.seal.resize(32, 32)
        wire = _image.icons.wire.resize(32, 32)
        splice = _image.icons.splice.resize(32, 32)
        bundle_cover = _image.icons.bundle_cover.resize(32, 32)
        tpa_lock = _image.icons.tpa_lock.resize(32, 32)
        cpa_lock = _image.icons.cpa_lock.resize(32, 32)

        btns = [
            (self.ID_POINTER, pointer, 'Pointer'),
            (self.ID_TRANSITION, transition, 'Transition'),
            (self.ID_CONNECTOR, connector, 'Connector'),
            (self.ID_TERMINAL, terminal, 'Terminal'),
            (self.ID_SEAL, seal, 'Seal'),
            (self.ID_WIRE, wire, 'Wire'),
            (self.ID_SPLICE, splice, 'Splice'),
            (self.ID_BUNDLE_COVER, bundle_cover, 'Bundle'),
            (self.ID_TPA_LOCK, tpa_lock, 'TPA'),
            (self.ID_CPA_LOCK, cpa_lock, 'CPA')
        ]

        self.buttons = []

        for id, img, label in btns:  # NOQA
            item = self.editor3d_toolbar.AddTool(id, label, img.bitmap,
                                                 img.disabled_bitmap, wx.ITEM_RADIO)
            self.buttons.append(item)
            self.Bind(wx.EVT_MENU, self.on_tool, id=id)

        # self.preview_pane = PreviewPane(self.mainframe)

        self.editor3d_toolbar.Realize()
        self.editor3d_toolbar_pane = (
            aui.AuiPaneInfo()
            .Floatable(True)
            .Top()
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('editor_toolbar')
            .CaptionVisible(False)
            .PaneBorder(True)
            .CloseButton(False)
            .MaximizeButton(False)
            .MinimizeButton(False)
            .PinButton(False)
            .DestroyOnClose(False)
            .Show()
            .ToolbarPane()
        )

        self.mainframe.manager.AddPane(self.editor3d_toolbar,
                                       self.editor3d_toolbar_pane)
        self.mainframe.manager.Update()

        # v_sizer = wx.BoxSizer(wx.VERTICAL)
        # h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # h_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        # v_sizer.Add(h_sizer, 1, wx.EXPAND)
        # self.SetSizer(v_sizer)

        self.objects = []

        def _do():
            self.buttons[0].SetState(aui.AUI_BUTTON_STATE_CHECKED)

        wx.CallAfter(_do)

        self.panel = wx.Panel(self, wx.ID_ANY)  # , size=view_size.as_int[:-1], pos=(0, 0))
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.panel, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        self.SetSizer(vsizer)

        self._overlay_init = True

        self.axis_overlay = _axis_indicators.Overlay(self.panel)

        self.canvas = wxOpenGL.Canvas(self)

        self.canvas.Bind(wxOpenGL.EVT_GL_OBJECT_SELECTED, self.on_obj_selected)
        self.canvas.Bind(wxOpenGL.EVT_GL_OBJECT_UNSELECTED, self.on_obj_unselected)
        self.canvas.Bind(wxOpenGL.EVT_GL_OBJECT_ACTIVATED, self.on_obj_activated)
        self.canvas.Bind(wxOpenGL.EVT_GL_OBJECT_RIGHT_CLICK, self.on_obj_right_click)
        self.canvas.Bind(wxOpenGL.EVT_GL_OBJECT_RIGHT_DCLICK, self.on_obj_right_dclick)
        self.canvas.Bind(wxOpenGL.EVT_GL_OBJECT_MIDDLE_CLICK, self.on_obj_middle_click)
        self.canvas.Bind(wxOpenGL.EVT_GL_OBJECT_MIDDLE_DCLICK, self.on_obj_middle_dclick)
        self.canvas.Bind(wxOpenGL.EVT_GL_OBJECT_AUX1_CLICK, self.on_obj_aux1_click)
        self.canvas.Bind(wxOpenGL.EVT_GL_OBJECT_AUX1_DCLICK, self.on_obj_aux1_dclick)
        self.canvas.Bind(wxOpenGL.EVT_GL_OBJECT_AUX2_CLICK, self.on_obj_aux2_click)
        self.canvas.Bind(wxOpenGL.EVT_GL_OBJECT_AUX2_DCLICK, self.on_obj_aux2_dclick)

        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def on_obj_selected(self, evt: wxOpenGL.GLObjectEvent):
        evt.Skip()

    def on_obj_unselected(self, evt: wxOpenGL.GLObjectEvent):
        evt.Skip()

    def on_obj_activated(self, evt: wxOpenGL.GLObjectEvent):
        evt.Skip()

    def on_obj_right_click(self, evt: wxOpenGL.GLObjectEvent):
        evt.Skip()

    def on_obj_right_dclick(self, evt: wxOpenGL.GLObjectEvent):
        evt.Skip()

    def on_obj_middle_click(self, evt: wxOpenGL.GLObjectEvent):
        evt.Skip()

    def on_obj_middle_dclick(self, evt: wxOpenGL.GLObjectEvent):
        evt.Skip()

    def on_obj_aux1_click(self, evt: wxOpenGL.GLObjectEvent):
        evt.Skip()

    def on_obj_aux1_dclick(self, evt: wxOpenGL.GLObjectEvent):
        evt.Skip()

    def on_obj_aux2_click(self, evt: wxOpenGL.GLObjectEvent):
        evt.Skip()

    def on_obj_aux2_dclick(self, evt: wxOpenGL.GLObjectEvent):
        evt.Skip()

    def set_selected_object(self, obj: "_objects.ObjectBase"):
        self._selected_obj = obj

    def get_selected_obj(self) -> "_objects.ObjectBase":
        return self._selected_obj

    def on_size(self, evt):
        if self._overlay_init:
            self._overlay_init = False
            evt.Skip()
            return

        w, h = evt.GetSize()

        view_size = self.canvas.GetViewSize()

        size = _point.Point(_decimal(w), _decimal(h))
        pos = (size - view_size) / _decimal(2.0)

        self.canvas.Move(pos.as_int[:-1])

        x1, y1 = self.axis_overlay.GetPosition()
        aw, ah = self.axis_overlay.GetSize()

        x2 = x1 + aw
        y2 = y1 + ah

        if x1 < 0:
            x = 0
        elif x2 > w:
            x = w - aw
        else:
            x = x1

        if y1 < 0:
            y = 0
        elif y2 > ah:
            y = h - ah
        else:
            y = y1

        self.axis_overlay.Move((x, y))
        evt.Skip()

    def on_erase_background(self, _):
        pass

    def on_tool(self, evt):
        self.mode = evt.GetId()
