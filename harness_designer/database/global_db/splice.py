# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QTabWidget
from typing import TYPE_CHECKING, Iterable as _Iterable


from ...ui import prop_ctrls as _prop_ctrls
from .bases import EntryBase, TableBase
from .mixins import (
    PartNumberMixin, PartNumberControl,
    DescriptionMixin, DescriptionControl,
    ManufacturerMixin, ManufacturerControl,
    FamilyMixin, FamilyControl,
    SeriesMixin, SeriesControl,
    MaterialMixin, MaterialControl,
    ColorMixin, ColorControl,
    PlatingMixin, PlatingControl,
    ResourceMixin, ResourcesControl,
    Model3DMixin, Model3DControl,
    WeightMixin, WeightControl,
    WireSizeMixin, WireSizeControl,
    TemperatureMixin, TemperatureControl,
    DimensionMixin, DimensionControl
)


if TYPE_CHECKING:
    from . import splice_types as _splice_types


class SplicesTable(TableBase):
    """Represent a splices table in :mod:`harness_designer.database.global_db.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'splices'

    _control: "SpliceControl" = None

    @property
    def control(self) -> "SpliceControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`SpliceControl`
        """
        if self._control is None:
            self._control = SpliceControl(self.db.mainframe)
            self._control.hide()
        return self._control

    def _load_database(self, splash):
        """Load the database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import splices

        data_path = self._con.db_data.open(splash)
        splices.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import splices

        return splices.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import splices

        splices.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        splices.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import splices

        splices.table.update_fields(self)

    def __iter__(self) -> _Iterable["Splice"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Splice']
        """
        for db_id in TableBase.__iter__(self):
            yield Splice(self, db_id)

    def __getitem__(self, item) -> "Splice":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Splice`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Splice(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Splice(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, description: str, mfg_id: int, family_id: int,
               series_id: int, material_id: int, color_id: int, plating_id: int,
               type_id: int, min_dia: float, max_dia: float, resistance: float,
               length: float, weight: float) -> "Splice":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_number: Value for ``part_number``.
        :type part_number: str
        :param description: Value for ``description``.
        :type description: str
        :param mfg_id: Identifier for the mfg.
        :type mfg_id: int
        :param family_id: Identifier for the family.
        :type family_id: int
        :param series_id: Identifier for the series.
        :type series_id: int
        :param material_id: Identifier for the material.
        :type material_id: int
        :param color_id: Identifier for the color.
        :type color_id: int
        :param plating_id: Identifier for the plating.
        :type plating_id: int
        :param type_id: Identifier for the type.
        :type type_id: int
        :param min_dia: Value for ``min_dia``.
        :type min_dia: float
        :param max_dia: Value for ``max_dia``.
        :type max_dia: float
        :param resistance: Value for ``resistance``.
        :type resistance: float
        :param length: Value for ``length``.
        :type length: float
        :param weight: Value for ``weight``.
        :type weight: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Splice`
        """

        db_id = TableBase.insert(self, part_number=part_number, description=description,
                                 mfg_id=mfg_id, family_id=family_id, series_id=series_id,
                                 material_id=material_id, color_id=color_id, plating_id=plating_id,
                                 type_id=type_id, min_dia=min_dia, max_dia=max_dia,
                                 resistance=resistance, length=length, weight=weight)

        return Splice(self, db_id)

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
                'label': 'Material',
                'type': [int, str],
                'search_params': ['material_id', 'materials', 'name']
            },
            6: {
                'label': 'Plating',
                'type': [int, str],
                'search_params': ['plating_id', 'platings', 'symbol']
            },
            7: {
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            8: {
                'label': 'Type',
                'type': [int, str],
                'search_params': ['type_id', 'splice_types', 'name']
            },
            9: {
                'label': 'Diameter (Min)(mm)',
                'type': [float],
                'search_params': ['min_dia']
            },
            10: {
                'label': 'Diameter (Max)(mm)',
                'type': [float],
                'search_params': ['max_dia']
            },
            11: {
                'label': 'Resistance (ohms)',
                'type': [float],
                'search_params': ['resistance']
            },
            12: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            13: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class Splice(EntryBase, PartNumberMixin, DescriptionMixin, ManufacturerMixin,
             FamilyMixin, SeriesMixin, MaterialMixin, ColorMixin, PlatingMixin,
             ResourceMixin, Model3DMixin, WeightMixin, TemperatureMixin,
             DimensionMixin, WireSizeMixin):
    """Represent a splice in :mod:`harness_designer.database.global_db.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: SplicesTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        mfg = self.manufacturer
        color = self.color

        packet = {
            'tpa_locks': [self.db_id],
            'families': [self.family_id],
            'splice_types': [self.type_id],
            'series': [self.series_id],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id],
            'models3d': [self.model3d_id]
        }

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

    @property
    def type(self) -> "_splice_types.SpliceType":
        """Return the type.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_splice_types.SpliceType`
        """
        db_id = self.type_id
        return self._table.db.splice_types_table[db_id]

    @property
    def type_id(self) -> int:
        """Return the type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('type_id', id=self._db_id)[0][0]

    @type_id.setter
    def type_id(self, value: int):
        """Set the type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, type_id=value)
        self._populate('type_id')

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
    def min_dia(self) -> float:
        """Return the min dia.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('min_dia', id=self._db_id)[0][0]

    @min_dia.setter
    def min_dia(self, value: float):
        """Set the min dia.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, min_dia=value)
        self._populate('min_dia')

    @property
    def max_dia(self) -> float:
        """Return the max dia.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('max_dia', id=self._db_id)[0][0]

    @max_dia.setter
    def max_dia(self, value: float):
        """Set the max dia.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, min_dia=value)
        self._populate('max_dia')


class SpliceControl(QTabWidget):
    """Represent a splice control in :mod:`harness_designer.database.global_db.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    # TODO: Add splice types

    def set_obj(self, db_obj: Splice):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Splice`
        """
        self.db_obj = db_obj

        self.mfg_page.set_obj(db_obj)
        self.family_page.set_obj(db_obj)
        self.series_page.set_obj(db_obj)
        self.temperature_page.set_obj(db_obj)
        self.dimension_page.set_obj(db_obj)
        self.resources_page.set_obj(db_obj)
        self.plating_page.set_obj(db_obj)
        self.model3d_page.set_obj(db_obj)

        self.material_ctrl.set_obj(db_obj)
        self.part_number_ctrl.set_obj(db_obj)
        self.description_ctrl.set_obj(db_obj)
        self.color_ctrl.set_obj(db_obj)
        self.weight_ctrl.set_obj(db_obj)
        self.wire_size_page.set_obj(db_obj)

        if db_obj is None:
            self.splice_type_choices = []
            self.splice_type_ctrl.SetItems([])
            self.splice_type_ctrl.SetValue('')
            self.resistance_ctrl.SetValue(0.0)
            self.min_dia_ctrl.SetValue(0.0)
            self.max_dia_ctrl.SetValue(0.0)

            self.splice_type_ctrl.setEnabled(False)
            self.resistance_ctrl.setEnabled(False)
            self.min_dia_ctrl.setEnabled(False)
            self.max_dia_ctrl.setEnabled(False)
        else:
            self.db_obj.table.execute(f'SELECT name FROM splice_types;')
            rows = self.db_obj.table.fetchall()

            self.splice_type_choices = sorted([row[0] for row in rows])

            self.splice_type_ctrl.SetItems(self.splice_type_choices)
            self.splice_type_ctrl.SetValue(db_obj.type.name)

            self.resistance_ctrl.SetValue(db_obj.resistance)
            self.min_dia_ctrl.SetValue(db_obj.min_dia)
            self.max_dia_ctrl.SetValue(db_obj.max_dia)

            self.splice_type_ctrl.setEnabled(True)
            self.resistance_ctrl.setEnabled(True)
            self.min_dia_ctrl.setEnabled(True)
            self.max_dia_ctrl.setEnabled(True)

    def _on_resistance(self, evt):
        """Handle the resistance event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.resistance = value

    def _on_max_dia(self, evt):
        """Handle the max dia event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.max_dia = value

    def _on_min_dia(self, evt):
        """Handle the min dia event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.min_dia = value

    def _on_splice_type(self, evt):
        """Handle the splice type event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        name = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM splice_types WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id = rows[0][0]

        else:
            db_obj = self.db_obj.table.db.splice_types_table.insert(name)
            db_id = db_obj.db_id

            self.splice_type_choices.append(name)
            self.splice_type_choices.sort()
            self.splice_type_ctrl.SetItems(self.splice_type_choices)
            self.splice_type_ctrl.SetValue(name)

        self.db_obj.type_id = db_id

    def __init__(self, parent):
        """Initialise the :class:`SpliceControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Splice = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        general_page = _prop_ctrls.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.color_ctrl = ColorControl(general_page)

        self.resistance_ctrl = _prop_ctrls.FloatProperty(
            general_page, 'Resistance', min_value=0.0,
            max_value=100000, increment=0.01, units='Ω')

        self.material_ctrl = MaterialControl(general_page)

        self.splice_type_choices: list[str] = []
        self.splice_type_ctrl = _prop_ctrls.ComboBoxProperty(general_page, 'Type')

        general_page.addWidget(self.part_number_ctrl)
        general_page.addWidget(self.description_ctrl)
        general_page.addWidget(self.color_ctrl)
        general_page.addWidget(self.resistance_ctrl)
        general_page.addWidget(self.material_ctrl)
        general_page.addWidget(self.splice_type_ctrl)

        self.plating_page = PlatingControl(self)

        diameter_page = _prop_ctrls.Category(self, 'Diameter')
        self.min_dia_ctrl = _prop_ctrls.FloatProperty(
            diameter_page, 'Minimum', min_value=0.0,
            max_value=99.9, increment=0.01, units='mm')

        self.max_dia_ctrl = _prop_ctrls.FloatProperty(
            general_page, 'Maximum', min_value=0.00,
            max_value=99.9, increment=0.01, units='mm')

        diameter_page.addWidget(self.min_dia_ctrl)
        diameter_page.addWidget(self.max_dia_ctrl)

        self.splice_type_ctrl.propertyChanged.connect(self._on_splice_type)
        self.resistance_ctrl.propertyChanged.connect(self._on_resistance)
        self.min_dia_ctrl.propertyChanged.connect(self._on_min_dia)
        self.max_dia_ctrl.propertyChanged.connect(self._on_max_dia)

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)

        self.dimension_page = DimensionControl(self)
        self.weight_ctrl = WeightControl(self.dimension_page)

        self.dimension_page.addWidget(self.weight_ctrl)

        self.resources_page = ResourcesControl(self)

        self.model3d_page = Model3DControl(self)

        self.wire_size_page = WireSizeControl(self)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.dimension_page,
            self.resources_page,
            diameter_page,
            self.plating_page,
            self.model3d_page,
            self.wire_size_page
        ):
            self.addTab(page, page.GetLabel())
