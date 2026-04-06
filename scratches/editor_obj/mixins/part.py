from typing import TYPE_CHECKING, Union

import wx
from . import mixinbase as _mixinbase
from ...widgets import text_ctrl as _text_ctrl
from ...widgets import combobox_ctrl as _combobox_ctrl
from ...widgets import color_ctrl as _color_ctrl

from ...dialogs import add_family_db as _add_family_db
from ...dialogs import add_series_db as _add_series_db
from ...dialogs import add_manufacturer_db as _add_manufacturer_db


if TYPE_CHECKING:
    from ....database.global_db.mixins import manufacturer as _manufacturer
    from ....database.global_db.mixins import part_number as _part_number
    from ....database.global_db.mixins import description as _description
    from ....database.global_db.mixins import color as _color
    from ....database.global_db.mixins import family as _family
    from ....database.global_db.mixins import series as _series
    from ....database.global_db.mixins import temperature as _temperature
    from ....database.global_db.mixins import resource as _resource


class PartMixin(_mixinbase.MixinBase):

    def __init__(self, panel, db_obj: Union["_part_number.PartNumberMixin",
                                            "_description.DescriptionMixin",
                                            "_color.ColorMixin",
                                            "_family.FamilyMixin",
                                            "_series.SeriesMixin",
                                            "_manufacturer.ManufacturerMixin",
                                            "_temperature.TemperatureMixin",
                                            "_resource.ResourceMixin"]):

        self._part_obj = db_obj
        _mixinbase.MixinBase.__init__(self)

        vsizer = panel.GetSizer()

        self.part_number = _text_ctrl.TextCtrl(
            panel, 'Part Number:', (-1, -1),
            style=wx.TE_READONLY, apply_button=False)

        self.part_number.SetValue(db_obj.part_number)

        self.description = _text_ctrl.TextCtrl(
            panel, 'Description:', (-1, -1), wx.TE_MULTILINE)
        self.description.SetValue(db_obj.description)
        self.description.Bind(wx.EVT_BUTTON, self._on_description)

        db_obj.table.execute(f'SELECT id, name FROM manufacturers;')
        rows = db_obj.table.fetchall()
        self._mfg_choices = sorted([row for row in rows], key=lambda x: x[1])

        self.mfg = _combobox_ctrl.ComboBoxCtrl(
            panel, 'Manufacturer:', [item[1] for item in self._mfg_choices])
        self.mfg.SetValue(db_obj.manufacturer.name)

        mfg_id = db_obj.mfg_id

        db_obj.table.execute(f'SELECT id, name FROM families WHERE mfg_id={mfg_id};')
        rows = db_obj.table.fetchall()
        self._family_choices = sorted([row for row in rows], key=lambda x: x[1])

        self.family = _combobox_ctrl.ComboBoxCtrl(
            panel, 'Family:', [item[1] for item in self._family_choices])

        self.family.SetValue(db_obj.family.name)
        self.family.Bind(wx.EVT_COMBOBOX, self._on_family)

        db_obj.table.execute(f'SELECT id, name FROM series WHERE mfg_id={mfg_id};')
        rows = db_obj.table.fetchall()
        self._series_choices = sorted([row for row in rows], key=lambda x: x[1])

        self.series = _combobox_ctrl.ComboBoxCtrl(
            panel, 'Series:', [item[1] for item in self._series_choices])

        self.series.SetValue(db_obj.series.name)
        self.series.Bind(wx.EVT_COMBOBOX, self._on_series)

        self.color = _color_ctrl.ColorCtrl(
            panel, 'Color:', db_obj.table.db.colors_table)

        self.color.SetValue(db_obj.color.name)

        self.image = _text_ctrl.TextCtrl(
            panel, 'Image:', (-1, -1))

        image_id = db_obj.image_id
        if image_id:
            image = db_obj.table.db.images_table[image_id]
            self.image.SetValue(image.path)

        self.datasheet = _text_ctrl.TextCtrl(
            panel, 'Datasheet:', (-1, -1))

        datasheet_id = db_obj.datasheet_id
        if datasheet_id:
            datasheet = db_obj.table.db.datasheets_table[datasheet_id]
            self.datasheet.SetValue(datasheet.path)

        self.cad = _text_ctrl.TextCtrl(
            panel, 'CAD:', (-1, -1))

        cad_id = db_obj.cad_id
        if cad_id:
            cad = db_obj.table.db.cads_table[cad_id]
            self.cad.SetValue(cad.path)

        db_obj.table.execute(f'SELECT id, name FROM temperatures;')
        rows = db_obj.table.fetchall()
        self._temperature_choices = sorted([row for row in rows], key=lambda x: x[1])

        self.min_temp = _combobox_ctrl.ComboBoxCtrl(
            panel, 'Min Temperature:', [item[1] for item in self._temperature_choices])
        self.min_temp.SetValue(db_obj.min_temp)

        self.max_temp = _combobox_ctrl.ComboBoxCtrl(
            panel, 'Max Temperature:', [item[1] for item in self._temperature_choices])
        self.max_temp.SetValue(db_obj.max_temp)

        vsizer.Add(self.part_number, 1, wx.EXPAND)
        vsizer.Add(self.description, 1, wx.EXPAND)
        vsizer.Add(self.mfg, 1, wx.EXPAND)
        vsizer.Add(self.family, 1, wx.EXPAND)
        vsizer.Add(self.series, 1, wx.EXPAND)
        vsizer.Add(self.color, 1, wx.EXPAND)
        vsizer.Add(self.image, 1, wx.EXPAND)
        vsizer.Add(self.datasheet, 1, wx.EXPAND)
        vsizer.Add(self.cad, 1, wx.EXPAND)
        vsizer.Add(self.min_temp, 1, wx.EXPAND)
        vsizer.Add(self.max_temp, 1, wx.EXPAND)

    def _on_mfg(self, evt):
        value = self.family.GetValue().strip()
        values = [item[1] for item in self._family_choices]
        if value not in values:
            mfg = self.mfg.GetValue().strip()

            dlg = _add_family_db.AddFamilyDialog(self, value, mfg, self._part_obj.table.db.families_table)
            try:
                if dlg.ShowModal() == wx.ID_OK:
                    values = dlg.GetValues()
                    family = self._part_obj.table.db.families_table.insert(*values)
                    family_id = family.db_id
                else:
                    return
            finally:
                dlg.Destroy()

        else:
            family_id = self._family_choices[values.index(value)][0]

        self._part_obj.family_id = family_id
        self._family_choices.append((family_id, value))
        self._family_choices = sorted(self._family_choices, key=lambda x: x[1])
        self.family.SetItems([item[1] for item in self._family_choices])
        self.family.SetValue(value)
        evt.Skip()

    def _on_family(self, evt):
        value = self.mfg.GetValue().strip()
        values = [item[1] for item in self._mfg_choices]
        if value not in values:
            dlg = _add_manufacturer_db.AddManufacturerDialog(self, value, self._part_obj.table.db.manufacturers_table)
            try:
                if dlg.ShowModal() == wx.ID_OK:
                    values = dlg.GetValues()
                    mfg = self._part_obj.table.db.manufacturers_table.insert(*values)
                    mfg_id = mfg.db_id
                else:
                    return
            finally:
                dlg.Destroy()

        else:
            mfg_id = self._mfg_choices[values.index(value)][0]

        self._part_obj.mfg_id = mfg_id
        self._mfg_choices.append((mfg_id, value))
        self._mfg_choices = sorted(self._mfg_choices, key=lambda x: x[1])
        self.mfg.SetItems([item[1] for item in self._mfg_choices])
        self.mfg.SetValue(value)
        evt.Skip()

    def _on_series(self, evt):
        value = self.series.GetValue().strip()
        values = [item[1] for item in self._series_choices]
        if value not in values:
            mfg = self.mfg.GetValue().strip()

            dlg = _add_series_db.AddSeriesDialog(self, value, mfg, self._part_obj.table.db.series_table)
            try:
                if dlg.ShowModal() == wx.ID_OK:
                    values = dlg.GetValues()
                    series = self._part_obj.table.db.series_table.insert(*values)
                    series_id = series.db_id
                else:
                    return
            finally:
                dlg.Destroy()

        else:
            series_id = self._series_choices[values.index(value)][0]

        self._part_obj.series_id = series_id
        self._series_choices.append((series_id, value))
        self._series_choices = sorted(self._series_choices, key=lambda x: x[1])
        self.series.SetItems([item[1] for item in self._series_choices])
        self.series.SetValue(value)
        evt.Skip()

    def _on_description(self, evt):
        desc = self.description.GetValue()
        self._part_obj.description = desc
        evt.Skip()

    def _on_image(self, evt):
        path = self.image.GetValue().strip()
        if path:
            image = self._part_obj.table.db.images_table.insert(path)
            self._part_obj.image_id = image.db_id
            evt.Skip()
        else:
            self._part_obj.image_id = None

    def _on_datasheet(self, evt):
        path = self.datasheet.GetValue().strip()
        if path:
            datasheet = self._part_obj.table.db.datasheets_table.insert(path)
            self._part_obj.datasheet_id = datasheet.db_id
            evt.Skip()
        else:
            self._part_obj.datasheet_id = None

    def _on_cad(self, evt):
        path = self.cad.GetValue().strip()
        if path:
            cad = self._part_obj.table.db.cads_table.insert(path)
            self._part_obj.cad_id = cad.db_id
            evt.Skip()
        else:
            self._part_obj.cad_id = None

    def _on_min_temp(self, evt):
        value = self.min_temp.GetValue().strip()
        values = [item[1] for item in self._temperature_choices]
        if value not in values:
            temp = self._part_obj.table.db.temperatures_table.insert(value)
            temp_id = temp.db_id
        else:
            temp_id = self._temperature_choices[values.index(value)][0]

        self._part_obj.min_temp_id = temp_id
        self._temperature_choices.append((temp_id, value))
        self._temperature_choices = sorted(self._temperature_choices, key=lambda x: x[1])
        self.min_temp.SetItems([item[1] for item in self._temperature_choices])
        self.min_temp.SetValue(value)

        value = self.max_temp.GetValue()
        self.max_temp.SetItems([item[1] for item in self._temperature_choices])
        self.max_temp.SetValue(value)

        evt.Skip()

    def _on_max_temp(self, evt):
        value = self.max_temp.GetValue().strip()
        values = [item[1] for item in self._temperature_choices]
        if value not in values:
            temp = self._part_obj.table.db.temperatures_table.insert(value)
            temp_id = temp.db_id
        else:
            temp_id = self._temperature_choices[values.index(value)][0]

        self._part_obj.max_temp_id = temp_id
        self._temperature_choices.append((temp_id, value))
        self._temperature_choices = sorted(self._temperature_choices, key=lambda x: x[1])
        self.max_temp.SetItems([item[1] for item in self._temperature_choices])
        self.max_temp.SetValue(value)

        value = self.min_temp.GetValue()
        self.min_temp.SetItems([item[1] for item in self._temperature_choices])
        self.min_temp.SetValue(value)

        evt.Skip()
