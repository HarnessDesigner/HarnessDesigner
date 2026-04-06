
from ...widgets import foldpanelbar as _foldpanelbar
from .. import bases as _bases


class MixinBase:

    def AddFoldPanelWindow(self, panel, window, flags=_foldpanelbar.FPB_ALIGN_WIDTH,
                           spacing=_foldpanelbar.FPB_DEFAULT_SPACING,
                           leftSpacing=_foldpanelbar.FPB_DEFAULT_LEFTLINESPACING,
                           rightSpacing=_foldpanelbar.FPB_DEFAULT_RIGHTLINESPACING):

        return _bases.FPBBase.AddFoldPanelWindow(self, panel, window, flags, spacing,
                                                 leftSpacing, rightSpacing)

    def AddFoldPanel(self, caption="", collapsed=False, foldIcons=None, cbstyle=None):
        return _bases.FPBBase.AddFoldPanel(self, caption, collapsed, foldIcons, cbstyle)
