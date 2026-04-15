from typing import Iterable as _Iterable, TYPE_CHECKING

import uuid
import wx

from ...ui.editor_obj import prop_grid as _prop_grid
from .bases import EntryBase, TableBase
from ...geometry import point as _point

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
    Model3DMixin,
    WireSizeMixin,
    CompatSealsMixin, CompatSealsControl,
    CavityLockMixin, CavityLockControl,
    GenderMixin, GenderControl,
    PlatingMixin, PlatingControl,
    DimensionMixin, DimensionControl,
    CompatHousingsMixin, CompatHousingsControl,
)


if TYPE_CHECKING:
    from . import seal as _seal


class TerminalsTable(TableBase):
    __table_name__: str = 'terminals'

    def _load_database(self, splash):
        from ..create_database import terminals

        data_path = self._con.db_data.open(splash)
        terminals.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        from ..create_database import terminals

        return terminals.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import terminals

        terminals.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        terminals.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import terminals

        terminals.table.update_fields(self)

    def __iter__(self) -> _Iterable["Terminal"]:
        for db_id in TableBase.__iter__(self):
            yield Terminal(self, db_id)

    def __getitem__(self, item) -> "Terminal":
        if isinstance(item, int):
            if item in self:
                return Terminal(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Terminal(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, gender_id: int,
               series_id: int, family_id: int, sealing: bool, cavity_lock_id: int,
               image_id: int, datasheet_id: int, cad_id: int, material_id: int,
               blade_size: float, resistance: int, mating_cycles: int,
               max_vibration_g: int, max_current_ma: int, wire_size_min_awg: int,
               wire_size_max_awg: int, wire_dia_min: float, wire_dia_max: float,
               min_wire_cross: float, max_wire_cross: float, plating_id: int,
               weight: float, length: float, width, _decimal, height: float) -> "Terminal":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 gender_id=gender_id, series_id=series_id, family_id=family_id, sealing=int(sealing),
                                 cavity_lock_id=cavity_lock_id, image_id=image_id, datasheet_id=datasheet_id,
                                 cad_id=cad_id, material_id=material_id, blade_size=float(blade_size),
                                 resistance=resistance, mating_cycles=mating_cycles,
                                 max_vibration_g=max_vibration_g, max_current_ma=max_current_ma,
                                 wire_size_min_awg=wire_size_min_awg, wire_size_max_awg=wire_size_max_awg,
                                 wire_dia_min=float(wire_dia_min), wire_dia_max=float(wire_dia_max),
                                 min_wire_cross=float(min_wire_cross), max_wire_cross=float(max_wire_cross),
                                 plating_id=plating_id, weight=float(weight), length=float(length), width=float(width),
                                 height=float(height))

        return Terminal(self, db_id)

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
                'label': 'Plating',
                'type': [int, str],
                'search_params': ['plating_id', 'platings', 'symbol']
            },
            6: {
                'label': 'Gender',
                'type': [int, str],
                'search_params': ['gender_id', 'genders', 'name']
            },
            7: {
                'label': 'Current (ma)',
                'type': [int],
                'search_params': ['max_current_ma']
            },
            8: {
                'label': 'Blade Size (mm)',
                'type': [float],
                'search_params': ['blade_size']
            },
            9: {
                'label': 'Wire Size (Min)(AWG)',
                'type': [int],
                'search_params': ['wire_size_min_awg']
            },
            10: {
                'label': 'Wire Size (Max)(AWG)',
                'type': [int],
                'search_params': ['wire_size_max_awg']
            },
            11: {
                'label': 'Wire Size (Min)(mm2)',
                'type': [float],
                'search_params': ['min_wire_cross']
            },
            12: {
                'label': 'Wire Size (Max)(mm2)',
                'type': [float],
                'search_params': ['max_wire_cross']
            },
            13: {
                'label': 'Sealable',
                'type': [bool],
                'search_params': ['sealing']
            },
            14: {
                'label': 'Resistance',
                'type': [float],
                'out_params': 'resistance'
            },
            15: {
                'label': 'Mating Cycles',
                'type': [int],
                'out_params': 'mating_cycles'
            },
            16: {
                'label': 'Cavity Lock',
                'type': [int, str],
                'search_params': ['cavity_lock_id', 'cavity_locks', 'name']
            },
            17: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            18: {
                'label': 'Width (mm)',
                'type': [float],
                'search_params': ['width']
            },
            19: {
                'label': 'Height (mm)',
                'type': [float],
                'search_params': ['height']
            },
            20: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class Terminal(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin,
               GenderMixin, SeriesMixin, FamilyMixin, ResourceMixin, TemperatureMixin,
               WeightMixin, CavityLockMixin, PlatingMixin, Model3DMixin, DimensionMixin,
               CompatHousingsMixin, CompatSealsMixin, ColorMixin, WireSizeMixin):

    _table: TerminalsTable = None

    def build_monitor_packet(self):
        mfg = self.manufacturer

        packet = {
            'terminals': [self.db_id],
            'families': [self.family_id],
            'series': [self.series_id],
            'platings': [self.plating_id],
            'datasheets': [self.datasheet_id],
            'cavity_locks': [self.cavity_lock_id],
            'genders': [self.gender_id],
            'cads': [self.cad_id],
            'images': [self.image_id],
            'models3d': [self.model3d_id]
        }

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

    @property
    def compat_seals(self) -> list["_seal.Seal"]:
        if not self.sealing:
            return []

        min_dia = self.min_dia
        max_dia = self.max_dia

        if not min_dia or not max_dia:
            return []

        cmd = (f'SELECT id FROM seals WHERE wire_dia_min <= {min_dia} '
               f'AND wire_dia_max >= {max_dia};')

        self._table.db.seals_table.execute(cmd)
        rows = self._table.db.seals_table.fetchall()

        res = []
        for row in rows:
            seal = self._table.db.seals_table[row[0]]
            if seal.type.name.lower() not in ('sws', 'single wire seal'):
                continue
            res.append(seal)

        return res

    @property
    def sealing(self) -> bool:
        return bool(self._table.select('sealing', id=self._db_id)[0][0])

    @sealing.setter
    def sealing(self, value: bool):
        self._table.update(self._db_id, size=int(value))

    @property
    def blade_size(self) -> float:
        return self._table.select('blade_size', id=self._db_id)[0][0]

    @blade_size.setter
    def blade_size(self, value: float):
        self._table.update(self._db_id, blade_size=value)

    @property
    def resistance(self) -> float:
        return self._table.select('resistance', id=self._db_id)[0][0]

    @resistance.setter
    def resistance(self, value: float):
        self._table.update(self._db_id, resistance=value)

    @property
    def mating_cycles(self) -> int:
        return self._table.select('mating_cycles', id=self._db_id)[0][0]

    @mating_cycles.setter
    def mating_cycles(self, value: int):
        self._table.update(self._db_id, mating_cycles=value)

    @property
    def max_vibration_g(self) -> int:
        return self._table.select('max_vibration_g', id=self._db_id)[0][0]

    @max_vibration_g.setter
    def max_vibration_g(self, value: int):
        self._table.update(self._db_id, max_vibration_g=value)

    @property
    def max_current_ma(self) -> int:
        return self._table.select('max_current_ma', id=self._db_id)[0][0]

    @max_current_ma.setter
    def max_current_ma(self, value: int):
        self._table.update(self._db_id, max_current_ma=value)

    @property
    def round_terminal(self) -> bool:
        return bool(self._table.select('round_terminal', id=self._db_id)[0][0])

    @round_terminal.setter
    def round_terminal(self, value: bool):
        self._table.update(self._db_id, round_terminal=int(value))

    @property
    def length(self) -> float:
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=round(value, 6))

    @property
    def width(self) -> float:
        if self.round_terminal:
            width, height = self._table.select('width', 'height', id=self._db_id)[0]
            if width != height:
                width = min(width, height)
                self._table.update(self._db_id, width=width, height=width)
            return width

        else:
            return self._table.select('width', id=self._db_id)[0][0]

    @width.setter
    def width(self, value: float):
        if self.round_terminal:
            self._table.update(self._db_id, width=round(value, 6), height=round(value, 6))
        else:
            self._table.update(self._db_id, width=round(value, 6))

    @property
    def height(self) -> float:
        if self.round_terminal:
            width, height = self._table.select('width', 'height', id=self._db_id)[0]
            if width != height:
                height = min(width, height)
                self._table.update(self._db_id, width=height, height=height)

            return height

        else:
            return self._table.select('height', id=self._db_id)[0][0]

    @height.setter
    def height(self, value: float):
        if self.round_terminal:
            self._table.update(self._db_id, width=round(value, 6), height=round(value, 6))
        else:
            self._table.update(self._db_id, height=round(value, 6))

    _scale_id: str = None

    def _update_scale(self, scale: _point.Point):
        width, height, length = scale.as_float

        if self.round_terminal and width != height:
            width = height = min(width, height)

        self._table.update(self._db_id, width=width, height=height, length=length)

    @property
    def scale(self) -> "_point.Point":
        if self._scale_id is None:
            self._scale_id = str(uuid.uuid4())

        x = self.width
        y = self.height
        z = self.length

        if x <= 0:
            if self.round_terminal:
                if y > 0:
                    x = y

                    self._table.update(self._db_id, width=y)
                else:
                    self._table.update(self._db_id, width=1.0, height=1.0)
                    x = y = 1.0
            else:
                self._table.update(self._db_id, width=1.0)
                x = 1.0

        if y <= 0:
            if self.round_terminal:
                if x > 0:
                    y = x

                    self._table.update(self._db_id, height=x)
                else:
                    self._table.update(self._db_id, width=1.0, height=1.0)
                    x = y = 1.0
            else:
                self._table.update(self._db_id, height=1.0)
                y = 1.0

        if z <= 0:
            self._table.update(self._db_id, length=1.0)
            z = 1.0

        scale = _point.Point(x, y, z, db_id=self._scale_id)
        scale.bind(self._update_scale)
        return scale


