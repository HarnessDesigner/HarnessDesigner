from typing import TYPE_CHECKING

import wx

from ..widgets import text_ctrl as _text_ctrl
from ..widgets import float_ctrl as _float_ctrl
from ..widgets import combobox_ctrl as _combobox_ctrl
from ..widgets import color_ctrl as _color_ctrl

from . import dialog_base as _dialog_base
from . import add_manufacturer_db as _add_manufacturer_db
from . import add_series_db as _add_series_db
from . import add_family_db as _add_family_db
from . import add_material_db as _add_material_db


if TYPE_CHECKING:
    from ...database.global_db import bundle_cover as _bundle_cover


class AddBundleCoverDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, part_number, table: "_bundle_cover.BundleCoversTable"):
        _dialog_base.BaseDialog.__init__(
            self, parent, 'Add to Database', 'Add Bundle Covering')

        self.table = table

        if part_number:
            self.part_number = _text_ctrl.TextCtrl(
                self, 'Part Number:', (-1, -1), style=wx.TE_READONLY,
                apply_button=False)

            self.part_number.SetValue(part_number)
        else:
            self.part_number = _text_ctrl.TextCtrl(
                self, 'Part Number:', (-1, -1), apply_button=False)

            self.part_number.Bind(wx.EVT_CHAR, self.on_part_number)

        table.execute('SELECT part_number FROM bundle_covers;')
        rows = table.fetchall()
        self._part_numbers = sorted(row[0] for row in rows)

        self.description = _text_ctrl.TextCtrl(
            self, 'Description:', (-1, -1), style=wx.TE_MULTILINE,
            apply_button=False)

        table.execute('SELECT id, name FROM manufacturers;')
        rows = table.fetchall()
        self._mfgs = sorted([row for row in rows], key=lambda x: x[1])

        self.mfg = _combobox_ctrl.ComboBoxCtrl(
            self, 'Manufacturer:', [item[1] for item in self._mfgs])

        self.mfg.SetValue('')

        self.family = _combobox_ctrl.ComboBoxCtrl(
            self, 'Family:', [])

        self.family.SetValue('')
        self.family.Enable(False)

        self.series = _combobox_ctrl.ComboBoxCtrl(
            self, 'Series:', [])

        self.series.SetValue('')
        self.series.Enable(False)

        self.color = _color_ctrl.ColorCtrl(
            self, 'Color:', table.db.colors_table)

        self._families = []
        self._series = []

        table.execute('SELECT name FROM materials;')
        rows = table.fetchall()
        self._materials = sorted([row[0] for row in rows])

        self.material = _combobox_ctrl.ComboBoxCtrl(
            self, 'Material:', self._materials)

        self.material.SetValue('')

        table.execute('SELECT name FROM temperatures;')
        rows = table.fetchall()
        self._temperatures = sorted([row[0] for row in rows])

        self.shrink_temp = _combobox_ctrl.ComboBoxCtrl(
            self, 'Shrink Temperature:', self._temperatures)

        self.min_temp = _combobox_ctrl.ComboBoxCtrl(
            self, 'Min Temperature:', self._temperatures)

        self.max_temp = _combobox_ctrl.ComboBoxCtrl(
            self, 'Max Temperature:', self._temperatures)

        table.execute('SELECT name FROM protections;')
        rows = table.fetchall()
        self._protections = sorted([row[0] for row in rows])

        self.protections = _combobox_ctrl.ComboBoxCtrl(
            self, 'Protections:', self._protections)

        self.rigidity = _text_ctrl.TextCtrl(
            self, 'Rigidity:', (-1, -1), apply_button=False)

        self.shrink_ratio = _text_ctrl.TextCtrl(
            self, 'Shrink Ratio:', (-1, -1), apply_button=False)

        self.wall = _text_ctrl.TextCtrl(
            self, 'Wall Type:', (-1, -1), apply_button=False)

        self.image = _text_ctrl.TextCtrl(
            self, 'Image:', (-1, -1), apply_button=False)

        self.datasheet = _text_ctrl.TextCtrl(
            self, 'Datasheet:', (-1, -1), apply_button=False)

        self.cad = _text_ctrl.TextCtrl(
            self, 'CAD:', (-1, -1), apply_button=False)

        self.image.SetValue('')
        self.datasheet.SetValue('')
        self.cad.SetValue('')

        self.min_dia = _float_ctrl.FloatCtrl(
            self, 'Min Diameter:', 0.0, 9999.99, inc=0.01, slider=True)

        self.max_dia = _float_ctrl.FloatCtrl(
            self, 'Max Diameter:', 0.0, 9999.99, inc=0.01, slider=True)

        self.weight = _float_ctrl.FloatCtrl(
            self, 'Weight:', 0.0, 9999.99, inc=0.01, slider=True)

        self.max_dia.SetValue(0.0)
        self.min_dia.SetValue(0.0)
        self.weight.SetValue(0.0)

        self.mfg.Bind(wx.EVT_COMBOBOX, self.on_mfg)
        self.family.Bind(wx.EVT_COMBOBOX, self.on_family)
        self.series.Bind(wx.EVT_COMBOBOX, self.on_series)
        self.material.Bind(wx.EVT_COMBOBOX, self.on_material)
        self.shrink_temp.Bind(wx.EVT_COMBOBOX, self.on_shrink_temp)
        self.min_temp.Bind(wx.EVT_COMBOBOX, self.on_min_temp)
        self.max_temp.Bind(wx.EVT_COMBOBOX, self.on_max_temp)

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(self.part_number, 1, wx.EXPAND)
        sizer.Add(self.description, 1, wx.EXPAND)
        sizer.Add(self.mfg, 1, wx.EXPAND)
        sizer.Add(self.family, 1, wx.EXPAND)
        sizer.Add(self.series, 1, wx.EXPAND)
        sizer.Add(self.color, 1, wx.EXPAND)
        sizer.Add(self.material, 1, wx.EXPAND)
        sizer.Add(self.rigidity, 1, wx.EXPAND)
        sizer.Add(self.protections, 1, wx.EXPAND)
        sizer.Add(self.shrink_ratio, 1, wx.EXPAND)
        sizer.Add(self.shrink_temp, 1, wx.EXPAND)
        sizer.Add(self.min_temp, 1, wx.EXPAND)
        sizer.Add(self.max_temp, 1, wx.EXPAND)
        sizer.Add(self.image, 1, wx.EXPAND)
        sizer.Add(self.datasheet, 1, wx.EXPAND)
        sizer.Add(self.cad, 1, wx.EXPAND)
        sizer.Add(self.min_dia, 1, wx.EXPAND)
        sizer.Add(self.max_dia, 1, wx.EXPAND)
        sizer.Add(self.weight, 1, wx.EXPAND)

        self.panel.SetSizer(sizer)

    def on_part_number(self, evt):
        def _do():
            value = self.part_number.GetValue()
            hit = any(s.startswith(value) for s in self._part_numbers)
            if hit:
                self.part_number.SetStyle(
                    0, len(value), wx.TextAttr(wx.Colour(255, 0, 0)))
            else:
                self.part_number.SetStyle(
                    0, len(value), wx.TextAttr(self.GetForegroundColour()))

        wx.CallAfter(_do)
        evt.Skip()

    def on_mfg(self, evt: wx.CommandEvent):
        evt.Skip()

        names = [item[1] for item in self._mfgs]
        name = self.mfg.GetValue()

        if name in names:
            index = names.index(name)
            mfg_id = self._mfgs[index][0]
        else:
            dlg = _add_manufacturer_db.AddManufacturerDialog(
                self, name, self.table.db.manufacturers_table)

            try:
                if dlg.ShowModal() == wx.ID_OK:
                    value = dlg.GetValue()
                    try:
                        mfg = self.table.db.manufacturers_table.insert(*value)
                        mfg_id = mfg.db_id

                        self._mfgs.append((mfg_id, name))
                        self._mfgs = sorted(self._mfgs, key=lambda x: x[1])
                        self.mfg.SetItems([item[1] for item in self._mfgs])
                        self.mfg.SetValue(name)
                    except Exception as err:  # NOQA
                        from ...logger import logger as _logger

                        _logger.print_traceback(err, 'Adding Manufacturer')
                        self.family.Enable(False)
                        self.series.Enable(False)
                        return
                else:
                    self.family.Enable(False)
                    self.series.Enable(False)
                    return

            finally:
                dlg.Destroy()

        self.table.execute(f'SELECT name FROM families WHERE mfg_id={mfg_id};')
        rows = self.table.fetchall()
        self._families = sorted([row[0] for row in rows])

        self.table.execute(f'SELECT name FROM series WHERE mfg_id={mfg_id};')
        rows = self.table.fetchall()
        self._series = sorted([row[0] for row in rows])

        self.family.SetItems(self._families)
        self.family.SetValue('')
        self.family.Enable(True)

        self.series.SetItems(self._series)
        self.series.SetValue('')
        self.series.Enable(True)

    def on_family(self, evt: wx.CommandEvent):
        evt.Skip()
        name = self.family.GetValue().strip()
        if name not in self._families:
            mfg = self.mfg.GetValue()

            dlg = _add_family_db.AddFamilyDialog(
                self, name, mfg, self.table.db.families_table)

            try:
                if dlg.ShowModal() == wx.ID_OK:

                    description = dlg.GetValue()[1]
                    try:
                        self.table.db.families_table.insert(name, mfg, description)
                        self._families.append(name)
                        self._families = sorted(self._families)
                        self.family.SetItems(self._families)
                        self.family.SetValue(name)

                    except Exception as err:  # NOQA
                        from ...logger import logger as _logger

                        _logger.print_traceback(err, 'Adding Family')
                        return
                else:
                    return
            finally:
                dlg.Destroy()

    def on_series(self, evt: wx.CommandEvent):
        evt.Skip()
        name = self.series.GetValue().strip()
        if name not in self._series:
            mfg = self.mfg.GetValue()

            dlg = _add_series_db.AddSeriesDialog(
                self, name, mfg, self.table.db.series_table)

            try:
                if dlg.ShowModal() == wx.ID_OK:
                    values = dlg.GetValue()[1]
                    try:
                        self.table.db.families_table.insert(*values)
                        self._series.append(name)
                        self._series = sorted(self._series)
                        self.series.SetItems(self._series)
                        self.series.SetValue(name)

                    except Exception as err:  # NOQA
                        from ...logger import logger as _logger

                        _logger.print_traceback(err, 'Adding Series')
                        return
                else:
                    return
            finally:
                dlg.Destroy()

    def ShowModal(self):
        res = _dialog_base.BaseDialog.ShowModal(self)
        if res == wx.ID_OK:
            part_number = self.part_number.GetValue().strip()
            family = self.family.GetValue().strip()
            series = self.series.GetValue().strip()
            material = self.material.GetValue().strip()
            mfg = self.mfg.GetValue().strip()

            if any(s.startswith(part_number) for s in self._part_numbers):
                return wx.ID_CANCEL
            if family not in self._families:
                return wx.ID_CANCEL
            if series not in self._series:
                return wx.ID_CANCEL
            if material not in self._materials:
                return wx.ID_CANCEL

            mfgs = [item[1] for item in self._mfgs]
            if mfg not in mfgs:
                return wx.ID_CANCEL

        return res

    def on_material(self, evt: wx.CommandEvent):
        evt.Skip()
        name = self.material.GetValue().strip()
        if name not in self._materials:
            dlg = _add_material_db.AddMaterialDialog(
                self, name, self.table.db.materials_table)

            try:
                if dlg.ShowModal() == wx.ID_OK:
                    values = dlg.GetValue()[1]
                    try:
                        self.table.db.materials_table.insert(*values)
                        self._materials.append(name)
                        self._materials = sorted(self._materials)
                        self.material.SetItems(self._materials)
                        self.material.SetValue(name)

                    except Exception as err:  # NOQA
                        from ...logger import logger as _logger

                        _logger.print_traceback(err, 'Adding Material')
                        return
                else:
                    return
            finally:
                dlg.Destroy()

    def on_shrink_temp(self, evt: wx.CommandEvent):
        evt.Skip()
        name = self.shrink_temp.GetValue().strip()
        if name not in self._temperatures:
            self.table.execute(
                'INSERT INTO temperatures (name) VALUES (?);', (name,))

            self.table.commit()
            self._temperatures.append(name)
            self._temperatures = sorted(self._temperatures)

            self.shrink_temp.SetItemMinSize(self._temperatures)
            self.shrink_temp.SetValue(name)

            name = self.min_temp.GetValue()
            self.min_temp.SetItemMinSize(self._temperatures)
            self.min_temp.SetValue(name)

            name = self.max_temp.GetValue()
            self.max_temp.SetItems(self._temperatures)
            self.max_temp.SetValue(name)

    def on_min_temp(self, evt: wx.CommandEvent):
        evt.Skip()
        name = self.min_temp.GetValue().strip()
        if name not in self._temperatures:
            self.table.execute(
                'INSERT INTO temperatures (name) VALUES (?);', (name,))

            self.table.commit()
            self._temperatures.append(name)
            self._temperatures = sorted(self._temperatures)
            self.min_temp.SetItemMinSize(self._temperatures)
            self.min_temp.SetValue(name)

            name = self.max_temp.GetValue()
            self.max_temp.SetItems(self._temperatures)
            self.max_temp.SetValue(name)

            name = self.shrink_temp.GetValue()
            self.shrink_temp.SetItemMinSize(self._temperatures)
            self.shrink_temp.SetValue(name)

    def on_max_temp(self, evt: wx.CommandEvent):
        evt.Skip()
        name = self.max_temp.GetValue().strip()
        if name not in self._temperatures:
            self.table.execute(
                'INSERT INTO temperatures (name) VALUES (?);', (name,))

            self.table.commit()
            self._temperatures.append(name)
            self._temperatures = sorted(self._temperatures)
            self.max_temp.SetItemMinSize(self._temperatures)
            self.max_temp.SetValue(name)

            name = self.min_temp.GetValue()
            self.min_temp.SetItems(self._temperatures)
            self.min_temp.SetValue(name)

            name = self.shrink_temp.GetValue()
            self.shrink_temp.SetItemMinSize(self._temperatures)
            self.shrink_temp.SetValue(name)

    def GetValue(self):
        pn = self.part_number.GetValue().strip()
        desc = self.description.GetValue().strip()
        mfg = self.mfg.GetValue().strip()
        family = self.family.GetValue().strip()
        series = self.series.GetValue().strip()
        color_name = self.color.GetValue().strip()
        color = self.color.GetColour()
        material = self.material.GetValue().strip()
        image = self.image.GetValue().strip()
        datasheet = self.datasheet.GetValue().strip()
        cad = self.cad.GetValue().strip()
        shrink_temp = self.shrink_temp.GetValue()
        min_temp = self.min_temp.GetValue()
        max_temp = self.max_temp.GetValue()
        protection = self.protection.GetValue()
        rigidity = self.rigidity.GetValue()
        shrink_ratio = self.shrink_ratio.GetValue()
        wall = self.wall.GetValue()
        min_dia = self.min_dia.GetValue()
        max_dia = self.max_dia.GetValue()
        
        # TODO: Add adhesive part numbers
        adhesive_ids = '[]'
        weight = self.weight.GetValue()

        self.table.execute(f'SELECT id FROM colors where name="{color_name}";')
        rows = self.table.fetchall()
        if not rows:
            self.table.execute('INSERT INTO colors (name, rgb) VALUES (?, ?);',
                               (color_name, color.rgba_scalar))
            self.table.commit()

        return (pn, desc, mfg, family, series, color_name, material,
                image, datasheet, cad, shrink_temp, min_temp, max_temp, protection,
                rigidity, shrink_ratio, wall, min_dia, max_dia, adhesive_ids, weight)
