# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QTabWidget
from typing import Iterable as _Iterable, TYPE_CHECKING

import uuid

from ...ui import prop_ctrls as _prop_ctrls
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
    Model3DMixin, Model3DControl,
    CompatHousingsMixin, CompatHousingsControl,
    CompatSealsMixin, CompatSealsControl,
    CompatTerminalsMixin, CompatTerminalsControl
)

if TYPE_CHECKING:
    from . import cavity as _cavity


class HousingsTable(TableBase):
    """Represent a housings table in :mod:`harness_designer.database.global_db.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'housings'

    _control: "HousingControl" = None

    @property
    def control(self) -> "HousingControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`HousingControl`
        """
        if self._control is None:
            self._control = HousingControl(self.db.mainframe)
            self._control.hide()
        return self._control

    def _load_database(self, splash):
        """Load the database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import housings

        data_path = self._con.db_data.open(splash)
        housings.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import housings

        return housings.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import housings

        housings.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        housings.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import housings

        housings.table.update_fields(self)

    def __iter__(self) -> _Iterable["Housing"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Housing']
        """

        for db_id in TableBase.__iter__(self):
            yield Housing(self, db_id)

    def __getitem__(self, item) -> "Housing":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Housing`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Housing(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Housing(self, db_id[0][0])

        raise KeyError(item)

    def get_compat(self, seal: str = None, terminal: str = None,
                   cpa_lock: str = None, tpa_lock: str = None,
                   cover: str = None):
        """Return the compat.

        UNKNOWN details are inferred from the callable name and signature.

        :param seal: Value for ``seal``.
        :type seal: str
        :param terminal: Value for ``terminal``.
        :type terminal: str
        :param cpa_lock: Value for ``cpa_lock``.
        :type cpa_lock: str
        :param tpa_lock: Value for ``tpa_lock``.
        :type tpa_lock: str
        :param cover: Value for ``cover``.
        :type cover: str
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        res = []

        if seal is not None:
            part_number = seal
            field_name = 'compat_seals'

        elif terminal is not None:
            part_number = terminal
            field_name = 'compat_terminals'

        elif cpa_lock is not None:
            part_number = cpa_lock
            field_name = 'compat_cpas'

        elif tpa_lock is not None:
            part_number = tpa_lock
            field_name = 'compat_tpas'

        elif cover is not None:
            part_number = cover
            field_name = 'compat_covers'
        else:
            return []

        self.execute(f'SELECT id, {field_name} FROM housings WHERE {field_name} LIKE "%{part_number}%";')
        rows = self.fetchall()
        for db_id, compat in rows:
            compat = compat[1:-1].split(', ')

            if part_number not in compat:
                continue

            res.append(db_id)

        return res

    def insert(self, part_number: str, mfg_id: int, description: str, family_id: int, series_id: int,
               gender_id: int, ip_rating_id: int, image_id: int, datasheet_id: int, cad_id: int,
               min_temp_id: int, max_temp_id: int, cavity_lock_id: int, direction_id: int, sealed: bool,
               length: float, width: float, height: float, centerline: float, color_id: int, rows: int,
               num_pins: int, terminal_sizes: list[float], compat_cpas: list[str], compat_tpas: list[str],
               compat_covers: list[str], compat_terminals: list[str], compat_seals: list[str],
               compat_housings: list[str], weight: float) -> "Housing":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_number: Value for ``part_number``.
        :type part_number: str
        :param mfg_id: Identifier for the mfg.
        :type mfg_id: int
        :param description: Value for ``description``.
        :type description: str
        :param family_id: Identifier for the family.
        :type family_id: int
        :param series_id: Identifier for the series.
        :type series_id: int
        :param gender_id: Identifier for the gender.
        :type gender_id: int
        :param ip_rating_id: Identifier for the ip rating.
        :type ip_rating_id: int
        :param image_id: Identifier for the image.
        :type image_id: int
        :param datasheet_id: Identifier for the datasheet.
        :type datasheet_id: int
        :param cad_id: Identifier for the cad.
        :type cad_id: int
        :param min_temp_id: Identifier for the min temp.
        :type min_temp_id: int
        :param max_temp_id: Identifier for the max temp.
        :type max_temp_id: int
        :param cavity_lock_id: Identifier for the cavity lock.
        :type cavity_lock_id: int
        :param direction_id: Identifier for the direction.
        :type direction_id: int
        :param sealed: Value for ``sealed``.
        :type sealed: bool
        :param length: Value for ``length``.
        :type length: float
        :param width: Value for ``width``.
        :type width: float
        :param height: Value for ``height``.
        :type height: float
        :param centerline: Value for ``centerline``.
        :type centerline: float
        :param color_id: Identifier for the color.
        :type color_id: int
        :param rows: Value for ``rows``.
        :type rows: int
        :param num_pins: Value for ``num_pins``.
        :type num_pins: int
        :param terminal_sizes: Value for ``terminal_sizes``.
        :type terminal_sizes: list[float]
        :param compat_cpas: Value for ``compat_cpas``.
        :type compat_cpas: list[str]
        :param compat_tpas: Value for ``compat_tpas``.
        :type compat_tpas: list[str]
        :param compat_covers: Value for ``compat_covers``.
        :type compat_covers: list[str]
        :param compat_terminals: Value for ``compat_terminals``.
        :type compat_terminals: list[str]
        :param compat_seals: Value for ``compat_seals``.
        :type compat_seals: list[str]
        :param compat_housings: Value for ``compat_housings``.
        :type compat_housings: list[str]
        :param weight: Value for ``weight``.
        :type weight: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Housing`
        """

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
        """Return the search items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: dict
        """
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
    """Represent a housing in :mod:`harness_designer.database.global_db.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: HousingsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
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
        """Return the compat covers.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_cover.Cover]
        """
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
        """Return the compat covers array.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        value = self._table.select('compat_covers', id=self._db_id)[0][0]

        if value.startswith('['):
            value = value[1:-1]

        return value.split(', ')

    @compat_covers_array.setter
    def compat_covers_array(self, value: list[str]):
        """Set the compat covers array.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """
        value = ", ".join(value)
        self._table.update(self._db_id, compat_covers=value)
        self._populate('compat_covers_array')

    @property
    def compat_boots(self) -> list[_boot.Boot]:
        """Return the compat boots.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_boot.Boot]
        """
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
        """Return the compat boots array.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        value = self._table.select('compat_boots', id=self._db_id)[0][0]

        if value.startswith('['):
            value = value[1:-1]

        return value.split(', ')

    @compat_boots_array.setter
    def compat_boots_array(self, value: list[str]):
        """Set the compat boots array.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """
        value = ", ".join(value)
        self._table.update(self._db_id, compat_boots=value)
        self._populate('compat_boots_array')

    @property
    def compat_cpas(self) -> list[_cpa_lock.CPALock]:
        """Return the compat cpas.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_cpa_lock.CPALock]
        """
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
        """Return the compat cpas array.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        value = self._table.select('compat_cpas', id=self._db_id)[0][0]

        if value.startswith('['):
            value = value[1:-1]

        return value.split(', ')

    @compat_cpas_array.setter
    def compat_cpas_array(self, value: list[str]):
        """Set the compat cpas array.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """

        value = ', '.join(value)
        self._table.update(self._db_id, compat_cpas=value)

        self._populate('compat_cpas_array')

    @property
    def compat_tpas(self) -> list[_tpa_lock.TPALock]:
        """Return the compat tpas.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_tpa_lock.TPALock]
        """

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
        """Return the compat tpas array.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """

        value = self._table.select('compat_tpas', id=self._db_id)[0][0]
        return value[1:-1].split(', ')

    @compat_tpas_array.setter
    def compat_tpas_array(self, value: list[str]):
        """Set the compat tpas array.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """

        value = f'[{", ".join(value)}]'
        self._table.update(self._db_id, compat_tpas=value)
        self._populate('compat_tpas_array')

    @property
    def ip_rating(self) -> _ip.IPRating:
        """Return the ip rating.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_ip.IPRating`
        """

        ip_rating_id = self._table.select('ip_rating_id', id=self._db_id)
        return _ip.IPRating(self._table.db.ip_ratings_table, ip_rating_id[0][0])

    @property
    def ip_rating_id(self):
        """Return the ip rating ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        return self._table.select('ip_rating_id', id=self._db_id)[0][0]

    @ip_rating_id.setter
    def ip_rating_id(self, value):
        """Set the ip rating ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """

        self._table.update(self._db_id, ip_rating_id=value)
        self._populate('ip_rating_id')

    @property
    def cavity_lock(self) -> _cavity_lock.CavityLock:
        """Return the cavity lock.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_cavity_lock.CavityLock`
        """

        cavity_lock_id = self.cavity_lock_id
        return self._table.db.cavity_locks_table[cavity_lock_id]

    @property
    def cavity_lock_id(self):
        """Return the cavity lock ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        return self._table.select('cavity_lock_id', id=self._db_id)[0][0]

    @cavity_lock_id.setter
    def cavity_lock_id(self, value):
        """Set the cavity lock ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """

        self._table.update(self._db_id, cavity_lock_id=value)
        self._populate('cavity_lock_id')

    @property
    def seal_type(self) -> _seal_type.SealType:
        """Return the seal type.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_seal_type.SealType`
        """

        seal_type_id = self.seal_type_id
        return self._table.db.seal_types_table[seal_type_id]

    @property
    def seal_type_id(self):
        """Return the seal type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        return self._table.select('seal_type_id', id=self._db_id)[0][0]

    @seal_type_id.setter
    def seal_type_id(self, value):
        """Set the seal type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """

        self._table.update(self._db_id, seal_type_id=value)
        self._populate('seal_type_id')

    @property
    def cpa_lock_type(self) -> _cpa_lock_type.CPALockType:
        """Return the CPA lock type.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_cpa_lock_type.CPALockType`
        """

        cpa_lock_type_id = self.cpa_lock_type_id
        return self._table.db.cpa_lock_types_table[cpa_lock_type_id]

    @property
    def cpa_lock_type_id(self):
        """Return the CPA lock type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        return self._table.select('cpa_lock_type_id', id=self._db_id)[0][0]

    @cpa_lock_type_id.setter
    def cpa_lock_type_id(self, value):
        """Set the CPA lock type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """

        self._table.update(self._db_id, cpa_lock_type_id=value)
        self._populate('cpa_lock_type_id')

    @property
    def terminal_sizes(self) -> list[float]:
        """Return the terminal sizes.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[float]
        """

        value = self._table.select('terminal_sizes', id=self._db_id)[0][0]

        if not value.startswith('['):
            value = f'[{value}]'

        return eval(value)

    @terminal_sizes.setter
    def terminal_sizes(self, value: list[float]):
        """Set the terminal sizes.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[float]
        """
        self._table.update(self._db_id, terminal_sizes=str(value)[1:-1])
        self._populate('terminal_sizes')

    @property
    def terminal_size_counts(self) -> list[int]:
        """Return the terminal size counts.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[int]
        """

        value = self._table.select('terminal_size_counts', id=self._db_id)[0][0]

        if not value.startswith('['):
            value = f'[{value}]'

        return eval(value)

    @terminal_size_counts.setter
    def terminal_size_counts(self, value: list[int]):
        """Set the terminal size counts.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[int]
        """
        self._table.update(self._db_id, terminal_size_counts=str(value)[1:-1])
        self._populate('terminal_size_counts')

    @property
    def sealing(self) -> bool:
        """Return the sealing.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self._table.select('sealing', id=self._db_id)[0][0])

    @sealing.setter
    def sealing(self, value: bool):
        """Set the sealing.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, sealing=int(value))
        self._populate('sealing')

    @property
    def centerline(self) -> float:
        """Return the centerline.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('centerline', id=self._db_id)[0][0]

    @centerline.setter
    def centerline(self, value: float):
        """Set the centerline.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, centerline=value)
        self._populate('centerline')

    @property
    def rows(self) -> int:
        """Return the rows.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('rows', id=self._db_id)[0][0]

    @rows.setter
    def rows(self, value: int):
        """Set the rows.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, rows=value)
        self._populate('rows')

    @property
    def num_pins(self) -> int:
        """Return the num pins.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('num_pins', id=self._db_id)[0][0]

    @num_pins.setter
    def num_pins(self, value: int):
        """Set the num pins.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, num_pins=value)
        self._populate('num_pins')

    @property
    def cavities(self) -> list["_cavity.Cavity"]:
        """Return the cavities.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_cavity.Cavity']
        """

        num_pins = self.num_pins

        res = [None] * num_pins

        rows = self._table.db.cavities_table.select(
            "id", "idx", housing_id=self._db_id)
        #
        # indexes = [row[1] for row in rows]
        # high_index = max(indexes)
        #
        # cavity_count = len(indexes)
        #
        # if high_index > cavity_count < num_pins < high_index:
        #     inds = [None] * high_index
        #     for idx in indexes:
        #         inds[idx] = idx
        #
        #     while None in indexes:
        #         indexes.remove(None)
        #
        #     for new_index, old_index in enumerate(inds):
        #         new_index += 1
        #         if new_index != old_index:
        #             for db_id, db_index in rows:
        #                 if db_index != old_index:
        #                     continue
        #
        #                 self._table.db.cavities_table.update(
        #                     db_id, idx=new_index, housing_id=self._db_id)
        #                 break
        #
        #     rows = self._table.db.cavities_table.select(
        #         "id", "idx", housing_id=self._db_id)

        for db_id, idx in rows:
            res[idx] = self._table.db.cavities_table[db_id]

        return res

    _cover_position3d: str = None
    
    def __update_cover_position3d(self, point: _point.Point):
        """Update the cover position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        self._table.update(self._db_id, cover_point3d=str(list(point.as_float)))
        self._populate('cover_position3d')

    @property
    def cover_position3d(self) -> "_point.Point":
        """Return the cover position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        position_coords = eval(self._table.select('cover_point3d', id=self._db_id)[0][0])
        
        if self._cover_position3d is None:
            self._cover_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._cover_position3d)
        
        position.bind(self.__update_cover_position3d)
                
        return position

    _seal_position3d: str = None
    
    def __update_seal_position3d(self, point: _point.Point):
        """Update the seal position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        self._table.update(self._db_id, seal_point3d=str(list(point.as_float)))
        self._populate('seal_position3d')

    @property
    def seal_position3d(self) -> "_point.Point":
        """Return the seal position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        position_coords = eval(self._table.select('seal_point3d', id=self._db_id)[0][0])
        
        if self._seal_position3d is None:
            self._seal_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._seal_position3d)
        
        position.bind(self.__update_seal_position3d)
                
        return position
    
    _boot_position3d: str = None

    def __update_boot_position3d(self, point: _point.Point):
        """Update the boot position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        self._table.update(self._db_id, boot_point3d=str(list(point.as_float)))
        self._populate('boot_position3d')

    @property
    def boot_position3d(self) -> "_point.Point":
        """Return the boot position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        position_coords = eval(self._table.select('boot_point3d', id=self._db_id)[0][0])
        
        if self._boot_position3d is None:
            self._boot_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._boot_position3d)
        
        position.bind(self.__update_boot_position3d)
                
        return position
    
    _tpa_lock_1_position3d: str = None
    
    def __update_tpa_lock_1_position3d(self, point: _point.Point):
        """Update the TPA lock 1 position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        self._table.update(self._db_id, tpa_lock_1_point3d=str(list(point.as_float)))
        self._populate('tpa_lock_1_position3d')

    @property
    def tpa_lock_1_position3d(self) -> "_point.Point":
        """Return the TPA lock 1 position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        position_coords = eval(self._table.select('tpa_lock_1_point3d', id=self._db_id)[0][0])
        
        if self._tpa_lock_1_position3d is None:
            self._tpa_lock_1_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._tpa_lock_1_position3d)
        
        position.bind(self.__update_tpa_lock_1_position3d)
                
        return position

    _tpa_lock_2_position3d: str = None
    
    def __update_tpa_lock_2_position3d(self, point: _point.Point):
        """Update the TPA lock 2 position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        self._table.update(self._db_id, tpa_lock_2_point3d=str(list(point.as_float)))
        self._populate('tpa_lock_2_position3d')

    @property
    def tpa_lock_2_position3d(self) -> "_point.Point":
        """Return the TPA lock 2 position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        position_coords = eval(self._table.select('tpa_lock_2_point3d', id=self._db_id)[0][0])
        
        if self._tpa_lock_2_position3d is None:
            self._tpa_lock_2_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._tpa_lock_2_position3d)
        
        position.bind(self.__update_tpa_lock_2_position3d)
                
        return position    

    _cpa_lock_position3d: str = None
    
    def __update_cpa_lock_position3d(self, point: _point.Point):
        """Update the CPA lock position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        self._table.update(self._db_id, cpa_lock_point3d=str(list(point.as_float)))
        self._populate('cpa_lock_position3d')

    @property
    def cpa_lock_position3d(self) -> "_point.Point":
        """Return the CPA lock position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        position_coords = eval(self._table.select('cpa_lock_point3d', id=self._db_id)[0][0])
        
        if self._cpa_lock_position3d is None:
            self._cpa_lock_position3d = str(uuid.uuid4())
        
        position = _point.Point(*position_coords, db_id=self._cpa_lock_position3d)
        
        position.bind(self.__update_cpa_lock_position3d)
                
        return position

    _angle3d_db_id: str = None

    def __update_angle3d(self, angle: _angle.Angle):
        """Update the angle 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        quat = str(list(angle.as_quat_float))
        euler = str(list(angle.as_euler_float))

        if 'nan' in euler or 'nan' in quat:
            return

        self._table.update(self._db_id, quat3d=quat)
        self._table.update(self._db_id, angle3d=euler)
        self._populate('angle3d')

    @property
    def angle3d(self) -> _angle.Angle:
        """Return the angle 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_angle.Angle`
        """
        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        if self._angle3d_db_id is None:
            self._angle3d_db_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, euler_angle, db_id=self._angle3d_db_id)
        angle.bind(self.__update_angle3d)

        return angle


class HousingControl(QTabWidget):
    """Represent a housing control in :mod:`harness_designer.database.global_db.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: Housing):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Housing`
        """
        self.manufacturer_page.set_obj(db_obj)
        self.family_page.set_obj(db_obj)
        self.series_page.set_obj(db_obj)
        self.resources_page.set_obj(db_obj)
        self.dimensions_page.set_obj(db_obj)
        self.cavity_lock_page.set_obj(db_obj)
        self.temperature_page.set_obj(db_obj)
        self.model3d_page.set_obj(db_obj)

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

        for i in range(self.cavities_notebook.count()):
            self.cavities_notebook.removeTab(i)

        for page in self.cavity_pages:
            page.setParent(db_obj.table.db.mainframe)
            page.hide()

        self.cavity_pages = []

        for i, cavity in enumerate(db_obj.cavities):
            if cavity is None:
                continue

            ctrl = db_obj.table.db.cavities_table.get_control(i)
            ctrl.setParent(self.cavities_notebook)
            self.cavities_notebook.addTab(ctrl, ctrl.GetLabel())
            ctrl.set_obj(cavity)
            self.cavity_pages.append(ctrl)

    def _on_seal_type(self, evt):
        """Handle the seal type event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
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
        """Handle the sealing event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.sealing = value

    def _on_compat_tpas(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the compat tpas event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        compat_tpas = evt.GetValue()
        self.db_obj.compat_tpas_array = compat_tpas

    def _on_compat_cpas(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the compat cpas event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        compat_cpas = evt.GetValue()
        self.db_obj.compat_cpas_array = compat_cpas

    def _on_compat_boots(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the compat boots event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        compat_boots = evt.GetValue()
        self.db_obj.compat_boots_array = compat_boots

    def _on_compat_covers(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the compat covers event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        compat_covers = evt.GetValue()
        self.db_obj.compat_covers_array = compat_covers

    def _on_terminal_sizes(self, evt):
        """Handle the terminal sizes event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.terminal_sizes = evt.GetValue()

    def _on_terminal_size_count(self, evt):
        """Handle the terminal size count event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.terminal_size_counts = evt.GetValue()

    def _on_pitch(self, evt):
        """Handle the pitch event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.centerline = evt.GetValue()

    def _on_rows(self, evt):
        """Handle the rows event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.rows = evt.GetValue()

    def _on_pin_count(self, evt):
        """Handle the pin count event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.num_pins = evt.GetValue()

    def __init__(self, parent):
        """Initialise the :class:`HousingControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Housing = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self.manufacturer_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.resources_page = ResourcesControl(self)
        self.dimensions_page = DimensionControl(self)
        self.cavity_lock_page = CavityLockControl(self)
        self.temperature_page = TemperatureControl(self)

        self.weight_ctrl = WeightControl(self.dimensions_page)

        self.dimensions_page.addWidget(self.weight_ctrl)

        general_page = _prop_ctrls.Category(self, 'General')
        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.gender_ctrl = GenderControl(general_page)
        self.color_ctrl = ColorControl(general_page)
        self.direction_ctrl = DirectionControl(general_page)
        self.angle_ctrl = _prop_ctrls.Angle3DProperty(general_page, '3D Angle')

        general_page.addWidget(self.part_number_ctrl)
        general_page.addWidget(self.description_ctrl)
        general_page.addWidget(self.gender_ctrl)
        general_page.addWidget(self.color_ctrl)
        general_page.addWidget(self.direction_ctrl)
        general_page.addWidget(self.angle_ctrl)

        housings_page = _prop_ctrls.Category(self, 'Housings')
        self.compat_housings_ctrl = CompatHousingsControl(housings_page)

        housings_page.addWidget(self.compat_housings_ctrl)

        terminal_page = _prop_ctrls.Category(self, 'Terminals')
        self.compat_terminals_ctrl = CompatTerminalsControl(terminal_page)

        terminal_page.addWidget(self.compat_terminals_ctrl)

        self.terminal_sizes_ctrl = _prop_ctrls.ArrayFloatProperty(
            terminal_page, 'Terminal Sizes')

        terminal_page.addWidget(self.terminal_sizes_ctrl)

        self.terminal_sizes_ctrl.propertyChanged.connect(self._on_terminal_sizes)

        self.terminal_size_count_ctrl = _prop_ctrls.ArrayIntProperty(
            terminal_page, 'Terminal Size Counts')

        terminal_page.addWidget(self.terminal_size_count_ctrl)

        self.terminal_size_count_ctrl.propertyChanged.connect(self._on_terminal_size_count)

        self.pitch_ctrl = _prop_ctrls.FloatProperty(
            terminal_page, 'Pitch', min_value=0.01,
            max_value=999.9, increment=0.01, units='mm')

        terminal_page.addWidget(self.pitch_ctrl)

        self.pitch_ctrl.propertyChanged.connect(self._on_pitch)

        self.rows_ctrl = _prop_ctrls.IntProperty(
            terminal_page, 'Rows', min_value=1, max_value=999)

        terminal_page.addWidget(self.rows_ctrl)

        self.rows_ctrl.propertyChanged.connect(self._on_rows)

        self.pin_count_ctrl = _prop_ctrls.IntProperty(
            terminal_page, 'Pin Count', min_value=1, max_value=999)

        terminal_page.addWidget(self.pin_count_ctrl)

        self.pin_count_ctrl.propertyChanged.connect(self._on_pin_count)

        seals_page = _prop_ctrls.Category(self, 'Seals')

        self.compat_seals_ctrl = CompatSealsControl(seals_page)

        seals_page.addWidget(self.compat_seals_ctrl)

        self.sealing_ctrl = _prop_ctrls.BoolProperty(seals_page, 'Sealing')

        seals_page.addWidget(self.sealing_ctrl)

        self.sealing_ctrl.propertyChanged.connect(self._on_sealing)

        self.seal_type_choices: list[str] = []
        self.seal_type_ctrl = _prop_ctrls.ComboBoxProperty(
            seals_page, 'Seal Type')

        seals_page.addWidget(self.seal_type_ctrl)

        self.seal_type_ctrl.propertyChanged.connect(self._on_seal_type)

        self.seal_ctrl = _prop_ctrls.Position3DProperty(seals_page, 'Seal')

        seals_page.addWidget(self.seal_ctrl)

        tpas_page = _prop_ctrls.Category(self, 'TPA Locks')

        self.compat_tpas_ctrl = _prop_ctrls.ArrayStringProperty(tpas_page, 'Compatible TPA Locks')

        tpas_page.addWidget(self.compat_tpas_ctrl)

        self.compat_tpas_ctrl.propertyChanged.connect(self._on_compat_tpas)

        self.tpa_lock_1_ctrl = _prop_ctrls.Position3DProperty(tpas_page, 'TPA Lock 1')

        tpas_page.addWidget(self.tpa_lock_1_ctrl)

        self.tpa_lock_2_ctrl = _prop_ctrls.Position3DProperty(tpas_page, 'TPA Lock 2')

        tpas_page.addWidget(self.tpa_lock_2_ctrl)

        cpas_page = _prop_ctrls.Category(self, 'CPA Locks')

        self.compat_cpas_ctrl = _prop_ctrls.ArrayStringProperty(cpas_page, 'Compatible CPA Locks')

        cpas_page.addWidget(self.compat_cpas_ctrl)

        self.compat_cpas_ctrl.propertyChanged.connect(self._on_compat_cpas)

        self.cpa_lock_ctrl = _prop_ctrls.Position3DProperty(cpas_page, 'CPA Lock')

        cpas_page.addWidget(self.cpa_lock_ctrl)

        boots_page = _prop_ctrls.Category(self, 'Boots')

        self.compat_boots_ctrl = _prop_ctrls.ArrayStringProperty(boots_page, 'Compatible Boots')

        boots_page.addWidget(self.compat_boots_ctrl)

        self.compat_boots_ctrl.propertyChanged.connect(self._on_compat_boots)
        self.boot_ctrl = _prop_ctrls.Position3DProperty(boots_page, 'Boot')

        boots_page.addWidget(self.boot_ctrl)

        covers_page = _prop_ctrls.Category(self, 'Covers')

        self.compat_covers_ctrl = _prop_ctrls.ArrayStringProperty(covers_page, 'Compatible Covers')

        covers_page.addWidget(self.compat_covers_ctrl)

        self.compat_covers_ctrl.propertyChanged.connect(self._on_compat_covers)
        self.cover_ctrl = _prop_ctrls.Position3DProperty(covers_page, 'Cover')

        covers_page.addWidget(self.cover_ctrl)

        cavities_page = _prop_ctrls.Category(self, 'Cavities')
        self.cavities_notebook = QTabWidget(cavities_page)
        self.cavities_notebook.setTabPosition(QTabWidget.TabPosition.North)
        self.cavities_notebook.setUsesScrollButtons(True)
        self.cavity_pages = []

        cavities_page.addWidget(self.cavities_notebook)

        self.model3d_page = Model3DControl(self)

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
            covers_page,
            cavities_page,
            self.model3d_page
        ):

            self.addTab(page, page.GetLabel())
