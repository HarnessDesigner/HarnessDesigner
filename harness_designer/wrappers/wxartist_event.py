from typing import Union

import wx

wxEVT_COMMAND_ARTIST_SET_SELECTED = wx.NewEventType()
wxEVT_COMMAND_ARTIST_UNSET_SELECTED = wx.NewEventType()

EVT_ARTIST_SET_SELECTED = wx.PyEventBinder(wxEVT_COMMAND_ARTIST_SET_SELECTED, 1)
EVT_ARTIST_UNSET_SELECTED = wx.PyEventBinder(wxEVT_COMMAND_ARTIST_UNSET_SELECTED, 1)


class ArtistEvent(wx.PyCommandEvent):

    def __init__(self, command_type, win_id):
        if isinstance(command_type, int):
            wx.PyCommandEvent.__init__(self, command_type, win_id)
        else:
            wx.PyCommandEvent.__init__(self, command_type.GetEventType(), command_type.GetId())

        self.is_dropdown_clicked = False
        self.click_pt = wx.Point(-1, -1)
        self.rect = wx.Rect(-1, -1, 0, 0)
        self.tool_id = -1
        self._artist = None
        self._pos_3d = None
        self._pos = None
        self._m_event = None

    def SetMatplotlibEvent(self, event):
        self._m_event = event

    def GetMatplotlibEvent(self):
        return self._m_event

    def SetPosition(self, pos: wx.Point):
        self._pos = pos

    def GetPosition(self) -> wx.Point:
        return self._pos

    def GetPosition3D(self) -> "Point":
        return self._pos_3d

    def SetPosition3D(self, pos_3d: "Point"):
        self._pos_3d = pos_3d

    def SetArtist(self, artist: Union["Transition"]):
        self._artist = artist

    def GetArtist(self) -> Union["Transition"]:
        return self._artist
