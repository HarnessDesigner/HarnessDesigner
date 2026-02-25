from . import MixinBase

import wx


class Pan(MixinBase):

    def on_move(self, evt):
        pass

    def on_left_down(self, evt):
        pass

    def on_left_up(self, evt):
        pass

    def on_pan(self, evt):
        self.SetCursor(self.hand_cursor)
        self.mode = self.ID_PAN_TOOL
        evt.Skip()
