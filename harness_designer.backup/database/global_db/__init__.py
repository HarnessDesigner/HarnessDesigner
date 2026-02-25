from typing import Iterable as _Iterable, TYPE_CHECKING

import weakref

if TYPE_CHECKING:
    from ... import ui as _ui


class _EntrySingleton(type):
    _instances = {}

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        setattr(cls, '_instances', {})
        cls._instances = {}

    @classmethod
    def __remove_ref(cls, ref):
        for key, value in cls._instances.items():
            if value == ref:
                break
        else:
            return

        del cls._instances[key]

    def __call__(cls, table, db_id: int):
        if db_id in cls._instances:
            ref = cls._instances[db_id]
            instance = ref()
        else:
            instance = None

        if instance is None:
            instance = super().__call__(table, db_id)
            cls._instances[db_id] = weakref.ref(instance, cls.__remove_ref)

        return instance


class EntryBase(metaclass=_EntrySingleton):

    def __init__(self, table: "TableBase", db_id: int):
        self._table = table
        self._db_id = db_id

    @property
    def db_id(self):
        return self._db_id

    def delete(self) -> None:
        self._table.delete(self.db_id)


class TableBase:
    __table_name__: str = None

    def __init__(self, db: "GLBTables"):
        self.db = db
        self._con = db.connector

    def __getitem__(self, item):
        self._con.execute(f'SELECT * FROM {self.__table_name__} WHERE id = {item};')

        for line in self._con.fetchall():
            return line

    def __iter__(self) -> _Iterable[int]:
        self._con.execute(f'SELECT id FROM {self.__table_name__};')

        for line in self._con.fetchall():
            yield line[0]

    @property
    def table_name(self) -> str:
        return self.__table_name__

    def __contains__(self, db_id: int) -> bool:
        self._con.execute(f'SELECT id FROM {self.__table_name__} WHERE id = {db_id};')

        if self._con.fetchall():
            return True

        return False

    def insert(self, *_, **kwargs) -> int:
        fields = []
        values = []
        args = []

        for key, value in kwargs.items():
            fields.append(key)
            args.append(value)
            values.append('?')

        fields = ', '.join(fields)
        values = ', '.join(values)
        self._con.execute(f'INSERT INTO {self.__table_name__} ({fields}) VALUES ({values});', args)
        self._con.commit()
        return self._con.lastrowid

    def select(self, *args, **kwargs):
        args = ', '.join(args)

        if kwargs:
            values = []
            for key, value in kwargs.items():
                if isinstance(value, (str, float)):
                    value = f'"{value}"'
                elif value is None:
                    value = 'NULL'

                values.append(f'{key} = {value}')

            values = ' AND '.join(values)

            where = f' WHERE {values}'
        else:
            where = ''

        self._con.execute(f'SELECT {args} FROM {self.__table_name__}{where};')
        res = self._con.fetchall()
        return res

    def delete(self, db_id: int) -> None:
        self._con.execute(f'DELETE FROM {self.__table_name__} WHERE id = {db_id};')
        self._con.commit()

    def update(self, db_id: int, **kwargs):
        fields = []
        values = []

        for key, value in kwargs.items():
            fields.append(f'{key} = ?')
            values.append(value)

        fields = ', '.join(fields)
        self._con.execute(f'UPDATE {self.__table_name__} SET {fields} WHERE id = {db_id};', values)
        self._con.commit()

    def execute(self, cmd, params=None):
        if params is None:
            return self._con.execute(cmd)
        else:
            return self._con.execute(cmd, params)

    def fetchall(self):
        return self._con.fetchall()

    def fetchone(self):
        return self._con.fetchone()

    @property
    def search_items(self) -> dict:
        raise NotImplementedError

    def get_unique(self, field_name, table_name=None, get_field_name='name'):
        if table_name is None:
            self.execute(f'SELECT DISTINCT {field_name} FROM {self.__table_name__} ORDER BY {field_name};')
            res = self._con.fetchall()
        else:
            cmd = (f'SELECT DISTINCT tbl2.id, tbl2.{get_field_name} '
                   f'FROM {self.__table_name__} tbl1 JOIN {table_name} tbl2 '
                   f'ON tbl1.{field_name}=tbl2.id ORDER BY tbl2.{get_field_name};')

            self.execute(cmd)
            res = self.fetchall()

        if not res:
            res = []

        return res

    def search(self, search_items: dict, **kwargs):
        """
        Search table.

        Thi function is a bit tricky. The search_items parameter is the dict
        returned by the search_items method for a table. The format of the
        dictionary is as follows.

        The key is an integer that is the index for the column to display the results
        the value is a dict that has the following keys/values

        * 'label': Label for the results column. example: `'label': 'Column Label'`
        * 'type': Type of data that is to be returned. There are 2 ways this can be done

          * `'type': [data_type]`: where `data_type` can be `int`, `float`, `str`
          * `'type': [int, data_type]`: where `data_type` can be `int`, `float`, `str`.
                                        This one is for use when querying a referenced
                                        table and the id for the record is needed to collect
                                        the value in that table.

        * 'out_params': This is an optional entry and is only used to pull data
                        for the results and not used for searchs.
                        example: `'out_params': field_name` where `field_name` is
                        the name of the field to collect the data from.
        * 'search_params': This is another optional entry. Either this entry or `'out_params'`
                           MUST be present. This entry is searchable and it can be formatted
                           in one of 2 ways.

          * `'search_params': [field_name]`: if the data you are searching for is
                                             located in the queried table.
          * `'search_params': [field_name, referenced_table, field_name_in_table]`: If the data is in a referenced table.

        The kwargs parameter gets passed to it the things that have been selected
        to search for. It will consist of the first item in 'search_params' and the
        value that is passed for it will be a list of the values selected for that
        field. If the 'search_params' entry only has the single field name and no
        table information then the results of the search is only going to be values
        for that column. If there is table information then the returned data for
        that column is going to be the id for the record in the referenced table
        and the value collected from that tableusing the field name in that table
        which is the 3rd item in the 'search_params' entry.
        """
        select_args = ['tbl1.id']
        tables = []

        for key in sorted(list(search_items.keys())):
            value = search_items[key]

            if 'out_params' in value:
                select_args.append(f'tbl1.{value["out_params"]}')
            else:
                param = value["search_params"]
                if len(param == 1):
                    select_args.append(f'tbl1.{param[0]}')
                else:
                    table = f'tbl{len(tables) + 2}'
                    tables.append(f'JOIN {param[1]} {table} ON tbl1.{param[0]}={table}.id')
                    select_args.append(f'{table}.{param[2]}')

        select_args = ', '.join(select_args)
        tables = ' '.join(tables)
        if tables:
            tables = ' JOIN ' + tables

        query = [
            f'SELECT {select_args} FROM {self.__table_name__} tbl1 {tables}'
        ]

        args = []

        for key, value in kwargs.items():
            items = ' OR '.join(f'{key}="{item}"' if isinstance(item, float)
                                else f'{key}={repr(item)}'
                                for item in value)

            args.append(f'({items})')

        args = ' AND '.join(args)
        if args:
            query.extend(['WHERE', args])

        query = ' '.join(query)

        cmd = 'WITH results AS ({query}) SELECT (SELECT COUNT(*) FROM results) AS count, * FROM results;'

        self.execute(cmd)
        count = self.fetchone()

        count = count[0][0] if count else 0
        return self, count


