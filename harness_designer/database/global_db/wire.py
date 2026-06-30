# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QTabWidget
from typing import Iterable as _Iterable, TYPE_CHECKING


from ... import utils as _utils
from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .bases import EntryBase, TableBase
from .mixins import (
    PartNumberMixin, PartNumberControl,
    ManufacturerMixin, ManufacturerControl,
    DescriptionMixin, DescriptionControl,
    SeriesMixin, SeriesControl,
    ResourceMixin, ResourcesControl,
    ColorMixin, ColorControl,
    FamilyMixin, FamilyControl,
    MaterialMixin, MaterialControl,
    TemperatureMixin, TemperatureControl,
    PlatingControl
)


if TYPE_CHECKING:
    from . import color as _color
    from . import plating as _plating


class WiresTable(TableBase):
    """Represent a wires table in :mod:`harness_designer.database.global_db.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__: str = 'wires'

    _control: "WireControl" = None

    @property
    def control(self) -> "WireControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`WireControl`
        """
        if self._control is None:
            self._control = WireControl(self.db.mainframe)
            self._control.hide()
        return self._control

    def _load_database(self, splash):
        """Load the database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import wires

        data_path = self._con.db_data.open(splash)
        wires.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import wires

        return wires.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import wires

        wires.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        wires.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wires

        wires.table.update_fields(self)

    def __iter__(self) -> _Iterable["Wire"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Wire']
        """

        for db_id in TableBase.__iter__(self):
            yield Wire(self, db_id)

    def __getitem__(self, item) -> "Wire":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Wire`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Wire(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Wire(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, family_id: int, series_id: int,
               image_id: int, datasheet_id: int, cad_id: int, color_id: int, addl_color_ids: list,
               material_id: int, num_conductors: int, shielded: bool, tpi: int, conductor_dia_mm: float,
               size_mm2: float, size_awg: int, od_mm: float, max_temp_id: int, weight: float) -> "Wire":
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
        :param image_id: Identifier for the image.
        :type image_id: int
        :param datasheet_id: Identifier for the datasheet.
        :type datasheet_id: int
        :param cad_id: Identifier for the cad.
        :type cad_id: int
        :param color_id: Identifier for the color.
        :type color_id: int
        :param addl_color_ids: Identifier for the addl color.
        :type addl_color_ids: list
        :param material_id: Identifier for the material.
        :type material_id: int
        :param num_conductors: Value for ``num_conductors``.
        :type num_conductors: int
        :param shielded: Value for ``shielded``.
        :type shielded: bool
        :param tpi: Value for ``tpi``.
        :type tpi: int
        :param conductor_dia_mm: Value for ``conductor_dia_mm``.
        :type conductor_dia_mm: float
        :param size_mm2: Value for ``size_mm2``.
        :type size_mm2: float
        :param size_awg: Value for ``size_awg``.
        :type size_awg: int
        :param od_mm: Value for ``od_mm``.
        :type od_mm: float
        :param max_temp_id: Identifier for the max temp.
        :type max_temp_id: int
        :param weight: Value for ``weight``.
        :type weight: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Wire`
        """

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 family_id=family_id, series_id=series_id, image_id=image_id,
                                 datasheet_id=datasheet_id, cad_id=cad_id, color_id=color_id,
                                 addl_color_ids=str(addl_color_ids), material_id=material_id,
                                 num_conductors=num_conductors, shielded=int(shielded), tpi=tpi,
                                 conductor_dia_mm=conductor_dia_mm, size_mm2=size_mm2, size_awg=size_awg,
                                 od_mm=od_mm, max_temp_id=max_temp_id, weight=weight)

        return Wire(self, db_id)

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
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            6: {
                'label': 'Stripe Color',
                'type': [int, str],
                'search_params': ['stripe_color_id', 'colors', 'name']
            },
            7: {
                'label': 'Material',
                'type': [int, str],
                'search_params': ['material_id', 'materials', 'name']
            },
            8: {
                'label': 'Temperature (Min)',
                'type': [int, str],
                'search_params': ['min_temp_id', 'temperatures', 'name']
            },
            9: {
                'label': 'Temperature (Max)',
                'type': [int, str],
                'search_params': ['max_temp_id', 'temperatures', 'name']
            },
            10: {
                'label': 'Conductors',
                'type': [int],
                'search_params': ['num_conductors']
            },
            11: {
                'label': 'Shielded',
                'type': [bool],
                'search_params': ['shielded']
            },
            12: {
                'label': 'TPI',
                'type': [float],
                'search_params': ['tpi']
            },
            13: {
                'label': 'Conductor Diameter (mm)',
                'type': [float],
                'out_params': 'conductor_dia_mm'
            },
            14: {
                'label': 'Size (AWG)',
                'type': [int],
                'search_params': ['size_awg']
            },
            15: {
                'label': 'Size (mm2)',
                'type': [float],
                'search_params': ['size_mm2']
            },
            16: {
                'label': 'Diameter (OD)(mm)',
                'type': [float],
                'search_params': ['od_mm']
            },
            17: {
                'label': 'Core Material',
                'type': [int, str],
                'search_params': ['core_material_id', 'platings', 'symbol']
            },
            18: {
                'label': 'Volts',
                'type': [float],
                'search_params': ['volts']
            },
            19: {
                'label': 'Weight (1km)(g)',
                'type': [float],
                'search_params': ['weight_1km']
            }
        }

        return ret


class Wire(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin,
           FamilyMixin, SeriesMixin, ResourceMixin, ColorMixin, MaterialMixin,
           TemperatureMixin):
    """Represent a wire in :mod:`harness_designer.database.global_db.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: WiresTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        mfg = self.manufacturer
        color = self.color

        packet = {
            'wires': [self.db_id],
            'families': [self.family_id],
            'series': [self.series_id],
            'materials': [self.material_id],
            'platings': [self.core_material_id],
            'temperatures': [self.min_temp_id, self.max_temp_id],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id]
        }

        stripe_color_id = self.stripe_color_id
        if stripe_color_id is not None:
            packet['colors'].append(stripe_color_id)

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

    @property
    def resistance_1km(self) -> float:
        """Return the resistance 1km.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        resistance = self._table.select('resistance_1km', id=self._db_id)[0][0]
        return resistance

    @resistance_1km.setter
    def resistance_1km(self, value: float):
        """Set the resistance 1km.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, resistance_1km=value)
        self._populate('resistance_1km')

    @property
    def resistance_1kft(self) -> float:
        """Return the resistance 1kft.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.resistance_ft * 1000

    @resistance_1kft.setter
    def resistance_1kft(self, value: float):
        """Set the resistance 1kft.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.resistance_ft = value / 1000

    @property
    def resistance_m(self) -> float:
        """Return the resistance m.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        resistance = self.resistance_1km
        return resistance / 1000

    @resistance_m.setter
    def resistance_m(self, value: float):
        """Set the resistance m.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        value *= 1000
        self.resistance_1km = value

    @property
    def resistance_ft(self) -> float:
        """Return the resistance ft.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        resistance = self.resistance_m
        return resistance * 3.28084

    @resistance_ft.setter
    def resistance_ft(self, value: float):
        """Set the resistance ft.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        value /= 3.28084
        self.resistance_m = value

    @property
    def weight_1km(self) -> float:
        """Return the weight 1km.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        weight = self._table.select('weight_1km', id=self._db_id)[0][0]
        return weight

    @weight_1km.setter
    def weight_1km(self, value: float):
        """Set the weight 1km.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, weight_1km=value)
        self._populate('weight_1km')

    @property
    def weight_1kft(self) -> float:
        """Return the weight 1kft.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.weight_lb_ft * 1000

    @weight_1kft.setter
    def weight_1kft(self, value: float):
        """Set the weight 1kft.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.weight_lb_ft = value / 1000

    @property
    def weight_g_m(self) -> float:
        """Return the weight g m.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        weight = self.weight_1km
        return weight / 1000

    @weight_g_m.setter
    def weight_g_m(self, value: float):
        """Set the weight g m.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        value *= 1000
        self.weight_1km = value

    @property
    def weight_g_ft(self) -> float:
        """Return the weight g ft.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        weight = self.weight_g_m
        return weight * 3.28084

    @weight_g_ft.setter
    def weight_g_ft(self, value: float):
        """Set the weight g ft.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        value /= 3.28084
        self.weight_g_m = value

    @property
    def weight_lb_ft(self) -> float:
        """Return the weight lb ft.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        weight = self.weight_g_ft
        return weight / 453.592

    @weight_lb_ft.setter
    def weight_lb_ft(self, value: float):
        """Set the weight lb ft.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        value *= 453.592
        self.weight_g_ft = value

    @property
    def volts(self) -> float:
        """Return the volts.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('volts', id=self._db_id)[0][0]

    @volts.setter
    def volts(self, value: float):
        """Set the volts.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, volts=value)
        self._populate('volts')

    @property
    def od_mm(self) -> float:
        """Return the od mm.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('od_mm', id=self._db_id)[0][0]

    @od_mm.setter
    def od_mm(self, value: float):
        """Set the od mm.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, od_mm=value)
        self._populate('od_mm')

    @property
    def shielded(self) -> bool:
        """Return the shielded.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self._table.select('shielded', id=self._db_id)[0][0])

    @shielded.setter
    def shielded(self, value: bool):
        """Set the shielded.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, shielded=int(value))
        self._populate('shielded')

    @property
    def strands(self) -> int:
        """Return the strands.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('strands', id=self._db_id)[0][0]

    @strands.setter
    def strands(self, value: int):
        """Set the strands.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, strands=value)
        self._populate('strands')

    @property
    def tpi(self) -> int:
        """Return the tpi.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('tpi', id=self._db_id)[0][0]

    @tpi.setter
    def tpi(self, value: int):
        """Set the tpi.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, tpi=value)
        self._populate('tpi')

    @property
    def num_conductors(self) -> int:
        """Return the num conductors.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('num_conductors', id=self._db_id)[0][0]

    @num_conductors.setter
    def num_conductors(self, value: int):
        """Set the num conductors.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, num_conductors=value)
        self._populate('num_conductors')

    @property
    def core_material(self) -> "_plating.Plating":
        """Return the core material.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_plating.Plating`
        """
        db_id = self.core_material_id
        return self._table.db.platings_table[db_id]

    @property
    def core_material_id(self) -> int:
        """Return the core material ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('core_material_id', id=self._db_id)[0][0]

    @core_material_id.setter
    def core_material_id(self, value: int):
        """Set the core material ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, core_material_id=value)
        self._populate('core_material_id')

    @property
    def conductor_dia_mm(self) -> float:
        """Return the conductor dia mm.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        mm = self._table.select('wire_size_dia', id=self._db_id)[0][0]

        if mm is None:
            _utils.d_in_to_d_mm(self.conductor_dia_in, self.strands)

        return mm

    @conductor_dia_mm.setter
    def conductor_dia_mm(self, value: float):
        """Set the conductor dia mm.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, wire_size_dia=value)
        self._table.update(self._db_id, wire_size_awg=_utils.d_mm_to_awg(value, self.strands))
        self._table.update(self._db_id, wire_size_cross=_utils.d_mm_to_mm2(value, self.strands))

        self._populate('conductor_dia_mm')

    @property
    def conductor_dia_in(self) -> float:
        """Return the conductor dia in.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return _utils.awg_to_d_in(self.size_awg, self.strands)

    @conductor_dia_in.setter
    def conductor_dia_in(self, value: float):
        """Set the conductor dia in.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.conductor_dia_mm = value * 25.4

    @property
    def size_mm2(self) -> float:
        """Return the size mm 2.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        mm2 = self._table.select('wire_size_cross', id=self._db_id)[0][0]

        if mm2 is None:
            awg = self.size_awg

            if awg is None:
                mm = self.conductor_dia_mm

                if mm is None:
                    raise RuntimeError('sanity check')

                return _utils.d_mm_to_mm2(mm, self.strands)

            return _utils.awg_to_mm2(awg, self.strands)

        return mm2

    @size_mm2.setter
    def size_mm2(self, value: float):
        """Set the size mm 2.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, wire_size_cross=value)
        self._table.update(self._db_id, wire_size_awg=_utils.mm2_to_awg(value, self.strands))
        self._table.update(self._db_id, wire_size_dia=_utils.mm2_to_d_mm(value, self.strands))
        self._populate('size_mm2')

    @property
    def size_awg(self) -> int:
        """Return the size awg.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        awg = self._table.select('wire_size_awg', id=self._db_id)[0][0]

        if awg is None:
            mm2 = self.size_mm2

            if mm2 is None:
                mm = self.conductor_dia_mm

                if mm is None:
                    raise RuntimeError('sanity check')

                return _utils.d_mm_to_awg(mm, self.strands)

            return _utils.mm2_to_awg(mm2, self.strands)

        return awg

    @size_awg.setter
    def size_awg(self, value: int):
        """Set the size awg.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, wire_size_awg=value)
        self._table.update(self._db_id, wire_size_dia=_utils.awg_to_d_mm(value, self.strands))
        self._table.update(self._db_id, wire_size_cross=_utils.awg_to_mm2(value, self.strands))
        self._populate('size_awg')

    @property
    def size_in2(self) -> float:
        """Return the size in 2.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return _utils.mm2_to_in2(self.size_mm2, self.strands)

    @size_in2.setter
    def size_in2(self, value: float):
        """Set the size in 2.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.size_mm2 = _utils.in2_to_mm2(value, self.strands)

    @property
    def in2_symbol(self) -> str:
        """Return the in 2 symbol.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return 'in²'

    @property
    def mm2_symbol(self) -> str:
        """Return the mm 2 symbol.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return 'mm²'

    @property
    def stripe_color(self) -> "_color.Color":
        """Return the stripe color.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_color.Color`
        """
        db_id = self.stripe_color_id
        return self._table.db.colors_table[db_id]

    @property
    def stripe_color_id(self) -> int | None:
        """Return the stripe color ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int | None
        """
        return self._table.select('stripe_color_id', id=self._db_id)[0][0]

    @stripe_color_id.setter
    def stripe_color_id(self, value: int | None):
        """Set the stripe color ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int | None
        """
        self._table.update(self._db_id, stripe_color_id=value)
        self._populate('stripe_color_id')


class WireControl(QTabWidget, LazyTabMixin):
    """Represent a wire control in :mod:`harness_designer.database.global_db.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: Wire):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Wire`
        """
        self._lazy_set_obj(db_obj)

    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.part_number_ctrl.set_obj(self.db_obj)
            self.description_ctrl.set_obj(self.db_obj)
            if self.db_obj is None:
                self.tpi_ctrl.SetValue(0.0)
                self.weight_1km_ctrl.SetValue(0.0)
                self.volts_ctrl.SetValue(0.0)
                self.resistance_1km_ctrl.SetValue(0.0)
                self.num_conductors_ctrl.SetValue(1)
                self.shielded_ctrl.SetValue(False)
                self.tpi_ctrl.setEnabled(False)
                self.weight_1km_ctrl.setEnabled(False)
                self.volts_ctrl.setEnabled(False)
                self.resistance_1km_ctrl.setEnabled(False)
                self.num_conductors_ctrl.setEnabled(False)
                self.shielded_ctrl.setEnabled(False)
            else:
                self.tpi_ctrl.SetValue(self.db_obj.tpi)
                self.weight_1km_ctrl.SetValue(self.db_obj.weight_1km)
                self.volts_ctrl.SetValue(self.db_obj.volts)
                self.resistance_1km_ctrl.SetValue(self.db_obj.resistance_1km)
                self.num_conductors_ctrl.SetValue(self.db_obj.num_conductors)
                self.shielded_ctrl.SetValue(self.db_obj.shielded)
                self.tpi_ctrl.setEnabled(True)
                self.weight_1km_ctrl.setEnabled(True)
                self.volts_ctrl.setEnabled(True)
                self.resistance_1km_ctrl.setEnabled(True)
                self.num_conductors_ctrl.setEnabled(True)
                self.shielded_ctrl.setEnabled(True)
        elif page is self.mfg_page:
            self.mfg_page.set_obj(self.db_obj)
        elif page is self.family_page:
            self.family_page.set_obj(self.db_obj)
        elif page is self.series_page:
            self.series_page.set_obj(self.db_obj)
        elif page is self.temperature_page:
            self.temperature_page.set_obj(self.db_obj)
        elif page is self.resources_page:
            self.resources_page.set_obj(self.db_obj)
        elif page is self._size_page:
            if self.db_obj is None:
                self.conductor_dia_mm_ctrl.SetValue(0.05)
                self.size_mm2_ctrl.SetValue(0.05)
                self.size_awg_ctrl.SetValue(30.0)
                self.od_mm_ctrl.SetValue(0.05)
                self.conductor_dia_mm_ctrl.setEnabled(False)
                self.size_mm2_ctrl.setEnabled(False)
                self.size_awg_ctrl.setEnabled(False)
                self.od_mm_ctrl.setEnabled(False)
            else:
                self.conductor_dia_mm_ctrl.SetValue(self.db_obj.conductor_dia_mm)
                self.size_mm2_ctrl.SetValue(self.db_obj.size_mm2)
                self.size_awg_ctrl.SetValue(self.db_obj.size_awg)
                self.od_mm_ctrl.SetValue(self.db_obj.od_mm)
                self.conductor_dia_mm_ctrl.setEnabled(True)
                self.size_mm2_ctrl.setEnabled(True)
                self.size_awg_ctrl.setEnabled(True)
                self.od_mm_ctrl.setEnabled(True)
        elif page is self._color_page:
            self.color_ctrl.set_obj(self.db_obj)
            self.stripe_color_ctrl.set_obj(self.db_obj)
        elif page is self._materials_page:
            self.material_ctrl.set_obj(self.db_obj)
            self.core_material_ctrl.set_obj(self.db_obj)
        self._tab_loaded[index] = True

    def _on_tpi(self, evt):
        """Handle the tpi event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.tpi = value

    def _on_weight_1km(self, evt):
        """Handle the weight 1km event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.weight_1km = value

    def _on_volts(self, evt):
        """Handle the volts event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.volts = value

    def _on_resistance_1km(self, evt):
        """Handle the resistance 1km event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.resistance_1km = value

    def _on_num_conductors(self, evt):
        """Handle the num conductors event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.num_conductors = value

    def _on_strands(self, evt):
        """Handle the strands event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        awg = self.size_awg_ctrl.GetValue()
        self.db_obj.strands = value
        self.db_obj.size_awg = awg

        self.size_mm2_ctrl.SetValue(self.db_obj.size_mm2)
        self.conductor_dia_mm_ctrl.SetValue(self.db_obj.conductor_dia_mm)

    def _on_shielded(self, evt):
        """Handle the shielded event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.shielded = value

    def _on_conductor_dia_mm(self, evt):
        """Handle the conductor dia mm event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.conductor_dia_mm = value
        self.size_mm2_ctrl.SetValue(self.db_obj.size_mm2)
        self.size_awg_ctrl.SetValue(self.db_obj.size_awg)

    def _on_size_mm2(self, evt):
        """Handle the size mm 2 event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.size_mm2 = value

        self.conductor_dia_mm_ctrl.SetValue(self.db_obj.conductor_dia_mm)
        self.size_awg_ctrl.SetValue(self.db_obj.size_awg)

    def _on_size_awg(self, evt):
        """Handle the size awg event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.size_awg = value
        self.conductor_dia_mm_ctrl.SetValue(self.db_obj.conductor_dia_mm)
        self.size_mm2_ctrl.SetValue(self.db_obj.size_mm2)

    def _on_od_mm(self, evt):
        """Handle the od mm event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.od_mm = value

    def __init__(self, parent):
        """Initialise the :class:`WireControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Wire = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)

        self.tpi_ctrl = _prop_ctrls.FloatProperty(
            general_page, 'Twists per Inch',
            min_value=0.00, max_value=5.0, increment=0.5, units='tpi')

        self.weight_1km_ctrl = _prop_ctrls.FloatProperty(
            general_page, 'Weight',
            min_value=0.0, max_value=500.0, increment=0.01, units='g/km')

        self.volts_ctrl = _prop_ctrls.FloatProperty(
            general_page, 'Volts',
            min_value=0.00, max_value=44000.00, increment=0.1, units='V')

        self.resistance_1km_ctrl = _prop_ctrls.FloatProperty(
            general_page, 'Resistance',
            min_value=0.0, max_value=99999.99, increment=0.01, units='Ω/km')

        self.num_conductors_ctrl = _prop_ctrls.IntProperty(
            general_page, 'Conductor Count', min_value=1, max_value=10)

        self.strands_ctrl = _prop_ctrls.IntProperty(
            general_page, 'Strand Count', min_value=0, max_value=5000)

        self.shielded_ctrl = _prop_ctrls.BoolProperty(
            general_page, 'Shielded')

        general_page.addWidget(self.part_number_ctrl)
        general_page.addWidget(self.description_ctrl)
        general_page.addWidget(self.tpi_ctrl)
        general_page.addWidget(self.weight_1km_ctrl)
        general_page.addWidget(self.volts_ctrl)
        general_page.addWidget(self.resistance_1km_ctrl)
        general_page.addWidget(self.num_conductors_ctrl)
        general_page.addWidget(self.strands_ctrl)
        general_page.addWidget(self.shielded_ctrl)

        self._color_page = color_page = _prop_ctrls.Category(self, 'Color')
        self.color_ctrl = ColorControl(color_page)
        self.color_ctrl.SetLabel('Primary')

        self.stripe_color_ctrl = ColorControl(color_page)
        self.stripe_color_ctrl.SetLabel('Stripe')
        self.stripe_color_ctrl.SetAttributeName('stripe_color')

        color_page.addWidget(self.color_ctrl)
        color_page.addWidget(self.stripe_color_ctrl)

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)

        self.resources_page = ResourcesControl(self)

        self._materials_page = materials_page = _prop_ctrls.Category(self, 'Materials')
        self.material_ctrl = MaterialControl(materials_page)
        self.material_ctrl.SetLabel('Jacket')

        self.core_material_ctrl = PlatingControl(materials_page)
        self.core_material_ctrl.SetLabel('Core')
        self.core_material_ctrl.SetAttributeName('core_material')

        materials_page.addWidget(self.material_ctrl)
        materials_page.addWidget(self.core_material_ctrl)

        self._size_page = size_page = _prop_ctrls.Category(self, 'Size')

        self.conductor_dia_mm_ctrl = _prop_ctrls.FloatProperty(
            size_page, 'Conductor Diameter',
            min_value=0.05, max_value=60.0, increment=0.01, units='mm')

        self.size_mm2_ctrl = _prop_ctrls.FloatProperty(
            size_page, 'Conductor Cross Section',
            min_value=0.00, max_value=99.9999, increment=0.0001, units='mm²')

        self.size_awg_ctrl = _prop_ctrls.IntProperty(
            size_page, 'Conductor Size', min_value=-4,
            max_value=30, units='awg')

        self.od_mm_ctrl = _prop_ctrls.FloatProperty(
            size_page, 'Outside Diameter',
            min_value=0.0, max_value=99.9999, increment=0.0001, units='mm')

        size_page.addWidget(self.conductor_dia_mm_ctrl)
        size_page.addWidget(self.size_mm2_ctrl)
        size_page.addWidget(self.size_awg_ctrl)
        size_page.addWidget(self.od_mm_ctrl)

        self.tpi_ctrl.propertyChanged.connect(self._on_tpi)
        self.weight_1km_ctrl.propertyChanged.connect(self._on_weight_1km)
        self.volts_ctrl.propertyChanged.connect(self._on_volts)
        self.resistance_1km_ctrl.propertyChanged.connect(self._on_resistance_1km)
        self.num_conductors_ctrl.propertyChanged.connect(self._on_num_conductors)
        self.strands_ctrl.propertyChanged.connect(self._on_strands)
        self.shielded_ctrl.propertyChanged.connect(self._on_shielded)
        self.conductor_dia_mm_ctrl.propertyChanged.connect(self._on_conductor_dia_mm)
        self.size_mm2_ctrl.propertyChanged.connect(self._on_size_mm2)
        self.size_awg_ctrl.propertyChanged.connect(self._on_size_awg)
        self.od_mm_ctrl.propertyChanged.connect(self._on_od_mm)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.resources_page,
            size_page,
            color_page,
            materials_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
