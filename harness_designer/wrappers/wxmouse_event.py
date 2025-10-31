import wx
from .wxreal_point import RealPoint


class MouseEvent(wx.MouseEvent):

    def __init__(self, mouseEventType):
        wx.MouseEvent.__init__(self, mouseEventType)

        self._u_key = None
        self._key_code = None
        self._raw_key_code = None
        self._raw_key_flags = None
        self._pos3d = None
        self._artist = None

    def SetUnicodeKey(self, key: None | bytes):
        self._u_key = key

    def GetUnicodeKey(self) -> None | bytes:
        return self._u_key

    def SetKeyCode(self, key_code: None | int):
        self._key_code = key_code

    def GetKeyCode(self) -> None | int:
        return self._key_code

    def SetRawKeyCode(self, key_code: None | int):
        self._raw_key_code = key_code

    def GetRawKeyCode(self) -> None | int:
        return self._raw_key_code

    def SetRawKeyFlags(self, flags: None | int):
        self._raw_key_flags = flags

    def GetRawKeyFlags(self) -> None | int:
        return self._raw_key_flags

    def GetPosition3D(self) -> RealPoint:
        return self._pos3d

    def SetPosition3D(self, pt: RealPoint | tuple | list):
        if isinstance(pt, (tuple, list)):
            x, y, z = pt
            pt = RealPoint(x, y, z=z)

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
            f'roght_down={self.RightDown()}',
            f'right_dclick={self.RightDClick()}',
            f'right_is_down={self.RightIsDown()}',
            f'alt_down={self.AltDown()}',
            f'control_down={self.ControlDown()}'
        ]
        return ', '.join(res)
