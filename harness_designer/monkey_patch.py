# There is a bug in wxWidgets when running on Windows 10 and Windows 11 where
# the size and position re not calculated properly. Due to the development
# looking like it has stalled for wxPython this bug is not going to end up
# getting fixed anytime soon if at all. I have looked at other UI frameworks
# to switch to using and the only viable one is QT which carries with it a
# a pretty heavy cost for commercial licenses. So I mut stick with what works
# for the time being. and patch any bugs I come across.


import wx
import sys


if sys.platform.startswith('win'):
    import ctypes
    from ctypes.wintypes import HWND, DWORD, RECT
    import platform

    _is_at_least_ten = platform.release() == '10'

    user32 = ctypes.WinDLL('User32')
    dwmapi = ctypes.WinDLL('Dwmapi')

    DWMWA_EXTENDED_FRAME_BOUNDS = 0x09

    GetWindowRect = user32.GetWindowRect
    DwmGetWindowAttribute = dwmapi.DwmGetWindowAttribute

    if _is_at_least_ten:

        def get_offsets(hwnd):
            windowRect = RECT()
            visibleRect = RECT()

            GetWindowRect(HWND(hwnd), ctypes.byref(windowRect))
            DwmGetWindowAttribute(
                HWND(hwnd),
                DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
                ctypes.byref(visibleRect),
                DWORD(ctypes.sizeof(RECT))
            )

            set_w = windowRect.right - windowRect.left
            set_h = windowRect.bottom - windowRect.top

            real_w = visibleRect.right - visibleRect.left
            real_h = visibleRect.bottom - visibleRect.top

            w = set_w - real_w
            h = set_h - real_h

            x = windowRect.left - visibleRect.left
            y = windowRect.top - visibleRect.top

            return x, y, w, h
    else:
        def get_offsets(_):
            return 0, 0, 0, 0


else:
    def get_offsets(_):
        return 0, 0, 0, 0


_original_frame = wx.Frame
_original_dialog = wx.Dialog


class _Dialog(_original_dialog):

    def __init__(self, parent, id=wx.ID_ANY, title='', pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE,
                 name=wx.DialogNameStr):

        super().__init__(parent, id=id, title=title, pos=pos, size=size, style=style, name=name)

        off_x, off_y, off_w, off_h = get_offsets(self.GetHandle())

        x, y = pos
        w, h = size

        self._offset_x = off_x
        self._offset_y = off_y
        self._offset_w = off_w
        self._offset_h = off_h

        def _do(x_, y_, w_, h_):
            self.SetSize((w_, h_))
            self.SetPosition((x_, y_))

        for item in (x, y, w, h):
            if item != -1:
                wx.CallAfter(_do, x, y, w, h)
                break

        _original_dialog.Bind(self, wx.EVT_MOVE, self.__on_move)

    def GetSize(self):
        w, h = _original_dialog.GetSize(self)

        w -= self._offset_w
        h -= self._offset_h

        return wx.Size(w, h)

    def SetSize(self, *args, **kwargs):
        if len(args) == 1:
            if isinstance(args[0], wx.Rect):
                rect = args[0]
                x = rect.GetX()
                y = rect.GetY()
                w = rect.GetWidth()
                h = rect.GetHeight()

                w += self._offset_w
                h += self._offset_h

                x += self._offset_x
                y += self._offset_y

                _original_dialog.SetSize(self, wx.Rect(x, y, w, h))

            elif isinstance(args[0], (wx.Size, tuple)):
                size = args[0]
                w, h = size

                w += self._offset_w
                h += self._offset_h
                _original_dialog.SetSize(self, wx.Size(w, h))
            else:
                raise RuntimeError('sanity check')

        elif len(args) == 2:
            w, h = args
            w += self._offset_w
            h += self._offset_h
            _original_dialog.SetSize(self, w, h)

        elif len(args) == 4:
            x, y, w, h = args

            w += self._offset_w
            h += self._offset_h

            x += self._offset_x
            y += self._offset_y

            _original_dialog.SetSize(self, x, y, w, h, **kwargs)  # NOQA

    def GetScreenPosition(self):
        x, y = _original_dialog.GetScreenPosition(self)

        x -= self._offset_x
        y -= self._offset_y

        return wx.Point(x, y)

    def GetPosition(self):
        x, y = _original_dialog.GetPosition(self)

        x -= self._offset_x
        y -= self._offset_y

        return wx.Point(x, y)

    def SetPosition(self, pt):
        x, y = pt

        x += self._offset_x
        y += self._offset_y

        _original_dialog.SetPosition(self, (x, y))

    def Move(self, x, y, flags=wx.SIZE_USE_EXISTING):
        x += self._offset_x
        y += self._offset_y
        _original_dialog.Move(self, x, y, flags=flags)  # NOQA

    def GetRect(self):
        size = self.GetSize()
        pos = self.GetPosition()
        return wx.Rect(pos, size)

    def Bind(self, event, handler, source=None, id=-1, id2=-1):
        self.Unbind(wx.EVT_MOVE, handler=self.__on_move)
        _original_dialog.Bind(self, event, handler, source, id, id2)
        _original_dialog.Bind(self, wx.EVT_MOVE, self.__on_move)

    def __on_move(self, evt):
        pos = self.GetPosition()
        evt.SetPosition(pos)
        evt.Skip()


