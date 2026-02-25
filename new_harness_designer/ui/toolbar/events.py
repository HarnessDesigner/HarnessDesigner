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
