from typing import TYPE_CHECKING

from wx import aui
import wx

from ...gl import canvas3d as _canvas3d

from ... import image as _image


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


'''
_canvas3d.EVT_GL_OBJECT_SELECTED
_canvas3d.EVT_GL_OBJECT_UNSELECTED
_canvas3d.EVT_GL_OBJECT_ACTIVATED
_canvas3d.EVT_GL_OBJECT_RIGHT_CLICK
_canvas3d.EVT_GL_OBJECT_RIGHT_DCLICK
_canvas3d.EVT_GL_OBJECT_MIDDLE_CLICK
_canvas3d.EVT_GL_OBJECT_MIDDLE_DCLICK
_canvas3d.EVT_GL_OBJECT_AUX1_CLICK
_canvas3d.EVT_GL_OBJECT_AUX1_DCLICK
_canvas3d.EVT_GL_OBJECT_AUX2_CLICK
_canvas3d.EVT_GL_OBJECT_AUX2_DCLICK
_canvas3d.EVT_GL_OBJECT_DRAG
_canvas3d.EVT_GL_LEFT_DOWN
_canvas3d.EVT_GL_LEFT_UP
_canvas3d.EVT_GL_LEFT_DCLICK
_canvas3d.EVT_GL_RIGHT_DOWN
_canvas3d.EVT_GL_RIGHT_UP
_canvas3d.EVT_GL_RIGHT_DCLICK
_canvas3d.EVT_GL_MIDDLE_DOWN
_canvas3d.EVT_GL_MIDDLE_UP
_canvas3d.EVT_GL_MIDDLE_DCLICK
_canvas3d.EVT_GL_AUX1_DOWN
_canvas3d.EVT_GL_AUX1_UP
_canvas3d.EVT_GL_AUX1_DCLICK
_canvas3d.EVT_GL_AUX2_DOWN
_canvas3d.EVT_GL_AUX2_UP
_canvas3d.EVT_GL_AUX2_DCLICK
'''

ID_SELECT = wx.NewIdRef()
ID_CONNECTOR = wx.NewIdRef()
ID_TERMINAL = wx.NewIdRef()
ID_WIRE = wx.NewIdRef()
ID_SPLICE = wx.NewIdRef()
ID_NOTE = wx.NewIdRef()

ID_ZOOM_IN = wx.NewIdRef()
ID_ZOOM_OUT = wx.NewIdRef()

ID_CIRCLE = wx.NewIdRef()
ID_SQUARE = wx.NewIdRef()

ID_TRANSITION = wx.NewIdRef()
ID_SEAL = wx.NewIdRef()
ID_BUNDLE_COVER = wx.NewIdRef()
ID_TPA_LOCK = wx.NewIdRef()
ID_CPA_LOCK = wx.NewIdRef()


