from typing import Iterable as _Iterable, TYPE_CHECKING

import wx

from ...ui.editor_obj import prop_grid as _prop_grid
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
    __table_name__ = 'transitions'

    def _table_needs_update(self) -> bool:
        from ..create_database import transitions

        return transitions.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import transitions

        transitions.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        transitions.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import transitions

        transitions.table.update_fields(self)

    def __iter__(self) -> _Iterable["Transition"]:
        for db_id in TableBase.__iter__(self):
            yield Transition(self, db_id)

    def __getitem__(self, item) -> "Transition":
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

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 family_id=family_id, series_id=series_id, color_id=color_id,
                                 material_id=material_id, branch_count=branch_count, shape_id=shape_id,
                                 protection_ids=str(protection_ids), adhesive_ids=str(adhesive_ids),
                                 cad_id=cad_id, datasheet_id=datasheet_id, image_id=image_id,
                                 min_temp_id=min_temp_id, max_temp_id=max_temp_id, weight=weight)

        return Transition(self, db_id)

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
    
    _table: TransitionsTable = None

    def build_monitor_packet(self):
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
        return self._table.select('branch_count', id=self._db_id)[0][0]

    @branch_count.setter
    def branch_count(self, value: int):
        self._table.update(self._db_id, branch_count=value)
        self._populate('branch_count')

    @property
    def branches(self) -> list["_transition_branch.TransitionBranch"]:
        res = [None] * self.branch_count

        branch_ids = self._table.db.transition_branches_table.select('id', transition_id=self._db_id)

        for branch_id in branch_ids:
            branch = self._table.db.transition_branches_table[branch_id[0]]
            res[branch.idx - 1] = branch

        return res

    @property
    def shape(self) -> "_shape.Shape":
        shape_id = self.shape_id
        from .shape import Shape

        return Shape(self._table.db.shapes_table, shape_id)

    @property
    def shape_id(self) -> int:
        return self._table.select('shape_id', id=self._db_id)[0][0]

    @shape_id.setter
    def shape_id(self, value: int):
        self._table.update(self._db_id, shape_id=value)
        self._populate('shape_id')


class TransitionControl(wx.Notebook):

    def set_obj(self, db_obj: Transition):
        if self.db_obj is not None:
            for i in range(self.branch_count_ctrl.GetValue()):
                self.branch_page.RemovePage(i)

                branch = self.branches[i]
                branch.Show(False)
                branch.Reparent(self.db_obj.table.db.mainframe)

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
                branch_ctrl.Reparent(self.branch_page)
                self.branch_page.AddPage(branch_ctrl, branch_ctrl.GetLabel())
                branch_ctrl.Realize()
                self.branches.append(branch_ctrl)

    def _on_branch_count(self, evt):
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
            branch_ctrl.Reparent(self.branch_page)
            self.branch_page.AddPage(branch_ctrl, branch_ctrl.GetLabel())
            branch_ctrl.Realize()
            self.branches.append(branch_ctrl)
        else:
            branch_ctrl = self.branches.pop(-1)
            self.branch_page.RemovePage(new_value + 1)
            branch_ctrl.Reparent(self.db_obj.table.db.mainframe)
            branch_ctrl.Show(False)

        self.db_obj.branch_count = new_value

    def __init__(self, parent):
        self.db_obj: Transition = None
        self.branches = []

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.color_ctrl = ColorControl(general_page)
        self.weight_ctrl = WeightControl(general_page)
        self.material_ctrl = MaterialControl(general_page)
        self.protection_ctrl = ProtectionControl(general_page)
        self.adhesive_ctrl = AdhesiveControl(general_page)

        branch_page = _prop_grid.Category(self, 'Branches')

        self.branch_count_ctrl = _prop_grid.IntProperty(
            branch_page, 'Branch Count', min_value=1, max_value=6)

        self.branch_page = wx.Notebook(branch_page, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        self.branch_count_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_branch_count)

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
            self.AddPage(page, page.GetLabel())
            page.Realize()