class TerminalControl(wx.Notebook):

    def set_obj(self, db_obj: Terminal):
        self.db_obj = db_obj

        self.mfg_page.set_obj(db_obj)
        self.family_page.set_obj(db_obj)
        self.series_page.set_obj(db_obj)
        self.temperature_page.set_obj(db_obj)
        self.dimension_page.set_obj(db_obj)
        self.resources_page.set_obj(db_obj)
        self.plating_page.set_obj(db_obj)
        self.part_number_ctrl.set_obj(db_obj)
        self.description_ctrl.set_obj(db_obj)
        self.color_ctrl.set_obj(db_obj)
        self.cavity_lock_ctrl.set_obj(db_obj)
        self.weight_ctrl.set_obj(db_obj)
        self.compat_housing_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.sealing_ctrl.SetValue(False)
            self.blade_size_ctrl.SetValue(0.0)
            self.resistance_ctrl.SetValue(0.0)
            self.mating_cycles_ctrl.SetValue(0)
            self.max_vibration_g_ctrl.SetValue(0)
            self.max_current_ma_ctrl.SetValue(0)

            self.sealing_ctrl.Enable(False)
            self.blade_size_ctrl.Enable(False)
            self.resistance_ctrl.Enable(False)
            self.mating_cycles_ctrl.Enable(False)
            self.max_vibration_g_ctrl.Enable(False)
            self.max_current_ma_ctrl.Enable(False)
        else:
            self.sealing_ctrl.SetValue(db_obj.sealing)
            self.blade_size_ctrl.SetValue(db_obj.blade_size)
            self.resistance_ctrl.SetValue(db_obj.resistance)
            self.mating_cycles_ctrl.SetValue(db_obj.mating_cycles)
            self.max_vibration_g_ctrl.SetValue(db_obj.max_vibration_g)
            self.max_current_ma_ctrl.SetValue(db_obj.max_current_ma)

            self.sealing_ctrl.Enable(True)
            self.blade_size_ctrl.Enable(True)
            self.resistance_ctrl.Enable(True)
            self.mating_cycles_ctrl.Enable(True)
            self.max_vibration_g_ctrl.Enable(True)
            self.max_current_ma_ctrl.Enable(True)

    def _on_sealing(self, evt):
        value = evt.GetValue()
        self.db_obj.sealing = value

    def _on_blade_size(self, evt):
        value = evt.GetValue()
        self.db_obj.blade_size = value

    def _on_resistance(self, evt):
        value = evt.GetValue()
        self.db_obj.resistance = value

    def _on_mating_cycles(self, evt):
        value = evt.GetValue()
        self.db_obj.mating_cycles = value

    def _on_vibration(self, evt):
        value = evt.GetValue()
        self.db_obj.max_vibration_g = value

    def _on_current(self, evt):
        value = evt.GetValue()
        self.db_obj.max_current_ma = value

    def __init__(self, parent):
        self.db_obj: Terminal = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.color_ctrl = ColorControl(general_page)
        self.gender_ctrl = GenderControl(general_page)
        self.cavity_lock_ctrl = CavityLockControl(general_page)

        self.sealing_ctrl = _prop_grid.BoolProperty(
            general_page, 'Sealing', False)

        self.blade_size_ctrl = _prop_grid.FloatProperty(
            general_page, 'Blade Size', 0.0,
            min_value=0.0, max_value=99.00, increment=0.01, units='mm')

        self.resistance_ctrl = _prop_grid.FloatProperty(
            general_page, 'Resistance', 0.0,
            min_value=0.0, max_value=10000000.00, increment=0.1, units='Ω')

        self.mating_cycles_ctrl = _prop_grid.IntProperty(
            general_page, 'Mating Cycles', 0,
            min_value=0, max_value=100000)

        self.max_vibration_g_ctrl = _prop_grid.IntProperty(
            general_page, 'Maximum Vibration', 0,
            min_value=0, max_value=100000, units='G')

        self.max_current_ma_ctrl = _prop_grid.IntProperty(
            general_page, 'Maximum Current', 0,
            min_value=0, max_value=100000, units='ma')

        self.sealing_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_sealing)
        self.blade_size_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_blade_size)
        self.resistance_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_resistance)
        self.mating_cycles_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_mating_cycles)
        self.max_vibration_g_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_vibration)
        self.max_current_ma_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_current)

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)

        self.dimension_page = DimensionControl(self)
        self.weight_ctrl = WeightControl(self.dimension_page)

        self.plating_page = PlatingControl(self)

        self.resources_page = ResourcesControl(self)

        compat_parts_page = _prop_grid.Category(self, 'Compatible Parts')
        self.compat_housing_ctrl = CompatHousingsControl(compat_parts_page)
        self.compat_seal_ctrl = CompatSealsControl(compat_parts_page)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.dimension_page,
            self.plating_page,
            self.resources_page,
            compat_parts_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
