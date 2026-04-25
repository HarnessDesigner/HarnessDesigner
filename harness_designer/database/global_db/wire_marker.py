from typing import Iterable as _Iterable

import wx

from ...ui.editor_obj import prop_grid as _prop_grid
from .bases import EntryBase, TableBase

from .mixins import (
    PartNumberMixin, PartNumberControl,
    ManufacturerMixin, ManufacturerControl,
    DescriptionMixin, DescriptionControl,
    FamilyMixin, FamilyControl,
    SeriesMixin, SeriesControl,
    ColorMixin, ColorControl,
    TemperatureMixin, TemperatureControl,
    ResourceMixin, ResourcesControl,
    WeightMixin, WeightControl
)


class WireMarkersTable(TableBase):
    __table_name__: str = 'wire_markers'

    def _table_needs_update(self) -> bool:
        from ..create_database import wire_markers

        return wire_markers.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import wire_markers

        wire_markers.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        wire_markers.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import wire_markers

        wire_markers.table.update_fields(self)

    def __iter__(self) -> _Iterable["WireMarker"]:

        for db_id in TableBase.__iter__(self):
            yield WireMarker(self, db_id)

    def __getitem__(self, item) -> "WireMarker":
        if isinstance(item, int):
            if item in self:
                return WireMarker(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return WireMarker(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, image_id: int, datasheet_id: int,
               cad_id: int, color_id: int, min_diameter: float, max_diameter: float, length: float) -> "WireMarker":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 image_id=image_id, datasheet_id=datasheet_id, cad_id=cad_id,
                                 color_id=color_id, min_diameter=min_diameter,
                                 max_diameter=max_diameter, length=length)

        return WireMarker(self, db_id)

    @property
    def search_items(self) -> dict:
        ret = {
            0: {
                'label': 'Part Number',
                'type': [str],
                'out_params': 'part_number'
            },
            1: {
                'label': 'Description',
                'type': [str],
                'out_params': 'description'
            },
            2: {
                'label': 'Manufacturer',
                'type': [int, str],
                'search_params': ['mfg_id', 'manufacturers', 'name']
            },
            3: {
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            4: {
                'label': 'Diameter (Min)(AWG)',
                'type': [int],
                'search_params': ['min_awg']
            },
            5: {
                'label': 'Diameter (Min)(AWG)',
                'type': [int],
                'search_params': ['max_awg']
            },
            6: {
                'label': 'Diameter (Min)(mm)',
                'type': [float],
                'search_params': ['min_diameter']
            },
            7: {
                'label': 'Diameter (Min)(mm)',
                'type': [float],
                'search_params': ['max_diameter']
            },
            8: {
                'label': 'Label',
                'type': [bool],
                'search_params': ['has_label']
            },
            9: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            10: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class WireMarker(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin,
                 FamilyMixin, SeriesMixin, ColorMixin, TemperatureMixin, ResourceMixin,
                 WeightMixin):

    _table: WireMarkersTable = None

    def build_monitor_packet(self):
        mfg = self.manufacturer
        color = self.color

        packet = {
            'wire_markers': [self.db_id],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id]
        }

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

    @property
    def weight(self) -> float:
        return self._table.select('weight', id=self._db_id)[0][0]

    @weight.setter
    def weight(self, value: float):
        self._table.update(self._db_id, weight=value)
        self._populate('weight')

    @property
    def has_label(self) -> bool:
        return bool(self._table.select('has_label', id=self._db_id)[0][0])

    @has_label.setter
    def has_label(self, value: bool):
        self._table.update(self._db_id, has_label=int(value))
        self._populate('has_label')

    @property
    def min_diameter(self) -> float:
        return self._table.select('min_diameter', id=self._db_id)[0][0]

    @min_diameter.setter
    def min_diameter(self, value: float):
        self._table.update(self._db_id, min_diameter=value)
        self._populate('min_diameter')

    @property
    def max_diameter(self) -> float:
        return self._table.select('max_diameter', id=self._db_id)[0][0]

    @max_diameter.setter
    def max_diameter(self, value: float):
        self._table.update(self._db_id, max_diameter=value)
        self._populate('max_diameter')

    @property
    def min_awg(self) -> int:
        return self._table.select('min_awg', id=self._db_id)[0][0]

    @min_awg.setter
    def min_awg(self, value: int):
        self._table.update(self._db_id, min_awg=value)
        self._populate('min_awg')

    @property
    def max_awg(self) -> int:
        return self._table.select('max_awg', id=self._db_id)[0][0]

    @max_awg.setter
    def max_awg(self, value: int):
        self._table.update(self._db_id, max_awg=value)
        self._populate('max_awg')

    @property
    def length(self) -> float:
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=value)
        self._populate('length')


