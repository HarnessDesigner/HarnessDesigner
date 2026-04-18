from typing import Iterable as _Iterable, TYPE_CHECKING, IO

import weakref
import json

from ... import logger as _logger
from ..common_db import callback as _callback


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import splash as _splash


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


class EntryBase(_callback.CallbackMixin, metaclass=_EntrySingleton):

    def __init__(self, table: "TableBase", db_id: int):
        self._table = table
        self._db_id = db_id
        self._objects = []
        _callback.CallbackMixin.__init__(self)

    def update_objects(self):
        for ref in self._objects:
            obj = ref()
            if obj is None:
                continue

            obj.reload_from_db()

    def __remove_ref(self, ref):
        try:
            self._objects.remove(ref)
        except ValueError:
            pass

    def add_object(self, obj):
        self._objects.append(weakref.ref(obj, self.__remove_ref))

    @property
    def db_id(self):
        return self._db_id

    def delete(self) -> None:
        self._table.delete(self.db_id)

    @staticmethod
    def merge_packet_data(src: dict, dst: dict):
        for key, values in src.items():
            if key in dst:
                values = [value for value in values if value not in dst[key]]
                dst[key].extend(values)
            else:
                dst[key] = values[:]


class TableBase:
    __table_name__: str = None

    def __init__(self, db: "GLBTables", table_names: list['str'], splash: "_splash.Splash", load_database: bool):
        self.__field_names__ = None
        self.db = db
        self._con = db.connector

        if self.__table_name__ not in table_names:
            splash.SetText(f'Creating {self.__table_name__.replace("_", " ")} database table...')
            splash.flush()
            self._add_table_to_db(splash)
        elif load_database:
            self._load_database(splash)

        if self._table_needs_update():
            splash.SetText(f'Adding {self.__table_name__.replace("_", " ")} table fields...')
            splash.flush()
            self._update_table_in_db()

        splash.SetText(f'Loading {self.__table_name__.replace("_", " ")} database table...')
        splash.flush()

    @property
    def field_names(self):
        if self.__field_names__ is None:
            field_names = list(self._con.get_table_column_names(self.__table_name__))
            if 'id' in field_names:
                field_names.remove('id')

            field_names = sorted(field_names)
            field_names.insert(0, 'id')

            self.__field_names__ = field_names

        return self.__field_names__

    def get_record(self, db_id):
        self.execute(f'SELECT {", ".join(self.field_names)} FROM {self.__table_name__} WHERE id={db_id};')
        rows = self.fetchall()

        if rows:
            rows = list(rows)
        else:
            rows = []

        rows.insert(0, tuple(self.field_names))
        return rows

    def _load_database(self, splash):
        pass

    def _table_needs_update(self) -> bool:
        raise NotImplementedError

    def _add_table_to_db(self, splash) -> None:
        raise NotImplementedError

    def _update_table_in_db(self) -> None:
        raise NotImplementedError

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

    def insert(self, **kwargs) -> int:
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

    def export_as_json(self, file: str | IO[bytes]) -> int:
        """
        This function dumps to a file or a file like object.

        :param file: The data that is exported can be quite large in size which
                     is why you can optionally provide a file name. If passing
                     a file object the object MUST be opened using `'wb'` as
                     the mode. If passing in an `io.BytesIO` object or a file
                     object the writing occurs at the exact position the object
                     is at when it is passed to this function.

                     If a file object or a `io.BytesIO` object is passed the
                     object will remain open after the function is called. It
                     is the users responsibility to close the object.

        :type file: `str` or `io.BytesIO` or a file object

        :return: number of records written
        :rtype: int
        """

        self.execute(f'SELECT "(\'" || group_concat(name, "\', \'") || "\')" from '
                     f'pragma_table_info("{self.__table_name__}");')

        column_names = eval(self.fetchall()[0][0])

        self.execute(f'SELECT {", ".join(column_names)} FROM {self.__table_name__};')

        if isinstance(file, str):
            is_file_object = False

            file = open(file, 'wb')
        else:
            is_file_object = True

        file.write(b'[')
        row = self.fetchone()
        count = 0
        while row:
            count += 1
            entry = dict(tuple(zip(column_names, row)))
            j_data = json.dumps(entry).strip()
            file.write(b'  ' + j_data.encode('utf-8') + b',\n')

            row = self.fetchone()

        cur_pos = file.tell()
        file.seek(cur_pos - 2)
        file.write(b'\n]')

        if not is_file_object:
            file.close()

        return count

    def load_from_json(self, data: list[dict[str, float | int | str]] | str) -> int:
        if isinstance(data, str):
            data = json.loads(data)

        self.execute(f'SELECT "(\'" || group_concat(name, "\', \'") || "\')" from '
                     f'pragma_table_info("{self.__table_name__}");')

        column_names = sorted(list(eval(self.fetchall()[0][0])))
        values = ['?'] * len(column_names)
        found_column_names = []

        insert_cmd = (f'INSERT INTO {self.__table_name__} ({", ".join(column_names)}) '
                      f'VALUES ({", ".join(values)});')
        count = 0
        for line in data:
            if not found_column_names:
                found_column_names = sorted(list(line.keys()))

                if found_column_names != column_names:
                    raise RuntimeError(
                        'column names in file do not match database table')

            row_data = []
            for key in column_names:
                row_data.append(line[key])

            self._con.execute(insert_cmd, row_data)

            count += 1

        self._con.commit()
        return count

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

    def commit(self):
        self._con.commit()

    @property
    def lastrowid(self):
        return self._con.lastrowid

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

    def search(self, search_items: dict, *compat_parts, **kwargs):
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

        _logger.logger.database('search_items:', search_items)
        _logger.logger.database('compat_parts:', compat_parts)
        _logger.logger.database('kwargs:', kwargs)

        for key in sorted(list(search_items.keys())):
            value = search_items[key]

            if 'out_params' in value:
                select_args.append(f'tbl1.{value["out_params"]}')
            else:
                param = value["search_params"]

                if len(param) == 1:
                    select_args.append(f'tbl1.{param[0]}')
                else:
                    table = f'tbl{len(tables) + 2}'
                    tables.append(f'JOIN {param[1]} {table} ON tbl1.{param[0]}={table}.id')
                    select_args.append(f'{table}.{param[2]}')

        select_args = ', '.join(select_args)
        tables = ' '.join(tables)

        query = [
            f'SELECT {select_args} FROM {self.__table_name__} tbl1 {tables}'
        ]

        args = []

        for key, value in kwargs.items():
            items = ' OR '.join(f'tbl1.{key}="{item}"' if isinstance(item, float)
                                else f'tbl1.{key}={repr(item)}'
                                for item in value)

            args.append(f'({items})')

        cp = []
        for pn in compat_parts:
            cp.append(f'tbl1.part_number="{pn}"')

        if cp:
            cp = ' OR '.join(cp)
            cp = '(' + cp + ')'
            args.append(cp)

        args = ' AND '.join(args)
        if args:
            query.extend(['WHERE', args])

        query = ' '.join(query)

        cmd = f'WITH results AS ({query}) SELECT (SELECT COUNT(*) FROM results) AS count, * FROM results;'

        self.execute(cmd)
        count = self.fetchone()

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
from .seal_type import SealTypesTable  # NOQA
from .temperature import TemperaturesTable  # NOQA
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
from .setting import SettingsTable # NOQA
from .file_types import FileTypesTable  # NOQA
from .cad import CADsTable  # NOQA
from .image import ImagesTable  # NOQA
from .datasheet import DatasheetsTable  # NOQA
from .cpa_lock_type import CPALockTypesTable  # NOQA


