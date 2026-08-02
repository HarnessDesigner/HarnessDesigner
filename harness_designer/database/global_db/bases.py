# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable, TYPE_CHECKING, IO

import weakref
import json
import uuid

from ... import logger as _logger
from ..common_db import callback as _callback
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import splash as _splash


@_check_types.do
def _as_db_value(value):
    """Convert a ``uuid.UUID`` to raw bytes for binding; pass everything else through.

    :param value: The value being bound as a query parameter.

    :returns: ``value.bytes`` if ``value`` is a ``uuid.UUID``, otherwise ``value`` unchanged.
    """
    if isinstance(value, uuid.UUID):
        return value.bytes
    return value


# These next 2 classes are for cached values.
# declare the value as an instance variable using the following syntax
# _stored_value: DefaultStoredValueType | float = DefaultStoredValue
#
# Then to do a test to see what the cached value is set to...
# if self._stored_value is DefaultStoredValue:
#     ...
#
class DefaultStoredValueType(type):
    pass


class DefaultStoredValue(metaclass=DefaultStoredValueType):
    pass


class _EntrySingleton(type):
    """Represent an entry singleton in :mod:`harness_designer.database.global_db.bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _instances = {}

    @_check_types.do
    def __init__(cls, name, bases, dct):
        """Initialise the :class:`_EntrySingleton` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: UNKNOWN
        :param bases: Value for ``bases``.
        :type bases: UNKNOWN
        :param dct: Value for ``dct``.
        :type dct: UNKNOWN
        """
        super().__init__(name, bases, dct)
        setattr(cls, '_instances', {})
        cls._instances = {}

    @classmethod
    @_check_types.do
    def __remove_ref(cls, ref):
        """Remove the ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param ref: Value for ``ref``.
        :type ref: UNKNOWN
        """
        for key, value in cls._instances.items():
            if value == ref:
                break
        else:
            return

        del cls._instances[key]

    @_check_types.do
    def __call__(cls, table, db_id: int):
        """Call the instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param table: Value for ``table``.
        :type table: UNKNOWN
        :param db_id: Identifier for the database.
        :type db_id: int
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
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
    """Represent an entry base in :mod:`harness_designer.database.global_db.bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, table: "TableBase", db_id: int):
        """Initialise the :class:`EntryBase` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param table: Value for ``table``.
        :type table: :class:`TableBase`
        :param db_id: Identifier for the database.
        :type db_id: int
        """
        self._table = table
        self._db_id = db_id
        self._objects = []
        _callback.CallbackMixin.__init__(self)

    @_check_types.do
    def update_objects(self):
        """Update the objects.

        UNKNOWN details are inferred from the callable name and signature.
        """
        for ref in self._objects:
            obj = ref()
            if obj is None:
                continue

            obj.reload_from_db()

    @_check_types.do
    def __remove_ref(self, ref):
        """Remove the ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param ref: Value for ``ref``.
        :type ref: UNKNOWN
        """
        try:
            self._objects.remove(ref)
        except ValueError:
            pass

    @_check_types.do
    def add_object(self, obj):
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._objects.append(weakref.ref(obj, self.__remove_ref))

    @property
    @_check_types.do
    def db_id(self):
        """Return the database ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._db_id

    @_check_types.do
    def delete(self) -> None:
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._table.delete(self.db_id)


