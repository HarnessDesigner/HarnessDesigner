import wx
from ..geometry import point as _point


class MouseEvent(wx.MouseEvent):

    def __init__(self, mouseEventType):
        wx.MouseEvent.__init__(self, mouseEventType)

        self._u_key = None
        self._key_code = None
        self._raw_key_code = None
        self._raw_key_flags = None
        self._pos3d = None
        self._artist = None
        self._m_event = None

    def SetMatplotlibEvent(self, event):
        self._m_event = event

    def GetMatplotlibEvent(self):
        return self._m_event

    def SetUnicodeKey(self, key):
        self._u_key = key

    def GetUnicodeKey(self):
        return self._u_key

    def SetKeyCode(self, key_code):
        self._key_code = key_code

    def GetKeyCode(self):
        return self._key_code

    def SetRawKeyCode(self, key_code):
        self._raw_key_code = key_code

    def GetRawKeyCode(self):
        return self._raw_key_code

    def SetRawKeyFlags(self, flags):
        self._raw_key_flags = flags

    def GetRawKeyFlags(self):
        return self._raw_key_flags

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
            f'wheel={self.GetWheelDelta()}',
            f'left_down={self.LeftDown()}',
            f'left_dclick={self.LeftDClick()}',
            f'left_is_down={self.LeftIsDown()}',
            f'right_down={self.RightDown()}',
            f'right_dclick={self.RightDClick()}',
            f'right_is_down={self.RightIsDown()}',
            f'alt_down={self.AltDown()}',
            f'control_down={self.ControlDown()}'
        ]
        return ', '.join(res)
