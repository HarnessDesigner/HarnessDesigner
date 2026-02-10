import wx
from ..geometry import point as _point


class KeyEvent(wx.KeyEvent):

    def __init__(self, keyEventType):
        wx.KeyEvent.__init__(self, keyEventType)
        self._pos3d = None
        self._pos2d = None
        self._artist = None
        self._unicode_key = None
        self._m_event = None

    def SetMatplotlibEvent(self, event):
        self._m_event = event

    def GetMatplotlibEvent(self):
        return self._m_event

    def GetUnicodeKey(self):
        return self._unicode_key

    def SetUnicodeKey(self, char):
        self._unicode_key = char

    def SetPosition(self, pt: tuple[int, int] | wx.Point):
        if isinstance(pt, tuple):
            pt = wx.Point(*[int(item) for item in pt])

        self._pos2d = pt

    def GetPosition(self) -> wx.Point:
        return self._pos2d

    def GetPosition3D(self) -> _point.Point:
        return self._pos3d

    def SetPosition3D(self, pt: _point.Point):
        self._pos3d = pt

    def SetArtist(self, artist):
        self._artist = artist

    def GetArtist(self):
        return self._artist

    def __str__(self):
        res = [
            f'artist={self.GetArtist()}',
            f'pos3d={str(self.GetPosition3D())}',
            f'pos2d={str(self.GetPosition())}',
            f'keycode={self.GetKeyCode()}',
            f'key={self.GetUnicodeKey()}',
            f'alt_down={self.AltDown()}',
            f'control_down={self.ControlDown()}'
        ]
        return ', '.join(res)