# wx.Dialog = _Dialog


class _Frame(_original_frame):

    def __init__(
        self, parent, id=wx.ID_ANY, title='', pos=wx.DefaultPosition,
        size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE,
        name=wx.FrameNameStr
    ):

        super().__init__(
            parent,
            id=id,
            title=title,
            pos=pos,
            size=size,
            style=style,
            name=name
            )

        off_x, off_y, off_w, off_h = get_offsets(self.GetHandle())

        x, y = pos
        w, h = size

        self._offset_x = off_x
        self._offset_y = off_y
        self._offset_w = off_w
        self._offset_h = off_h

        def _do(x_, y_, w_, h_):
            self.SetSize((w_, h_))
            self.SetPosition((x_, y_))

        for item in (x, y, w, h):
            if item != -1:
                wx.CallAfter(_do, x, y, w, h)
                break

        _original_frame.Bind(self, wx.EVT_MOVE, self.__on_move)

    def GetSize(self):
        w, h = _original_frame.GetSize(self)

        w -= self._offset_w
        h -= self._offset_h

        return wx.Size(w, h)

    def SetSize(self, *args, **kwargs):
        if len(args) == 1:
            if isinstance(args[0], wx.Rect):
                rect = args[0]
                x = rect.GetX()
                y = rect.GetY()
                w = rect.GetWidth()
                h = rect.GetHeight()

                w += self._offset_w
                h += self._offset_h

                x += self._offset_x
                y += self._offset_y

                _original_frame.SetSize(self, wx.Rect(x, y, w, h))

            elif isinstance(args[0], (wx.Size, tuple)):
                size = args[0]
                w, h = size

                w += self._offset_w
                h += self._offset_h
                _original_frame.SetSize(self, wx.Size(w, h))
            else:
                raise RuntimeError('sanity check')

        elif len(args) == 2:
            w, h = args
            w += self._offset_w
            h += self._offset_h
            _original_frame.SetSize(self, w, h)

        elif len(args) == 4:
            x, y, w, h = args

            w += self._offset_w
            h += self._offset_h

            x += self._offset_x
            y += self._offset_y

            _original_frame.SetSize(self, x, y, w, h, **kwargs)  # NOQA

    def GetScreenPosition(self):
        x, y = _original_frame.GetScreenPosition(self)

        x -= self._offset_x
        y -= self._offset_y

        return wx.Point(x, y)

    def GetPosition(self):
        x, y = _original_frame.GetPosition(self)

        x -= self._offset_x
        y -= self._offset_y

        return wx.Point(x, y)

    def SetPosition(self, pt):
        x, y = pt

        x += self._offset_x
        y += self._offset_y

        _original_frame.SetPosition(self, (x, y))

    def Move(self, x, y, flags=wx.SIZE_USE_EXISTING):
        x += self._offset_x
        y += self._offset_y
        _original_frame.Move(self, (x, y), flags=flags)  # NOQA

    def GetRect(self):
        size = self.GetSize()
        pos = self.GetPosition()
        return wx.Rect(pos, size)

    def Bind(self, event, handler, source=None, id=-1, id2=-1):
        self.Unbind(wx.EVT_MOVE, handler=self.__on_move)
        _original_frame.Bind(self, event, handler, source, id, id2)
        _original_frame.Bind(self, wx.EVT_MOVE, self.__on_move)

    def __on_move(self, evt):
        pos = self.GetPosition()
        evt.SetPosition(pos)
        evt.Skip()


wx.Frame = _Frame