class WireMarkerControl(wx.Notebook):

    def set_obj(self, db_obj: WireMarker):
        self.db_obj = db_obj

        self.mfg_page.set_obj(db_obj)
        self.family_page.set_obj(db_obj)
        self.series_page.set_obj(db_obj)
        self.temperature_page.set_obj(db_obj)
        self.resources_page.set_obj(db_obj)

        self.part_number_ctrl.set_obj(db_obj)
        self.description_ctrl.set_obj(db_obj)
        self.color_ctrl.set_obj(db_obj)
        self.weight_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.length_ctrl.SetValue(0.05)
            self.min_diameter_ctrl.SetValue(0.05)
            self.max_diameter_ctrl.SetValue(0.05)
            self.min_awg_ctrl.SetValue(0)
            self.max_awg_ctrl.SetValue(0)
            self.label_ctrl.SetValue(False)

            self.length_ctrl.Enable(False)
            self.min_diameter_ctrl.Enable(False)
            self.max_diameter_ctrl.Enable(False)
            self.min_awg_ctrl.Enable(False)
            self.max_awg_ctrl.Enable(False)
            self.label_ctrl.Enable(False)
        else:
            self.length_ctrl.SetValue(db_obj.length)
            self.min_diameter_ctrl.SetValue(db_obj.min_diameter)
            self.max_diameter_ctrl.SetValue(db_obj.max_diameter)
            self.min_awg_ctrl.SetValue(db_obj.min_awg)
            self.max_awg_ctrl.SetValue(db_obj.max_awg)
            self.label_ctrl.SetValue(db_obj.has_label)

            self.length_ctrl.Enable(True)
            self.min_diameter_ctrl.Enable(True)
            self.max_diameter_ctrl.Enable(True)
            self.min_awg_ctrl.Enable(True)
            self.max_awg_ctrl.Enable(True)
            self.label_ctrl.Enable(True)

    def _on_min_diameter(self, evt):
        value = evt.GetValue()
        self.db_obj.min_diameter = value

    def _on_max_diameter(self, evt):
        value = evt.GetValue()
        self.db_obj.max_diameter = value

    def _on_min_awg(self, evt):
        value = evt.GetValue()
        self.db_obj.min_awg = value

    def _on_max_awg(self, evt):
        value = evt.GetValue()
        self.db_obj.max_awg = value

    def _on_length(self, evt):
        value = evt.GetValue()
        self.db_obj.length = value

    def _on_label(self, evt):
        value = evt.GetValue()
        self.db_obj.has_label = value

    def __init__(self, parent):
        self.db_obj: WireMarker = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)

        self.color_ctrl = ColorControl(general_page)
        self.weight_ctrl = WeightControl(general_page)

        self.length_ctrl = _prop_grid.FloatProperty(
            general_page, 'Length', min_value=0.01,
            max_value=99.99, increment=0.01, units='mm')

        self.label_ctrl = _prop_grid.BoolProperty(
            general_page, 'Has Label')

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)

        self.resources_page = ResourcesControl(self)

        diameter_page = _prop_grid.Category(self, 'Diameter')

        self.min_diameter_ctrl = _prop_grid.FloatProperty(
            diameter_page, 'Minimum', min_value=0.05,
            max_value=60.0, increment=0.01, units='mm')

        self.max_diameter_ctrl = _prop_grid.FloatProperty(
            diameter_page, 'Maximum', min_value=0.05,
            max_value=60.0, increment=0.01, units='mm')

        wire_size_page = _prop_grid.Category(self, 'Wire Size')

        self.min_awg_ctrl = _prop_grid.IntProperty(
            wire_size_page, 'Minimum', min_value=0,
            max_value=30, units='awg')

        self.max_awg_ctrl = _prop_grid.IntProperty(
            wire_size_page, 'Maximum', min_value=0,
            max_value=30, units='awg')

        self.min_diameter_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_min_diameter)
        self.max_diameter_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_max_diameter)
        self.min_awg_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_min_awg)
        self.max_awg_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_max_awg)

        self.length_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_length)
        self.label_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_label)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.resources_page,
            diameter_page,
            wire_size_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
