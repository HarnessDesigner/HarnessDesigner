import wx

from ..geometry import point as _point


wxEVT_GL_OBJECT_SELECTED = wx.NewEventType()
EVT_GL_OBJECT_SELECTED = wx.PyEventBinder(wxEVT_GL_OBJECT_SELECTED, 0)

wxEVT_GL_OBJECT_UNSELECTED = wx.NewEventType()
EVT_GL_OBJECT_UNSELECTED = wx.PyEventBinder(wxEVT_GL_OBJECT_UNSELECTED, 0)

wxEVT_GL_OBJECT_ACTIVATED = wx.NewEventType()
EVT_GL_OBJECT_ACTIVATED = wx.PyEventBinder(wxEVT_GL_OBJECT_ACTIVATED, 0)


wxEVT_GL_OBJECT_RIGHT_CLICK = wx.NewEventType()
EVT_GL_OBJECT_RIGHT_CLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_RIGHT_CLICK, 0)

wxEVT_GL_OBJECT_RIGHT_DCLICK = wx.NewEventType()
EVT_GL_OBJECT_RIGHT_DCLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_RIGHT_DCLICK, 0)


wxEVT_GL_OBJECT_MIDDLE_CLICK = wx.NewEventType()
EVT_GL_OBJECT_MIDDLE_CLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_MIDDLE_CLICK, 0)

wxEVT_GL_OBJECT_MIDDLE_DCLICK = wx.NewEventType()
EVT_GL_OBJECT_MIDDLE_DCLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_MIDDLE_DCLICK, 0)


wxEVT_GL_OBJECT_AUX1_CLICK = wx.NewEventType()
EVT_GL_OBJECT_AUX1_CLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_AUX1_CLICK, 0)

wxEVT_GL_OBJECT_AUX1_DCLICK = wx.NewEventType()
EVT_GL_OBJECT_AUX1_DCLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_AUX1_DCLICK, 0)


wxEVT_GL_OBJECT_AUX2_CLICK = wx.NewEventType()
EVT_GL_OBJECT_AUX2_CLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_AUX2_CLICK, 0)

wxEVT_GL_OBJECT_AUX2_DCLICK = wx.NewEventType()
EVT_GL_OBJECT_AUX2_DCLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_AUX2_DCLICK, 0)


wxEVT_GL_OBJECT_DRAG = wx.NewEventType()
EVT_GL_OBJECT_DRAG = wx.PyEventBinder(wxEVT_GL_OBJECT_DRAG, 0)


wxEVT_GL_LEFT_DOWN = wx.NewEventType()
EVT_GL_LEFT_DOWN = wx.PyEventBinder(wxEVT_GL_LEFT_DOWN, 0)

wxEVT_GL_LEFT_UP = wx.NewEventType()
EVT_GL_LEFT_UP = wx.PyEventBinder(wxEVT_GL_LEFT_UP, 0)

wxEVT_GL_LEFT_DCLICK = wx.NewEventType()
EVT_GL_LEFT_DCLICK = wx.PyEventBinder(wxEVT_GL_LEFT_DCLICK, 0)


wxEVT_GL_RIGHT_DOWN = wx.NewEventType()
EVT_GL_RIGHT_DOWN = wx.PyEventBinder(wxEVT_GL_RIGHT_DOWN, 0)

wxEVT_GL_RIGHT_UP = wx.NewEventType()
EVT_GL_RIGHT_UP = wx.PyEventBinder(wxEVT_GL_RIGHT_UP, 0)

wxEVT_GL_RIGHT_DCLICK = wx.NewEventType()
EVT_GL_RIGHT_DCLICK = wx.PyEventBinder(wxEVT_GL_RIGHT_DCLICK, 0)

wxEVT_GL_MIDDLE_DOWN = wx.NewEventType()
EVT_GL_MIDDLE_DOWN = wx.PyEventBinder(wxEVT_GL_MIDDLE_DOWN, 0)

wxEVT_GL_MIDDLE_UP = wx.NewEventType()
EVT_GL_MIDDLE_UP = wx.PyEventBinder(wxEVT_GL_MIDDLE_UP, 0)

wxEVT_GL_MIDDLE_DCLICK = wx.NewEventType()
EVT_GL_MIDDLE_DCLICK = wx.PyEventBinder(wxEVT_GL_MIDDLE_DCLICK, 0)

wxEVT_GL_AUX1_DOWN = wx.NewEventType()
EVT_GL_AUX1_DOWN = wx.PyEventBinder(wxEVT_GL_AUX1_DOWN, 0)

wxEVT_GL_AUX1_UP = wx.NewEventType()
EVT_GL_AUX1_UP = wx.PyEventBinder(wxEVT_GL_AUX1_UP, 0)

wxEVT_GL_AUX1_DCLICK = wx.NewEventType()
EVT_GL_AUX1_DCLICK = wx.PyEventBinder(wxEVT_GL_AUX1_DCLICK, 0)

wxEVT_GL_AUX2_DOWN = wx.NewEventType()
EVT_GL_AUX2_DOWN = wx.PyEventBinder(wxEVT_GL_AUX2_DOWN, 0)

wxEVT_GL_AUX2_UP = wx.NewEventType()
EVT_GL_AUX2_UP = wx.PyEventBinder(wxEVT_GL_AUX2_UP, 0)

wxEVT_GL_AUX2_DCLICK = wx.NewEventType()
EVT_GL_AUX2_DCLICK = wx.PyEventBinder(wxEVT_GL_AUX2_DCLICK, 0)


wxEVT_GL_DRAG = wx.NewEventType()
EVT_GL_DRAG = wx.PyEventBinder(wxEVT_GL_AUX2_DCLICK, 0)


class GLEvent(wx.CommandEvent):

    def __init__(self, evtType):
        wx.CommandEvent.__init__(self, evtType)
        self._mouse_pos = None
        self._world_pos = None
        self._mouse_button = wx.MOUSE_BTN_NONE

    def RightIsDown(self) -> bool:
        return bool(self._mouse_button & wx.MOUSE_BTN_RIGHT)

    def LeftIsDown(self) -> bool:
        return bool(self._mouse_button & wx.MOUSE_BTN_LEFT)

    def MiddleIsDown(self) -> bool:
        return bool(self._mouse_button & wx.MOUSE_BTN_MIDDLE)

    def Aux1IsDown(self) -> bool:
        return bool(self._mouse_button & wx.MOUSE_BTN_AUX1)

    def Aux2IsDown(self) -> bool:
        return bool(self._mouse_button & wx.MOUSE_BTN_AUX2)

    def SetMouseButtons(self, buttons):
        """
        :param buttons: OR'ed of
        wx.MOUSE_BTN_LEFT
        wx.MOUSE_BTN_RIGHT
        wx.MOUSE_BTN_MIDDLE
        wx.MOUSE_BTN_AUX1
        wx.MOUSE_BTN_AUX2
        :return:
        """
        self._mouse_button = buttons

    def GetPosition(self) -> _point.Point:
        return self._mouse_pos

    def SetPosition(self, pos: _point.Point):
        self._mouse_pos = pos

    def SetWorldPosition(self, pos: _point.Point):
        self._world_pos = pos

    def GetWorldPosition(self) -> _point.Point:
        return self._world_pos


class GLObjectEvent(GLEvent):

    def __init__(self, evtType):
        wx.CommandEvent.__init__(self, evtType)
        self._gl_object = None

    def GetGLObject(self):
        return self._gl_object

    def SetGLObject(self, obj):
        self._gl_object = obj
