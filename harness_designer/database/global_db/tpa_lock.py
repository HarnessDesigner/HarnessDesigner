from typing import Iterable as _Iterable

import wx

from ...ui.editor_obj import prop_grid as _prop_grid
from .bases import EntryBase, TableBase


from .mixins import (
    PartNumberMixin, PartNumberControl,
    ManufacturerMixin, ManufacturerControl,
    DescriptionMixin, DescriptionControl,
    ColorMixin, ColorControl,
    FamilyMixin, FamilyControl,
    SeriesMixin, SeriesControl,
    ResourceMixin, ResourcesControl,
    WeightMixin, WeightControl,
    TemperatureMixin, TemperatureControl,
    Model3DMixin, Model3DControl,
    DimensionMixin, DimensionControl,
    CompatHousingsMixin, CompatHousingsControl
)


class TPALocksTable(TableBase):
    __table_name__ = 'tpa_locks'

    def _load_database(self, splash):
        from ..create_database import tpa_locks

        data_path = self._con.db_data.open(splash)
        tpa_locks.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        from ..create_database import tpa_locks

        return tpa_locks.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import tpa_locks

        tpa_locks.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        tpa_locks.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import tpa_locks

        tpa_locks.table.update_fields(self)

    def __iter__(self) -> _Iterable["TPALock"]:

        for db_id in TableBase.__iter__(self):
            yield TPALock(self, db_id)

    def __getitem__(self, item) -> "TPALock":
        if isinstance(item, int):
            if item in self:
                return TPALock(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return TPALock(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, family_id: int,
               series_id: int, image_id: int, datasheet_id: int, cad_id: int, min_temp_id: int,
               max_temp_id: int, pins: str, color_id: int, length: float, width: float,
               height: float, terminal_size: float, weight: float) -> "TPALock":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 family_id=family_id, series_id=series_id, image_id=image_id,
                                 datasheet_id=datasheet_id, cad_id=cad_id, min_temp_id=min_temp_id,
                                 max_temp_id=max_temp_id, pins=pins, color_id=color_id, length=float(length),
                                 width=float(width), height=float(height), terminal_size=float(terminal_size),
                                 weight=float(weight))

        return TPALock(self, db_id)

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
                'label': 'Family',
                'type': [int, str],
                'search_params': ['family_id', 'families', 'name']
            },
            4: {
                'label': 'Series',
                'type': [int, str],
                'search_params': ['series_id', 'series', 'name']
            },
            5: {
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            7: {
                'label': 'Temperature (Min)',
                'type': [int, str],
                'search_params': ['min_temp_id', 'temperatures', 'name']
            },
            8: {
                'label': 'Temperature (Max)',
                'type': [int, str],
                'search_params': ['max_temp_id', 'temperatures', 'name']
            },
            9: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            10: {
                'label': 'Width (mm)',
                'type': [float],
                'search_params': ['width']
            },
            11: {
                'label': 'Height (mm)',
                'type': [float],
                'search_params': ['height']
            },
            12: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class TPALock(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin, FamilyMixin,
              SeriesMixin, ResourceMixin, TemperatureMixin, Model3DMixin,
              ColorMixin, DimensionMixin, WeightMixin, CompatHousingsMixin):

    _table: TPALocksTable = None

    def build_monitor_packet(self):
        mfg = self.manufacturer
        color = self.color

        packet = {
            'tpa_locks': [self.db_id],
            'families': [self.family_id],
            'series': [self.series_id],
            'temperatures': [self.min_temp_id, self.max_temp],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id],
            'models3d': [self.model3d_id]
        }

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

    @property
    def pins(self) -> str:
        return self._table.select('pins', id=self._db_id)[0][0]

    @pins.setter
    def pins(self, value: str):
        self._table.update(self._db_id, pins=value)
        self._populate('pins')

    @property
    def lock_type(self) -> str:
        return self._table.select('lock_type', id=self._db_id)[0][0]

    @lock_type.setter
    def lock_type(self, value: str):
        self._table.update(self._db_id, lock_type=value)
        self._populate('lock_type')


class TPALockControl(wx.Notebook):

    # TODO: Add lock type and pins

    def set_obj(self, db_obj: TPALock):
        self.db_obj = db_obj

        self.mfg_page.set_obj(db_obj)
        self.family_page.set_obj(db_obj)
        self.series_page.set_obj(db_obj)
        self.temperature_page.set_obj(db_obj)
        self.dimension_page.set_obj(db_obj)
        self.resources_page.set_obj(db_obj)
        self.model3d_page.set_obj(db_obj)

        self.part_number_ctrl.set_obj(db_obj)
        self.description_ctrl.set_obj(db_obj)
        self.color_ctrl.set_obj(db_obj)
        self.weight_ctrl.set_obj(db_obj)
        self.compat_housing_ctrl.set_obj(db_obj)

    def __init__(self, parent):
        self.db_obj: TPALock = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.color_ctrl = ColorControl(general_page)

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)

        self.dimension_page = DimensionControl(self)
        self.weight_ctrl = WeightControl(self.dimension_page)

        self.resources_page = ResourcesControl(self)

        compat_parts_page = _prop_grid.Category(self, 'Compatible Parts')
        self.compat_housing_ctrl = CompatHousingsControl(compat_parts_page)

        self.model3d_page = Model3DControl(self)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.dimension_page,
            self.resources_page,
            compat_parts_page,
            self.model3d_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
