from typing import Iterable as _Iterable, TYPE_CHECKING
import uuid

from .bases import EntryBase, TableBase
from ...geometry import point as _point

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, GenderMixin,
                     SeriesMixin, FamilyMixin, ResourceMixin, WeightMixin, CavityLockMixin,
                     Model3DMixin, PlatingMixin)

if TYPE_CHECKING:
    from . import seal as _seal


class TerminalsTable(TableBase):
    __table_name__: str = 'terminals'

    def _load_database(self, splash):
        from ..create_database import terminals
        terminals.add_records(self._con, splash)

    def _table_needs_update(self) -> bool:
        from ..create_database import terminals

        return terminals.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import terminals

        terminals.table.add_to_db(self)
        terminals.add_records(self._con, splash)


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
               GenderMixin, SeriesMixin, FamilyMixin, ResourceMixin,
               WeightMixin, CavityLockMixin, PlatingMixin, Model3DMixin):

    _table: TerminalsTable = None

    @property
    def compat_seals(self) -> list["_seal.Seal"]:
        if not self.sealing:
            return []

        dia_min = self.wire_dia_min
        dia_max = self.wire_dia_max

        if not dia_min or not dia_max:
            return []

        cmd = (f'SELECT id FROM seals WHERE wire_dia_min <= {self.wire_dia_min} '
               f'AND wire_dia_max >= {self.wire_dia_max};')

        self._table.db.seals_table.execute(cmd)
        rows = self._table.db.seals_table.fetchall()

        res = []
        for row in rows:
            seal = self._table.db.seals_table[row[0]]
            if seal.type.lower() not in ('sws', 'single wire seal'):
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
    def wire_size_min_awg(self) -> int:
        return self._table.select('wire_size_min_awg', id=self._db_id)[0][0]

    @wire_size_min_awg.setter
    def wire_size_min_awg(self, value: int):
        self._table.update(self._db_id, wire_size_min_awg=value)

    @property
    def wire_size_max_awg(self) -> int:
        return self._table.select('wire_size_max_awg', id=self._db_id)[0][0]

    @wire_size_max_awg.setter
    def wire_size_max_awg(self, value: int):
        self._table.update(self._db_id, wire_size_max_awg=value)

    @property
    def wire_dia_min(self) -> float:
        return self._table.select('wire_dia_min', id=self._db_id)[0][0]

    @wire_dia_min.setter
    def wire_dia_min(self, value: float):
        self._table.update(self._db_id, wire_dia_min=value)

    @property
    def wire_dia_max(self) -> float:
        return self._table.select('wire_dia_max', id=self._db_id)[0][0]

    @wire_dia_max.setter
    def wire_dia_max(self, value: float):
        self._table.update(self._db_id, wire_dia_max=value)

    @property
    def min_wire_cross(self) -> float:
        return self._table.select('min_wire_cross', id=self._db_id)[0][0]

    @min_wire_cross.setter
    def min_wire_cross(self, value: float):
        self._table.update(self._db_id, min_wire_cross=value)

    @property
    def max_wire_cross(self) -> float:
        return self._table.select('max_wire_cross', id=self._db_id)[0][0]

    @max_wire_cross.setter
    def max_wire_cross(self, value: float):
        self._table.update(self._db_id, max_wire_cross=value)

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
