from typing import Iterable as _Iterable, TYPE_CHECKING

from . import EntryBase, TableBase
from . import terminal as _terminal
from . import seal as _seal
from . import cpa_lock as _cpa_lock
from . import tpa_lock as _tpa_lock
from . import cover as _cover
from . import ip as _ip
from . import cavity_lock as _cavity_lock

from ...wrappers.decimal import Decimal as _decimal

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, FamilyMixin, 
                     SeriesMixin, GenderMixin, ResourceMixin, WeightMixin, CavityLockMixin,
                     TemperatureMixin, DirectionMixin, DimensionMixin, ColorMixin, Model3DMixin)

if TYPE_CHECKING:
    from . import cavity as _cavity
    from . import resource as _resource


class HousingsTable(TableBase):
    __table_name__ = 'housings'

    def __iter__(self) -> _Iterable["Housing"]:

        for db_id in TableBase.__iter__(self):
            yield Housing(self, db_id)

    def __getitem__(self, item) -> "Housing":
        if isinstance(item, int):
            if item in self:
                return Housing(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Housing(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, family_id: int, series_id: int,
               gender_id: int, ip_rating_id: int, image_id: int, datasheet_id: int, cad_id: int,
               min_temp_id: int, max_temp_id: int, cavity_lock_id: int, direction_id: int, sealed: bool,
               length: float, width: float, height: float, centerline: float, color_id: int, rows: int,
               num_pins: int, terminal_sizes: list[float], compat_cpas: list[str], compat_tpas: list[str],
               compat_covers: list[str], compat_terminals: list[str], compat_seals: list[str],
               compat_housings: list[str], weight: float) -> "Housing":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 family_id=family_id, series_id=series_id, gender_id=gender_id, 
                                 ip_rating_id=ip_rating_id, image_id=image_id, datasheet_id=datasheet_id,
                                 cad_id=cad_id, min_temp_id=min_temp_id, max_temp_id=max_temp_id, 
                                 cavity_lock_id=cavity_lock_id, direction_id=direction_id, sealed=int(sealed),
                                 length=length, width=width, height=height, centerline=centerline,
                                 color_id=color_id, rows=rows, num_pins=num_pins, terminal_sizes=str(terminal_sizes),
                                 compat_cpas=str(compat_cpas), compat_tpas=str(compat_tpas), 
                                 compat_covers=str(compat_covers), compat_terminals=str(compat_terminals),
                                 compat_seals=str(compat_seals), mates_to=str(compat_housings), weight=weight)

        return Housing(self, db_id)

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
                'label': 'Gender',
                'type': [int, str],
                'search_params': ['gender_id', 'genders', 'name']
            },
            6: {
                'label': 'Rows',
                'type': [int],
                'search_params': ['rows']
            },
            7: {
                'label': 'Pins',
                'type': [int],
                'search_params': ['pins']
            },
            8: {
                'label': 'Centerline (mm)',
                'type': [float],
                'search_params': ['centerline']
            },
            9: {
                'label': 'Sealable',
                'type': [bool],
                'search_params': ['sealing']
            },
            10: {
                'label': 'Direction',
                'type': [int, str],
                'search_params': ['direction_id', 'directions', 'name']
            },
            11: {
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            12: {
                'label': 'Temperature (Min)',
                'type': [int, str],
                'search_params': ['min_temp_id', 'temperatures', 'name']
            },
            13: {
                'label': 'Temperature (Max)',
                'type': [int, str],
                'search_params': ['max_temp_id', 'temperatures', 'name']
            },
            14: {
                'label': 'Cavity Lock',
                'type': [int, str],
                'search_params': ['cavity_lock_id', 'cavity_locks', 'name']
            },
            15: {
                'label': 'IP Rating',
                'type': [int, str],
                'search_params': ['ip_rating_id', 'ip_ratings', 'name']
            },
            16: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            17: {
                'label': 'Width (mm)',
                'type': [float],
                'search_params': ['width']
            },
            18: {
                'label': 'Height (mm)',
                'type': [float],
                'search_params': ['height']
            },
            19: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class Housing(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin, FamilyMixin, 
              SeriesMixin, ColorMixin, TemperatureMixin, ResourceMixin, GenderMixin,
              DirectionMixin, DimensionMixin, WeightMixin, CavityLockMixin, Model3DMixin):

    _table: HousingsTable = None

    @property
    def compat_covers(self) -> list[_cover.Cover]:
        compat_covers = eval(self._table.select('compat_covers', id=self._db_id)[0][0])
        res = []
        for part_number in compat_covers:
            try:
                res.append(self._table.db.covers_table[part_number])
            except KeyError:
                pass
        return res

    @compat_covers.setter
    def compat_covers(self, value: list[_cover.Cover]):
        compat_covers = [cover.part_number for cover in value]
        self._table.update(self._db_id, compat_covers=str(compat_covers))

    @property
    def compat_cpas(self) -> list[_cpa_lock.CPALock]:
        compat_cpas = eval(self._table.select('compat_cpas', id=self._db_id)[0][0])
        res = []
        for part_number in compat_cpas:
            try:
                res.append(self._table.db.cpa_locks_table[part_number])
            except KeyError:
                pass
        return res

    @compat_cpas.setter
    def compat_cpas(self, value: list[_cpa_lock.CPALock]):
        compat_cpas = [cpa.part_number for cpa in value]
        self._table.update(self._db_id, compat_cpas=str(compat_cpas))

    @property
    def compat_tpas(self) -> list[_tpa_lock.TPALock]:
        compat_tpas = eval(self._table.select('compat_tpas', id=self._db_id)[0][0])
        res = []
        for part_number in compat_tpas:
            try:
                res.append(self._table.db.tpa_locks_table[part_number])
            except KeyError:
                pass
        return res

    @compat_tpas.setter
    def compat_tpas(self, value: list[_tpa_lock.TPALock]):
        compat_tpas = [tpa.part_number for tpa in value]
        self._table.update(self._db_id, compat_tpas=str(compat_tpas))

    @property
    def compat_terminals(self) -> list[_terminal.Terminal]:
        compat_terminals = eval(self._table.select('compat_terminals', id=self._db_id)[0][0])
        res = []
        for part_number in compat_terminals:
            try:
                res.append(self._table.db.terminals_table[part_number])
            except KeyError:
                pass
        return res

    @compat_terminals.setter
    def compat_terminals(self, value: list[_terminal.Terminal]):
        compat_terminals = [terminal.part_number for terminal in value]
        self._table.update(self._db_id, compat_terminals=str(compat_terminals))

    @property
    def compat_seals(self) -> list[_seal.Seal]:
        compat_seals = eval(self._table.select('compat_seals', id=self._db_id)[0][0])
        res = []
        for part_number in compat_seals:
            try:
                res.append(self._table.db.seals_table[part_number])
            except KeyError:
                pass
        return res

    @compat_seals.setter
    def compat_seals(self, value: list[_seal.Seal]):
        compat_seals = [seal.part_number for seal in value]
        self._table.update(self._db_id, compat_seals=str(compat_seals))

    @property
    def mates_to(self) -> list["Housing"]:
        housings = eval(self._table.select('mates_to', id=self._db_id)[0][0])
        res = []
        for part_number in housings:
            try:
                res.append(self._table.db.housings_table[part_number])
            except KeyError:
                pass
        return res

    @mates_to.setter
    def mates_to(self, value: list["Housing"]):
        mates_to = [housing.part_number for housing in value]
        self._table.update(self._db_id, mates_to=str(mates_to))

    @property
    def ip_rating(self) -> _ip.IPRating:
        ip_rating_id = self._table.select('ip_rating_id', id=self._db_id)
        return _ip.IPRating(self._table.db.ip_ratings_table, ip_rating_id[0][0])

    @ip_rating.setter
    def ip_rating(self, value: _ip.IPRating):
        self._table.update(self._db_id, ip_rating_id=value.db_id)
    
    @property
    def ip_rating_id(self):
        return self._table.select('ip_rating_id', id=self._db_id)[0][0]

    @ip_rating_id.setter
    def ip_rating_id(self, value):
        self._table.update(self._db_id, ip_rating_id=value)

    @property
    def cavity_lock(self) -> _cavity_lock.CavityLock:
        cavity_lock_id = self._table.select('cavity_lock_id', id=self._db_id)
        return _cavity_lock.CavityLock(self._table.db.cavity_locks_table, cavity_lock_id[0][0])

    @cavity_lock.setter
    def cavity_lock(self, value: _cavity_lock.CavityLock):
        self._table.update(self._db_id, cavity_lock_id=value.db_id)

    @property
    def cavity_lock_id(self):
        return self._table.select('cavity_lock_id', id=self._db_id)[0][0]

    @cavity_lock_id.setter
    def cavity_lock_id(self, value):
        self._table.update(self._db_id, cavity_lock_id=value)

    @property
    def terminal_sizes(self) -> list[float]:
        return eval(self._table.select('terminal_sizes', id=self._db_id)[0][0])

    @terminal_sizes.setter
    def terminal_sizes(self, value: list[float]):
        self._table.update(self._db_id, terminal_sizes=str(value))

    @property
    def sealed(self) -> bool:
        return bool(self._table.select('sealed', id=self._db_id)[0][0])

    @sealed.setter
    def sealed(self, value: bool):
        self._table.update(self._db_id, sealed=int(value))

    @property
    def centerline(self) -> _decimal:
        return _decimal(self._table.select('centerline', id=self._db_id)[0][0])

    @centerline.setter
    def centerline(self, value: _decimal):
        self._table.update(self._db_id, centerline=float(value))

    @property
    def rows(self) -> int:
        return self._table.select('rows', id=self._db_id)[0][0]

    @rows.setter
    def rows(self, value: int):
        self._table.update(self._db_id, rows=value)

    @property
    def num_pins(self) -> int:
        return self._table.select('num_pins', id=self._db_id)[0][0]

    @num_pins.setter
    def num_pins(self, value: int):
        self._table.update(self._db_id, num_pins=value)

    @property
    def cavities(self) -> list["_cavity.Cavity"]:
        res = [None] * self.num_pins

        response = self._table.db.cavities_table.select("id", "idx",
                                                        housing_id=self._db_id)
        for db_id, idx in response:
            res[idx] = self._table.db.cavities_table[db_id]
        return res

    @property
    def dxf(self) -> "_resource.Resource":
        db_id = self.dxf_id
        if db_id is None:
            return None

        return self._table.db.resources_table[db_id]

    @dxf.setter
    def dxf(self, value: "_resource.Resource"):
        self._table.update(self._db_id, dxf_id=value.db_id)

    @property
    def dxf_id(self) -> int:
        return self._table.select('dxf_id', id=self._db_id)[0][0]

    @dxf_id.setter
    def dxf_id(self, value: int):
        self._table.update(self._db_id, dxf_id=value)
