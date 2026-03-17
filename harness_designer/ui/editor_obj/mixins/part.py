PartNumberMixin,
DescriptionMixin
ColorMixin
FamilyMixin
SeriesMixin


from typing import TYPE_CHECKING, Union

import wx
from . import mixinbase as _mixinbase
from ...widgets import text_ctrl as _text_ctrl
from ...widgets import combobox_ctrl as _combobox_ctrl


if TYPE_CHECKING:
    from ....database.global_db.mixins import manufacturer as _manufacturer
    from ....database.global_db.mixins import part_number as _part_number
    from ....database.global_db.mixins import description as _description
    from ....database.global_db.mixins import color as _color
    from ....database.global_db.mixins import family as _family
    from ....database.global_db.mixins import series as _series


class ManufacturerMixin(_mixinbase.MixinBase):

    def __init__(self, db_obj: Union["_part_number.PartNumberMixin", "_description.DescriptionMixin",
                                     "_color.ColorMixin", "_family.FamilyMixin", "_series.SeriesMixin",
                                     "_manufacturer.ManufacturerMixin"]):

        self.db_obj = db_obj
        _mixinbase.MixinBase.__init__(self)

        fold_panel = self.AddFoldPanel('Part', collapsed=True)

        panel = wx.Panel(fold_panel, wx.ID_ANY, style=wx.BORDER_NONE)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        pn_label = wx.StaticText(panel, wx.ID_ANY, 'Part Number:')
        pn = wx.StaticText(panel, wx.ID_ANY, db_obj.part_number)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(pn_label, 1, wx.ALL, 5)
        hsizer.Add(pn, 1, wx.ALL, 5)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        self.desc_ctrl = _text_ctrl.TextCtrl(panel, 'Description:', (-1, -1), wx.TE_MULTILINE)
        self.desc_ctrl.SetValue(db_obj.description)

        self.desc_ctrl.Bind(wx.EVT_BUTTON, self._on_description)

        vsizer.Add(self.desc_ctrl, 1, wx.EXPAND)

        mfg_id = db_obj.mfg_id

        db_obj.table.execute(f'SELECT id, name FROM families WHERE mfg_id={mfg_id};')
        rows = db_obj.table.fetchall()
        self._family_choices = sorted([row for row in rows], key=lambda x: x[1])

        db_obj.table.execute(f'SELECT id, name FROM series WHERE mfg_id={mfg_id};')
        rows = db_obj.table.fetchall()
        self._series_choices = sorted([row for row in rows], key=lambda x: x[1])

        self.family_ctrl = _combobox_ctrl.ComboBoxCtrl(panel, 'Family:', [item[1] for item in self._family_choices])
        self.series_ctrl = _combobox_ctrl.ComboBoxCtrl(panel, 'Series:', [item[1] for item in self._series_choices])

        self.family_ctrl.Bind(wx.EVT_COMBOBOX, self._on_family)
        self.series_ctrl.Bind(wx.EVT_COMBOBOX, self._on_series)

        vsizer.Add(self.family_ctrl, 1, wx.EXPAND)
        vsizer.Add(self.series_ctrl, 1, wx.EXPAND)


        db_obj.table.execute(f'SELECT id, name FROM series WHERE mfg_id={mfg_id};')

        def hsizer(label, data):
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            st1 = wx.StaticText(panel, wx.ID_ANY, label)
            st2 = wx.StaticText(panel, wx.ID_ANY, data)

            sizer.Add(st1, 1, wx.ALL | wx.ALIGN_TOP, 3)
            sizer.Add(st2, 1, wx.ALL, 3)
            vsizer.Add(sizer, 1)

        hsizer('Name:', db_obj.name)
        hsizer('Description:', db_obj.description)
        hsizer('Address:', db_obj.address)
        hsizer('Contact:', db_obj.contact_person)
        hsizer('Phone:', db_obj.phone + ' : ' + db_obj.ext)
        hsizer('Email:', db_obj.email)
        hsizer('Website:', db_obj.website)

        panel.SetSizer(vsizer)
        self.AddFoldPanelWindow(fold_panel, panel)

    def _on_family(self, evt):
        value = self.family_ctrl.GetValue()
        values = [item[1] for item in self._family_choices]
        if value not in values:
            self.db_obj.table.execute('INSERT INTO families mfg_id, name VALUES (?, ?);', (self.db_obj.mfg_id, value))
            self.db_obj.table.commit()
            family_id = self.db_obj.table.lastrowid
            self._family_choices.append((family_id, value))
            self._family_choices = sorted(self._family_choices, key=lambda x: x[1])
            self.family_ctrl.SetItems([item[1] for item in self._family_choices])
        else:
            for family_id, name in self._family_choices:
                if name == value:
                    break
            else:
                raise RuntimeError('sanity check')

        self.db_obj.family_id = family_id
        evt.Skip()

    def _on_series(self, evt):
        value = self.series_ctrl.GetValue()
        values = [item[1] for item in self._family_choices]

        if value not in values:
            self.db_obj.table.execute('INSERT INTO series mfg_id, name VALUES (?, ?);', (self.db_obj.mfg_id, value))
            self.db_obj.table.commit()
            series_id = self.db_obj.table.lastrowid
            self._series_choices.append((series_id, value))
            self._series_choices = sorted(self._series_choices, key=lambda x: x[1])
            self.series_ctrl.SetItems([item[1] for item in self._series_choices])
        else:
            for series_id, name in self._series_choices:
                if name == value:
                    break
            else:
                raise RuntimeError('sanity check')

        self.db_obj.series_id = series_id

        evt.Skip()

    def _on_description(self, evt):
        desc = self.desc_ctrl.GetValue()
        self.db_obj.description = desc
        evt.Skip()
