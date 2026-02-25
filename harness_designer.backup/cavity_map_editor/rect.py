from . import MixinBase

import wx


class Rect(MixinBase):

    def on_move(self, evt):
        pass

    def on_left_down(self, evt):
        pass

    def on_left_up(self, evt):
        pass

    def on_rectangle(self, evt):
        self.SetCursor(self.cross_cursor)
        self.mode = self.ID_RECT_TOOL
        evt.Skip()
