from typing import TYPE_CHECKING

from wx import aui
from wx.lib.agw.aui.aui_utilities import GetLabelSize
from wx.lib.agw.aui.aui_utilities import MakeDisabledBitmap
from wx.lib.agw.aui.aui_constants import *
import wx

from . import events as _events
from . import toolbar_art as _toolbar_art
from . import toolbar_item as _toolbar_item

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

class EditorToolbar(aui.AuiPaneInfo):
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

        self._select = self.toolbar.AddTool(toolId=self.ID_SELECT, label='Select', bitmap=select_object.bitmap,
                                            short_help_string='Select', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_SELECT)

        self._housing = self.toolbar.AddTool(toolId=self.ID_CONNECTOR, label='Add Housing', bitmap=connector.bitmap,
                                             short_help_string='Add Housing', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_CONNECTOR)

        self._terminal = self.toolbar.AddTool(toolId=self.ID_TERMINAL, label='Add Terminal', bitmap=terminal.bitmap,
                                              short_help_string='Add Terminal', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_TERMINAL)

        self._wire = self.toolbar.AddTool(toolId=self.ID_WIRE, label='Add Wire', bitmap=wire.bitmap,
                                          short_help_string='Add Wire', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_WIRE)

        self._splice = self.toolbar.AddTool(toolId=self.ID_SPLICE, label='Add Splice', bitmap=splice.bitmap,
                                            short_help_string='Add Splice', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_SPLICE)

        self._note = self.toolbar.AddTool(toolId=self.ID_NOTE, label='Add Note', bitmap=note.bitmap,
                                          short_help_string='Add Note', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_NOTE)

        self._zoom_in = self.toolbar.AddTool(toolId=self.ID_ZOOM_IN, label='Zoom +', bitmap=zoom_in.bitmap,
                                             short_help_string='Zoom +', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_ZOOM_IN)

        self._zoom_out = self.toolbar.AddTool(toolId=self.ID_ZOOM_OUT, label='Zoom -', bitmap=zoom_out.bitmap,
                                              short_help_string='Zoom -', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_ZOOM_OUT)

        self._draw_circle = self.toolbar.AddTool(toolId=self.ID_CIRCLE, label='Draw Circle', bitmap=circle.bitmap,
                                                 short_help_string='Draw Circle', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_CIRCLE)

        self._draw_square = self.toolbar.AddTool(toolId=self.ID_SQUARE, label='Draw Square', bitmap=square.bitmap,
                                                 short_help_string='Draw Square', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_SQUARE)

        self._transition = self.toolbar.AddTool(toolId=self.ID_TRANSITION, label='Add Transition', bitmap=transition.bitmap,
                                                short_help_string='Add Transition', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_TRANSITION)

        self._seal = self.toolbar.AddTool(toolId=self.ID_SEAL, label='Add Seal', bitmap=seal.bitmap,
                                          short_help_string='Add Seal', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_SEAL)

        self._bundle = self.toolbar.AddTool(toolId=self.ID_BUNDLE_COVER, label='Add Bundle', bitmap=bundle_cover.bitmap,
                                            short_help_string='Add Bundle', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_BUNDLE_COVER)

        self._tpa_lock = self.toolbar.AddTool(toolId=self.ID_TPA_LOCK, label='Add TPA Lock', bitmap=tpa_lock.bitmap,
                                              short_help_string='Add TPA Lock', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_TPA_LOCK)

        self._cpa_lock = self.toolbar.AddTool(toolId=self.ID_CPA_LOCK, label='Add CPA Lock', bitmap=cpa_lock.bitmap,
                                              short_help_string='Add CPA Lock', kind=wx.ITEM_RADIO)
        self.mainframe.Bind(wx.EVT_MENU, self.on_tools, id=self.ID_CPA_LOCK)

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

        self.mainframe.editor3d.Bind(_canvas3d.EVT_GL_LEFT_DOWN, self._on_left_down)
        self.mainframe.editor3d.Bind(_canvas3d.EVT_GL_LEFT_UP, self._on_left_up)
        self.mainframe.editor3d.Bind(_canvas3d.EVT_GL_OBJECT_SELECTED, self._on_obj_selected)
        self.mainframe.editor3d.Bind(_canvas3d.EVT_GL_OBJECT_UNSELECTED, self._on_obj_unselected)

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

        evt.Skip()

    def _on_left_down(self, evt: _canvas3d.GLEvent):
        if self._mode == self.ID_CONNECTOR:
            evt.StopPropagation()
            self.mainframe.add_housing(evt.GetWorldPosition())
        elif self._mode == self.ID_TERMINAL:
            evt.StopPropagation()
            self.mainframe.add_terminal(evt.GetWorldPosition())
        elif self._mode == self.ID_WIRE:
            evt.StopPropagation()
            self.mainframe.add_wire(evt.GetWorldPosition())
        elif self._mode == self.ID_SPLICE:
            evt.StopPropagation()
            self.mainframe.add_splice(evt.GetWorldPosition())
        elif self._mode == self.ID_NOTE:
            evt.StopPropagation()
            self.mainframe.add_note(evt.GetWorldPosition())
        elif self._mode == self.ID_CIRCLE:
            evt.StopPropagation()
            self.mainframe.add_circle(evt.GetWorldPosition())
        elif self._mode == self.ID_SQUARE:
            evt.StopPropagation()
            self.mainframe.add_square(evt.GetWorldPosition())
        elif self._mode == self.ID_TRANSITION:
            evt.StopPropagation()
            self.mainframe.add_transition(evt.GetWorldPosition())
        elif self._mode == self.ID_SEAL:
            evt.StopPropagation()
            self.mainframe.add_seal(evt.GetWorldPosition())
        elif self._mode == self.ID_BUNDLE_COVER:
            evt.StopPropagation()
            self.mainframe.add_bundle(evt.GetWorldPosition())
        elif self._mode == self.ID_TPA_LOCK:
            evt.StopPropagation()
            self.mainframe.add_tpa_lock(evt.GetWorldPosition())
        elif self._mode == self.ID_CPA_LOCK:
            evt.StopPropagation()
            self.mainframe.add_cpa_lock(evt.GetWorldPosition())
        elif self._mode == self.ID_ZOOM_IN:
            evt.StopPropagation()
            self.mainframe.editor3d.Zoom(1.0)
        elif self._mode == self.ID_ZOOM_OUT:
            evt.StopPropagation()
            self.mainframe.editor3d.Zoom(-1.0)

        evt.Skip()

    def _on_left_up(self, evt: _canvas3d.GLEvent):
        if self._mode in (self.ID_ZOOM_IN, self.ID_ZOOM_OUT):
            evt.StopPropagation()

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


