import wx
from .wxreal_point import RealPoint


class KeyEvent(wx.KeyEvent):

    def __init__(self, keyEventType):
        wx.KeyEvent.__init__(self, keyEventType)
        self._pos3d = None
        self._pos2d = None
        self._artist = None

    def SetPosition(self, pt: tuple[int, int] | wx.Point):
        if isinstance(pt, tuple):
            try:
                pt = wx.Point(*[int(item) for item in pt])
            except TypeError:
                print(pt)
                raise

        self._pos2d = pt

    def GetPosition(self) -> wx.Point:
        return self._pos2d

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
            f'alt_down={self.AltDown()}',
            f'control_down={self.ControlDown()}'
        ]
        return ', '.join(res)
