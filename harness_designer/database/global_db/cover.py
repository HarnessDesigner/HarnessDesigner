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
    ColorMixin, ColorControl,
    FamilyMixin, FamilyControl,
    SeriesMixin, SeriesControl,
    ResourceMixin, ResourcesControl,
    WeightMixin, WeightControl,
    TemperatureMixin, TemperatureControl,
    Model3DMixin, Model3DControl,
    DimensionMixin, DimensionControl,
    CompatHousingsMixin, CompatHousingsControl,
    DirectionMixin, DirectionControl
)


class CoversTable(TableBase):
    """Represent a covers table in :mod:`harness_designer.database.global_db.cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'covers'

    _control: "CoverControl" = None

    @property
    def control(self) -> "CoverControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`CoverControl`
        """
        if self._control is None:
            self._control = CoverControl(self.db.mainframe)
            self._control.hide()
        return self._control

    def _load_database(self, splash):
        """Load the database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import covers
        data_path = self._con.db_data.open(splash)

        covers.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import covers

        return covers.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import covers

        covers.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        covers.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import covers

        covers.table.update_fields(self)

    def __iter__(self) -> _Iterable["Cover"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Cover']
        """
        for db_id in TableBase.__iter__(self):
            yield Cover(self, db_id)

    def __getitem__(self, item) -> "Cover":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Cover`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Cover(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Cover(self, db_id[0][0])

        raise KeyError(item)

    def get_compat(self, housing: str = None):
        """Return the compat.

        UNKNOWN details are inferred from the callable name and signature.

        :param housing: Value for ``housing``.
        :type housing: str
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        res = []

        if housing is not None:
            part_number = housing
            field_name = 'compat_housings'
        else:
            return []

        self.execute(f'SELECT id, {field_name} FROM covers WHERE {field_name} LIKE ?;', (f'%{part_number}%',))
        rows = self.fetchall()
        for db_id, compat in rows:
            compat = compat[1:-1].split(', ')

            if part_number not in compat:
                continue

            res.append(db_id)

        return res

    def insert(self, part_number: str, mfg_id: int, description: str, family_id: int,
               series_id: int, image_id: int, datasheet_id: int, cad_id: int,
               direction_id: int, min_temp_id: int, max_temp_id: int, color_id: int,
               length: float, width: float, height: float, pins: str, weight: float) -> "Cover":
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
        :param direction_id: Identifier for the direction.
        :type direction_id: int
        :param min_temp_id: Identifier for the min temp.
        :type min_temp_id: int
        :param max_temp_id: Identifier for the max temp.
        :type max_temp_id: int
        :param color_id: Identifier for the color.
        :type color_id: int
        :param length: Value for ``length``.
        :type length: float
        :param width: Value for ``width``.
        :type width: float
        :param height: Value for ``height``.
        :type height: float
        :param pins: Value for ``pins``.
        :type pins: str
        :param weight: Value for ``weight``.
        :type weight: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Cover`
        """

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 family_id=family_id, series_id=series_id, image_id=image_id,
                                 datasheet_id=datasheet_id, cad_id=cad_id, direction_id=direction_id,
                                 min_temp_id=min_temp_id, max_temp_id=max_temp_id, color_id=color_id,
                                 length=float(length), width=float(width), height=float(height),
                                 pins=pins, weight=float(weight))

        return Cover(self, db_id)

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
                'label': 'Direction',
                'type': [int, str],
                'search_params': ['direction_id', 'directions', 'name']
            },
            7: {
                'label': 'Temperature (Min)',
                'type': [int, str],
                'search_params': ['min_temp_id', 'temperatures', 'name']
            },
            8: {
                'label': 'Temperature (Max)',
                'type': [int, str],
                'search_params': ['max_temp_id', 'temperatures', 'name']
            },
            9: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            10: {
                'label': 'Width (mm)',
                'type': [float],
                'search_params': ['width']
            },
            11: {
                'label': 'Height (mm)',
                'type': [float],
                'search_params': ['height']
            },
            12: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class Cover(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin, DirectionMixin,
            FamilyMixin, SeriesMixin, ResourceMixin, TemperatureMixin,
            ColorMixin, DimensionMixin, WeightMixin, Model3DMixin, CompatHousingsMixin):
    """Represent a cover in :mod:`harness_designer.database.global_db.cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: CoversTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        color = self.color

        packet = {
            'covers': [self.db_id],
            'families': [self.family_id],
            'series': [self.series_id],
            'directions': [self.direction_id],
            'temperatures': [self.min_temp_id, self.max_temp_id],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id],
            'models3d': [self.model3d_id]
        }

        self.merge_packet_data(self.manufacturer.build_monitor_packet(), packet)

        return packet

    _stored_pins: DefaultStoredValueType | str = DefaultStoredValue

    @property
    def pins(self) -> str:
        """Return the pins.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_pins is DefaultStoredValue:
            self._stored_pins = self._table.select('pins', id=self._db_id)[0][0]

        return self._stored_pins

    @pins.setter
    def pins(self, value: str):
        """Set the pins.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_pins = value
        self._table.update(self._db_id, pins=value)
        self._populate('pins')


class CoverControl(QTabWidget, LazyTabMixin):
    """Represent a cover control in :mod:`harness_designer.database.global_db.cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: Cover):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Cover`
        """
        self._lazy_set_obj(db_obj)

    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.part_number_ctrl.set_obj(self.db_obj)
            self.description_ctrl.set_obj(self.db_obj)
            self.color_ctrl.set_obj(self.db_obj)
            self.direction_ctrl.set_obj(self.db_obj)
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
            self.weight_ctrl.set_obj(self.db_obj)
        elif page is self.resources_page:
            self.resources_page.set_obj(self.db_obj)
        elif page is self._compat_parts_page:
            self.compat_housing_ctrl.set_obj(self.db_obj)
        elif page is self.model3d_page:
            self.model3d_page.set_obj(self.db_obj)
        self._tab_loaded[index] = True

    def __init__(self, parent):
        """Initialise the :class:`CoverControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Cover = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.color_ctrl = ColorControl(general_page)
        self.direction_ctrl = DirectionControl(general_page)

        general_page.addWidget(self.part_number_ctrl)
        general_page.addWidget(self.description_ctrl)
        general_page.addWidget(self.color_ctrl)
        general_page.addWidget(self.direction_ctrl)

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

        compat_parts_page.addWidget(self.compat_housing_ctrl)

        self.model3d_page = Model3DControl(self)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.dimension_page,
            self.resources_page,
            compat_parts_page,
            self.model3d_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