class EditorToolbar(aui.AuiPaneInfo):

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.toolbar = aui.AuiToolBar(mainframe, style=aui.AUI_TB_GRIPPER)
        self.mainframe = mainframe
        self.manager = mainframe.manager
        self._mode = None

        aui.AuiPaneInfo.__init__(self)

        self.Top()
        self.Floatable(True)
        self.Gripper(True)
        self.Resizable(True)
        self.Movable(True)
        self.Name('editor_toolbar')
        self.CaptionVisible(False)
        self.PaneBorder(True)
        self.CloseButton(False)
        self.MaximizeButton(False)
        self.MinimizeButton(False)
        self.PinButton(False)
        self.DestroyOnClose(False)
        self.ToolbarPane()

        self.toolbar.SetToolBitmapSize((32, 32))

        select_object = _image.icons.select_object.resize(32, 32)
        connector = _image.icons.connector.resize(32, 32)
        terminal = _image.icons.terminal.resize(32, 32)
        wire = _image.icons.wire.resize(32, 32)
        splice = _image.icons.splice.resize(32, 32)
        note = _image.icons.notes.resize(32, 32)

        zoom_in = _image.icons.zoom_in.resize(32, 32)
        zoom_out = _image.icons.zoom_out.resize(32, 32)
        circle = _image.icons.circle.resize(32, 32)
        square = _image.icons.square.resize(32, 32)
        transition = _image.icons.transition.resize(32, 32)

        seal = _image.icons.seal.resize(32, 32)
        bundle_cover = _image.icons.bundle_cover.resize(32, 32)
        tpa_lock = _image.icons.tpa_lock.resize(32, 32)
        cpa_lock = _image.icons.cpa_lock.resize(32, 32)

        self._select = self.toolbar.AddTool(toolId=ID_SELECT, label='Select', bitmap=select_object.bitmap,
                                            short_help_string='Select', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_SELECT)

        self._housing = self.toolbar.AddTool(toolId=ID_CONNECTOR, label='Add Housing', bitmap=connector.bitmap,
                                             short_help_string='Add Housing', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_CONNECTOR)

        self._terminal = self.toolbar.AddTool(toolId=ID_TERMINAL, label='Add Terminal', bitmap=terminal.bitmap,
                                              short_help_string='Add Terminal', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_TERMINAL)

        self._wire = self.toolbar.AddTool(toolId=ID_WIRE, label='Add Wire', bitmap=wire.bitmap,
                                          short_help_string='Add Wire', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_WIRE)

        self._splice = self.toolbar.AddTool(toolId=ID_SPLICE, label='Add Splice', bitmap=splice.bitmap,
                                            short_help_string='Add Splice', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_SPLICE)

        self._note = self.toolbar.AddTool(toolId=ID_NOTE, label='Add Note', bitmap=note.bitmap,
                                          short_help_string='Add Note', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_NOTE)

        self._zoom_in = self.toolbar.AddTool(toolId=ID_ZOOM_IN, label='Zoom +', bitmap=zoom_in.bitmap,
                                             short_help_string='Zoom +', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_ZOOM_IN)

        self._zoom_out = self.toolbar.AddTool(toolId=ID_ZOOM_OUT, label='Zoom -', bitmap=zoom_out.bitmap,
                                              short_help_string='Zoom -', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_ZOOM_OUT)

        self._draw_circle = self.toolbar.AddTool(toolId=ID_CIRCLE, label='Draw Circle', bitmap=circle.bitmap,
                                                 short_help_string='Draw Circle', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_CIRCLE)

        self._draw_square = self.toolbar.AddTool(toolId=ID_SQUARE, label='Draw Square', bitmap=square.bitmap,
                                                 short_help_string='Draw Square', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_SQUARE)

        self._transition = self.toolbar.AddTool(toolId=ID_TRANSITION, label='Add Transition', bitmap=transition.bitmap,
                                                short_help_string='Add Transition', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_TRANSITION)

        self._seal = self.toolbar.AddTool(toolId=ID_SEAL, label='Add Seal', bitmap=seal.bitmap,
                                          short_help_string='Add Seal', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_SEAL)

        self._bundle = self.toolbar.AddTool(toolId=ID_BUNDLE_COVER, label='Add Bundle', bitmap=bundle_cover.bitmap,
                                            short_help_string='Add Bundle', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_BUNDLE_COVER)

        self._tpa_lock = self.toolbar.AddTool(toolId=ID_TPA_LOCK, label='Add TPA Lock', bitmap=tpa_lock.bitmap,
                                              short_help_string='Add TPA Lock', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_TPA_LOCK)

        self._cpa_lock = self.toolbar.AddTool(toolId=ID_CPA_LOCK, label='Add CPA Lock', bitmap=cpa_lock.bitmap,
                                              short_help_string='Add CPA Lock', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=ID_CPA_LOCK)

        self._cpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._tpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._bundle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._seal.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._transition.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._draw_square.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._draw_circle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._splice.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._terminal.SetState(aui.AUI_BUTTON_STATE_DISABLED)

        self.toolbar.Realize()
        self.manager.AddPane(self.toolbar, self)

        self.Show()
        self.manager.Update()

        self.mainframe.editor3d.Bind(_canvas3d.EVT_GL_OBJECT_SELECTED, self._on_obj_selected)
        self.mainframe.editor3d.Bind(_canvas3d.EVT_GL_OBJECT_UNSELECTED, self._on_obj_unselected)

    def get_mode(self) -> int:
        return self._mode

    def _on_obj_selected(self, evt: _canvas3d.GLObjectEvent):
        from ...objects import housing as _housing
        from ...objects import wire as _wire
        from ...objects import terminal as _terminal
        from ...objects import bundle as _bundle

        obj = evt.GetGLObject()

        if isinstance(obj, _housing.Housing):
            self._cpa_lock.SetState(aui.AUI_BUTTON_STATE_NORMAL)
            self._tpa_lock.SetState(aui.AUI_BUTTON_STATE_NORMAL)
            self._seal.SetState(aui.AUI_BUTTON_STATE_NORMAL)
            self._terminal.SetState(aui.AUI_BUTTON_STATE_NORMAL)

            self._bundle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._transition.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._draw_square.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._draw_circle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._splice.SetState(aui.AUI_BUTTON_STATE_DISABLED)

        elif isinstance(obj, _wire.Wire):
            self._bundle.SetState(aui.AUI_BUTTON_STATE_NORMAL)
            self._splice.SetState(aui.AUI_BUTTON_STATE_NORMAL)

            self._cpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._tpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._seal.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._transition.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._draw_square.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._draw_circle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._terminal.SetState(aui.AUI_BUTTON_STATE_DISABLED)

        elif isinstance(obj, _bundle.Bundle):
            self._transition.SetState(aui.AUI_BUTTON_STATE_NORMAL)

            self._cpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._tpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._bundle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._seal.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._draw_square.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._draw_circle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._splice.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._terminal.SetState(aui.AUI_BUTTON_STATE_DISABLED)

        elif isinstance(obj, _terminal.Terminal):
            self._seal.SetState(aui.AUI_BUTTON_STATE_NORMAL)

            self._cpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._tpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._bundle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._transition.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._draw_square.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._draw_circle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._splice.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._terminal.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        else:
            self._cpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._tpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._bundle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._seal.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._transition.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._draw_square.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._draw_circle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._splice.SetState(aui.AUI_BUTTON_STATE_DISABLED)
            self._terminal.SetState(aui.AUI_BUTTON_STATE_DISABLED)

        self.toolbar.Refresh(False)
        evt.Skip()

    def _on_obj_unselected(self, evt: _canvas3d.GLObjectEvent):
        self._cpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._tpa_lock.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._bundle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._seal.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._transition.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._draw_square.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._draw_circle.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._splice.SetState(aui.AUI_BUTTON_STATE_DISABLED)
        self._terminal.SetState(aui.AUI_BUTTON_STATE_DISABLED)

        self.toolbar.Refresh(False)
        evt.Skip()

    def on_tools(self, evt: wx.MenuEvent):
        self._mode = evt.GetId()
        evt.Skip()

    def Refresh(self, *args, **kwargs):
        self.toolbar.Refresh(*args, **kwargs)

    def Destroy(self):
        self.toolbar.Destroy()


