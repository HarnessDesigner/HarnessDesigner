# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QTabWidget
from typing import Iterable as _Iterable, TYPE_CHECKING

import uuid

from ...ui import prop_ctrls as _prop_ctrls
from ... import utils as _utils
from ..common_db.lazy_tab_mixin import LazyTabMixin
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
    Model3DMixin, Model3DControl,
    WireSizeMixin, WireSizeControl,
    CompatSealsMixin, CompatSealsControl,
    CavityLockMixin, CavityLockControl,
    GenderMixin, GenderControl,
    PlatingMixin, PlatingControl,
    DimensionMixin, DimensionControl,
    CompatHousingsMixin, CompatHousingsControl,
)


if TYPE_CHECKING:
    from . import seal as _seal


def _seal_eff_dia(seal, side: str) -> float | None:
    """Resolve a seal's effective wire diameter for *side* ('min' or 'max').

    Tries wire_dia → wire_size_dia → cross-section → AWG, in that order.
    Returns None if every relevant field is NULL.
    """
    if side == 'min':
        v = seal.wire_dia_min
        if v is not None:
            return v
        v = seal.wire_size_dia_min
        if v is not None:
            return v
        v = seal.wire_size_cross_min
        if v is not None:
            return _utils.mm2_to_d_mm(v)
        v = seal.wire_size_awg_min
        if v is not None:
            return _utils.awg_to_d_mm(v)
    else:
        v = seal.wire_dia_max
        if v is not None:
            return v
        v = seal.wire_size_dia_max
        if v is not None:
            return v
        v = seal.wire_size_cross_max
        if v is not None:
            return _utils.mm2_to_d_mm(v)
        v = seal.wire_size_awg_max
        if v is not None:
            return _utils.awg_to_d_mm(v)
    return None


