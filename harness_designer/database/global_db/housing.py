from typing import Iterable as _Iterable, TYPE_CHECKING

import uuid
import wx
from ...ui.editor_obj import prop_grid as _prop_grid

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

from .mixins import (
    PartNumberMixin, PartNumberControl,
    ManufacturerMixin, ManufacturerControl,
    DescriptionMixin, DescriptionControl,
    FamilyMixin, FamilyControl,
    SeriesMixin, SeriesControl,
    GenderMixin, GenderControl,
    ResourceMixin, ResourcesControl,
    WeightMixin, WeightControl,
    CavityLockMixin, CavityLockControl,
    TemperatureMixin, TemperatureControl,
    DirectionMixin, DirectionControl,
    DimensionMixin, DimensionControl,
    ColorMixin, ColorControl,
    Model3DMixin,
    CompatHousingsMixin, CompatHousingsControl,
    CompatSealsMixin, CompatSealsControl,
    CompatTerminalsMixin, CompatTerminalsControl
)

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
            'temperatures': [self.min_temp_id, self.max_temp_id],
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
        compat_covers = self.compat_covers_array
        res = []
        for part_number in compat_covers:
            try:
                res.append(self._table.db.covers_table[part_number])
            except KeyError:
                pass
        return res

    @property
    def compat_covers_array(self) -> list[str]:
        value = self._table.select('compat_covers', id=self._db_id)[0][0]
        return value[1:-1].split(', ')

    @compat_covers_array.setter
    def compat_covers_array(self, value: list[str]):
        value = f'[{", ".join(value)}]'
        self._table.update(self._db_id, compat_covers=value)

    @property
    def compat_boots(self) -> list[_boot.Boot]:
        compat_boots = self.compat_boots_array
        res = []
        for part_number in compat_boots:
            try:
                res.append(self._table.db.boots_table[part_number])
            except KeyError:
                pass
        return res

    @property
    def compat_boots_array(self) -> list[str]:
        value = self._table.select('compat_boots', id=self._db_id)[0][0]
        return value[1:-1].split(', ')

    @compat_boots_array.setter
    def compat_boots_array(self, value: list[str]):
        value = f'[{", ".join(value)}]'
        self._table.update(self._db_id, compat_boots=value)

    @property
    def compat_cpas(self) -> list[_cpa_lock.CPALock]:
        compat_cpas = self.compat_cpas_array
        res = []
        for part_number in compat_cpas:
            try:
                res.append(self._table.db.cpa_locks_table[part_number])
            except KeyError:
                pass
        return res

    @property
    def compat_cpas_array(self) -> list[str]:
        value = self._table.select('compat_cpas', id=self._db_id)[0][0]
        return value[1:-1].split(', ')

    @compat_cpas_array.setter
    def compat_cpas_array(self, value: list[str]):
        value = f'[{", ".join(value)}]'
        self._table.update(self._db_id, compat_cpas=value)

    @property
    def compat_tpas(self) -> list[_tpa_lock.TPALock]:
        compat_tpas = self.compat_tpas_array
        res = []
        for part_number in compat_tpas:
            try:
                res.append(self._table.db.tpa_locks_table[part_number])
            except KeyError:
                pass
        return res

    @property
    def compat_tpas_array(self) -> list[str]:
        value = self._table.select('compat_tpas', id=self._db_id)[0][0]
        return value[1:-1].split(', ')

    @compat_tpas_array.setter
    def compat_tpas_array(self, value: list[str]):
        value = f'[{", ".join(value)}]'
        self._table.update(self._db_id, compat_tpas=value)
    
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