class NoteToolbar(aui.AuiPaneInfo):

    ID_ALIGN_HORIZ_CENTER = wx.NewIdRef()
    ID_ALIGN_HORIZ_LEFT = wx.NewIdRef()
    ID_ALIGN_HORIZ_RIGHT = wx.NewIdRef()

    ID_ALIGN_VERT_CENTER = wx.NewIdRef()
    ID_ALIGN_VERT_TOP = wx.NewIdRef()
    ID_ALIGN_VERT_BOTTOM = wx.NewIdRef()

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.toolbar = aui.AuiToolBar(mainframe, style=aui.AUI_TB_GRIPPER)
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Top()
        self.Floatable(True)
        self.Gripper(True)
        self.Resizable(True)
        self.Movable(True)
        self.Name('note_toolbar')
        self.CaptionVisible(False)
        self.PaneBorder(True)
        self.CloseButton(False)
        self.MaximizeButton(False)
        self.MinimizeButton(False)
        self.PinButton(False)
        self.DestroyOnClose(False)
        self.ToolbarPane()

        self.toolbar.SetToolBitmapSize((32, 32))

        align_horizontal_center = _image.icons.align_horizontal_center.resize(32, 32)
        align_left_edge = _image.icons.align_left_edge.resize(32, 32)
        align_right_edge = _image.icons.align_right_edge.resize(32, 32)
        align_vertical_center = _image.icons.align_vertical_center.resize(32, 32)
        align_top_edge = _image.icons.align_top_edge.resize(32, 32)
        align_bottom_edge = _image.icons.align_bottom_edge.resize(32, 32)

        self.toolbar.AddTool(toolId=self.ID_ALIGN_HORIZ_CENTER, label='Align Horizontal Center', bitmap=align_horizontal_center.bitmap,
                             short_help_string='Align Horizontal Center', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_ALIGN_HORIZ_CENTER)

        self.toolbar.AddTool(toolId=self.ID_ALIGN_HORIZ_LEFT, label='Align Horizontal Left', bitmap=align_left_edge.bitmap,
                             short_help_string='Align Horizontal Left', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_ALIGN_HORIZ_LEFT)
        
        self.toolbar.AddTool(toolId=self.ID_ALIGN_HORIZ_RIGHT, label='Align Horizontal Right', bitmap=align_right_edge.bitmap,
                             short_help_string='Align Horizontal Right', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_ALIGN_HORIZ_RIGHT)

        self.toolbar.AddTool(toolId=self.ID_ALIGN_VERT_CENTER, label='Align Vertical Center', bitmap=align_vertical_center.bitmap,
                             short_help_string='Align Vertical Center', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_ALIGN_VERT_CENTER)

        self.toolbar.AddTool(toolId=self.ID_ALIGN_VERT_TOP, label='Align Vertical Top', bitmap=align_top_edge.bitmap,
                             short_help_string='Align Vertical Top', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_ALIGN_VERT_TOP)

        self.toolbar.AddTool(toolId=self.ID_ALIGN_VERT_BOTTOM, label='Align Vertical Bottom', bitmap=align_bottom_edge.bitmap,
                             short_help_string='Align Vertical Bottom', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_ALIGN_VERT_BOTTOM)

        self.toolbar.Realize()
        self.manager.AddPane(self.toolbar, self)

        self.Show()
        self.manager.Update()

    def on_tools(self, evt):
        evt.Skip()

    def Refresh(self, *args, **kwargs):
        self.toolbar.Refresh(*args, **kwargs)

    def Destroy(self):
        self.toolbar.Destroy()