class TableBase:
    """Represent a table base in :mod:`harness_designer.database.global_db.bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__: str = None

    # True for every migrated global_db table (client-generated UUID row
    # ids). False only for AppUsersTable, which keeps a plain AUTO_INCREMENT
    # id -- see the migration plan for why.
    __uses_uuid_id__: bool = True

    @_check_types.do
    def __init__(self, db: "GLBTables", table_names: list[str], splash: "_splash.Splash", load_database: bool):
        """Initialise the :class:`TableBase` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param db: Database accessor or connection.
        :type db: :class:`GLBTables`
        :param table_names: Value for ``table_names``.
        :type table_names: list['str']
        :param splash: Value for ``splash``.
        :type splash: :class:`_splash.Splash`
        :param load_database: Value for ``load_database``.
        :type load_database: bool
        """
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
    @_check_types.do
    def field_names(self):
        """Return the field names.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if self.__field_names__ is None:
            field_names = list(self._con.get_table_column_names(self.__table_name__))
            if 'id' in field_names:
                field_names.remove('id')

            field_names = sorted(field_names)
            field_names.insert(0, 'id')

            self.__field_names__ = field_names

        return self.__field_names__

    @_check_types.do
    def get_record(self, db_id):
        """Return the record.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        self.execute(f'SELECT {", ".join(self.field_names)} FROM {self.__table_name__} WHERE id=?;',
                    (_as_db_value(db_id),))
        rows = self.fetchall()

        if rows:
            rows = list(rows)
        else:
            rows = []

        rows.insert(0, tuple(self.field_names))
        return rows

    @_check_types.do
    def _load_database(self, splash):
        """Load the database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        pass

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    @_check_types.do
    def _add_table_to_db(self, splash) -> None:
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    @_check_types.do
    def __getitem__(self, item):
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        self._con.execute(f'SELECT * FROM {self.__table_name__} WHERE id = ?;', (_as_db_value(item),))

        for line in self._con.fetchall():
            return line

    @_check_types.do
    def __iter__(self) -> _Iterable[int]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable[int]
        """
        self._con.execute(f'SELECT id FROM {self.__table_name__};')

        for line in self._con.fetchall():
            yield line[0]

    @property
    @_check_types.do
    def table_name(self) -> str:
        """Return the table name.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self.__table_name__

    @_check_types.do
    def __contains__(self, db_id: int | bytes | uuid.UUID) -> bool:
        """Return whether the requested item is present.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: int | bytes | uuid.UUID
        :returns: ``True`` when the condition is satisfied.
        :rtype: bool
        """
        self._con.execute(f'SELECT id FROM {self.__table_name__} WHERE id = ?;', (_as_db_value(db_id),))

        if self._con.fetchall():
            return True

        return False

    @_check_types.do
    def insert(self, **kwargs) -> int | uuid.UUID:
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        :returns: The new row's id -- a ``uuid.UUID`` for every migrated
            table, or a plain ``int`` for ``AppUsersTable`` (still
            AUTO_INCREMENT).
        :rtype: int | uuid.UUID
        """
        fields = []
        values = []
        args = []
        new_id = None

        if self.__uses_uuid_id__:
            new_id = _id_generator.generate_global_row_id(self._con)
            fields.append('id')
            values.append('?')
            args.append(new_id.bytes)

        for key, value in kwargs.items():
            fields.append(key)
            args.append(_as_db_value(value))
            values.append('?')

        fields = ', '.join(fields)
        values = ', '.join(values)
        self._con.execute(f'INSERT INTO {self.__table_name__} ({fields}) VALUES ({values});', args)
        self._con.commit()

        if self.__uses_uuid_id__:
            return new_id

        return self._con.lastrowid

    @_check_types.do
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

        is_file_object = False  # Cython C int; declare before first exception point to silence clang -Wuninitialized
        self.execute(f'SELECT "(\'" || group_concat(name, "\', \'") || "\')" from '
                     f'pragma_table_info("{self.__table_name__}");')

        column_names = eval(self.fetchall()[0][0])

        self.execute(f'SELECT {", ".join(column_names)} FROM {self.__table_name__};')

        if isinstance(file, str):
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

    @_check_types.do
    def select(self, *args, **kwargs):
        """Execute the select operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param args: Additional positional arguments.
        :type args: UNKNOWN
        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        args = ', '.join(args)

        if kwargs:
            clauses = []
            params = []
            for key, value in kwargs.items():
                if value is None:
                    clauses.append(f'{key} IS NULL')
                else:
                    clauses.append(f'{key} = ?')
                    params.append(_as_db_value(value))

            where = f' WHERE {" AND ".join(clauses)}'
        else:
            where = ''
            params = []

        self._con.execute(f'SELECT {args} FROM {self.__table_name__}{where};', params)
        res = self._con.fetchall()
        return res

    @_check_types.do
    def delete(self, db_id: int | bytes | uuid.UUID) -> None:
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: int | bytes | uuid.UUID
        """
        self._con.execute(f'DELETE FROM {self.__table_name__} WHERE id = ?;', (_as_db_value(db_id),))
        self._con.commit()

    @_check_types.do
    def update(self, db_id: int | bytes | uuid.UUID, **kwargs):
        """Execute the update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: int | bytes | uuid.UUID
        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        """
        fields = []
        values = []

        for key, value in kwargs.items():
            fields.append(f'{key} = ?')
            values.append(_as_db_value(value))

        fields = ', '.join(fields)
        values.append(_as_db_value(db_id))
        self._con.execute(f'UPDATE {self.__table_name__} SET {fields} WHERE id = ?;', values)
        self._con.commit()

    @_check_types.do
    def execute(self, cmd, params=None):
        """Execute the execute operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param cmd: Value for ``cmd``.
        :type cmd: UNKNOWN
        :param params: Value for ``params``.
        :type params: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if params is None:
            return self._con.execute(cmd)
        else:
            return self._con.execute(cmd, params)

    @_check_types.do
    def commit(self):
        """Execute the commit operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._con.commit()

    @property
    @_check_types.do
    def lastrowid(self):
        """Return the lastrowid.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._con.lastrowid

    @_check_types.do
    def fetchall(self):
        """Execute the fetchall operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._con.fetchall()

    @_check_types.do
    def fetchone(self):
        """Execute the fetchone operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._con.fetchone()

    @property
    @_check_types.do
    def search_items(self) -> dict:
        """Return the search items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: dict
        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    @_check_types.do
    def get_unique(self, field_name, table_name=None, get_field_name='name'):
        """Return the unique.

        UNKNOWN details are inferred from the callable name and signature.

        :param field_name: Value for ``field_name``.
        :type field_name: UNKNOWN
        :param table_name: Value for ``table_name``.
        :type table_name: UNKNOWN
        :param get_field_name: Value for ``get_field_name``.
        :type get_field_name: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
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

    @_check_types.do
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

        _logger.database('search_items:', search_items)
        _logger.database('compat_parts:', compat_parts)
        _logger.database('kwargs:', kwargs)

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
from .resource_state import ResourceStateTable  # NOQA
from .used_part import UsedPartsTable  # NOQA
from .app_users import AppUsersTable  # NOQA


