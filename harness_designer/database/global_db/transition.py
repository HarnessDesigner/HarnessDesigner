# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QTabWidget
from typing import Iterable as _Iterable, TYPE_CHECKING


from ...ui import prop_ctrls as _prop_ctrls
from .bases import EntryBase, TableBase
from .mixins import (
    PartNumberMixin, PartNumberControl,
    SeriesMixin, SeriesControl,
    MaterialMixin, MaterialControl,
    FamilyMixin, FamilyControl,
    ManufacturerMixin, ManufacturerControl,
    DescriptionMixin, DescriptionControl,
    ColorMixin, ColorControl,
    ProtectionMixin, ProtectionControl,
    AdhesiveMixin, AdhesiveControl,
    ResourceMixin, ResourcesControl,
    TemperatureMixin, TemperatureControl,
    WeightMixin, WeightControl
)


if TYPE_CHECKING:
    from . import transition_branch as _transition_branch
    from . import shape as _shape


class TransitionsTable(TableBase):
    """Represent a transitions table in :mod:`harness_designer.database.global_db.transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'transitions'

    _control: "TransitionControl" = None

    @property
    def control(self) -> "TransitionControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`TransitionControl`
        """
        if self._control is None:
            self._control = TransitionControl(self.db.mainframe)
            self._control.hide()
        return self._control

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import transitions

        return transitions.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import transitions

        transitions.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        transitions.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import transitions

        transitions.table.update_fields(self)

    def __iter__(self) -> _Iterable["Transition"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Transition']
        """
        for db_id in TableBase.__iter__(self):
            yield Transition(self, db_id)

    def __getitem__(self, item) -> "Transition":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Transition`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Transition(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Transition(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, family_id: int,
               series_id: int, color_id: int, material_id: int, branch_count: int,
               shape_id: int, protection_ids: list[int], adhesive_ids: list[int],
               cad_id: int, datasheet_id: int, image_id: int, min_temp_id: int,
               max_temp_id: int, weight: float) -> "Transition":
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
        :param color_id: Identifier for the color.
        :type color_id: int
        :param material_id: Identifier for the material.
        :type material_id: int
        :param branch_count: Value for ``branch_count``.
        :type branch_count: int
        :param shape_id: Identifier for the shape.
        :type shape_id: int
        :param protection_ids: Identifier for the protection.
        :type protection_ids: list[int]
        :param adhesive_ids: Identifier for the adhesive.
        :type adhesive_ids: list[int]
        :param cad_id: Identifier for the cad.
        :type cad_id: int
        :param datasheet_id: Identifier for the datasheet.
        :type datasheet_id: int
        :param image_id: Identifier for the image.
        :type image_id: int
        :param min_temp_id: Identifier for the min temp.
        :type min_temp_id: int
        :param max_temp_id: Identifier for the max temp.
        :type max_temp_id: int
        :param weight: Value for ``weight``.
        :type weight: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Transition`
        """

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 family_id=family_id, series_id=series_id, color_id=color_id,
                                 material_id=material_id, branch_count=branch_count, shape_id=shape_id,
                                 protection_ids=str(protection_ids), adhesive_ids=str(adhesive_ids),
                                 cad_id=cad_id, datasheet_id=datasheet_id, image_id=image_id,
                                 min_temp_id=min_temp_id, max_temp_id=max_temp_id, weight=weight)

        return Transition(self, db_id)

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
                'label': 'Branch Count',
                'type': [int],
                'search_params': ['branch_count']
            },
            6: {
                'label': 'Shape',
                'type': [int, str],
                'search_params': ['shape_id', 'shapes', 'name']
            },
            7: {
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            8: {
                'label': 'Material',
                'type': [int, str],
                'search_params': ['material_id', 'materials', 'name']
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
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class Transition(EntryBase, PartNumberMixin, SeriesMixin, MaterialMixin, FamilyMixin,
                 ManufacturerMixin, DescriptionMixin, ColorMixin, ProtectionMixin, AdhesiveMixin,
                 ResourceMixin, TemperatureMixin, WeightMixin):
    """Represent a transition in :mod:`harness_designer.database.global_db.transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    _table: TransitionsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        mfg = self.manufacturer
        color = self.color

        packet = {
            'transitions': [self.db_id],
            'families': [self.family_id],
            'series': [self.series_id],
            'shapes': [self.shape_id],
            'materials': [self.material_id],
            'temperatures': [self.min_temp_id, self.max_temp],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id]
        }

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

    @property
    def branch_count(self) -> int:
        """Return the branch count.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('branch_count', id=self._db_id)[0][0]

    @branch_count.setter
    def branch_count(self, value: int):
        """Set the branch count.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, branch_count=value)
        self._populate('branch_count')

    @property
    def branches(self) -> list["_transition_branch.TransitionBranch"]:
        """Return the branches.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_transition_branch.TransitionBranch']
        """
        res = [None] * self.branch_count

        branch_ids = self._table.db.transition_branches_table.select('id', transition_id=self._db_id)

        for branch_id in branch_ids:
            branch = self._table.db.transition_branches_table[branch_id[0]]
            res[branch.idx - 1] = branch

        return res

    @property
    def shape(self) -> "_shape.Shape":
        """Return the shape.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_shape.Shape`
        """
        shape_id = self.shape_id
        from .shape import Shape

        return Shape(self._table.db.shapes_table, shape_id)

    @property
    def shape_id(self) -> int:
        """Return the shape ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('shape_id', id=self._db_id)[0][0]

    @shape_id.setter
    def shape_id(self, value: int):
        """Set the shape ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, shape_id=value)
        self._populate('shape_id')


class TransitionControl(QTabWidget):
    """Represent a transition control in :mod:`harness_designer.database.global_db.transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: Transition):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Transition`
        """
        if self.db_obj is not None:
            for i in range(self.branch_count_ctrl.GetValue()):
                self.branch_page.removeTab(i)

                branch = self.branches[i]
                branch.hide()
                branch.setParent(self.db_obj.table.db.mainframe)

            self.branches = []

        self.db_obj = db_obj

        self.mfg_page.set_obj(db_obj)
        self.family_page.set_obj(db_obj)
        self.series_page.set_obj(db_obj)
        self.temperature_page.set_obj(db_obj)
        self.resources_page.set_obj(db_obj)
        self.part_number_ctrl.set_obj(db_obj)
        self.description_ctrl.set_obj(db_obj)
        self.color_ctrl.set_obj(db_obj)
        self.weight_ctrl.set_obj(db_obj)

        self.material_ctrl.set_obj(db_obj)
        self.protection_ctrl.set_obj(db_obj)
        self.adhesive_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.branch_count_ctrl.SetValue(1)
            self.branch_count_ctrl.Enable(False)
        else:
            self.branch_count_ctrl.SetValue(db_obj.branch_count)
            self.branch_count_ctrl.Enable(True)

            for i, branch in enumerate(db_obj.branches):
                branch_ctrl = db_obj.table.db.transition_branches_table.get_control(i)
                branch_ctrl.set_obj(branch)
                branch_ctrl.setParent(self.branch_page)
                self.branch_page.addTab(branch_ctrl, branch_ctrl.GetLabel())
                branch_ctrl.Realize()
                self.branches.append(branch_ctrl)

    def _on_branch_count(self, evt):
        """Handle the branch count event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        new_value = evt.GetValue()
        old_value = self.db_obj.branch_count

        if new_value > old_value:
            self.db_obj.table.execute(f'SELECT id FROM transition_branches WHERE idx={new_value} AND transition_id={self.db_obj.db_id};')
            rows = self.db_obj.table.fetchall()

            if rows:
                db_id = rows[0][0]
                branch = self.db_obj.table.db.transition_branches_table[db_id]
            else:
                branch = self.db_obj.table.db.transition_branches_table.insert(
                    transition_id=self.db_obj.db_id, idx=new_value, name='',
                    bulb_offset=None, bulb_length=None,min_dia=0.01, max_dia=0.01,
                    length=0.01, angle=0.0, offset=None, flange_height=None, flange_width=None)

            branch_ctrl = self.db_obj.table.db.transition_branches_table.get_control(new_value - 1)
            branch_ctrl.set_obj(branch)
            branch_ctrl.setParent(self.branch_page)
            self.branch_page.addTab(branch_ctrl, branch_ctrl.GetLabel())
            branch_ctrl.Realize()
            self.branches.append(branch_ctrl)
        else:
            branch_ctrl = self.branches.pop(-1)
            self.branch_page.removeTab(new_value + 1)
            branch_ctrl.setParent(self.db_obj.table.db.mainframe)
            branch_ctrl.hide()

        self.db_obj.branch_count = new_value

    def __init__(self, parent):
        """Initialise the :class:`TransitionControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Transition = None
        self.branches = []

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        general_page = _prop_ctrls.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.color_ctrl = ColorControl(general_page)
        self.weight_ctrl = WeightControl(general_page)
        self.material_ctrl = MaterialControl(general_page)
        self.protection_ctrl = ProtectionControl(general_page)
        self.adhesive_ctrl = AdhesiveControl(general_page)

        branch_page = _prop_ctrls.Category(self, 'Branches')

        self.branch_count_ctrl = _prop_ctrls.IntProperty(
            branch_page, 'Branch Count', min_value=1, max_value=6)

        self.branch_page = QTabWidget(branch_page)
        self.branch_page.setTabPosition(QTabWidget.TabPosition.North)
        self.branch_page.setUsesScrollButtons(True)

        self.branch_count_ctrl.property_changed.connect(self._on_branch_count)

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)

        self.resources_page = ResourcesControl(self)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.resources_page,
            branch_page
        ):
            self.addTab(page, page.GetLabel())
            page.Realize()