class EditorObjectToolbar(aui.AuiPaneInfo):

    ID_ROTATE_X = wx.NewIdRef()
    ID_ROTATE_Y = wx.NewIdRef()
    ID_ROTATE_Z = wx.NewIdRef()  # not available in 2d

    ID_SCALE_X = wx.NewIdRef()
    ID_SCALE_Y = wx.NewIdRef()
    ID_SCALE_Z = wx.NewIdRef()  # not available in 2d

    ID_MOVE_X = wx.NewIdRef()
    ID_MOVE_Y = wx.NewIdRef()
    ID_MOVE_Z = wx.NewIdRef()  # not available in 2d

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.toolbar = aui.AuiToolBar(mainframe, style=aui.AUI_TB_GRIPPER)
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Top()
        self.Floatable(True)
        self.Gripper(True)
        self.Resizable(True)
        self.Movable(True)
        self.Name('object_toolbar')
        self.CaptionVisible(False)
        self.PaneBorder(True)
        self.CloseButton(False)
        self.MaximizeButton(False)
        self.MinimizeButton(False)
        self.PinButton(False)
        self.DestroyOnClose(False)
        self.ToolbarPane()

        self.toolbar.SetToolBitmapSize((32, 32))

        rotate_x = _image.icons.rotate_x.resize(32, 32)
        rotate_y = _image.icons.rotate_y.resize(32, 32)
        rotate_z = _image.icons.rotate_z.resize(32, 32)
        scale_x = _image.icons.scale_x.resize(32, 32)
        scale_y = _image.icons.scale_y.resize(32, 32)
        scale_z = _image.icons.scale_z.resize(32, 32)
        move_x = _image.icons.move_x.resize(32, 32)
        move_y = _image.icons.move_y.resize(32, 32)
        move_z = _image.icons.move_z.resize(32, 32)

        self.toolbar.AddTool(toolId=self.ID_ROTATE_X, label='Rotate on X Axis', bitmap=rotate_x.bitmap,
                             short_help_string='Rotate on X Axis', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_ROTATE_X)

        self.toolbar.AddTool(toolId=self.ID_ROTATE_Y, label='Rotate on Y Axis', bitmap=rotate_y.bitmap,
                             short_help_string='Rotate on Y Axis', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_ROTATE_Y)

        self.toolbar.AddTool(toolId=self.ID_ROTATE_Z, label='Rotate on Z Axis', bitmap=rotate_z.bitmap,
                             short_help_string='Rotate on Z Axis', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_ROTATE_Z)

        self.toolbar.AddTool(toolId=self.ID_SCALE_X, label='Scale on X Axis', bitmap=scale_x.bitmap,
                             short_help_string='Scale on X Axis', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_SCALE_X)

        self.toolbar.AddTool(toolId=self.ID_SCALE_Y, label='Scale on Y Axis', bitmap=scale_y.bitmap,
                             short_help_string='Scale on Y Axis', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_SCALE_Y)

        self.toolbar.AddTool(toolId=self.ID_SCALE_Z, label='Scale on Z Axis', bitmap=scale_z.bitmap,
                             short_help_string='Scale on Z Axis', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_SCALE_Z)

        self.toolbar.AddTool(toolId=self.ID_MOVE_X, label='Move on X Axis', bitmap=move_x.bitmap,
                             short_help_string='Move on X Axis', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_MOVE_X)

        self.toolbar.AddTool(toolId=self.ID_MOVE_Y, label='Move on Y Axis', bitmap=move_y.bitmap,
                             short_help_string='Move on Y Axis', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_MOVE_Y)

        self.toolbar.AddTool(toolId=self.ID_MOVE_Z, label='Move on Z Axis', bitmap=move_z.bitmap,
                             short_help_string='Move on Z Axis', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_MOVE_Z)

        self.toolbar.Realize()
        self.manager.AddPane(self.toolbar, self)

        self.Show()
        self.manager.Update()

    def on_tools(self, evt):
        evt.Skip()

    def Refresh(self, *args, **kwargs):
        self.toolbar.Refresh(*args, **kwargs)

    def Destroy(self):
        self.toolbar.Destroy()


