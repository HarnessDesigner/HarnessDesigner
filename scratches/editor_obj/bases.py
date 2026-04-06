from typing import TYPE_CHECKING

import wx

from ..widgets import foldpanelbar as _foldpanelbar

if TYPE_CHECKING:
    from ... import objects as _objects


class FPBBase(_foldpanelbar.FoldPanelBar):
    obj: "_objects.ObjectBase" = None

    def __init__(self, parent, obj: "_objects.ObjectBase"):
        _foldpanelbar.FoldPanelBar.__init__(self, parent, wx.ID_ANY, agwStyle=_foldpanelbar.FPB_VERTICAL)

        self.obj = obj

        font = self.GetFont()

        font.MakeItalic()
        font.MakeBold()

        # font = wx.Font()

        style = _foldpanelbar.CaptionBarStyle()
        style.SetCaptionFont(font)
        style.SetFirstColour(wx.Colour(0, 0, 0, 255))
        style.SetSecondColour(wx.Colour(181, 28, 181, 255))
        style.SetCaptionColour(wx.Colour(255, 216, 0, 255))
        style.SetCaptionStyle(_foldpanelbar.CAPTIONBAR_GRADIENT_H)

        self.ApplyCaptionStyleAll(style)
