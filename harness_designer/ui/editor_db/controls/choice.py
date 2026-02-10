import wx
import wx.dataview as dv


class ChoiceRendererBase(dv.DataViewCustomRenderer):
    __table_name__ = ''
    __field_name__ = ''

    def __init__(self, choices, *args, **kw):
        self.choices = choices
        dv.DataViewCustomRenderer.__init__(self, *args, **kw)
        self.value = 0
        self.selection = 'N/A'
        self.EnableEllipsize(wx.ELLIPSIZE_NONE)

    def SetValue(self, value):
        value = int(value)

        for c_id, choice in self.choices:
            if c_id == value:
                break
        else:
            raise RuntimeError(f'sanity check {self.__class__.__name__}, {value}')

        self.value = value
        self.selection = choice
        return True

    def GetValue(self):
        return int(self.value)

    def GetSize(self):
        max_size = wx.Size(0, 0)
        for choice in self.choices:
            size = self.GetTextExtent(choice[1])
            if size.GetWidth() > max_size.GetWidth():
                max_size = size

        max_size += (15, 2)
        return max_size

    def Render(self, rect, dc, state):
        # if not state & dv.DATAVIEW_CELL_SELECTED:
        #     dc.SetBrush(wx.Brush('#ffd0d0'))
        #     dc.SetPen(wx.TRANSPARENT_PEN)
        #     rect.Deflate(1, 1)
        #     dc.DrawRoundedRectangle(rect, 2)

        value = str(self.selection)
        self.RenderText(value, 0, rect, dc, state)
        return True

    def ActivateCell(self, rect, model, item, col, mouseEvent):
        return False

    def HasEditorCtrl(self):
        return True

    def CreateEditorCtrl(self, parent, labelRect, value):


        ctrl = wx.Choice(parent, choices=[c[1] for c in self.choices],
                         pos=labelRect.GetPosition(), size=labelRect.GetSize())
        ctrl.SetStringSelection(str(self.selection))
        return ctrl

    def GetValueFromEditorCtrl(self, editor: wx.Choice):
        value = editor.GetStringSelection()

        for c_id, choice in self.choices:
            if choice == value:
                break
        else:
            raise RuntimeError('sanity check')

        return str(c_id)

    def LeftClick(self, pos, cellRect, model, item, col):
        return False

    def Activate(self, cellRect, model, item, col):
        # TODO: add new dialog
        return False


class ColorRenderer(ChoiceRendererBase):
    __table_name__ = 'colors'
    __field_name__ = 'name'

    def __init__(self, choices, *args, **kw):
        ChoiceRendererBase.__init__(self, choices, *args, **kw)
        self.value = None
        self.selection = None

    def GetValueFromEditorCtrl(self, editor: wx.Choice):
        value = editor.GetStringSelection()
        if value == 'None':
            return None

        for c_id, choice in self.choices:
            if choice == value:
                break
        else:
            raise RuntimeError('sanity check')

        return c_id


class ManufacturerRenderer(ChoiceRendererBase):
    __table_name__ = 'manufacturers'
    __field_name__ = 'name'


class TemperatureRenderer(ChoiceRendererBase):
    __table_name__ = 'temperatures'
    __field_name__ = 'name'


class GenderRenderer(ChoiceRendererBase):
    __table_name__ = 'genders'
    __field_name__ = 'name'


class ProtectionRenderer(ChoiceRendererBase):
    __table_name__ = 'protections'
    __field_name__ = 'name'


class AdhesiveRenderer(ChoiceRendererBase):
    __table_name__ = 'adhesives'
    __field_name__ = 'description'


class CavityLockRenderer(ChoiceRendererBase):
    __table_name__ = 'cavity_locks'
    __field_name__ = 'name'


class DirectionRenderer(ChoiceRendererBase):
    __table_name__ = 'directions'
    __field_name__ = 'name'


class PlatingRenderer(ChoiceRendererBase):
    __table_name__ = 'platings'
    __field_name__ = 'description'


class MaterialRenderer(ChoiceRendererBase):
    __table_name__ = 'materials'
    __field_name__ = 'name'


class ShapeRenderer(ChoiceRendererBase):
    __table_name__ = 'shapes'
    __field_name__ = 'name'


class SeriesRenderer(ChoiceRendererBase):
    __table_name__ = 'series'
    __field_name__ = 'name'


class FamilyRenderer(ChoiceRendererBase):
    __table_name__ = 'families'
    __field_name__ = 'name'


class IPRatingRenderer(ChoiceRendererBase):
    __table_name__ = 'ip_ratings'
    __field_name__ = 'name'


class TransitionSeriesRenderer(ChoiceRendererBase):
    __table_name__ = 'transition_series'
    __field_name__ = 'name'


class SpliceTypeRenderer(ChoiceRendererBase):
    __table_name__ = 'splice_types'
    __field_name__ = 'name'


class SealTypeRenderer(ChoiceRendererBase):
    __table_name__ = 'seal_types'
    __field_name__ = 'name'