from .accessory import AccessoriesTable  # NOQA
from .boot import BootsTable  # NOQA
from .wire import WiresTable  # NOQA
from .cover import CoversTable  # NOQA
from .seal import SealsTable  # NOQA
from .manufacturer import ManufacturersTable  # NOQA
from .tpa_lock import TPALocksTable  # NOQA
from .cpa_lock import CPALocksTable  # NOQA
from .plating import PlatingsTable  # NOQA
from .material import MaterialsTable  # NOQA
from .direction import DirectionsTable  # NOQA
from .terminal import TerminalsTable  # NOQA
from .series import SeriesTable  # NOQA
from .housing import HousingsTable  # NOQA
from .color import ColorsTable  # NOQA
from .sealing import SealingsTable  # NOQA
from .temperature import TemperaturesTable  # NOQA
from .resource import ResourcesTable  # NOQA
from .cavity import CavitiesTable  # NOQA
from .cavity_lock import CavityLocksTable  # NOQA
from .family import FamiliesTable  # NOQA
from .gender import GendersTable  # NOQA
from .ip import IPRatingsTable  # NOQA
from .ip.fluid import IPFluidsTable  # NOQA
from .ip.solid import IPSolidsTable  # NOQA
from .ip.supp import IPSuppsTable  # NOQA
from .bundle_cover import BundleCoversTable  # NOQA
from .shape import ShapesTable  # NOQA
from .transition_branch import TransitionBranchesTable  # NOQA
from .adhesive import AdhesivesTable  # NOQA
from .protection import ProtectionsTable  # NOQA
from .transition import TransitionsTable  # NOQA
from .splice import SplicesTable  # NOQA
from .model3d import Models3DTable  # NOQA
from .wire_marker import WireMarkersTable  # NOQA
from .splice_types import SpliceTypesTable  # NOQA
from .cavity_point2d import CavityPoints2DTable  # NOQA
from .cavity_point3d import CavityPoints3DTable  # NOQA
from .setting import SettingsTable # NOQA


