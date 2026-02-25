from . import MixinBase

import wx


class Cavity(MixinBase):

    def on_move(self, evt):
        pass

    def on_left_down(self, evt):
        pass

    def on_left_up(self, evt):
        pass

    def on_add_cavity(self, evt):
        self.SetCursor(self.cross_cursor)
        self.mode = self.ID_CAVITY_TOOL
        evt.Skip()
