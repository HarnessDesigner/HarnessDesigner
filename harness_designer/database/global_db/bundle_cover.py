# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QTabWidget
from typing import Iterable as _Iterable, TYPE_CHECKING


from ...ui import prop_ctrls as _prop_ctrls
from .bases import EntryBase, TableBase
from .mixins import (
    PartNumberMixin, PartNumberControl,
    ManufacturerMixin, ManufacturerControl,
    DescriptionMixin, DescriptionControl,
    ResourceMixin, ResourcesControl,
    TemperatureMixin, TemperatureControl,
    ColorMixin, ColorControl,
    SeriesMixin, SeriesControl,
    MaterialMixin, MaterialControl,
    ProtectionMixin, ProtectionControl,
    AdhesiveMixin, AdhesiveControl,
    WeightMixin, WeightControl,
    FamilyMixin, FamilyControl
)


if TYPE_CHECKING:
    from . import temperature as _temperature


class BundleCoversTable(TableBase):
    """Represent a bundle covers table in :mod:`harness_designer.database.global_db.bundle_cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'bundle_covers'

    _control: "BundleCoverControl" = None

    @property
    def control(self) -> "BundleCoverControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`BundleCoverControl`
        """
        if self._control is None:
            self._control = BundleCoverControl(self.db.mainframe)
            self._control.hide()
        return self._control

    def _load_database(self, splash):
        """Load the database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import bundle_covers

        data_path = self._con.db_data.open(splash)
        bundle_covers.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import bundle_covers

        return bundle_covers.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import bundle_covers

        bundle_covers.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        bundle_covers.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import bundle_covers

        bundle_covers.table.update_fields(self)

    def __iter__(self) -> _Iterable["BundleCover"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['BundleCover']
        """
        for db_id in TableBase.__iter__(self):
            yield BundleCover(self, db_id)

    def __getitem__(self, item) -> "BundleCover":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`BundleCover`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return BundleCover(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return BundleCover(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, series_id: int, image_id: int,
               datasheet_id: int, cad_id: int, min_temp_id: int, max_temp_id: int, color_id: int,
               min_size: float, max_size: float, wall: str, shrink_ratio: str, protections: str,
               material_id: int, rigidity: str, shrink_temp_id: int, adhesives: list[str],
               weight: float) -> "BundleCover":
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
        :param color_id: Identifier for the color.
        :type color_id: int
        :param min_size: Value for ``min_size``.
        :type min_size: float
        :param max_size: Value for ``max_size``.
        :type max_size: float
        :param wall: Value for ``wall``.
        :type wall: str
        :param shrink_ratio: Value for ``shrink_ratio``.
        :type shrink_ratio: str
        :param protections: Value for ``protections``.
        :type protections: str
        :param material_id: Identifier for the material.
        :type material_id: int
        :param rigidity: Value for ``rigidity``.
        :type rigidity: str
        :param shrink_temp_id: Identifier for the shrink temp.
        :type shrink_temp_id: int
        :param adhesives: Value for ``adhesives``.
        :type adhesives: list[str]
        :param weight: Value for ``weight``.
        :type weight: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`BundleCover`
        """
        
        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description, 
                                 series_id=series_id, image_id=image_id, datasheet_id=datasheet_id, 
                                 cad_id=cad_id, min_temp_id=min_temp_id, max_temp_id=max_temp_id,
                                 color_id=color_id, min_size=min_size, max_size=max_size, wall=wall,
                                 shrink_ratio=shrink_ratio, protections=protections,
                                 material_id=material_id, rigidity=rigidity, shrink_temp_id=shrink_temp_id,
                                 adhesives=f"[{', '.join(adhesives)}]", weight=weight)

        return BundleCover(self, db_id)

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
                'label': 'Material',
                'type': [int, str],
                'search_params': ['material_id', 'materials', 'name']
            },
            7: {
                'label': 'Diameter (Min)',
                'type': [float],
                'search_params': ['min_dia']
            },
            8: {
                'label': 'Diameter (Max)',
                'type': [float],
                'search_params': ['max_dia']
            },
            9: {
                'label': 'Temperature (Min)',
                'type': [int, str],
                'search_params': ['min_temp_id', 'temperatures', 'name']
            },
            10: {
                'label': 'Temperature (Max)',
                'type': [int, str],
                'search_params': ['max_temp_id', 'temperatures', 'name']
            },
            11: {
                'label': 'Temperature (Shrink)',
                'type': [int, str],
                'search_params': ['shrink_temp_id', 'temperatures', 'name']
            },
            12: {
                'label': 'Weight',
                'type': [float],
                'search_params': ['weight']
            },
            13: {
                'label': 'Rigidity',
                'type': [str],
                'search_params': ['rigidity']
            },
            14: {
                'label': 'Wall',
                'type': [str],
                'search_params': ['wall']
            },
            15: {
                'label': 'Shrink Ratio',
                'type': [str],
                'search_params': ['shrink_ratio']
            },
            16: {
                'label': 'Protection',
                'type': [int, str],
                'search_params': ['protection_id', 'protections', 'name']
            },
        }

        return ret


class BundleCover(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin, 
                  ResourceMixin, TemperatureMixin, ColorMixin, SeriesMixin,
                  MaterialMixin, ProtectionMixin, AdhesiveMixin, WeightMixin,
                  FamilyMixin):
    """Represent a bundle cover in :mod:`harness_designer.database.global_db.bundle_cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    _table: BundleCoversTable = None

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
            'temperatures': [self.min_temp_id, self.max_temp_id],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id],
        }

        self.merge_packet_data(self.manufacturer.build_monitor_packet(), packet)

        return packet

    @property
    def rigidity(self) -> str:
        """Return the rigidity.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('rigidity', id=self._db_id)[0][0]

    @rigidity.setter
    def rigidity(self, value: str):
        """Set the rigidity.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, rigidity=value)
        self._populate('rigidity')

    @property
    def shrink_temp(self) -> "_temperature.Temperature":
        """Return the shrink temp.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_temperature.Temperature`
        """
        shrink_temp_id = self.shrink_temp_id
        from .temperature import Temperature

        return Temperature(self._table.db.temperatures_table, shrink_temp_id)

    @property
    def shrink_temp_id(self) -> int:
        """Return the shrink temp ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('shrink_temp_id', id=self._db_id)[0][0]

    @shrink_temp_id.setter
    def shrink_temp_id(self, value: int):
        """Set the shrink temp ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, shrink_temp_id=value)
        self._populate('shrink_temp_id')

    @property
    def shrink_ratio(self) -> str:
        """Return the shrink ratio.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('shrink_ratio', id=self._db_id)[0][0]

    @shrink_ratio.setter
    def shrink_ratio(self, value: str):
        """Set the shrink ratio.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, shrink_ratio=value)
        self._populate('shrink_ratio')

    @property
    def wall(self) -> str:
        """Return the wall.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('wall', id=self._db_id)[0][0]

    @wall.setter
    def wall(self, value: str):
        """Set the wall.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, wall=value)
        self._populate('wall')

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
        self._table.update(self._db_id, min_dia=round(value, 6))
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
        self._table.update(self._db_id, max_dia=round(value, 6))
        self._populate('max_dia')


class BundleCoverControl(QTabWidget):
    """Represent a bundle cover control in :mod:`harness_designer.database.global_db.bundle_cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: BundleCover):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`BundleCover`
        """
        self.db_obj = db_obj

        self.mfg_page.set_obj(db_obj)
        self.family_page.set_obj(db_obj)
        self.series_page.set_obj(db_obj)
        self.temperature_page.set_obj(db_obj)
        self.resources_page.set_obj(db_obj)

        self.part_number_ctrl.set_obj(db_obj)
        self.description_ctrl.set_obj(db_obj)
        self.color_ctrl.set_obj(db_obj)
        self.material_ctrl.set_obj(db_obj)
        self.weight_ctrl.set_obj(db_obj)
        self.adhesive_ctrl.set_obj(db_obj)
        self.protection_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.shrink_temp_choices = []

            self.shrink_temp_ctrl.SetItems(self.shrink_temp_choices)
            self.shrink_temp_ctrl.SetValue('')
            self.rigidity_ctrl.SetValue('')
            self.shrink_ratio_ctrl.SetValue('')
            self.wall_ctrl.SetValue('')
            self.min_dia_ctrl.SetValue(0.0)
            self.max_dia_ctrl.SetValue(0.0)

            self.shrink_temp_ctrl.Enable(False)
            self.rigidity_ctrl.Enable(False)
            self.shrink_ratio_ctrl.Enable(False)
            self.wall_ctrl.Enable(False)
            self.min_dia_ctrl.Enable(False)
            self.max_dia_ctrl.Enable(False)
        else:
            db_obj.table.execute(f'SELECT name FROM temperatures;')
            rows = db_obj.table.fetchall()
            self.shrink_temp_choices = sorted([row[0] for row in rows])

            self.shrink_temp_ctrl.SetItems(self.shrink_temp_choices)
            self.shrink_temp_ctrl.SetValue(db_obj.min_temp.name)

            self.rigidity_ctrl.SetValue(db_obj.rigidity)
            self.shrink_ratio_ctrl.SetValue(db_obj.shrink_ratio)
            self.wall_ctrl.SetValue(db_obj.wall)
            self.min_dia_ctrl.SetValue(db_obj.min_dia)
            self.max_dia_ctrl.SetValue(db_obj.max_dia)

            self.shrink_temp_ctrl.Enable(True)
            self.rigidity_ctrl.Enable(True)
            self.shrink_ratio_ctrl.Enable(True)
            self.wall_ctrl.Enable(True)
            self.min_dia_ctrl.Enable(True)
            self.max_dia_ctrl.Enable(True)

    def _on_rigidity(self, evt):
        """Handle the rigidity event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.rigidity = value

    def _on_shrink_ratio(self, evt):
        """Handle the shrink ratio event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.shrink_ratio = value

    def _on_wall(self, evt):
        """Handle the wall event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.wall = value

    def _on_min_dia(self, evt):
        """Handle the min dia event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.min_dia = value

    def _on_max_dia(self, evt):
        """Handle the max dia event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.max_dia = value

    def _on_shrink_temp(self, evt):
        """Handle the shrink temp event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.rigidity = value

        name = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM temperatures WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.temperatures_table.insert(name)
            db_id = db_obj.db_id

            self.shrink_temp_choices.append(name)
            self.shrink_temp_choices.sort()

            self.shrink_temp_ctrl.SetItems(self.shrink_temp_choices)
            self.shrink_temp_ctrl.SetValue(name)

        self.db_obj.shrink_temp_id = db_id

    def __init__(self, parent):
        """Initialise the :class:`BundleCoverControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: BundleCover = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        general_page = _prop_ctrls.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.color_ctrl = ColorControl(general_page)
        self.material_ctrl = MaterialControl(general_page)
        self.adhesive_ctrl = AdhesiveControl(general_page)
        self.weight_ctrl = WeightControl(general_page)
        self.protection_ctrl = ProtectionControl(general_page)

        self.rigidity_ctrl = _prop_ctrls.StringProperty(general_page, 'Rigidity')
        self.shrink_ratio_ctrl = _prop_ctrls.StringProperty(general_page, 'Shrink Ratio')
        self.wall_ctrl = _prop_ctrls.StringProperty(general_page, 'Wall')

        self.rigidity_ctrl.property_changed.connect(self._on_rigidity)
        self.shrink_ratio_ctrl.property_changed.connect(self._on_shrink_ratio)
        self.wall_ctrl.property_changed.connect(self._on_wall)

        self.diameter_page = _prop_ctrls.Property(self, 'Diameter')

        self.min_dia_ctrl = _prop_ctrls.FloatProperty(
            self.diameter_page, 'Minimum', min_value=0.00,
            max_value=999.9, increment=0.01, units='mm')

        self.max_dia_ctrl = _prop_ctrls.FloatProperty(
            self.diameter_page, 'Maximum', min_value=0.00,
            max_value=999.9, increment=0.01, units='mm')

        self.min_dia_ctrl.property_changed.connect(self._on_min_dia)
        self.max_dia_ctrl.property_changed.connect(self._on_max_dia)

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)
        self.resources_page = ResourcesControl(self)

        self.shrink_temp_choices: list[str] = []
        self.shrink_temp_ctrl = _prop_ctrls.ComboBoxProperty(self.temperature_page, 'Shrink Temperature')
        self.shrink_temp_ctrl.property_changed.connect(self._on_shrink_temp)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.resources_page,
        ):
            self.addTab(page, page.GetLabel())
            page.Realize()