class GLBTables:

    def __init__(self, splash, mainframe: "_ui.MainFrame"):
        self.mainframe = mainframe

        self.connector = mainframe.db_connector

        from ..setup_db import create_tables

        tables = self.connector.get_tables()

        for table_name, func in create_tables.global_table_mapping():
            if table_name not in tables:
                splash.SetText(f'Creating database table {table_name}...')
                func(self.connector, self.connector)

        from ..setup_db import load_database

        load_database.splash = splash

        funcs = [
            load_database.tpa_locks,
            load_database.cpa_locks,
            load_database.boots,
            load_database.terminals,
            load_database.covers,
            load_database.seals,
            load_database.transitions,
            load_database.bundle_covers,
            load_database.housings,
            load_database.splices,
            load_database.wire_markers,
            load_database.wires,
            load_database.settings
        ]

        for func in funcs:
            try:
                func(self.connector, self.connector)
            except FileNotFoundError:
                continue
            except:
                print(func)
                raise

        splash.SetText(f'Loading boots database table...')
        self._boots_table = BootsTable(self)
        splash.SetText(f'Loading manufacturers database table...')
        self._manufacturers_table = ManufacturersTable(self)
        splash.SetText(f'Loading TPA locks database table...')
        self._tpa_locks_table = TPALocksTable(self)
        splash.SetText(f'Loading CPA locks database table...')
        self._cpa_locks_table = CPALocksTable(self)
        splash.SetText(f'Loading materials database table...')
        self._materials_table = MaterialsTable(self)
        splash.SetText(f'Loading platings database table...')
        self._platings_table = PlatingsTable(self)
        splash.SetText(f'Loading covers database table...')
        self._covers_table = CoversTable(self)
        splash.SetText(f'Loading housings database table...')
        self._housings_table = HousingsTable(self)
        splash.SetText(f'Loading seals database table...')
        self._seals_table = SealsTable(self)
        splash.SetText(f'Loading series database table...')
        self._series_table = SeriesTable(self)
        splash.SetText(f'Loading terminals database table...')
        self._terminals_table = TerminalsTable(self)
        splash.SetText(f'Loading wires database table...')
        self._wires_table = WiresTable(self)
        splash.SetText(f'Loading cavity locks database table...')
        self._cavity_locks_table = CavityLocksTable(self)
        splash.SetText(f'Loading colors database table...')
        self._colors_table = ColorsTable(self)
        splash.SetText(f'Loading directions database table...')
        self._directions_table = DirectionsTable(self)
        splash.SetText(f'Loading resources database table...')
        self._resources_table = ResourcesTable(self)
        splash.SetText(f'Loading families database table...')
        self._families_table = FamiliesTable(self)
        splash.SetText(f'Loading genders database table...')
        self._genders_table = GendersTable(self)
        splash.SetText(f'Loading temperatures database table...')
        self._temperatures_table = TemperaturesTable(self)
        splash.SetText(f'Loading IP solids database table...')
        self._ip_solids_table = IPSolidsTable(self)
        splash.SetText(f'Loading IP fluids database table...')
        self._ip_fluids_table = IPFluidsTable(self)
        splash.SetText(f'Loading IP supps database table...')
        self._ip_supps_table = IPSuppsTable(self)
        splash.SetText(f'Loading IP ratings database table...')
        self._ip_ratings_table = IPRatingsTable(self)
        splash.SetText(f'Loading housing cavities database table...')
        self._cavities_table = CavitiesTable(self)
        splash.SetText(f'Loading protections database table...')
        self._protections_table = ProtectionsTable(self)
        splash.SetText(f'Loading bundle covers database table...')
        self._bundle_covers_table = BundleCoversTable(self)
        splash.SetText(f'Loading transition branches database table...')
        self._transition_branches_table = TransitionBranchesTable(self)
        splash.SetText(f'Loading adhesives database table...')
        self._adhesives_table = AdhesivesTable(self)
        splash.SetText(f'Loading shapes database table...')
        self._shapes_table = ShapesTable(self)
        splash.SetText(f'Loading transitions database table...')
        self._transitions_table = TransitionsTable(self)
        splash.SetText(f'Loading accessories database table...')
        self._accessories_table = AccessoriesTable(self)
        splash.SetText(f'Loading splices database table...')
        self._splices_table = SplicesTable(self)
        splash.SetText(f'Loading 3d models database table...')
        self._models3d_table = Models3DTable(self)
        splash.SetText(f'Loading wire markers database table...')
        self._wire_markers_table = WireMarkersTable(self)
        splash.SetText(f'Loading splice types database table...')
        self._splice_types_table = SpliceTypesTable(self)
        splash.SetText(f'Loading cavity points 2d database table...')
        self._cavity_points2d_table = CavityPoints2DTable(self)
        splash.SetText(f'Loading cavity points 3d database table...')
        self._cavity_points3d_table = CavityPoints3DTable(self)

        self._settings_table = SettingsTable(self)

    @property
    def accessories_table(self) -> AccessoriesTable:
        return self._accessories_table

    @property
    def boots_table(self) -> BootsTable:
        return self._boots_table

    @property
    def manufacturers_table(self) -> ManufacturersTable:
        return self._manufacturers_table

    @property
    def tpa_locks_table(self) -> TPALocksTable:
        return self._tpa_locks_table

    @property
    def cpa_locks_table(self) -> CPALocksTable:
        return self._cpa_locks_table

    @property
    def platings_table(self) -> PlatingsTable:
        return self._platings_table

    @property
    def materials_table(self) -> MaterialsTable:
        return self._materials_table

    @property
    def covers_table(self) -> CoversTable:
        return self._covers_table

    @property
    def housings_table(self) -> HousingsTable:
        return self._housings_table

    @property
    def seals_table(self) -> SealsTable:
        return self._seals_table

    @property
    def series_table(self) -> SeriesTable:
        return self._series_table

    @property
    def terminals_table(self) -> TerminalsTable:
        return self._terminals_table

    @property
    def wires_table(self) -> WiresTable:
        return self._wires_table

    @property
    def cavity_locks_table(self) -> CavityLocksTable:
        return self._cavity_locks_table

    @property
    def colors_table(self) -> ColorsTable:
        return self._colors_table

    @property
    def directions_table(self) -> DirectionsTable:
        return self._directions_table

    @property
    def resources_table(self) -> ResourcesTable:
        return self._resources_table

    @property
    def families_table(self) -> FamiliesTable:
        return self._families_table

    @property
    def genders_table(self) -> GendersTable:
        return self._genders_table

    @property
    def temperatures_table(self) -> TemperaturesTable:
        return self._temperatures_table

    @property
    def ip_solids_table(self) -> IPSolidsTable:
        return self._ip_solids_table

    @property
    def ip_fluids_table(self) -> IPFluidsTable:
        return self._ip_fluids_table

    @property
    def ip_supps_table(self) -> IPSuppsTable:
        return self._ip_supps_table

    @property
    def ip_ratings_table(self) -> IPRatingsTable:
        return self._ip_ratings_table

    @property
    def cavities_table(self) -> CavitiesTable:
        return self._cavities_table

    @property
    def bundle_covers_table(self) -> BundleCoversTable:
        return self._bundle_covers_table

    @property
    def transition_branches_table(self) -> TransitionBranchesTable:
        return self._transition_branches_table

    @property
    def adhesives_table(self) -> AdhesivesTable:
        return self._adhesives_table

    @property
    def protections_table(self) -> ProtectionsTable:
        return self._protections_table

    @property
    def shapes_table(self) -> ShapesTable:
        return self._shapes_table

    @property
    def transitions_table(self) -> TransitionsTable:
        return self._transitions_table

    @property
    def splices_table(self) -> SplicesTable:
        return self._splices_table

    @property
    def models3d_table(self) -> Models3DTable:
        return self._models3d_table

    @property
    def wire_markers_table(self) -> WireMarkersTable:
        return self._wire_markers_table

    @property
    def splice_types_table(self) -> SpliceTypesTable:
        return self._splice_types_table

    @property
    def cavity_points2d_table(self) -> CavityPoints2DTable:
        return self._cavity_points2d_table

    @property
    def cavity_points3d_table(self) -> CavityPoints3DTable:
        return self._cavity_points3d_table

    @property
    def settings_table(self) -> SettingsTable:
        return self._settings_table