class Setting3DToolbar(aui.AuiPaneInfo):

    ID_SPOTLIGHT = wx.NewIdRef()
    ID_NORMALS = wx.NewIdRef()
    ID_SHOW_WIREFRAME = wx.NewIdRef()

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.toolbar = aui.AuiToolBar(mainframe, style=aui.AUI_TB_GRIPPER)
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Top()
        self.Floatable(True)
        self.Gripper(True)
        self.Resizable(True)
        self.Movable(True)
        self.Name('settings3d_toolbar')
        self.CaptionVisible(False)
        self.PaneBorder(True)
        self.CloseButton(False)
        self.MaximizeButton(False)
        self.MinimizeButton(False)
        self.PinButton(False)
        self.DestroyOnClose(False)
        self.ToolbarPane()

        self.toolbar.SetToolBitmapSize((32, 32))

        show_wireframe = (_image.icons.show_wireframe + _image.icons.checkbox).resize(32, 32)
        self._show_wireframe = show_wireframe.bitmap
        self._show_wireframe_disabled = show_wireframe.disabled_bitmap

        dont_show_wireframe = (_image.icons.show_wireframe + _image.icons.uncheckbox).resize(32, 32)
        self._dont_show_wireframe = dont_show_wireframe.bitmap
        self._dont_show_wireframe_disabled = dont_show_wireframe.disabled_bitmap

        show_shadows = (_image.icons.normals + _image.icons.checkbox).resize(32, 32)
        self._show_shadows = show_shadows.bitmap
        self._show_shadows_disabled = show_shadows.disabled_bitmap

        dont_show_shadows = (_image.icons.normals + _image.icons.uncheckbox).resize(32, 32)
        self._dont_show_shadows = dont_show_shadows.bitmap
        self._dont_show_shadows_disabled = dont_show_shadows.disabled_bitmap

        show_spotlight = (_image.icons.spot_light + _image.icons.checkbox).resize(32, 32)
        self._show_spotlight = show_spotlight.bitmap
        self._show_spotlight_disabled = show_spotlight.disabled_bitmap

        dont_show_spotlight = (_image.icons.spot_light + _image.icons.uncheckbox).resize(32, 32)
        self._dont_show_spotlight = dont_show_spotlight.bitmap
        self._dont_show_spotlight_disabled = dont_show_spotlight.disabled_bitmap

        self._wireframe_state = False
        self._wireframe = self.toolbar.AddTool(self.ID_SHOW_WIREFRAME, 'Show Wireframe',
                                               self._dont_show_wireframe, self._dont_show_wireframe_disabled,
                                               wx.ITEM_NORMAL, 'Show Wireframe', '', None)
        self.mainframe.Bind(wx.EVT_MENU, self.on_show_wireframe, id=self.ID_SHOW_WIREFRAME)

        self._shadows_state = False
        self._shadows = self.toolbar.AddTool(self.ID_NORMALS, 'Show Shadows',
                                             self._dont_show_shadows, self._dont_show_shadows_disabled,
                                             wx.ITEM_NORMAL, 'Show Shadows', '', None)
        self.mainframe.Bind(wx.EVT_MENU, self.on_show_shadows, id=self.ID_NORMALS)

        self._spotlight_state = False
        self._spotlight = self.toolbar.AddTool(self.ID_SPOTLIGHT, 'Show Spotlight',
                                               self._dont_show_spotlight, self._dont_show_spotlight_disabled,
                                               wx.ITEM_NORMAL, 'Show Spotlight', '', None)
        self.mainframe.Bind(wx.EVT_MENU, self.on_show_spotlight, id=self.ID_SPOTLIGHT)

        self.toolbar.Realize()
        self.manager.AddPane(self.toolbar, self)

        self.Show()
        self.manager.Update()

    def on_show_wireframe(self, evt: wx.MenuEvent):
        if not self._wireframe_state:
            self._wireframe_state = True
            self._wireframe.SetBitmap(self._show_wireframe)
            self._wireframe.SetDisabledBitmap(self._show_wireframe_disabled)
        else:
            self._wireframe_state = False
            self._wireframe.SetBitmap(self._dont_show_wireframe)
            self._wireframe.SetDisabledBitmap(self._dont_show_wireframe_disabled)

        evt.Skip()
        
    def on_show_shadows(self, evt):
        if not self._shadows_state:
            self._shadows_state = True
            self._wireframe.SetBitmap(self._show_shadows)
            self._wireframe.SetDisabledBitmap(self._show_shadows_disabled)
        else:
            self._shadows_state = False
            self._wireframe.SetBitmap(self._dont_show_shadows)
            self._wireframe.SetDisabledBitmap(self._dont_show_shadows_disabled)

        evt.Skip()
        
    def on_show_spotlight(self, evt):
        if not self._spotlight_state:
            self._spotlight_state = True
            self._wireframe.SetBitmap(self._show_spotlight)
            self._wireframe.SetDisabledBitmap(self._show_spotlight_disabled)
        else:
            self._spotlight_state = False
            self._wireframe.SetBitmap(self._dont_show_wireframe)
            self._wireframe.SetDisabledBitmap(self._dont_show_spotlight_disabled)

        evt.Skip()

    def Refresh(self, *args, **kwargs):
        self.toolbar.Refresh(*args, **kwargs)

    def Destroy(self):
        self.toolbar.Destroy()


