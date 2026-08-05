# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QTabWidget
from typing import Iterable as _Iterable


from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import (
    PartNumberMixin, PartNumberControl,
    ManufacturerMixin, ManufacturerControl,
    DescriptionMixin, DescriptionControl,
    FamilyMixin, FamilyControl,
    SeriesMixin, SeriesControl,
    ColorMixin, ColorControl,
    TemperatureMixin, TemperatureControl,
    ResourceMixin, ResourcesControl,
    WeightMixin, WeightControl,
    WireSizeMixin, WireSizeControl
)
from ... import check_types as _check_types


class WireMarkersTable(TableBase):
    """Represent a wire markers table in :mod:`harness_designer.database.global_db.wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__: str = 'wire_markers'

    _control: "WireMarkerControl" = None

    @property
    @_check_types.do
    def control(self) -> "WireMarkerControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`WireMarkerControl`
        """
        if self._control is None:
            self._control = WireMarkerControl(self.db.mainframe)
            self._control.hide()
        return self._control

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import wire_markers

        return wire_markers.table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import wire_markers

        wire_markers.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        wire_markers.add_records(self._con, splash, data_path)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wire_markers

        wire_markers.table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["WireMarker"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['WireMarker']
        """

        for db_id in TableBase.__iter__(self):
            yield WireMarker(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "WireMarker":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`WireMarker`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in self:
                return WireMarker(self, item)

            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return WireMarker(self, db_id[0][0])

        raise KeyError(item)

    @_check_types.do
    def insert(self, part_number: str, mfg_id: bytes, description: str, image_id: bytes, datasheet_id: bytes,
               cad_id: bytes, color_id: bytes, min_diameter: float, max_diameter: float, length: float) -> "WireMarker":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_number: Value for ``part_number``.
        :type part_number: str
        :param mfg_id: Identifier for the mfg.
        :type mfg_id: bytes
        :param description: Value for ``description``.
        :type description: str
        :param image_id: Identifier for the image.
        :type image_id: bytes
        :param datasheet_id: Identifier for the datasheet.
        :type datasheet_id: bytes
        :param cad_id: Identifier for the cad.
        :type cad_id: bytes
        :param color_id: Identifier for the color.
        :type color_id: bytes
        :param min_diameter: Value for ``min_diameter``.
        :type min_diameter: float
        :param max_diameter: Value for ``max_diameter``.
        :type max_diameter: float
        :param length: Value for ``length``.
        :type length: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`WireMarker`
        """

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 image_id=image_id, datasheet_id=datasheet_id, cad_id=cad_id,
                                 color_id=color_id, min_diameter=min_diameter,
                                 max_diameter=max_diameter, length=length)

        return WireMarker(self, db_id)

    @property
    @_check_types.do
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
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            4: {
                'label': 'Diameter (Min)(AWG)',
                'type': [int],
                'search_params': ['min_awg']
            },
            5: {
                'label': 'Diameter (Min)(AWG)',
                'type': [int],
                'search_params': ['max_awg']
            },
            6: {
                'label': 'Diameter (Min)(mm)',
                'type': [float],
                'search_params': ['min_diameter']
            },
            7: {
                'label': 'Diameter (Min)(mm)',
                'type': [float],
                'search_params': ['max_diameter']
            },
            8: {
                'label': 'Label',
                'type': [bool],
                'search_params': ['has_label']
            },
            9: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            10: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class WireMarker(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin,
                 FamilyMixin, SeriesMixin, ColorMixin, TemperatureMixin, ResourceMixin,
                 WeightMixin, WireSizeMixin):
    """Represent a wire marker in :mod:`harness_designer.database.global_db.wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: WireMarkersTable = None

    _stored_weight: float | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def weight(self) -> float:
        """Return the weight.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_weight is DefaultStoredValue:
            self._stored_weight = self._table.select('weight', id=self._db_id)[0][0]

        return self._stored_weight

    @weight.setter
    @_check_types.do
    def weight(self, value: float):
        """Set the weight.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_weight = value
        self._table.update(self._db_id, weight=value)
        self._populate('weight')

    _stored_has_label: bool | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def has_label(self) -> bool:
        """Return the has label.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        if self._stored_has_label is DefaultStoredValue:
            self._stored_has_label = bool(self._table.select('has_label', id=self._db_id)[0][0])

        return self._stored_has_label

    @has_label.setter
    @_check_types.do
    def has_label(self, value: bool):
        """Set the has label.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._stored_has_label = value
        self._table.update(self._db_id, has_label=int(value))
        self._populate('has_label')

    _stored_min_diameter: float | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def min_diameter(self) -> float:
        """Return the min diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_min_diameter is DefaultStoredValue:
            self._stored_min_diameter = self._table.select('min_diameter', id=self._db_id)[0][0]

        return self._stored_min_diameter

    @min_diameter.setter
    @_check_types.do
    def min_diameter(self, value: float):
        """Set the min diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_min_diameter = value
        self._table.update(self._db_id, min_diameter=value)
        self._populate('min_diameter')

    _stored_max_diameter: float | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def max_diameter(self) -> float:
        """Return the max diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_max_diameter is DefaultStoredValue:
            self._stored_max_diameter = self._table.select('max_diameter', id=self._db_id)[0][0]

        return self._stored_max_diameter

    @max_diameter.setter
    @_check_types.do
    def max_diameter(self, value: float):
        """Set the max diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_max_diameter = value
        self._table.update(self._db_id, max_diameter=value)
        self._populate('max_diameter')

    _stored_length: float | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def length(self) -> float:
        """Return the length.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_length is DefaultStoredValue:
            self._stored_length = self._table.select('length', id=self._db_id)[0][0]

        return self._stored_length

    @length.setter
    @_check_types.do
    def length(self, value: float):
        """Set the length.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_length = value
        self._table.update(self._db_id, length=value)
        self._populate('length')


class WireMarkerControl(QTabWidget, LazyTabMixin):
    """Represent a wire marker control in :mod:`harness_designer.database.global_db.wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def set_obj(self, db_obj: WireMarker | None):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`WireMarker`
        """
        self._lazy_set_obj(db_obj)

    @_check_types.do
    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.part_number_ctrl.set_obj(self.db_obj)
            self.description_ctrl.set_obj(self.db_obj)
            self.color_ctrl.set_obj(self.db_obj)
            self.weight_ctrl.set_obj(self.db_obj)
            if self.db_obj is None:
                self.length_ctrl.SetValue(0.05)
                self.label_ctrl.SetValue(False)
                self.length_ctrl.setEnabled(False)
                self.label_ctrl.setEnabled(False)
            else:
                self.length_ctrl.SetValue(self.db_obj.length)
                self.label_ctrl.SetValue(self.db_obj.has_label)
                self.length_ctrl.setEnabled(True)
                self.label_ctrl.setEnabled(True)
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
        elif page is self.wire_size_page:
            self.wire_size_page.set_obj(self.db_obj)
        elif page is self._diameter_page:
            if self.db_obj is None:
                self.min_diameter_ctrl.SetValue(0.05)
                self.max_diameter_ctrl.SetValue(0.05)
                self.min_diameter_ctrl.setEnabled(False)
                self.max_diameter_ctrl.setEnabled(False)
            else:
                self.min_diameter_ctrl.SetValue(self.db_obj.min_diameter)
                self.max_diameter_ctrl.SetValue(self.db_obj.max_diameter)
                self.min_diameter_ctrl.setEnabled(True)
                self.max_diameter_ctrl.setEnabled(True)
        self._tab_loaded[index] = True

    @_check_types.do
    def _on_min_diameter(self, evt):
        """Handle the min diameter event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.min_diameter = value

    @_check_types.do
    def _on_max_diameter(self, evt):
        """Handle the max diameter event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.max_diameter = value

    @_check_types.do
    def _on_length(self, evt):
        """Handle the length event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.length = value

    @_check_types.do
    def _on_label(self, evt):
        """Handle the label event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.has_label = value

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`WireMarkerControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: WireMarker | None = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)

        self.color_ctrl = ColorControl(general_page)
        self.weight_ctrl = WeightControl(general_page)

        self.length_ctrl = _prop_ctrls.FloatProperty(
            general_page, 'Length', min_value=0.01,
            max_value=99.99, increment=0.01, units='mm')

        self.label_ctrl = _prop_ctrls.BoolProperty(
            general_page, 'Has Label')

        general_page.addWidget(self.part_number_ctrl)
        general_page.addWidget(self.description_ctrl)
        general_page.addWidget(self.color_ctrl)
        general_page.addWidget(self.weight_ctrl)
        general_page.addWidget(self.length_ctrl)
        general_page.addWidget(self.label_ctrl)

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)

        self.resources_page = ResourcesControl(self)

        self._diameter_page = diameter_page = _prop_ctrls.Category(self, 'Diameter')

        self.min_diameter_ctrl = _prop_ctrls.FloatProperty(
            diameter_page, 'Minimum', min_value=0.05,
            max_value=60.0, increment=0.01, units='mm')

        self.max_diameter_ctrl = _prop_ctrls.FloatProperty(
            diameter_page, 'Maximum', min_value=0.05,
            max_value=60.0, increment=0.01, units='mm')

        diameter_page.addWidget(self.min_diameter_ctrl)
        diameter_page.addWidget(self.max_diameter_ctrl)

        self.wire_size_page = WireSizeControl(self)

        self.min_diameter_ctrl.propertyChanged.connect(self._on_min_diameter)
        self.max_diameter_ctrl.propertyChanged.connect(self._on_max_diameter)

        self.length_ctrl.propertyChanged.connect(self._on_length)
        self.label_ctrl.propertyChanged.connect(self._on_label)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.resources_page,
            self.wire_size_page,
            diameter_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
