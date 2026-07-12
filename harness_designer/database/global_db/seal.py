# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QTabWidget
from typing import TYPE_CHECKING, Iterable as _Iterable

import uuid

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType
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
    DimensionMixin, DimensionControl,
    CompatHousingsMixin, CompatHousingsControl,
    CompatTerminalsMixin, CompatTerminalsControl
)


if TYPE_CHECKING:
    from . import seal_type as _seal_type


class SealsTable(TableBase):
    """Represent a seals table in :mod:`harness_designer.database.global_db.seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'seals'

    _control: "SealControl" = None

    @property
    def control(self) -> "SealControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`SealControl`
        """
        if self._control is None:
            self._control = SealControl(self.db.mainframe)
            self._control.hide()
        return self._control

    def _load_database(self, splash):
        """Load the database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import seals

        data_path = self._con.db_data.open(splash)
        seals.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import seals

        return seals.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import seals

        seals.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        seals.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import seals

        seals.table.update_fields(self)

    def __iter__(self) -> _Iterable["Seal"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Seal']
        """
        for db_id in TableBase.__iter__(self):
            yield Seal(self, db_id)

    def __getitem__(self, item) -> "Seal":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Seal`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Seal(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Seal(self, db_id[0][0])

        raise KeyError(item)

    def get_compat(self, terminal: str = None, housing: str = None):
        """Return the compat.

        UNKNOWN details are inferred from the callable name and signature.

        :param terminal: Value for ``terminal``.
        :type terminal: str
        :param housing: Value for ``housing``.
        :type housing: str
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        res = []

        if terminal is not None:
            part_number = terminal
            field_name = 'compat_terminals'
        elif housing is not None:
            part_number = housing
            field_name = 'compat_housings'
        else:
            return []

        self.execute(f'SELECT id, {field_name} FROM seals WHERE {field_name} LIKE ?;', (f'%{part_number}%',))
        rows = self.fetchall()
        for db_id, compat in rows:
            compat = compat[1:-1].split(', ')

            if part_number not in compat:
                continue

            res.append(db_id)

        return res

    def insert(self, part_number: str, mfg_id: int, description: str, series_id: int, type: str, hardness: int,  # NOQA
               color_id: int, lubricant: str, min_temp_id: int, max_temp_id: int, length: float, o_dia: float,
               i_dia: float, wire_dia_min: float, wire_dia_max: float, image_id: int, datasheet_id: int,
               cad_id: int, weight: float) -> "Seal":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_number: Value for ``part_number``.
        :type part_number: str
        :param mfg_id: Identifier for the mfg.
        :type mfg_id: int
        :param description: Value for ``description``.
        :type description: str
        :param series_id: Identifier for the series.
        :type series_id: int
        :param type: Value for ``type``.
        :type type: str
        :param hardness: Value for ``hardness``.
        :type hardness: int
        :param color_id: Identifier for the color.
        :type color_id: int
        :param lubricant: Value for ``lubricant``.
        :type lubricant: str
        :param min_temp_id: Identifier for the min temp.
        :type min_temp_id: int
        :param max_temp_id: Identifier for the max temp.
        :type max_temp_id: int
        :param length: Value for ``length``.
        :type length: float
        :param o_dia: Value for ``o_dia``.
        :type o_dia: float
        :param i_dia: Value for ``i_dia``.
        :type i_dia: float
        :param wire_dia_min: Value for ``wire_dia_min``.
        :type wire_dia_min: float
        :param wire_dia_max: Value for ``wire_dia_max``.
        :type wire_dia_max: float
        :param image_id: Identifier for the image.
        :type image_id: int
        :param datasheet_id: Identifier for the datasheet.
        :type datasheet_id: int
        :param cad_id: Identifier for the cad.
        :type cad_id: int
        :param weight: Value for ``weight``.
        :type weight: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Seal`
        """

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 series_id=series_id, type=type, hardness=hardness, color_id=color_id,
                                 lubricant=lubricant, min_temp_id=min_temp_id, max_temp_id=max_temp_id,
                                 length=length, o_dia=o_dia, i_dia=i_dia, wire_dia_min=wire_dia_min,
                                 wire_dia_max=wire_dia_max, image_id=image_id, datasheet_id=datasheet_id,
                                 cad_id=cad_id, weight=weight)
        return Seal(self, db_id)

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
                'label': 'Series',
                'type': [int, str],
                'search_params': ['series_id', 'series', 'name']
            },
            4: {
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            5: {
                'label': 'Temperature (Min)',
                'type': [int, str],
                'search_params': ['min_temp_id', 'temperatures', 'name']
            },
            6: {
                'label': 'Temperature (Max)',
                'type': [int, str],
                'search_params': ['max_temp_id', 'temperatures', 'name']
            },
            7: {
                'label': 'Type',
                'type': [int, str],
                'search_params': ['type_id', 'seal_types', 'name']
            },
            8: {
                'label': 'Hardness (shore)',
                'type': [int],
                'search_params': ['hardness']
            },
            9: {
                'label': 'Lubricant',
                'type': [str],
                'out_params': 'lubricant'
            },
            10: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            11: {
                'label': 'Diameter (OD)(mm)',
                'type': [float],
                'search_params': ['o_dia']
            },
            12: {
                'label': 'Diameter (ID)(mm)',
                'type': [float],
                'search_params': ['i_dia']
            },
            13: {
                'label': 'Wire Diameter (Min)(mm)',
                'type': [float],
                'search_params': ['wire_dia_min']
            },
            14: {
                'label': 'Wire Diameter (Max)(mm)',
                'type': [float],
                'search_params': ['wire_dia_max']
            },
            15: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class Seal(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin,
           SeriesMixin, ColorMixin, TemperatureMixin, ResourceMixin, WeightMixin,
           Model3DMixin, DimensionMixin, FamilyMixin, WireSizeMixin, CompatHousingsMixin,
           CompatTerminalsMixin):
    """Represent a seal in :mod:`harness_designer.database.global_db.seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: SealsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        mfg = self.manufacturer
        color = self.color

        packet = {
            'seals': [self.db_id],
            'series': [self.series_id],
            'temperatures': [self.min_temp_id, self.max_temp_id],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id],
            'models3d': [self.model3d_id]
        }

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

    _scale_id: str = None

    def _update_scale(self, scale: _point.Point):
        """Update the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """
        width, height, length = scale.as_float

        is_sws = self.type.name.lower() in ('sws', 'single wire seal')
        if is_sws:
            o_dia = max(width, height)
            self._stored_o_dia = o_dia
            self._table.update(self._db_id, o_dia=o_dia, length=length)
        else:
            self._stored_width = width
            self._stored_height = height
            self._table.update(self._db_id, width=width, height=height, length=length)

        self._stored_length = length

    _stored_scale: _point.Point | DefaultStoredValueType = DefaultStoredValue

    @property
    def scale(self) -> "_point.Point":
        """Return the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_scale is DefaultStoredValue:
            if self._scale_id is None:
                self._scale_id = str(uuid.uuid4())

            is_sws = self.type.name.lower() in ('sws', 'single wire seal')

            if is_sws:
                x = y = self.o_dia
            else:
                x = self.width
                y = self.height

            z = self.length

            if x <= 0:
                if is_sws:
                    self._table.update(self._db_id, o_dia=1.0)
                    x = y = 1.0
                    self._stored_o_dia = 1.0
                else:
                    self._table.update(self._db_id, width=1.0)
                    x = 1.0
                    self._stored_width = 1.0

            if y <= 0:
                if is_sws:
                    self._table.update(self._db_id, o_dia=1.0)
                    x = y = 1.0
                    self._stored_o_dia = 1.0
                else:
                    self._table.update(self._db_id, height=1.0)
                    y = 1.0
                    self._stored_height = 1.0

            if z <= 0:
                self._table.update(self._db_id, length=1.0)
                z = 1.0
                self._stored_length = 1.0

            scale = _point.Point(x, y, z, db_id=self._scale_id)
            scale.bind(self._update_scale)
            self._stored_scale = scale

        return self._stored_scale

    _stored_o_dia: DefaultStoredValueType | float = DefaultStoredValue

    @property
    def o_dia(self) -> float:
        """Return the o dia.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_o_dia is DefaultStoredValue:
            self._stored_o_dia = self._table.select('o_dia', id=self._db_id)[0][0]

        return self._stored_o_dia

    @o_dia.setter
    def o_dia(self, value: float):
        """Set the o dia.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_o_dia = round(value, 6)
        self._table.update(self._db_id, o_dia=self._stored_o_dia)
        self._populate('o_dia')

    _stored_i_dia: DefaultStoredValueType | float = DefaultStoredValue

    @property
    def i_dia(self) -> float:
        """Return the i dia.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_i_dia is DefaultStoredValue:
            self._stored_i_dia = self._table.select('i_dia', id=self._db_id)[0][0]

        return self._stored_i_dia

    @i_dia.setter
    def i_dia(self, value: float):
        """Set the i dia.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_i_dia = round(value, 6)
        self._table.update(self._db_id, i_dia=self._stored_i_dia)
        self._populate('i_dia')

    _stored_type: "DefaultStoredValueType | _seal_type.SealType" = DefaultStoredValue

    @property
    def type(self) -> "_seal_type.SealType":
        """Return the type.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_seal_type.SealType`
        """
        if self._stored_type is DefaultStoredValue:
            self._stored_type = self.table.db.seal_types_table[self.type_id]

        return self._stored_type

    _stored_type_id: DefaultStoredValueType | int = DefaultStoredValue

    @property
    def type_id(self) -> int:
        """Return the type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_type_id is DefaultStoredValue:
            self._stored_type_id = self._table.select('type_id', id=self._db_id)[0][0]

        return self._stored_type_id

    @type_id.setter
    def type_id(self, value: int):
        """Set the type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_type_id = value
        self._stored_type = DefaultStoredValue

        self._table.update(self._db_id, type_id=value)
        self._populate('type_id')

    _stored_hardness: DefaultStoredValueType | int = DefaultStoredValue

    @property
    def hardness(self) -> int:
        """Return the hardness.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_hardness is DefaultStoredValue:
            self._stored_hardness = self._table.select('hardness', id=self._db_id)[0][0]

        return self._stored_hardness

    @hardness.setter
    def hardness(self, value: int):
        """Set the hardness.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_hardness = value
        self._table.update(self._db_id, hardness=value)
        self._populate('hardness')

    _stored_lubricant: DefaultStoredValueType | str = DefaultStoredValue

    @property
    def lubricant(self) -> str:
        """Return the lubricant.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_lubricant is DefaultStoredValue:
            self._stored_lubricant = self._table.select('lubricant', id=self._db_id)[0][0]

        return self._stored_lubricant

    @lubricant.setter
    def lubricant(self, value: str):
        """Set the lubricant.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_lubricant = value
        self._table.update(self._db_id, lubricant=value)
        self._populate('lubricant')

    _stored_wire_dia_min: DefaultStoredValueType | float | None = DefaultStoredValue

    @property
    def wire_dia_min(self) -> float:
        """Return the wire dia min.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_wire_dia_min is DefaultStoredValue:
            self._stored_wire_dia_min = self._table.select('wire_dia_min', id=self._db_id)[0][0]

        return self._stored_wire_dia_min

    @wire_dia_min.setter
    def wire_dia_min(self, value: float):
        """Set the wire dia min.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_wire_dia_min = round(value, 6)
        self._table.update(self._db_id, wire_dia_min=self._stored_wire_dia_min)
        self._populate('wire_dia_min')

    _stored_wire_dia_max: DefaultStoredValueType | float | None = DefaultStoredValue

    @property
    def wire_dia_max(self) -> float:
        """Return the wire dia max.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_wire_dia_max is DefaultStoredValue:
            self._stored_wire_dia_max = self._table.select('wire_dia_max', id=self._db_id)[0][0]

        return self._stored_wire_dia_max

    @wire_dia_max.setter
    def wire_dia_max(self, value: float):
        """Set the wire dia max.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_wire_dia_max = round(value, 6)
        self._table.update(self._db_id, wire_dia_max=self._stored_wire_dia_max)
        self._populate('wire_dia_max')


class SealControl(QTabWidget, LazyTabMixin):
    """Represent a seal control in :mod:`harness_designer.database.global_db.seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    # TODO: Add seal type

    def set_obj(self, db_obj: Seal):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Seal`
        """
        self._lazy_set_obj(db_obj)

    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.part_number_ctrl.set_obj(self.db_obj)
            self.description_ctrl.set_obj(self.db_obj)
            self.color_ctrl.set_obj(self.db_obj)
            self.weight_ctrl.set_obj(self.db_obj)
            if self.db_obj is None:
                self.hardness_ctrl.SetValue(0)
                self.lubricant_ctrl.SetValue('')
                self.o_dia_ctrl.SetValue(0.0)
                self.i_dia_ctrl.SetValue(0.0)
                self.hardness_ctrl.setEnabled(False)
                self.lubricant_ctrl.setEnabled(False)
                self.o_dia_ctrl.setEnabled(False)
                self.i_dia_ctrl.setEnabled(False)
            else:
                self.hardness_ctrl.SetValue(self.db_obj.hardness)
                self.lubricant_ctrl.SetValue(self.db_obj.lubricant)
                self.o_dia_ctrl.SetValue(self.db_obj.o_dia)
                self.i_dia_ctrl.SetValue(self.db_obj.i_dia)
                self.hardness_ctrl.setEnabled(True)
                self.lubricant_ctrl.setEnabled(True)
                self.o_dia_ctrl.setEnabled(True)
                self.i_dia_ctrl.setEnabled(True)
        elif page is self.mfg_page:
            self.mfg_page.set_obj(self.db_obj)
        elif page is self.family_page:
            self.family_page.set_obj(self.db_obj)
        elif page is self.series_page:
            self.series_page.set_obj(self.db_obj)
        elif page is self.temperature_page:
            self.temperature_page.set_obj(self.db_obj)
        elif page is self.dimension_page:
            self.dimension_page.set_obj(self.db_obj)
        elif page is self.wire_size_page:
            self.wire_size_page.set_obj(self.db_obj)
        elif page is self.resources_page:
            self.resources_page.set_obj(self.db_obj)
        elif page is self._compat_parts_page:
            self.compat_housing_ctrl.set_obj(self.db_obj)
            self.compat_terminals_ctrl.set_obj(self.db_obj)
        elif page is self.model3d_page:
            self.model3d_page.set_obj(self.db_obj)
        self._tab_loaded[index] = True

    def _on_hardness(self, evt):
        """Handle the hardness event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.hardness = value

    def _on_lubricant(self, evt):
        """Handle the lubricant event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.lubricant = value

    def _on_o_dia(self, evt):
        """Handle the o dia event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.o_dia = value

    def _on_i_dia(self, evt):
        """Handle the i dia event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.i_dia = value

    def __init__(self, parent):
        """Initialise the :class:`SealControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Seal = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.color_ctrl = ColorControl(general_page)

        self.hardness_ctrl = _prop_ctrls.IntProperty(
            general_page, 'Hardness', min_value=-1, max_value=999, units='shore')

        self.lubricant_ctrl = _prop_ctrls.StringProperty(general_page, 'Lubricant')

        self.o_dia_ctrl = _prop_ctrls.FloatProperty(
            general_page, 'Outside Diameter', min_value=0.0,
            max_value=99.9, increment=0.01, units='mm')

        self.i_dia_ctrl = _prop_ctrls.FloatProperty(
            general_page, 'Inside Diameter', min_value=0.00,
            max_value=99.9, increment=0.01, units='mm')

        general_page.addWidget(self.part_number_ctrl)
        general_page.addWidget(self.description_ctrl)
        general_page.addWidget(self.color_ctrl)
        general_page.addWidget(self.hardness_ctrl)
        general_page.addWidget(self.lubricant_ctrl)
        general_page.addWidget(self.o_dia_ctrl)
        general_page.addWidget(self.i_dia_ctrl)

        self.hardness_ctrl.propertyChanged.connect(self._on_hardness)
        self.lubricant_ctrl.propertyChanged.connect(self._on_lubricant)
        self.o_dia_ctrl.propertyChanged.connect(self._on_o_dia)
        self.i_dia_ctrl.propertyChanged.connect(self._on_i_dia)

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)

        self.dimension_page = DimensionControl(self)
        self.weight_ctrl = WeightControl(self.dimension_page)

        self.dimension_page.addWidget(self.weight_ctrl)

        self.resources_page = ResourcesControl(self)

        self._compat_parts_page = compat_parts_page = _prop_ctrls.Category(self, 'Compatible Parts')
        self.compat_housing_ctrl = CompatHousingsControl(compat_parts_page)
        self.compat_terminals_ctrl = CompatTerminalsControl(compat_parts_page)

        compat_parts_page.addWidget(self.compat_housing_ctrl)
        compat_parts_page.addWidget(self.compat_terminals_ctrl)

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
            self.resources_page,
            compat_parts_page,
            self.model3d_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