wxEVT_COMMAND_AUITOOLBAR_TOOL_DROPDOWN = _events.wxEVT_COMMAND_AUITOOLBAR_TOOL_DROPDOWN
wxEVT_COMMAND_AUITOOLBAR_OVERFLOW_CLICK = _events.wxEVT_COMMAND_AUITOOLBAR_OVERFLOW_CLICK
wxEVT_COMMAND_AUITOOLBAR_RIGHT_CLICK = _events.wxEVT_COMMAND_AUITOOLBAR_RIGHT_CLICK
wxEVT_COMMAND_AUITOOLBAR_MIDDLE_CLICK = _events.wxEVT_COMMAND_AUITOOLBAR_MIDDLE_CLICK
wxEVT_COMMAND_AUITOOLBAR_BEGIN_DRAG = _events.wxEVT_COMMAND_AUITOOLBAR_BEGIN_DRAG
EVT_AUITOOLBAR_TOOL_DROPDOWN = _events.EVT_AUITOOLBAR_TOOL_DROPDOWN
EVT_AUITOOLBAR_OVERFLOW_CLICK = _events.EVT_AUITOOLBAR_OVERFLOW_CLICK
EVT_AUITOOLBAR_RIGHT_CLICK = _events.EVT_AUITOOLBAR_RIGHT_CLICK
EVT_AUITOOLBAR_MIDDLE_CLICK = _events.EVT_AUITOOLBAR_MIDDLE_CLICK
EVT_AUITOOLBAR_BEGIN_DRAG = _events.EVT_AUITOOLBAR_BEGIN_DRAG
CommandToolBarEvent = _events.CommandToolBarEvent
AuiToolBarEvent = _events.AuiToolBarEvent
ToolbarCommandCapture = _events.ToolbarCommandCapture

AuiDefaultToolBarArt = _toolbar_art.AuiDefaultToolBarArt

AuiToolBarItem = _toolbar_item.AuiToolBarItem


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