class GeneralToolbar(aui.AuiPaneInfo):

    # --- single click buttons ---
    ID_BROWSER = wx.NewIdRef()
    ID_SETTINGS = wx.NewIdRef()
    ID_TOOLS = wx.NewIdRef()

    # connect to database (only available with mysql)
    ID_CONNECT = wx.NewIdRef()
    ID_BOM = wx.NewIdRef()

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.toolbar = aui.AuiToolBar(mainframe, style=aui.AUI_TB_GRIPPER)
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Top()
        self.Floatable(True)
        self.Gripper(True)
        self.Resizable(True)
        self.Movable(True)
        self.Name('general_toolbar')
        self.CaptionVisible(False)
        self.PaneBorder(True)
        self.CloseButton(False)
        self.MaximizeButton(False)
        self.MinimizeButton(False)
        self.PinButton(False)
        self.DestroyOnClose(False)
        self.ToolbarPane()

        self.toolbar.SetToolBitmapSize((32, 32))

        bom = _image.icons.bom.resize(32, 32)
        connect = _image.icons.connect.resize(32, 32)
        internet = _image.icons.internet.resize(32, 32)
        tool = _image.icons.tool.resize(32, 32)
        settings = _image.icons.settings.resize(32, 32)

        self.toolbar.AddTool(toolId=self.ID_BROWSER, label='Internet', bitmap=internet.bitmap,
                             short_help_string='Internet', kind=wx.ITEM_NORMAL)
        self.mainframe.Bind(wx.EVT_MENU, self.on_browser, id=self.ID_BROWSER)

        self.toolbar.AddTool(toolId=self.ID_SETTINGS, label='Settings', bitmap=settings.bitmap,
                             short_help_string='Settings', kind=wx.ITEM_NORMAL)
        self.mainframe.Bind(wx.EVT_MENU, self.on_settings, id=self.ID_SETTINGS)

        self.toolbar.AddTool(toolId=self.ID_TOOLS, label='Tools', bitmap=tool.bitmap,
                             short_help_string='Tools', kind=wx.ITEM_NORMAL)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_TOOLS)

        self.toolbar.AddTool(toolId=self.ID_CONNECT, label='Connect Database', bitmap=connect.bitmap,
                             short_help_string='Connect Database', kind=wx.ITEM_NORMAL)
        self.mainframe.Bind(wx.EVT_MENU, self.on_database, id=self.ID_CONNECT)

        self.toolbar.AddTool(toolId=self.ID_BOM, label='BOM', bitmap=bom.bitmap,
                             short_help_string='BOM', kind=wx.ITEM_NORMAL)
        self.mainframe.Bind(wx.EVT_MENU, self.on_bom, id=self.ID_BOM)

        self.toolbar.Realize()
        self.manager.AddPane(self.toolbar, self)

        self.Show()
        self.manager.Update()

    def on_browser(self, evt):
        evt.Skip()

    def on_settings(self, evt):
        evt.Skip()

    def on_tools(self, evt):
        evt.Skip()

    def on_database(self, evt):
        evt.Skip()

    def on_bom(self, evt):
        evt.Skip()

    def Refresh(self, *args, **kwargs):
        self.toolbar.Refresh(*args, **kwargs)

    def Destroy(self):
        self.toolbar.Destroy()

