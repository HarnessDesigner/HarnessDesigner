from typing import Iterable as _Iterable, TYPE_CHECKING

import uuid
from wx import propgrid as wxpg

from .bases import EntryBase, TableBase
from . import cpa_lock as _cpa_lock
from . import tpa_lock as _tpa_lock
from . import boot as _boot
from . import cover as _cover
from . import ip as _ip
from . import cavity_lock as _cavity_lock
from . import seal_type as _seal_type
from . import cpa_lock_type as _cpa_lock_type

from ...geometry import point as _point
from ...geometry import angle as _angle

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, FamilyMixin,
                     SeriesMixin, GenderMixin, ResourceMixin, WeightMixin, CavityLockMixin,
                     TemperatureMixin, DirectionMixin, DimensionMixin, ColorMixin, Model3DMixin,
                     CompatHousingsMixin, CompatSealsMixin, CompatTerminalsMixin)

if TYPE_CHECKING:
    from . import cavity as _cavity


class HousingsTable(TableBase):
    __table_name__ = 'housings'

    def _load_database(self, splash):
        from ..create_database import housings

        data_path = self._con.db_data.open(splash)
        housings.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        from ..create_database import housings

        return housings.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import housings

        housings.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        housings.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import housings

        housings.table.update_fields(self)

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
                'search_params': ['num_pins']
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
              DirectionMixin, DimensionMixin, WeightMixin, CavityLockMixin, Model3DMixin,
              CompatHousingsMixin, CompatSealsMixin, CompatTerminalsMixin):

    _table: HousingsTable = None

    def build_monitor_packet(self):
        color = self.color

        packet = {
            'housings': [self.db_id],
            'families': [self.family_id],
            'series': [self.series_id],
            'genders': [self.gender_id],
            'directions': [self.direction_id],
            'cavity_locks': [self.cavity_lock_id],
            'temperatures': [self.min_temp_id, self.max_temp],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id],
            'models3d': [self.model3d_id]
        }

        self.merge_packet_data(self.manufacturer.build_monitor_packet(), packet)
        self.merge_packet_data(self.ip_rating.build_monitor_packet(), packet)

        return packet

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

    @property
    def compat_covers_array(self) -> list[str]:
        return eval(self._table.select('compat_covers', id=self._db_id)[0][0])

    @compat_covers_array.setter
    def compat_covers_array(self, value: list[str]):
        self._table.update(self._db_id, compat_covers=str(value))
        
    @property
    def compat_boots(self) -> list[_boot.Boot]:
        compat_boots = eval(self._table.select('compat_boots', id=self._db_id)[0][0])
        res = []
        for part_number in compat_boots:
            try:
                res.append(self._table.db.boots_table[part_number])
            except KeyError:
                pass
        return res

    @property
    def compat_boots_array(self) -> list[str]:
        return eval(self._table.select('compat_boots', id=self._db_id)[0][0])

    @compat_boots_array.setter
    def compat_boots_array(self, value: list[str]):
        self._table.update(self._db_id, compat_boots=str(value))

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

    @property
    def compat_cpas_array(self) -> list[str]:
        return eval(self._table.select('compat_cpas', id=self._db_id)[0][0])

    @compat_cpas_array.setter
    def compat_cpas_array(self, value: list[str]):
        self._table.update(self._db_id, compat_cpas=str(value))

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

    @property
    def compat_tpas_array(self) -> list[str]:
        return eval(self._table.select('compat_tpas', id=self._db_id)[0][0])

    @compat_tpas_array.setter
    def compat_tpas_array(self, value: list[str]):
        self._table.update(self._db_id, compat_tpas=str(value))
    
    @property
    def ip_rating(self) -> _ip.IPRating:
        ip_rating_id = self._table.select('ip_rating_id', id=self._db_id)
        return _ip.IPRating(self._table.db.ip_ratings_table, ip_rating_id[0][0])

    @property
    def ip_rating_id(self):
        return self._table.select('ip_rating_id', id=self._db_id)[0][0]

    @ip_rating_id.setter
    def ip_rating_id(self, value):
        self._table.update(self._db_id, ip_rating_id=value)

    @property
    def cavity_lock(self) -> _cavity_lock.CavityLock:
        cavity_lock_id = self.cavity_lock_id
        return self._table.db.cavity_locks_table[cavity_lock_id]

    @property
    def cavity_lock_id(self):
        return self._table.select('cavity_lock_id', id=self._db_id)[0][0]

    @cavity_lock_id.setter
    def cavity_lock_id(self, value):
        self._table.update(self._db_id, cavity_lock_id=value)

    @property
    def seal_type(self) -> _seal_type.SealType:
        seal_type_id = self.seal_type_id
        return self._table.db.seal_types_table[seal_type_id]

    @property
    def seal_type_id(self):
        return self._table.select('seal_type_id', id=self._db_id)[0][0]

    @seal_type_id.setter
    def seal_type_id(self, value):
        self._table.update(self._db_id, seal_type_id=value)

    @property
    def cpa_lock_type(self) -> _cpa_lock_type.CPALockType:
        cpa_lock_type_id = self.cpa_lock_type_id
        return self._table.db.cpa_lock_types_table[cpa_lock_type_id]

    @property
    def cpa_lock_type_id(self):
        return self._table.select('cpa_lock_type_id', id=self._db_id)[0][0]

    @cpa_lock_type_id.setter
    def cpa_lock_type_id(self, value):
        self._table.update(self._db_id, cpa_lock_type_id=value)

    @property
    def terminal_sizes(self) -> list[float]:
        return eval(self._table.select('terminal_sizes', id=self._db_id)[0][0])

    @terminal_sizes.setter
    def terminal_sizes(self, value: list[float]):
        self._table.update(self._db_id, terminal_sizes=str(value))

    @property
    def terminal_size_counts(self) -> list[int]:
        return eval(self._table.select('terminal_size_counts', id=self._db_id)[0][0])

    @terminal_size_counts.setter
    def terminal_size_counts(self, value: list[int]):
        self._table.update(self._db_id, terminal_size_counts=str(value))

    @property
    def sealing(self) -> bool:
        return bool(self._table.select('sealing', id=self._db_id)[0][0])

    @sealing.setter
    def sealing(self, value: bool):
        self._table.update(self._db_id, sealing=int(value))

    @property
    def centerline(self) -> float:
        return self._table.select('centerline', id=self._db_id)[0][0]

    @centerline.setter
    def centerline(self, value: float):
        self._table.update(self._db_id, centerline=value)

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

        rows = self._table.db.cavities_table.select("id", "idx",
                                                        housing_id=self._db_id)

        for db_id, idx in rows:
            res[idx] = self._table.db.cavities_table[db_id]
        return res

    _cover_position3d: str = None
    
    def __update_cover_position3d(self, point: _point.Point):
        self._table.update(self._db_id, cover_point3d=str(list(point.as_float)))
            
    @property
    def cover_position3d(self) -> "_point.Point":
        position_coords = eval(self._table.select('cover_point3d', id=self._db_id)[0][0])
        
        if self._cover_position3d is None:
            self._cover_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._cover_position3d)
        
        position.bind(self.__update_cover_position3d)
                
        return position

    _seal_position3d: str = None
    
    def __update_seal_position3d(self, point: _point.Point):
        self._table.update(self._db_id, seal_point3d=str(list(point.as_float)))
            
    @property
    def seal_position3d(self) -> "_point.Point":
        position_coords = eval(self._table.select('seal_point3d', id=self._db_id)[0][0])
        
        if self._seal_position3d is None:
            self._seal_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._seal_position3d)
        
        position.bind(self.__update_seal_position3d)
                
        return position
    
    _boot_position3d: str = None

    def __update_boot_position3d(self, point: _point.Point):
        self._table.update(self._db_id, boot_point3d=str(list(point.as_float)))
            
    @property
    def boot_position3d(self) -> "_point.Point":
        position_coords = eval(self._table.select('boot_point3d', id=self._db_id)[0][0])
        
        if self._boot_position3d is None:
            self._boot_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._boot_position3d)
        
        position.bind(self.__update_boot_position3d)
                
        return position
    
    _tpa_lock_1_position3d: str = None
    
    def __update_tpa_lock_1_position3d(self, point: _point.Point):
        self._table.update(self._db_id, tpa_lock_1_point3d=str(list(point.as_float)))
            
    @property
    def tpa_lock_1_position3d(self) -> "_point.Point":
        position_coords = eval(self._table.select('tpa_lock_1_point3d', id=self._db_id)[0][0])
        
        if self._tpa_lock_1_position3d is None:
            self._tpa_lock_1_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._tpa_lock_1_position3d)
        
        position.bind(self.__update_tpa_lock_1_position3d)
                
        return position

    _tpa_lock_2_position3d: str = None
    
    def __update_tpa_lock_2_position3d(self, point: _point.Point):
        self._table.update(self._db_id, tpa_lock_2_point3d=str(list(point.as_float)))

    @property
    def tpa_lock_2_position3d(self) -> "_point.Point":
        position_coords = eval(self._table.select('tpa_lock_2_point3d', id=self._db_id)[0][0])
        
        if self._tpa_lock_2_position3d is None:
            self._tpa_lock_2_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._tpa_lock_2_position3d)
        
        position.bind(self.__update_tpa_lock_2_position3d)
                
        return position    

    _cpa_lock_position3d: str = None
    
    def __update_cpa_lock_position3d(self, point: _point.Point):
        self._table.update(self._db_id, cpa_lock_point3d=str(list(point.as_float)))
            
    @property
    def cpa_lock_position3d(self) -> "_point.Point":
        position_coords = eval(self._table.select('cpa_lock_point3d', id=self._db_id)[0][0])
        
        if self._cpa_lock_position3d is None:
            self._cpa_lock_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._cpa_lock_position3d)
        
        position.bind(self.__update_cpa_lock_position3d)
                
        return position

    _angle3d_db_id: str = None

    def __update_angle3d(self, angle: _angle.Angle):
        quat = list(angle.as_quat_float)
        euler_angle = list(angle.as_euler_float)

        self._table.update(self._db_id, quat3d=str(quat))
        self._table.update(self._db_id, angle3d=str(euler_angle))

    @property
    def angle3d(self) -> _angle.Angle:
        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        if self._angle3d_db_id is None:
            self._angle3d_db_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, euler_angle, db_id=self._angle3d_db_id)
        angle.bind(self.__update_angle3d)

        return angle

    @property
    def propgrid(self):
        from ...ui.editor_obj.prop_grid import array_string_prop as _array_string_prop

        part_cat = wxpg.PropertyCategory('Part Attributes')
        
        part_number_prop = self._part_number_propgrid
        manufacturer_prop = self._manufacturer_propgrid
        description_prop = self._description_propgrid
        family_prop = self._family_propgrid
        series_prop = self._series_propgrid
        gender_prop = self._gender_propgrid
        ip_rating_prop = self.ip_rating.propgrid
        color_prop = self._color_propgrid
        direction_prop = self._direction_propgrid
        temperature_prop = self._temperature_propgrid
        dimension_prop = self._dimension_propgrid
        weight_prop = self._weight_propgrid
        resource_prop = self._resource_propgrid
        model3d_prop = self._model3d_propgrid

        accessory_parts_prop = wxpg.PGProperty('Accessory Parts')

        compat_housings_prop = self._compat_housings_propgrid
        compat_terminals_prop = self._compat_terminals_propgrid
        compat_seals_prop = self._compat_seals_propgrid

        compat_tpas_prop = _array_string_prop.ArrayStringProperty(
            'Compatible TPA Locks', 'compat_tpas_array', self.compat_tpas_array)
        compat_cpas_prop = _array_string_prop.ArrayStringProperty(
            'Compatible CPA Locks', 'compat_cpas_array', self.compat_cpas_array)
        compat_boots_prop = _array_string_prop.ArrayStringProperty(
            'Compatible Boots', 'compat_boots_array', self.compat_boots_array)
        compat_covers_prop = _array_string_prop.ArrayStringProperty(
            'Compatible Covers', 'compat_covers_array', self.compat_covers_array)

        from ...ui.editor_obj.prop_grid import position_prop as _position_prop

        cover_position3d_prop = _position_prop.Position3DProperty(
            'Cover Position', 'cover_position3d', self.cover_position3d)

        seal_position3d_prop = _position_prop.Position3DProperty(
            'Seal Position', 'seal_position3d', self.seal_position3d)

        boot_position3d_prop = _position_prop.Position3DProperty(
            'Boot Position', 'boot_position3d', self.boot_position3d)

        tpa_lock_1_position3d_prop = _position_prop.Position3DProperty(
            'TPA Lock 1 Position', 'tpa_lock_1_position3d', self.tpa_lock_1_position3d)

        tpa_lock_2_position3d_prop = _position_prop.Position3DProperty(
            'TPA Lock 2 Position', 'tpa_lock_2_position3d', self.tpa_lock_2_position3d)

        cpa_lock_position3d_prop = _position_prop.Position3DProperty(
            'CPA Lock Position', 'cpa_lock_position3d', self.cpa_lock_position3d)

        from ...ui.editor_obj.prop_grid import array_float_prop as _array_float_prop
        from ...ui.editor_obj.prop_grid import array_int_prop as _array_int_prop
        from ...ui.editor_obj.prop_grid import bool_prop as _bool_prop
        from ...ui.editor_obj.prop_grid import float_prop as _float_prop
        from ...ui.editor_obj.prop_grid import int_prop as _int_prop

        terminal_sizes_prop = _array_float_prop.ArrayFloatProperty(
            'Terminal Sizes', 'terminal_sizes', self.terminal_sizes)

        terminal_size_counts_prop = _array_int_prop.ArrayIntProperty(
            'Terminal Size Counts', 'terminal_size_counts', self.terminal_size_counts)

        centerline_prop = _float_prop.FloatProperty(
            'Pitch', 'centerline', self.centerline, min_value=0.01,
            max_value=999.9, increment=0.01, units='mm')

        rows_prop = _int_prop.IntProperty(
            'Rows', 'rows', self.rows, min_value=1, max_value=999)

        num_pins_prop = _int_prop.IntProperty(
            'Pin Count', 'num_pins', self.num_pins, min_value=1, max_value=999)

        cavity_lock_prop = self._cavity_lock_propgrid

        terminal_prop = wxpg.PGProperty('Terminals')
        terminal_prop.AppendChild(compat_terminals_prop)
        terminal_prop.AppendChild(cavity_lock_prop)
        terminal_prop.AppendChild(terminal_sizes_prop)
        terminal_prop.AppendChild(terminal_size_counts_prop)
        terminal_prop.AppendChild(centerline_prop)
        terminal_prop.AppendChild(rows_prop)
        terminal_prop.AppendChild(num_pins_prop)

        housings_prop = wxpg.PGProperty('Housings')
        housings_prop.AppendChild(compat_housings_prop)
        accessory_parts_prop.AppendChild(housings_prop)

        sealing_prop = _bool_prop.BoolProperty(
            'Sealing', 'sealing', self.sealing)
        seal_type_prop = self.seal_type.propgrid

        seals_prop = wxpg.PGProperty('Seals')
        seals_prop.AppendChild(compat_seals_prop)
        seals_prop.AppendChild(sealing_prop)
        seals_prop.AppendChild(seal_type_prop)
        seals_prop.AppendChild(seal_position3d_prop)
        accessory_parts_prop.AppendChild(seals_prop)

        tpas_prop = wxpg.PGProperty('TPA Locks')
        tpas_prop.AppendChild(compat_tpas_prop)
        tpas_prop.AppendChild(tpa_lock_1_position3d_prop)
        tpas_prop.AppendChild(tpa_lock_2_position3d_prop)
        accessory_parts_prop.AppendChild(tpas_prop)

        cpa_lock_type_prop = self.cpa_lock_type.propgrid

        cpas_prop = wxpg.PGProperty('CPA Locks')
        cpas_prop.AppendChild(compat_cpas_prop)
        cpas_prop.AppendChild(cpa_lock_type_prop)
        cpas_prop.AppendChild(cpa_lock_position3d_prop)
        accessory_parts_prop.AppendChild(cpas_prop)

        boots_prop = wxpg.PGProperty('Boots')
        boots_prop.AppendChild(compat_boots_prop)
        boots_prop.AppendChild(boot_position3d_prop)
        accessory_parts_prop.AppendChild(boots_prop)

        covers_prop = wxpg.PGProperty('Covers')
        covers_prop.AppendChild(compat_covers_prop)
        covers_prop.AppendChild(cover_position3d_prop)
        accessory_parts_prop.AppendChild(covers_prop)

        from ...ui.editor_obj.prop_grid import angle_prop as _angle_prop

        angle3d_prop = _angle_prop.Angle3DProperty(
            'Housing Angle', 'angle3d', self.angle3d)

        part_cat.AppendChild(part_number_prop)
        part_cat.AppendChild(manufacturer_prop)
        part_cat.AppendChild(description_prop)
        part_cat.AppendChild(family_prop)
        part_cat.AppendChild(series_prop)
        part_cat.AppendChild(ip_rating_prop)
        part_cat.AppendChild(gender_prop)
        part_cat.AppendChild(color_prop)
        part_cat.AppendChild(direction_prop)
        part_cat.AppendChild(temperature_prop)
        part_cat.AppendChild(dimension_prop)
        part_cat.AppendChild(weight_prop)
        part_cat.AppendChild(resource_prop)
        part_cat.AppendChild(model3d_prop)
        part_cat.AppendChild(accessory_parts_prop)
        part_cat.AppendChild(angle3d_prop)

        return part_cat
