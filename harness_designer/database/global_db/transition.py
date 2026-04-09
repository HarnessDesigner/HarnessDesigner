from typing import Iterable as _Iterable, TYPE_CHECKING

from ...ui.editor_obj import prop_grid as _prop_grid

from .bases import EntryBase, TableBase
from .mixins import (PartNumberMixin, SeriesMixin, MaterialMixin, FamilyMixin,
                     ManufacturerMixin, DescriptionMixin, ColorMixin, ProtectionMixin,
                     AdhesiveMixin, ResourceMixin, TemperatureMixin, WeightMixin)


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

    @shape.setter
    def shape(self, value: "_shape.Shape"):
        self._table.update(self._db_id, shape_id=value.db_id)

    @property
    def shape_id(self) -> int:
        return self._table.select('shape_id', id=self._db_id)[0][0]

    @shape_id.setter
    def shape_id(self, value: int):
        self._table.update(self._db_id, shape_id=value)

    @property
    def propgrid(self) -> _prop_grid.Category:

        part_cat = _prop_grid.Category('Part Attributes')
        
        part_number_prop = self._part_number_propgrid
        manufacturer_prop = self._manufacturer_propgrid
        description_prop = self._description_propgrid
        family_prop = self._family_propgrid
        series_prop = self._series_propgrid
        color_prop = self._color_propgrid
        temperature_prop = self._temperature_propgrid
        resource_prop = self._resource_propgrid
        material_prop = self._material_propgrid
        shape_prop = self.shape.propgrid
        protection_prop = self._protections_propgrid
        weight_prop = self._weight_propgrid

        adhesives_prop = self._adhesives_propgrid

        branch_count_prop = _prop_grid.IntProperty(
            'Branch Count', 'branch_count', self.branch_count, min_value=1, max_value=6)

        branches_prop = _prop_grid.Property('Branches')

        for branch in self.branches:
            if branch is None:
                continue

            branches_prop.Append(branch.propgrid)

        part_cat.Append(part_number_prop)
        part_cat.Append(manufacturer_prop)
        part_cat.Append(description_prop)
        part_cat.Append(family_prop)
        part_cat.Append(series_prop)
        part_cat.Append(color_prop)
        part_cat.Append(temperature_prop)
        part_cat.Append(weight_prop)
        part_cat.Append(resource_prop)
        part_cat.Append(material_prop)
        part_cat.Append(shape_prop)
        part_cat.Append(protection_prop)
        part_cat.Append(adhesives_prop)
        part_cat.Append(branch_count_prop)
        part_cat.Append(branches_prop)

        return part_cat