class GLBTables:

    def __init__(self, splash, mainframe: "_ui.MainFrame"):
        self.mainframe = mainframe

        self.connector = mainframe.db_connector

        tables = self.connector.get_tables()

        load_database = splash.load_database
        self._settings_table = SettingsTable(self, tables, splash, load_database)
        self._file_types_table = FileTypesTable(self, tables, splash, load_database)
        self._images_table = ImagesTable(self, tables, splash, load_database)
        self._datasheets_table = DatasheetsTable(self, tables, splash, load_database)
        self._cads_table = CADsTable(self, tables, splash, load_database)
        self._models3d_table = Models3DTable(self, tables, splash, load_database)
        self._manufacturers_table = ManufacturersTable(self, tables, splash, load_database)
        self._cpa_lock_types_table = CPALockTypesTable(self, tables, splash, load_database)
        self._colors_table = ColorsTable(self, tables, splash, load_database)
        self._platings_table = PlatingsTable(self, tables, splash, load_database)
        self._seal_types_table = SealTypesTable(self, tables, splash, load_database)
        self._cavity_locks_table = CavityLocksTable(self, tables, splash, load_database)
        self._materials_table = MaterialsTable(self, tables, splash, load_database)
        self._temperatures_table = TemperaturesTable(self, tables, splash, load_database)
        self._shapes_table = ShapesTable(self, tables, splash, load_database)
        self._genders_table = GendersTable(self, tables, splash, load_database)
        self._directions_table = DirectionsTable(self, tables, splash, load_database)
        self._splice_types_table = SpliceTypesTable(self, tables, splash, load_database)
        self._protections_table = ProtectionsTable(self, tables, splash, load_database)
        self._ip_solids_table = IPSolidsTable(self, tables, splash, load_database)
        self._ip_fluids_table = IPFluidsTable(self, tables, splash, load_database)
        self._ip_supps_table = IPSuppsTable(self, tables, splash, load_database)
        self._ip_ratings_table = IPRatingsTable(self, tables, splash, load_database)
        self._families_table = FamiliesTable(self, tables, splash, load_database)
        self._series_table = SeriesTable(self, tables, splash, load_database)
        self._adhesives_table = AdhesivesTable(self, tables, splash, load_database)
        self._cavities_table = CavitiesTable(self, tables, splash, load_database)
        self._transition_branches_table = TransitionBranchesTable(self, tables, splash, load_database)
        self._accessories_table = AccessoriesTable(self, tables, splash, load_database)
        self._boots_table = BootsTable(self, tables, splash, load_database)
        self._bundle_covers_table = BundleCoversTable(self, tables, splash, load_database)
        self._covers_table = CoversTable(self, tables, splash, load_database)
        self._cpa_locks_table = CPALocksTable(self, tables, splash, load_database)
        self._housings_table = HousingsTable(self, tables, splash, load_database)
        self._seals_table = SealsTable(self, tables, splash, load_database)
        self._splices_table = SplicesTable(self, tables, splash, load_database)
        self._terminals_table = TerminalsTable(self, tables, splash, load_database)
        self._tpa_locks_table = TPALocksTable(self, tables, splash, load_database)
        self._transitions_table = TransitionsTable(self, tables, splash, load_database)
        self._wires_table = WiresTable(self, tables, splash, load_database)
        self._wire_markers_table = WireMarkersTable(self, tables, splash, load_database)

        self.connector.db_data = None

    @property
    def cpa_lock_types_table(self) -> CPALockTypesTable:
        return self._cpa_lock_types_table

    @property
    def images_table(self) -> ImagesTable:
        return self._images_table

    @property
    def datasheets_table(self) -> DatasheetsTable:
        return self._datasheets_table

    @property
    def cads_table(self) -> CADsTable:
        return self._cads_table

    @property
    def file_types_table(self) -> FileTypesTable:
        return self._file_types_table

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
    def seal_types_table(self) -> SealTypesTable:
        return self._seal_types_table

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
    def settings_table(self) -> SettingsTable:
        return self._settings_table