class HousingControl(wx.Notebook):

    def set_obj(self, db_obj: Housing):
        self.manufacturer_page.set_obj(db_obj)
        self.family_page.set_obj(db_obj)
        self.series_page.set_obj(db_obj)
        self.resources_page.set_obj(db_obj)
        self.dimensions_page.set_obj(db_obj)
        self.cavity_lock_page.set_obj(db_obj)
        self.temperature_page.set_obj(db_obj)

        self.weight_ctrl.set_obj(db_obj)
        self.part_number_ctrl.set_obj(db_obj)
        self.description_ctrl.set_obj(db_obj)
        self.gender_ctrl.set_obj(db_obj)
        self.color_ctrl.set_obj(db_obj)
        self.direction_ctrl.set_obj(db_obj)
        self.compat_housings_ctrl.set_obj(db_obj)
        self.compat_terminals_ctrl.set_obj(db_obj)
        self.compat_seals_ctrl.set_obj(db_obj)

        db_obj.table.execute('SELECT name FROM seal_types;')
        rows = db_obj.table.fetchall()

        self.seal_type_choices = sorted([item[0] for item in rows])
        self.seal_type_ctrl.SetItems(self.seal_type_choices)
        self.seal_type_ctrl.SetValue(db_obj.seal_type.name)

        self.sealing_ctrl.SetValue(db_obj.sealing)

        self.compat_tpas_ctrl.SetValue(db_obj.compat_tpas_array)
        self.compat_cpas_ctrl.SetValue(db_obj.compat_cpas_array)
        self.compat_boots_ctrl.SetValue(db_obj.compat_boots_array)
        self.compat_covers_ctrl.SetValue(db_obj.compat_covers_array)

        self.seal_ctrl.SetValue(db_obj.seal_position3d)
        self.tpa_lock_1_ctrl.SetValue(db_obj.tpa_lock_1_position3d)
        self.tpa_lock_2_ctrl.SetValue(db_obj.tpa_lock_2_position3d)
        self.cpa_lock_ctrl.SetValue(db_obj.cpa_lock_position3d)
        self.boot_ctrl.SetValue(db_obj.boot_position3d)
        self.cover_ctrl.SetValue(db_obj.cover_position3d)

        self.terminal_sizes_ctrl.SetValue(db_obj.terminal_sizes)
        self.terminal_size_count_ctrl.SetValue(db_obj.terminal_size_counts)
        self.pitch_ctrl.SetValue(db_obj.centerline)
        self.rows_ctrl.SetValue(db_obj.rows)
        self.pin_count_ctrl.SetValue(db_obj.num_pins)

        self.angle_ctrl.SetValue(db_obj.angle3d)

    def _on_seal_type(self, evt):
        name = evt.GetValue()
        self.db_obj.table.execute('SELECT id FROM seal_types WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.seal_types_table.insert(name)
            db_id = db_obj.db_id

            self.seal_type_choices.append(name)
            self.seal_type_choices.sort()

            self.seal_type_ctrl.SetItems(self.seal_type_choices)
            self.seal_type_ctrl.SetValue(name)

        self.db_obj.seal_type_id = db_id

    def _on_sealing(self, evt):
        value = evt.GetValue()
        self.db_obj.sealing = value

    def _on_compat_tpas(self, evt: _prop_grid.PropertyEvent):
        compat_tpas = evt.GetValue()
        self.db_obj.compat_tpas_array = compat_tpas

    def _on_compat_cpas(self, evt: _prop_grid.PropertyEvent):
        compat_cpas = evt.GetValue()
        self.db_obj.compat_cpas_array = compat_cpas

    def _on_compat_boots(self, evt: _prop_grid.PropertyEvent):
        compat_boots = evt.GetValue()
        self.db_obj.compat_boots_array = compat_boots

    def _on_compat_covers(self, evt: _prop_grid.PropertyEvent):
        compat_covers = evt.GetValue()
        self.db_obj.compat_covers_array = compat_covers

    def _on_terminal_sizes(self, evt):
        self.db_obj.terminal_sizes = evt.GetValue()

    def _on_terminal_size_count(self, evt):
        self.db_obj.terminal_size_counts = evt.GetValue()

    def _on_pitch(self, evt):
        self.db_obj.centerline = evt.GetValue()

    def _on_rows(self, evt):
        self.db_obj.rows = evt.GetValue()

    def _on_pin_count(self, evt):
        self.db_obj.num_pins = evt.GetValue()

    def __init__(self, parent):
        self.db_obj: Housing = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        self.manufacturer_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.resources_page = ResourcesControl(self)
        self.dimensions_page = DimensionControl(self)
        self.cavity_lock_page = CavityLockControl(self)
        self.temperature_page = TemperatureControl(self)

        self.weight_ctrl = WeightControl(self.dimensions_page)

        general_page = _prop_grid.Category(self, 'General')
        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.gender_ctrl = GenderControl(general_page)
        self.color_ctrl = ColorControl(general_page)
        self.direction_ctrl = DirectionControl(general_page)
        self.angle_ctrl = _prop_grid.Angle3DProperty(general_page, '3D Angle')

        housings_page = _prop_grid.Category(self, 'Housings')
        self.compat_housings_ctrl = CompatHousingsControl(housings_page)

        terminal_page = _prop_grid.Category(self, 'Terminals')
        self.compat_terminals_ctrl = CompatTerminalsControl(terminal_page)

        self.terminal_sizes_ctrl = _prop_grid.ArrayFloatProperty(
            terminal_page, 'Terminal Sizes', [])
        self.terminal_sizes_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_terminal_sizes)

        self.terminal_size_count_ctrl = _prop_grid.ArrayIntProperty(
            terminal_page, 'Terminal Size Counts', [])
        self.terminal_size_count_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_terminal_size_count)

        self.pitch_ctrl = _prop_grid.FloatProperty(
            terminal_page, 'Pitch', 0.01, min_value=0.01,
            max_value=999.9, increment=0.01, units='mm')
        self.pitch_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_pitch)

        self.rows_ctrl = _prop_grid.IntProperty(
            terminal_page, 'Rows', 1, min_value=1, max_value=999)
        self.rows_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_rows)

        self.pin_count_ctrl = _prop_grid.IntProperty(
            terminal_page, 'Pin Count', 1, min_value=1, max_value=999)

        self.pin_count_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_pin_count)

        seals_page = _prop_grid.Category(self, 'Seals')

        self.compat_seals_ctrl = CompatSealsControl(seals_page)

        self.sealing_ctrl = _prop_grid.BoolProperty(seals_page, 'Sealing', False)
        self.sealing_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_sealing)

        self.seal_type_choices: list[str] = []
        self.seal_type_ctrl = _prop_grid.ComboBoxProperty(
            seals_page, 'Seal Type', '', self.seal_type_choices)
        self.seal_type_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_seal_type)

        self.seal_ctrl = _prop_grid.Position3DProperty(seals_page, 'Seal')

        tpas_page = _prop_grid.Category(self, 'TPA Locks')

        self.compat_tpas_ctrl = _prop_grid.ArrayStringProperty(tpas_page, 'Compatible TPA Locks', [])
        self.compat_tpas_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_compat_tpas)

        self.tpa_lock_1_ctrl = _prop_grid.Position3DProperty(tpas_page, 'TPA Lock 1')
        self.tpa_lock_2_ctrl = _prop_grid.Position3DProperty(tpas_page, 'TPA Lock 2')

        cpas_page = _prop_grid.Category(self, 'CPA Locks')

        self.compat_cpas_ctrl = _prop_grid.ArrayStringProperty(cpas_page, 'Compatible CPA Locks', [])
        self.compat_cpas_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_compat_cpas)

        self.cpa_lock_ctrl = _prop_grid.Position3DProperty(cpas_page, 'CPA Lock')

        boots_page = _prop_grid.Category(self, 'Boots')

        self.compat_boots_ctrl = _prop_grid.ArrayStringProperty(boots_page, 'Compatible Boots', [])
        self.compat_boots_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_compat_boots)
        self.boot_ctrl = _prop_grid.Position3DProperty(boots_page, 'Boot')

        covers_page = _prop_grid.Category(self, 'Covers')

        self.compat_covers_ctrl = _prop_grid.ArrayStringProperty(covers_page, 'Compatible Covers', [])
        self.compat_covers_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_compat_covers)
        self.cover_ctrl = _prop_grid.Position3DProperty(covers_page, 'Cover')

        for page in (
            general_page,
            self.manufacturer_page,
            self.series_page,
            self.family_page,
            self.dimensions_page,
            self.temperature_page,
            self.cavity_lock_page,
            self.resources_page,
            housings_page,
            terminal_page,
            seals_page,
            tpas_page,
            cpas_page,
            boots_page,
            covers_page
        ):

            self.AddPage(page, page.GetName())