class GLBTables:
    """Represent a glb tables in :mod:`harness_designer.database.global_db.bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, splash, mainframe: "_ui.MainFrame"):
        """Initialise the :class:`GLBTables` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """
        self.mainframe = mainframe

        self.connector = mainframe.db_connector

        tables = self.connector.get_tables()

        load_database = splash.load_database
        self._settings_table = SettingsTable(self, tables, splash, load_database)
        self._file_types_table = FileTypesTable(self, tables, splash, load_database)
        self._resource_state_table = ResourceStateTable(self, tables, splash, load_database)
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
        self._used_parts_table = UsedPartsTable(self, tables, splash, load_database)
        self._wires_table = WiresTable(self, tables, splash, load_database)
        self._wire_markers_table = WireMarkersTable(self, tables, splash, load_database)
        self._app_users_table = AppUsersTable(self, tables, splash, load_database)

        self.connector.db_data = None

    @property
    @_check_types.do
    def cpa_lock_types_table(self) -> CPALockTypesTable:
        """Return the CPA lock types table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`CPALockTypesTable`
        """
        return self._cpa_lock_types_table

    @property
    @_check_types.do
    def resource_state_table(self) -> ResourceStateTable:
        """Return the resource state coordination table.

        :returns: The shared resource state table.
        :rtype: :class:`ResourceStateTable`
        """
        return self._resource_state_table

    @property
    @_check_types.do
    def images_table(self) -> ImagesTable:
        """Return the images table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`ImagesTable`
        """
        return self._images_table

    @property
    @_check_types.do
    def datasheets_table(self) -> DatasheetsTable:
        """Return the datasheets table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`DatasheetsTable`
        """
        return self._datasheets_table

    @property
    @_check_types.do
    def cads_table(self) -> CADsTable:
        """Return the cads table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`CADsTable`
        """
        return self._cads_table

    @property
    @_check_types.do
    def file_types_table(self) -> FileTypesTable:
        """Return the file types table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`FileTypesTable`
        """
        return self._file_types_table

    @property
    @_check_types.do
    def accessories_table(self) -> AccessoriesTable:
        """Return the accessories table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`AccessoriesTable`
        """
        return self._accessories_table

    @property
    @_check_types.do
    def boots_table(self) -> BootsTable:
        """Return the boots table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`BootsTable`
        """
        return self._boots_table

    @property
    @_check_types.do
    def app_users_table(self) -> AppUsersTable:
        """Return the app_users table.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`AppUsersTable`
        """
        return self._app_users_table

    @property
    @_check_types.do
    def manufacturers_table(self) -> ManufacturersTable:
        """Return the manufacturers table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`ManufacturersTable`
        """
        return self._manufacturers_table

    @property
    @_check_types.do
    def tpa_locks_table(self) -> TPALocksTable:
        """Return the TPA locks table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`TPALocksTable`
        """
        return self._tpa_locks_table

    @property
    @_check_types.do
    def cpa_locks_table(self) -> CPALocksTable:
        """Return the CPA locks table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`CPALocksTable`
        """
        return self._cpa_locks_table

    @property
    @_check_types.do
    def platings_table(self) -> PlatingsTable:
        """Return the platings table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PlatingsTable`
        """
        return self._platings_table

    @property
    @_check_types.do
    def materials_table(self) -> MaterialsTable:
        """Return the materials table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`MaterialsTable`
        """
        return self._materials_table

    @property
    @_check_types.do
    def covers_table(self) -> CoversTable:
        """Return the covers table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`CoversTable`
        """
        return self._covers_table

    @property
    @_check_types.do
    def housings_table(self) -> HousingsTable:
        """Return the housings table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`HousingsTable`
        """
        return self._housings_table

    @property
    @_check_types.do
    def seal_types_table(self) -> SealTypesTable:
        """Return the seal types table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`SealTypesTable`
        """
        return self._seal_types_table

    @property
    @_check_types.do
    def seals_table(self) -> SealsTable:
        """Return the seals table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`SealsTable`
        """
        return self._seals_table

    @property
    @_check_types.do
    def series_table(self) -> SeriesTable:
        """Return the series table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`SeriesTable`
        """
        return self._series_table

    @property
    @_check_types.do
    def terminals_table(self) -> TerminalsTable:
        """Return the terminals table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`TerminalsTable`
        """
        return self._terminals_table

    @property
    @_check_types.do
    def wires_table(self) -> WiresTable:
        """Return the wires table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`WiresTable`
        """
        return self._wires_table

    @property
    @_check_types.do
    def cavity_locks_table(self) -> CavityLocksTable:
        """Return the cavity locks table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`CavityLocksTable`
        """
        return self._cavity_locks_table

    @property
    @_check_types.do
    def colors_table(self) -> ColorsTable:
        """Return the colors table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`ColorsTable`
        """
        return self._colors_table

    @property
    @_check_types.do
    def directions_table(self) -> DirectionsTable:
        """Return the directions table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`DirectionsTable`
        """
        return self._directions_table

    @property
    @_check_types.do
    def families_table(self) -> FamiliesTable:
        """Return the families table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`FamiliesTable`
        """
        return self._families_table

    @property
    @_check_types.do
    def genders_table(self) -> GendersTable:
        """Return the genders table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`GendersTable`
        """
        return self._genders_table

    @property
    @_check_types.do
    def temperatures_table(self) -> TemperaturesTable:
        """Return the temperatures table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`TemperaturesTable`
        """
        return self._temperatures_table

    @property
    @_check_types.do
    def ip_solids_table(self) -> IPSolidsTable:
        """Return the ip solids table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`IPSolidsTable`
        """
        return self._ip_solids_table

    @property
    @_check_types.do
    def ip_fluids_table(self) -> IPFluidsTable:
        """Return the ip fluids table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`IPFluidsTable`
        """
        return self._ip_fluids_table

    @property
    @_check_types.do
    def ip_supps_table(self) -> IPSuppsTable:
        """Return the ip supps table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`IPSuppsTable`
        """
        return self._ip_supps_table

    @property
    @_check_types.do
    def ip_ratings_table(self) -> IPRatingsTable:
        """Return the ip ratings table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`IPRatingsTable`
        """
        return self._ip_ratings_table

    @property
    @_check_types.do
    def cavities_table(self) -> CavitiesTable:
        """Return the cavities table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`CavitiesTable`
        """
        return self._cavities_table

    @property
    @_check_types.do
    def bundle_covers_table(self) -> BundleCoversTable:
        """Return the bundle covers table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`BundleCoversTable`
        """
        return self._bundle_covers_table

    @property
    @_check_types.do
    def transition_branches_table(self) -> TransitionBranchesTable:
        """Return the transition branches table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`TransitionBranchesTable`
        """
        return self._transition_branches_table

    @property
    @_check_types.do
    def adhesives_table(self) -> AdhesivesTable:
        """Return the adhesives table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`AdhesivesTable`
        """
        return self._adhesives_table

    @property
    @_check_types.do
    def protections_table(self) -> ProtectionsTable:
        """Return the protections table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`ProtectionsTable`
        """
        return self._protections_table

    @property
    @_check_types.do
    def shapes_table(self) -> ShapesTable:
        """Return the shapes table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`ShapesTable`
        """
        return self._shapes_table

    @property
    @_check_types.do
    def transitions_table(self) -> TransitionsTable:
        """Return the transitions table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`TransitionsTable`
        """
        return self._transitions_table

    @property
    @_check_types.do
    def splices_table(self) -> SplicesTable:
        """Return the splices table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`SplicesTable`
        """
        return self._splices_table

    @property
    @_check_types.do
    def models3d_table(self) -> Models3DTable:
        """Return the models 3D table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`Models3DTable`
        """
        return self._models3d_table

    @property
    @_check_types.do
    def wire_markers_table(self) -> WireMarkersTable:
        """Return the wire markers table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`WireMarkersTable`
        """
        return self._wire_markers_table

    @property
    @_check_types.do
    def splice_types_table(self) -> SpliceTypesTable:
        """Return the splice types table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`SpliceTypesTable`
        """
        return self._splice_types_table

    @property
    @_check_types.do
    def settings_table(self) -> SettingsTable:
        """Return the settings table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`SettingsTable`
        """
        return self._settings_table

    @property
    @_check_types.do
    def used_parts_table(self) -> UsedPartsTable:
        """Return the used parts table.

        Tracks accessory parts (TPA lock, CPA lock, cover, terminal) that
        have previously been used together with a given housing.

        :returns: Property value.
        :rtype: :class:`UsedPartsTable`
        """
        return self._used_parts_table
