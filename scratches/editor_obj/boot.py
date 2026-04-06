from typing import TYPE_CHECKING

import wx

from . import bases as _bases
from . import mixins as _mixins

if TYPE_CHECKING:
    from ...database.project_db import pjt_boot as _pjt_boot


class Boot(_bases.FPBBase, _mixins.Angle3DMixin,
           _mixins.DimensionMixin, _mixins.PartMixin,
           _mixins.Position3DMixin, _mixins.Visible3DMixin,
           _mixins.WeightMixin, _mixins.Scale3DMixin):

    db_obj: "_pjt_boot.PJTBoot" = None

    def __init__(self, parent, db_obj: "_pjt_boot.PJTBoot"):
        _bases.FPBBase.__init__(self, parent, db_obj)

        self.part_bar = self.AddFoldPanel('Part', collapsed=True)
        self.part_panel = wx.Panel(self.part_bar, wx.ID_ANY, style=wx.BORDER_NONE)

        part_sizer = wx.BoxSizer(wx.VERTICAL)
        self.part_panel.SetSizer(part_sizer)

        _mixins.PartMixin.__init__(self, self.part_panel, db_obj.part)



        self.settings_bar = self.AddFoldPanel('Settings')
        self.settings_panel = wx.Panel(self.settings_bar, wx.ID_ANY, wx.BORDER_NONE)
        settings_sizer = wx.BoxSizer(wx.VERTICAL)
        self.settings_panel.SetSizer(settings_sizer)

        _mixins.Visible3DMixin.__init__(self, self.settings_panel, db_obj)

        self.dimension_bar = self.AddFoldPanel('Dimensions/Scale')
        self.dimension_panel = wx.Panel(self.dimension_bar, wx.ID_ANY, wx.BORDER_NONE)
        dimension_sizer = wx.BoxSizer(wx.VERTICAL)
        self.dimension_panel.SetSizer(dimension_sizer)

        _mixins.DimensionMixin.__init__(self, self.dimension_panel, db_obj.part)
        _mixins.WeightMixin.__init__(self, self.dimension_panel, db_obj.part)
        _mixins.Scale3DMixin.__init__(self, self.dimension_panel, db_obj.part)

        self.angle_bar = self.AddFoldPanel('Angle')
        self.angle_panel = wx.Panel(self.angle_bar, wx.ID_ANY, wx.BORDER_NONE)
        angle_sizer = wx.BoxSizer(wx.VERTICAL)
        self.angle_panel.SetSizer(angle_sizer)

        _mixins.Angle3DMixin.__init__(self, self.angle_panel, db_obj)

        self.position_bar = self.AddFoldPanel('Position')
        self.position_panel = wx.Panel(self.position_bar, wx.ID_ANY, wx.BORDER_NONE)
        position_sizer = wx.BoxSizer(wx.VERTICAL)
        self.position_panel.SetSizer(position_sizer)

        _mixins.Position3DMixin.__init__(self, self.position_panel, db_obj)

        self.AddFoldPanelWindow(self.part_bar, self.part_panel)
        self.AddFoldPanelWindow(self.settings_bar, self.settings_panel)
        self.AddFoldPanelWindow(self.dimension_bar, self.dimension_panel)
        self.AddFoldPanelWindow(self.position_bar, self.position_panel)
        self.AddFoldPanelWindow(self.angle_bar, self.angle_panel)

        part_number
        description
        mfg
        family
        series
        color
        image
        datasheet
        cad
        min_temp
        max_temp

        material = None
        direction = None

        model3d = None

        compat_housings = None
