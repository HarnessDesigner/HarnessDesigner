import wx
from wx import dataview as dv


class DataViewCtrl(dv.DataViewCtrl):

    def __init__(self, parent: wx.Window, id: int = wx.ID_ANY, pos: wx.Point = wx.DefaultPosition,
                 size: wx.Size = wx.DefaultSize, style: int = 0, validator: wx.Validator = wx.DefaultValidator,
                 name: bytes = dv.DataViewCtrlNameStr):

        dv.DataViewCtrl.__init__(self, parent, id, pos=pos, size=size, style=style, validator=validator, name=name)

        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)

    def _on_erase_background(self, _):
        pass

    def AppendTextColumn(self, label, model_column, mode=dv.DATAVIEW_CELL_INERT,
                         width=wx.COL_WIDTH_DEFAULT, align=wx.ALIGN_NOT,
                         flags=dv.DATAVIEW_COL_RESIZABLE):

        min_width = self.GetTextExtent(label)[0] + 20

        if width == wx.COL_WIDTH_DEFAULT:
            width = min_width

        col = dv.DataViewCtrl.AppendTextColumn(self, label, model_column, mode,
                                               width, align, flags)

        col.SetMinWidth(min_width)
        return col


class DataViewColumn(dv.DataViewColumn):

    def __init__(self, title: str, renderer: dv.DataViewRenderer, model_column: int,
                 width: int = dv.DVC_DEFAULT_WIDTH, align: wx.Alignment = wx.ALIGN_CENTER,
                 flags: int = dv.DATAVIEW_COL_RESIZABLE):

        dv.DataViewColumn.__init__(self, title, renderer, model_column, align=align, flags=flags)

        dc = wx.MemoryDC()
        min_width = dc.GetTextExtent(title)[0] + 20
        dc.Destroy()
        del dc

        if width == dv.DVC_DEFAULT_WIDTH:
            width = min_width

        self.SetMinWidth(min_width)
        self.SetWidth(width)

        renderer.EnableEllipsize(wx.ELLIPSIZE_END)