class TerminalsTable(TableBase):
    """Represent a terminals table in :mod:`harness_designer.database.global_db.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__: str = 'terminals'

    _control: "TerminalControl" = None

    @property
    def control(self) -> "TerminalControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`TerminalControl`
        """
        if self._control is None:
            self._control = TerminalControl(self.db.mainframe)
            self._control.hide()
        return self._control

    def _load_database(self, splash):
        """Load the database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import terminals

        data_path = self._con.db_data.open(splash)
        terminals.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import terminals

        return terminals.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import terminals

        terminals.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        terminals.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import terminals

        terminals.table.update_fields(self)

    def __iter__(self) -> _Iterable["Terminal"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Terminal']
        """
        for db_id in TableBase.__iter__(self):
            yield Terminal(self, db_id)

    def __getitem__(self, item) -> "Terminal":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Terminal`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Terminal(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Terminal(self, db_id[0][0])

        raise KeyError(item)

    def get_compat(self, seal: str = None, housing: str = None):
        """Return the compat.

        UNKNOWN details are inferred from the callable name and signature.

        :param seal: Value for ``seal``.
        :type seal: str
        :param housing: Value for ``housing``.
        :type housing: str
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        res = []

        if seal is not None:
            part_number = seal
            field_name = 'compat_seals'
        elif housing is not None:
            part_number = housing
            field_name = 'compat_housings'
        else:
            return []

        self.execute(f'SELECT id, {field_name} FROM terminals WHERE {field_name} LIKE "%{part_number}%;')
        rows = self.fetchall()
        for db_id, compat in rows:
            compat = compat[1:-1].split(', ')

            if part_number not in compat:
                continue

            res.append(db_id)

        return res

    def insert(self, part_number: str, mfg_id: int, description: str, gender_id: int,
               series_id: int, family_id: int, sealing: bool, cavity_lock_id: int,
               image_id: int, datasheet_id: int, cad_id: int, material_id: int,
               blade_size: float, resistance: int, mating_cycles: int,
               max_vibration_g: int, max_current_ma: int, wire_size_min_awg: int,
               wire_size_max_awg: int, wire_dia_min: float, wire_dia_max: float,
               min_wire_cross: float, max_wire_cross: float, plating_id: int,
               weight: float, length: float, width, _decimal, height: float) -> "Terminal":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_number: Value for ``part_number``.
        :type part_number: str
        :param mfg_id: Identifier for the mfg.
        :type mfg_id: int
        :param description: Value for ``description``.
        :type description: str
        :param gender_id: Identifier for the gender.
        :type gender_id: int
        :param series_id: Identifier for the series.
        :type series_id: int
        :param family_id: Identifier for the family.
        :type family_id: int
        :param sealing: Value for ``sealing``.
        :type sealing: bool
        :param cavity_lock_id: Identifier for the cavity lock.
        :type cavity_lock_id: int
        :param image_id: Identifier for the image.
        :type image_id: int
        :param datasheet_id: Identifier for the datasheet.
        :type datasheet_id: int
        :param cad_id: Identifier for the cad.
        :type cad_id: int
        :param material_id: Identifier for the material.
        :type material_id: int
        :param blade_size: Value for ``blade_size``.
        :type blade_size: float
        :param resistance: Value for ``resistance``.
        :type resistance: int
        :param mating_cycles: Value for ``mating_cycles``.
        :type mating_cycles: int
        :param max_vibration_g: Value for ``max_vibration_g``.
        :type max_vibration_g: int
        :param max_current_ma: Value for ``max_current_ma``.
        :type max_current_ma: int
        :param wire_size_min_awg: Value for ``wire_size_min_awg``.
        :type wire_size_min_awg: int
        :param wire_size_max_awg: Value for ``wire_size_max_awg``.
        :type wire_size_max_awg: int
        :param wire_dia_min: Value for ``wire_dia_min``.
        :type wire_dia_min: float
        :param wire_dia_max: Value for ``wire_dia_max``.
        :type wire_dia_max: float
        :param min_wire_cross: Value for ``min_wire_cross``.
        :type min_wire_cross: float
        :param max_wire_cross: Value for ``max_wire_cross``.
        :type max_wire_cross: float
        :param plating_id: Identifier for the plating.
        :type plating_id: int
        :param weight: Value for ``weight``.
        :type weight: float
        :param length: Value for ``length``.
        :type length: float
        :param width: Value for ``width``.
        :type width: UNKNOWN
        :param _decimal: Value for ``decimal``.
        :type _decimal: UNKNOWN
        :param height: Value for ``height``.
        :type height: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Terminal`
        """

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
    """Represent a terminal in :mod:`harness_designer.database.global_db.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: TerminalsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
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
        """Return the compat seals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_seal.Seal']
        """
        if not self.sealing:
            return []

        term_min = self.wire_size_dia_min
        term_max = self.wire_size_dia_max

        if not term_min or not term_max:
            return []

        res = []
        for seal in self._table.db.seals_table:
            if seal.type.name.lower() not in ('sws', 'single wire seal'):
                continue

            seal_min = _seal_eff_dia(seal, 'min')
            seal_max = _seal_eff_dia(seal, 'max')

            if seal_min is None and seal_max is None:
                continue

            if seal_min is not None and seal_min > term_min:
                continue

            if seal_max is not None and seal_max < term_max:
                continue

            res.append(seal)

        return res

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
        self._table.update(self._db_id, size=int(value))
        self._populate('sealing')

    @property
    def blade_size(self) -> float:
        """Return the blade size.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('blade_size', id=self._db_id)[0][0]

    @blade_size.setter
    def blade_size(self, value: float):
        """Set the blade size.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, blade_size=value)
        self._populate('blade_size')

    @property
    def resistance(self) -> float:
        """Return the resistance.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('resistance', id=self._db_id)[0][0]

    @resistance.setter
    def resistance(self, value: float):
        """Set the resistance.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, resistance=value)
        self._populate('resistance')

    @property
    def mating_cycles(self) -> int:
        """Return the mating cycles.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('mating_cycles', id=self._db_id)[0][0]

    @mating_cycles.setter
    def mating_cycles(self, value: int):
        """Set the mating cycles.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, mating_cycles=value)
        self._populate('mating_cycles')

    @property
    def max_vibration_g(self) -> int:
        """Return the max vibration g.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('max_vibration_g', id=self._db_id)[0][0]

    @max_vibration_g.setter
    def max_vibration_g(self, value: int):
        """Set the max vibration g.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, max_vibration_g=value)
        self._populate('max_vibration_g')

    @property
    def max_current_ma(self) -> int:
        """Return the max current ma.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('max_current_ma', id=self._db_id)[0][0]

    @max_current_ma.setter
    def max_current_ma(self, value: int):
        """Set the max current ma.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, max_current_ma=value)
        self._populate('max_current_ma')

    @property
    def round_terminal(self) -> bool:
        """Return the round terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self._table.select('round_terminal', id=self._db_id)[0][0])

    @round_terminal.setter
    def round_terminal(self, value: bool):
        """Set the round terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, round_terminal=int(value))
        self._populate('round_terminal')

    @property
    def length(self) -> float:
        """Return the length.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        """Set the length.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, length=round(value, 6))
        self._populate('length')

    @property
    def width(self) -> float:
        """Return the width.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
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
        """Set the width.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        if self.round_terminal:
            self._table.update(self._db_id, width=round(value, 6), height=round(value, 6))
        else:
            self._table.update(self._db_id, width=round(value, 6))
        self._populate('width')

    @property
    def height(self) -> float:
        """Return the height.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
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
        """Set the height.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        if self.round_terminal:
            self._table.update(self._db_id, width=round(value, 6), height=round(value, 6))
        else:
            self._table.update(self._db_id, height=round(value, 6))
        self._populate('height')

    _scale_id: str = None

    def _update_scale(self, scale: _point.Point):
        """Update the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """
        width, height, length = scale.as_float

        if self.round_terminal and width != height:
            width = height = min(width, height)

        self._table.update(self._db_id, width=width, height=height, length=length)

    @property
    def scale(self) -> "_point.Point":
        """Return the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
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


class TerminalControl(QTabWidget, LazyTabMixin):
    """Represent a terminal control in :mod:`harness_designer.database.global_db.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: Terminal):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Terminal`
        """
        self.db_obj = db_obj

        self.mfg_page.set_obj(db_obj)
        self.family_page.set_obj(db_obj)
        self.series_page.set_obj(db_obj)
        self.temperature_page.set_obj(db_obj)
        self.dimension_page.set_obj(db_obj)
        self.resources_page.set_obj(db_obj)
        self.model3d_page.set_obj(db_obj)
        self.plating_page.set_obj(db_obj)
        self.wire_size_page.set_obj(db_obj)

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

            self.sealing_ctrl.setEnabled(False)
            self.blade_size_ctrl.setEnabled(False)
            self.resistance_ctrl.setEnabled(False)
            self.mating_cycles_ctrl.setEnabled(False)
            self.max_vibration_g_ctrl.setEnabled(False)
            self.max_current_ma_ctrl.setEnabled(False)
        else:
            self.sealing_ctrl.SetValue(db_obj.sealing)
            self.blade_size_ctrl.SetValue(db_obj.blade_size)
            self.resistance_ctrl.SetValue(db_obj.resistance)
            self.mating_cycles_ctrl.SetValue(db_obj.mating_cycles)
            self.max_vibration_g_ctrl.SetValue(db_obj.max_vibration_g)
            self.max_current_ma_ctrl.SetValue(db_obj.max_current_ma)

            self.sealing_ctrl.setEnabled(True)
            self.blade_size_ctrl.setEnabled(True)
            self.resistance_ctrl.setEnabled(True)
            self.mating_cycles_ctrl.setEnabled(True)
            self.max_vibration_g_ctrl.setEnabled(True)
            self.max_current_ma_ctrl.setEnabled(True)

    def _on_sealing(self, evt):
        """Handle the sealing event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.sealing = value

    def _on_blade_size(self, evt):
        """Handle the blade size event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.blade_size = value

    def _on_resistance(self, evt):
        """Handle the resistance event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.resistance = value

    def _on_mating_cycles(self, evt):
        """Handle the mating cycles event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.mating_cycles = value

    def _on_vibration(self, evt):
        """Handle the vibration event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.max_vibration_g = value

    def _on_current(self, evt):
        """Handle the current event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.max_current_ma = value

    def __init__(self, parent):
        """Initialise the :class:`TerminalControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Terminal = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        general_page = _prop_ctrls.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.color_ctrl = ColorControl(general_page)
        self.gender_ctrl = GenderControl(general_page)
        self.cavity_lock_ctrl = CavityLockControl(general_page)

        self.sealing_ctrl = _prop_ctrls.BoolProperty(general_page, 'Sealing')

        self.blade_size_ctrl = _prop_ctrls.FloatProperty(
            general_page, 'Blade Size',
            min_value=0.0, max_value=99.00, increment=0.01, units='mm')

        self.resistance_ctrl = _prop_ctrls.FloatProperty(
            general_page, 'Resistance',
            min_value=0.0, max_value=10000000.00, increment=0.1, units='Ω')

        self.mating_cycles_ctrl = _prop_ctrls.IntProperty(
            general_page, 'Mating Cycles',
            min_value=0, max_value=100000)

        self.max_vibration_g_ctrl = _prop_ctrls.IntProperty(
            general_page, 'Maximum Vibration',
            min_value=0, max_value=100000, units='G')

        self.max_current_ma_ctrl = _prop_ctrls.IntProperty(
            general_page, 'Maximum Current',
            min_value=0, max_value=100000, units='ma')

        general_page.addWidget(self.part_number_ctrl)
        general_page.addWidget(self.description_ctrl)
        general_page.addWidget(self.color_ctrl)
        general_page.addWidget(self.gender_ctrl)
        general_page.addWidget(self.cavity_lock_ctrl)
        general_page.addWidget(self.sealing_ctrl)
        general_page.addWidget(self.blade_size_ctrl)
        general_page.addWidget(self.resistance_ctrl)
        general_page.addWidget(self.mating_cycles_ctrl)
        general_page.addWidget(self.max_vibration_g_ctrl)
        general_page.addWidget(self.max_current_ma_ctrl)

        self.sealing_ctrl.propertyChanged.connect(self._on_sealing)
        self.blade_size_ctrl.propertyChanged.connect(self._on_blade_size)
        self.resistance_ctrl.propertyChanged.connect(self._on_resistance)
        self.mating_cycles_ctrl.propertyChanged.connect(self._on_mating_cycles)
        self.max_vibration_g_ctrl.propertyChanged.connect(self._on_vibration)
        self.max_current_ma_ctrl.propertyChanged.connect(self._on_current)

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)

        self.dimension_page = DimensionControl(self)
        self.weight_ctrl = WeightControl(self.dimension_page)

        self.dimension_page.addWidget(self.weight_ctrl)

        self.plating_page = PlatingControl(self)

        self.resources_page = ResourcesControl(self)

        compat_parts_page = _prop_ctrls.Category(self, 'Compatible Parts')
        self.compat_housing_ctrl = CompatHousingsControl(compat_parts_page)
        self.compat_seal_ctrl = CompatSealsControl(compat_parts_page)

        compat_parts_page.addWidget(self.compat_housing_ctrl)
        compat_parts_page.addWidget(self.compat_seal_ctrl)

        self.model3d_page = Model3DControl(self)

        self.wire_size_page = WireSizeControl(self)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.dimension_page,
            self.wire_size_page,
            self.plating_page,
            self.resources_page,
            compat_parts_page,
            self.model3d_page
        ):
            self.addTab(page, page.GetLabel())
