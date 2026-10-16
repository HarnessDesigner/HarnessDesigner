# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Any, Iterable as _Iterable, TYPE_CHECKING, Union as _Union
from collections.abc import Callable, Generator as _Generator

import weakref
import threading
import functools
import pkgutil
import importlib

from ... import logger as _logger
from ..common_db import callback as _callback
from ... import check_types as _check_types
from .. import id_generator as _id_generator
from . import table_data as _table_data
from ...crash_dump import Attr, capturable, dump_property


_dependency_order_cache: list[str] | None = None


def _schema_dependency_order() -> list[str]:
    """Every ``create_database`` module's own SQL table name,
    topologically sorted so a table always comes after every OTHER
    table one of its own columns holds a foreign key into (parent
    before child) -- the real insert-safe order, derived straight from
    each table's own ``SQLField.references`` metadata.

    :meth:`PJTTables._ordered_project_tables`'s own hand-picked list is
    NOT a valid order for this -- confirmed by its own prior comment
    (``PJTTableBase.batch_insert``'s docstring): ``pjt_bundles``
    references ``pjt_points3d`` but is visited before it there. That
    list still exists for :meth:`~PJTTables.load`'s own use (plain
    reads, so ordering doesn't matter for correctness); this is the
    one the gesture flush actually needs for real cross-table inserts.

    Computed once and cached -- the schema is fixed for the process's
    whole lifetime, and building it imports every module under
    ``database.create_database`` (global and project tables alike;
    whichever aren't project tables just never show up in a flush's own
    dirty set, so including them here is harmless).
    """
    global _dependency_order_cache
    if _dependency_order_cache is not None:
        return _dependency_order_cache

    from .. import create_database as _create_database

    schema_tables = {}
    for module_info in pkgutil.iter_modules(_create_database.__path__):
        module = importlib.import_module(
            f'{_create_database.__name__}.{module_info.name}')
        pjt_table = getattr(module, 'pjt_table', None)
        if pjt_table is not None:
            schema_tables[pjt_table.name] = pjt_table

    graph: dict[str, set[str]] = {}
    for name, table in schema_tables.items():
        deps = set()
        for field in table.fields:
            reference = getattr(field, 'references', None)
            if reference is not None and reference.table.name != name:
                deps.add(reference.table.name)
        graph[name] = deps

    ordered: list[str] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def _visit(name: str) -> None:
        if name in visited or name not in graph:
            return
        if name in visiting:
            raise RuntimeError(f'circular foreign-key reference involving {name!r}')
        visiting.add(name)
        for dep in graph[name]:
            _visit(dep)
        visiting.discard(name)
        visited.add(name)
        ordered.append(name)

    for name in graph:
        _visit(name)

    _dependency_order_cache = ordered
    return ordered


if TYPE_CHECKING:
    from PySide6 import QtWidgets
    from ... import ui as _ui
    from ... import splash as _splash
    from ...objects import object_base as _object_base


@_check_types.do
def _project_id_bounds(project_id: int) -> tuple[bytes, bytes]:
    """Return the inclusive ``(low, high)`` id bounds for every row
    belonging to a project.

    There is no real ``project_id`` column. A ``GENERATED ALWAYS AS (...)
    VIRTUAL`` column was tried, but SQLite's schema-diffing (see
    ``TableBase._table_needs_update``) can't tell a virtual column apart
    from a genuinely missing one -- it kept trying to re-add the column on
    every startup and failing against the one already there. project_id
    is only ever embedded in the leading ``PROJECT_ID_BYTES`` of ``id``
    (see database/id_generator.py), so filtering by project means an
    inclusive byte-range scan on ``id`` itself instead: every id with the
    same project_id prefix, followed by anything, falls between the
    prefix padded with all-zero and the prefix padded with all-0xff.

    :param project_id: The project's plain integer id (``projects.id``).

    :returns: ``(low, high)`` -- both 16-byte, both valid ``id`` values to
        bind directly in a ``WHERE id >= ? AND id <= ?`` clause.
    :rtype: tuple[bytes, bytes]
    """

    prefix = project_id.to_bytes(_id_generator.PROJECT_ID_BYTES, byteorder='big')
    padding = b'\x00' * (16 - _id_generator.PROJECT_ID_BYTES)
    return prefix + padding, prefix + (b'\xff' * len(padding))


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


class _PJTEntrySingleton(type):
    """Represent a PJT entry singleton in :mod:`harness_designer.database.project_db.pjt_bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _instances = {}

    @_check_types.do
    def __init__(cls, name: str, bases: tuple[type, ...], dct: dict[str, Any]) -> None:
        """Initialise the :class:`_PJTEntrySingleton` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: UNKNOWN
        :param bases: Value for ``bases``.
        :type bases: UNKNOWN
        :param dct: Value for ``dct``.
        :type dct: UNKNOWN
        """
        super().__init__(name, bases, dct)
        cls._instances = {}
        # See _EntrySingleton (global_db/bases.py) for why this needs a
        # lock: _instances is read/written from __call__ (any thread that
        # looks up or constructs an entry) and mutated from
        # __remove_instance_ref, which runs as a weakref callback on
        # whatever thread happens to drop the last reference -- unrelated
        # to whichever thread is concurrently in __call__. Unsynchronized
        # concurrent mutation was corrupting this dict's internal
        # structure (see the crash investigation).
        cls._instances_lock = threading.RLock()

    @staticmethod
    @_check_types.do
    def __remove_instance_ref(cls, ref: weakref.ref) -> None:
        """Remove the instance ref.

        A plain staticmethod, not a classmethod -- this is defined ON
        the metaclass, and a classmethod accessed via ``cls.method``
        where ``cls`` is itself an instance of this metaclass (i.e. any
        real entry class like PJTHousing) binds to ``type(cls)`` (this
        metaclass) rather than ``cls``, per the classmethod descriptor
        protocol. That silently broke this method for every entry class:
        the weakref callback below always ran with ``cls`` rebound to
        ``_PJTEntrySingleton`` itself, which never got its own
        ``_instances_lock``/``_instances`` (those are only set on real
        entry classes, once each, by ``__init__`` above). A staticmethod
        never auto-binds, so ``functools.partial`` in ``__call__`` below
        is what supplies the correct ``cls`` instead.

        :param cls: The real entry class whose ``_instances`` this
            reference belongs to -- explicitly bound via
            ``functools.partial`` at registration time (see ``__call__``).
        :param ref: Value for ``ref``.
        :type ref: UNKNOWN
        """
        with cls._instances_lock:
            for key, value in cls._instances.items():
                if value == ref:
                    break
            else:
                return

            del cls._instances[key]

    def __contains__(cls, db_id: int | bytes) -> bool:
        return db_id in cls._instances and cls._instances[db_id]() is not None

    @_check_types.do
    def __call__(cls, table: "PJTTableBase", db_id: int | bytes) -> "PJTEntryBase":
        """Call the instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param table: Value for ``table``.
        :type table: UNKNOWN
        :param db_id: Identifier for the database.
        :type db_id: int | bytes
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        # db_id alone is a sufficient cache key: it's globally unique on
        # its own (bytes ids embed project_id/timestamp/user_id; a
        # Project's own int id is unique within ProjectsTable), so there's
        # no need for a separate project_id component the way a
        # pre-migration per-table AUTO_INCREMENT id would have required.
        with cls._instances_lock:
            if db_id in cls._instances:
                ref = cls._instances[db_id]
                instance = ref()
            else:
                instance = None

            if instance is None:
                instance = super().__call__(table, db_id)
                cls._instances[db_id] = weakref.ref(
                    instance, functools.partial(cls.__remove_instance_ref, cls))

            return instance


@capturable(severity=2)
class PJTEntryBase(_callback.CallbackMixin, metaclass=_PJTEntrySingleton):
    """Represent a PJT entry base in :mod:`harness_designer.database.project_db.pjt_bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, table: "PJTTableBase", db_id: int | bytes) -> None:
        """Initialise the :class:`PJTEntryBase` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param table: Value for ``table``.
        :type table: :class:`PJTTableBase`
        :param db_id: Identifier for the database.
        :type db_id: int | bytes
        """
        self._table = table
        self._db_id = db_id

        self._obj = None
        self._objects = []
        self._treeitem = None
        _callback.CallbackMixin.__init__(self)

    @property
    @dump_property(severity=2)
    @_check_types.do
    def project_id(self) -> int:
        """Return the owning project's id.

        For every migrated child table, this is derived from ``db_id``
        itself -- the leading ``PROJECT_ID_BYTES`` bytes of the packed row
        id (see database/id_generator.py).

        ``Project`` rows are the one exception: ``db_id`` there is
        ``ProjectsTable``'s own plain int id, and a project's id *is* its
        own project_id -- there's no separate value to unpack, and no
        other project it could belong to -- so ``db_id`` is returned as-is.

        :returns: The embedded project id.
        :rtype: int
        """
        if isinstance(self._db_id, bytes):
            return _id_generator.unpack_project_id(self._db_id)

        return self._db_id

    @_check_types.do
    def update_objects(self) -> None:
        """Update the objects.

        UNKNOWN details are inferred from the callable name and signature.
        """
        for ref in self._objects:
            obj = ref()
            if obj is None:
                continue

            obj.reload_from_db()

    @_check_types.do
    def __remove_ref(self, ref: weakref.ref) -> None:
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
    def add_object(self, obj: "PJTEntryBase") -> None:
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._objects.append(weakref.ref(obj, self.__remove_ref))

    @_check_types.do
    def get_object(self) -> _Union["_object_base.ObjectBase", None]:
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    @_check_types.do
    def set_object(self, obj: _Union["_object_base.ObjectBase", None]) -> None:
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    _bind_object_callbacks = {}

    def bind_object(self, callback: Callable[..., None]) -> None:
        if self not in self._bind_object_callbacks:
            self._bind_object_callbacks[self] = []

        self._bind_object_callbacks[self].append(weakref.ref(callback))

    def _process_bind_callbacks(self, obj: _Union["_object_base.ObjectBase", None]) -> None:
        if self in self._bind_object_callbacks:
            refs = self._bind_object_callbacks.pop(self)
            for ref in refs:
                cb = ref()
                if cb is None:
                    continue

                cb(obj)

    _selected: bool = False

    @property
    @dump_property(severity=2)
    @_check_types.do
    def selected(self) -> bool:
        """Return the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._selected

    @selected.setter
    @_check_types.do
    def selected(self, flag: bool) -> None:
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self._selected = flag

    @property
    @dump_property(severity=2)
    @_check_types.do
    def db_id(self) -> int | bytes:
        """Return the database ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int | bytes
        """
        return self._db_id

    @property
    @dump_property(severity=1)
    @_check_types.do
    def table(self) -> "PJTTableBase":
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._table

    @_check_types.do
    def delete(self) -> None:
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._table.delete(self.db_id)

        key = self.db_id

        with self.__class__._instances_lock:  # NOQA
            if key in self.__class__._instances:  # NOQA
                del self.__class__._instances[key]  # NOQA


@capturable(severity=1)
class PJTTableBase:
    """Represent a PJT table base in :mod:`harness_designer.database.project_db.pjt_bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __dump_schema__ = (Attr('_cache', severity=1),)

    __table_name__: str = None

    # True for every migrated pjt_* table (client-generated UUID row ids).
    # False only for ProjectsTable, which keeps a plain AUTO_INCREMENT id --
    # see the migration plan for why.
    __uses_uuid_id__: bool = True

    @_check_types.do
    def __init__(self, db: "PJTTables", project_id: int | None, table_names: list[str], splash: "_splash.Splash") -> None:
        """Initialise the :class:`PJTTableBase` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param db: Database accessor or connection.
        :type db: :class:`PJTTables`
        :param project_id: Identifier for the project.
        :type project_id: int | None
        :param table_names: Value for ``table_names``.
        :type table_names: list['str']
        :param splash: Value for ``splash``.
        :type splash: :class:`_splash.Splash`
        """
        self.db = db
        self._con = db.connector
        self.__field_names__ = None
        self._cache: _table_data.TableData | None = None

        if self.__table_name__ not in table_names:
            splash.SetText(f'Creating {self.__table_name__.replace("_", " ")} database table...')

            self._add_table_to_db()

        if self._table_needs_update():
            splash.SetText(f'Adding {self.__table_name__.replace("_", " ")} table fields...')

            self._update_table_in_db()

        splash.SetText(f'Loading {self.__table_name__.replace("_", " ")} database table...')

        self.project_id = project_id

    @_check_types.do
    def _require_cache(self) -> _table_data.TableData:
        """Return the loaded cache, or raise if this table was never loaded.

        :returns: The table's cache.
        :rtype: _table_data.TableData
        """
        if self._cache is None:
            raise RuntimeError(f'{self.__table_name__} cache is not loaded')

        return self._cache

    @_check_types.do
    def load_cache(self) -> None:
        """Load this project's rows into the table cache with one query.

        Only tables whose ids are project-scoped (``__uses_uuid_id__``) are
        cached. The others keep reading the database.
        """
        if not self.__uses_uuid_id__:
            return

        low, high = _project_id_bounds(self.project_id)
        cache = _table_data.TableData(self.__table_name__, self.field_names)
        cache.load(self._con, low, high)
        self._cache = cache

    @property
    @_check_types.do
    def control(self) -> _Union["QtWidgets.QWidget", None]:
        """Return the property editor control for this table's rows.

        Tables whose rows have a property editor override this. Every other
        table (lookup tables, and tables with no editor of their own) returns
        ``None``, so callers can check for it instead of probing with getattr.

        :returns: Property value.
        """
        return None

    @property
    @_check_types.do
    def field_names(self) -> list[str]:
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
    def get_records(self, project_id: bytes) -> list[tuple]:
        """Return the records.

        UNKNOWN details are inferred from the callable name and signature.

        :param project_id: Identifier for the project.
        :type project_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        low, high = _project_id_bounds(project_id)
        self.execute(f'SELECT {", ".join(self.field_names)} FROM {self.__table_name__} WHERE id>=? AND id<=?;',
                     (low, high))

        rows = self.fetchall()
        if rows:
            rows = list(rows)
        else:
            rows = []

        rows.insert(0, tuple(self.field_names))

        return rows

    @_check_types.do
    def set_project(self, project_id: int | None = None) -> None:
        """Set the project.

        UNKNOWN details are inferred from the callable name and signature.

        :param project_id: Identifier for the project.
        :type project_id: int | None
        """
        self.project_id = project_id

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
    def _add_table_to_db(self) -> None:
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

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
    def __getitem__(self, item: int | bytes | str) -> tuple | None:
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if self.__uses_uuid_id__:
            return self._require_cache().row(item)

        self._con.execute(f'SELECT * FROM {self.__table_name__} WHERE id = ?;',
                          (item,))

        for line in self._con.fetchall():
            return line

    @_check_types.do
    def __iter__(self) -> _Iterable[int]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable[int]
        """
        if self.__uses_uuid_id__:
            yield from self._require_cache().row_ids()
            return

        if self.project_id is None:
            self._con.execute(f'SELECT id FROM {self.__table_name__};')
        else:
            low, high = _project_id_bounds(self.project_id)
            self._con.execute(f'SELECT id FROM {self.__table_name__} WHERE id >= ? AND id <= ?;',
                              (low, high))

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
    def __contains__(self, db_id: int | bytes) -> bool:
        """Return whether the requested item is present.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: int | bytes
        :returns: ``True`` when the condition is satisfied.
        :rtype: bool
        """
        if self.__uses_uuid_id__:
            return self._require_cache().contains(db_id)

        self._con.execute(f'SELECT id FROM {self.__table_name__} WHERE id = ?;',
                          (db_id,))

        if self._con.fetchall():
            return True

        return False

    @_check_types.do
    def insert(self, **kwargs) -> int | bytes:
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        :returns: The new row's id -- ``bytes`` for every migrated table,
            or a plain ``int`` for ``ProjectsTable`` (still AUTO_INCREMENT).
        :rtype: int | bytes
        """
        if self.__uses_uuid_id__:
            cache = self._require_cache()
            new_id = _id_generator.generate_project_row_id(self._con, self.project_id)

            # A gesture (drag/rotate in progress -- WRITE_DESIGN.md
            # section 4.12) defers this into the cache instead of
            # touching the database, same as update()/batch_update()
            # already do. Safe here (unlike a plain AUTO_INCREMENT
            # table) because the row's own id is already fully known --
            # generated in Python, never read back from the database --
            # and every insert() override in this codebase already
            # supplies every column explicitly (confirmed 2026-10-13: no
            # caller relies on a schema-level DEFAULT for a column it
            # silently omits, so there is nothing left for a real INSERT
            # to discover that kwargs doesn't already have). The
            # outermost end_gesture() flushes everything that
            # accumulated in one transaction.
            if self.db.gesture_depth > 0:
                cache.insert(id=new_id.bytes, **kwargs)
                return new_id.bytes

            fields = ['id'] + list(kwargs.keys())
            values = ['?'] * len(fields)
            args = [new_id.bytes] + list(kwargs.values())

            fields_sql = ', '.join(fields)
            values_sql = ', '.join(values)
            self._con.execute(
                f'INSERT INTO {self.__table_name__} ({fields_sql}) VALUES ({values_sql});', args)
            self._con.commit()

            # Read the row back rather than assembling it from kwargs, since
            # kwargs can omit columns that the database fills with a default.
            self._con.execute(
                f'SELECT {", ".join(self.field_names)} FROM {self.__table_name__} WHERE id = ?;',
                (new_id.bytes,))
            row = self._con.fetchall()[0]
            cache.mirror_insert(**dict(zip(self.field_names, row)))
            return new_id.bytes

        # ProjectsTable only -- no cache, never gesture-deferred, still
        # AUTO_INCREMENT (there is no real project_id column for it to
        # scope a Python-generated id against -- see _project_id_bounds()).
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

    @_check_types.do
    def select(self, *args: str, OR: bool = False, **kwargs: Any) -> list[tuple]:
        """Execute the select operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param args: Additional positional arguments.
        :type args: UNKNOWN
        :param OR: Value for ``OR``.
        :type OR: bool
        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if self.__uses_uuid_id__:
            return self._require_cache().select(*args, OR=OR, **kwargs)

        args = ', '.join(args)

        kwarg_clauses = []
        kwarg_params = []

        for key, value in kwargs.items():
            if value is None:
                kwarg_clauses.append(f'{key} IS NULL')
            else:
                kwarg_clauses.append(f'{key} = ?')
                kwarg_params.append(value)

        if OR:
            kwarg_clause = ' OR '.join(kwarg_clauses)
            if kwarg_clauses:
                kwarg_clause = f'({kwarg_clause})'
        else:
            kwarg_clause = ' AND '.join(kwarg_clauses)

        # project_id must always be AND-ed against the kwarg clause, even
        # when OR=True -- otherwise "id BETWEEN low AND high OR <kwargs>"
        # matches every row in the project regardless of the kwargs.
        where_parts = []
        where_params = []
        if self.__uses_uuid_id__:
            low, high = _project_id_bounds(self.project_id)
            where_parts.append('(id >= ? AND id <= ?)')
            where_params.extend((low, high))

        if kwarg_clause:
            where_parts.append(kwarg_clause)
            where_params.extend(kwarg_params)

        where_clause = ' AND '.join(where_parts)
        where = f' WHERE {where_clause}' if where_clause else ''

        self._con.execute(f'SELECT {args} FROM {self.__table_name__}{where};', where_params)
        res = self._con.fetchall()
        return res

    @_check_types.do
    def delete(self, db_id: int | bytes) -> None:
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: int | bytes
        """
        cache = self._require_cache() if self.__uses_uuid_id__ else None

        # A gesture defers this into the cache instead of touching the
        # database, same as insert()/update() -- see insert()'s own
        # comment on why that's safe here. The row is marked for deletion
        # now (so anything that reads this table during the same gesture
        # sees it gone -- WRITE_DESIGN.md section 4.5a); the outermost
        # end_gesture() flushes the real DELETE in one transaction.
        if cache is not None and self.db.gesture_depth > 0:
            cache.delete(db_id)
            return

        self._con.execute(f'DELETE FROM {self.__table_name__} WHERE id = ?;',
                          (db_id,))

        self._con.commit()

        if cache is not None:
            cache.mirror_delete(db_id)

    @_check_types.do
    def update(self, db_id: int | bytes, **kwargs) -> None:
        """Execute the update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: int | bytes
        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        """
        cache = self._require_cache() if self.__uses_uuid_id__ else None

        # A gesture (drag/rotate in progress -- WRITE_DESIGN.md section 4.12)
        # defers this into the cache instead of touching the database. The
        # outermost end_gesture() flushes everything that accumulated in one
        # transaction. Outside a gesture, behavior is unchanged.
        if cache is not None and self.db.gesture_depth > 0:
            cache.change(db_id, **kwargs)
            return

        fields = []
        values = []

        for key, value in kwargs.items():
            fields.append(f'{key} = ?')
            values.append(value)

        fields = ', '.join(fields)
        values.append(db_id)
        self._con.execute(f'UPDATE {self.__table_name__} SET {fields} WHERE id = ?;', values)
        self._con.commit()

        if cache is not None:
            cache.mirror_update(db_id, **kwargs)

    @_check_types.do
    def batch_update(self, field_names: list, rows: list) -> None:
        """Update multiple rows in one transaction.

        :param field_names: Column names to update, e.g. ``['x', 'y', 'z']``.
        :type field_names: list[str]
        :param rows: Sequence of ``(val1, val2, ..., row_id)`` tuples.
            The last element of every tuple must be the row ``id``.
        :type rows: list[tuple]
        """
        if not rows:
            return

        cache = self._require_cache() if self.__uses_uuid_id__ else None

        # Same deferral as update() above -- see WRITE_DESIGN.md section 4.12.
        if cache is not None and self.db.gesture_depth > 0:
            for row in rows:
                cache.change(row[-1], **dict(zip(field_names, row[:-1])))
            return

        set_clause = ', '.join(f'{f} = ?' for f in field_names)
        sql = f'UPDATE {self.__table_name__} SET {set_clause} WHERE id = ?'
        self._con.executemany(sql, rows)
        self._con.commit()

        if cache is not None:
            for row in rows:
                cache.mirror_update(row[-1], **dict(zip(field_names, row[:-1])))

    @_check_types.do
    def batch_insert(self, rows: list[dict], commit: bool = True) -> None:
        """Insert many complete rows into this table in ONE ``executemany``.

        Unlike :meth:`insert`, there is no read-back: every row here already
        carries an explicit value for every column (id included), so there is
        no database-computed default left to discover. This is what lets a
        caller building hundreds of rows at once (e.g. a housing's cavity
        set -- see ``PJTHousingsTable.insert``/``PJTHousing.update_cavities``)
        do it as one statement instead of looping a per-row ``insert()``.

        Trade-off that comes with skipping the read-back: a caller that
        wants every row's columns to exactly match the schema's OWN
        defaults (``create_database/cavities.py`` etc.) has to keep its own
        copy of those defaults up to date by hand -- unlike ``insert()``'s
        read-back, which tolerates the live table carrying columns beyond
        what any one INSERT names (e.g. a column kept around from an
        earlier schema revision) because it asks the database what actually
        landed instead of assuming. A schema change that adds, removes, or
        re-defaults a column must update every :meth:`batch_insert` caller
        for that table in the same change, or the next call raises (see
        below) rather than silently drifting.

        Always immediate -- this never defers into the cache during an open
        gesture, unlike :meth:`update`/:meth:`batch_update`. A cross-table
        insert batch's statement order has to match real foreign-key
        dependency order (every point row before the cavity row that
        references it, etc.), and that order is this method's CALLER's job,
        not something to hand off to the gesture flush's own table order --
        confirmed that order is not a valid dependency order for inserts in
        general (``pjt_bundles`` references ``pjt_points3d`` but is visited
        before it there), so :meth:`batch_insert` deliberately doesn't ride
        on it. See WRITE_DESIGN.md section 4.12 for the gesture mechanism
        this intentionally stays outside of.

        :param rows: Every row to insert, each a dict covering every column
            of this table (id included) with its real intended value.
        :type rows: list[dict]
        :param commit: Commit after this table's insert. ``False`` lets a
            caller inserting into several tables at once (e.g. points then
            the cavity row referencing them) share ONE commit at the end,
            instead of one per table -- see the callers above for why that
            matters (a failure partway through must not leave an earlier
            table's rows committed with nothing yet referencing them).
        :type commit: bool
        :raises ValueError: A row's keys don't match this table's columns
            exactly.
        """
        if not rows:
            return

        cache = self._require_cache() if self.__uses_uuid_id__ else None

        fields = self.field_names
        field_set = frozenset(fields)

        for row in rows:
            if set(row) != field_set:
                raise ValueError(
                    f'{self.__table_name__} batch_insert needs exactly {sorted(field_set)} per row, '
                    f'got {sorted(row)}')

        columns = ', '.join(fields)
        placeholders = ', '.join(['?'] * len(fields))
        sql = f'INSERT INTO {self.__table_name__} ({columns}) VALUES ({placeholders});'

        param_rows = [[row[field] for field in fields] for row in rows]
        self._con.executemany(sql, param_rows)

        if commit:
            self._con.commit()

        if cache is not None:
            for row in rows:
                cache.mirror_insert(**row)

    @property
    @_check_types.do
    def has_points3d(self) -> bool:
        """Return the has points 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return any([name for name in self.field_names if name.endswith('point3d_id')])

    @property
    @_check_types.do
    def has_points2d(self) -> bool:
        """Return the has points 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return any([name for name in self.field_names if name.endswith('point2d_id')])

    @_check_types.do
    def find_unreferenced_point3d_ids(self, candidate_ids: list[int]) -> list[int]:
        """Find the unreferenced point 3D IDs.

        UNKNOWN details are inferred from the callable name and signature.

        :param candidate_ids: Identifier for the candidate.
        :type candidate_ids: list[int]
        :returns: Return value. UNKNOWN details.
        :rtype: list[int]
        """
        return self._find_unreferenced_point_ids(candidate_ids, 'point3d_id')

    @_check_types.do
    def find_unreferenced_point2d_ids(self, candidate_ids: list[int]) -> list[int]:
        """Find the unreferenced point 2D IDs.

        UNKNOWN details are inferred from the callable name and signature.

        :param candidate_ids: Identifier for the candidate.
        :type candidate_ids: list[int]
        :returns: Return value. UNKNOWN details.
        :rtype: list[int]
        """
        return self._find_unreferenced_point_ids(candidate_ids, 'point2d_id')

    @_check_types.do
    def _find_unreferenced_point_ids(self, candidate_ids: list[int], suffix: str) -> list[int]:
        """
        Given a set of candidate point IDs, return only those NOT referenced
        by any column in this table that ends with *suffix*.

        Uses a CTE to define the candidates, LEFT JOINs against a UNION of
        every matching column, and returns the rows where the join found
        nothing — the IDs not present in this table.

        The returned set is passed to the next table in the chain.  Each
        table call can only reduce or maintain the set, never grow it, so
        the set monotonically shrinks toward the confirmed orphan set.

        A ``project_id`` filter is applied to every SELECT in the UNION so
        that only rows belonging to the currently open project are considered.
        This prevents a cleanup pass on one seat from treating another
        project's mid-operation points as orphaned when multiple users share
        the same database with different projects open.

        Query structure::

            WITH candidates(id) AS (VALUES (?), (?), ...)
            SELECT candidates.id
            FROM candidates
            LEFT JOIN (
                SELECT col1 AS point_id FROM table
                    WHERE id >= ? AND id <= ? AND col1 IN (?, ?, ...)
                UNION
                SELECT col2 FROM table
                    WHERE id >= ? AND id <= ? AND col2 IN (?, ?, ...)
            ) AS referenced ON candidates.id = referenced.point_id
            WHERE referenced.point_id IS NULL;

        Parameters
        ----------
        candidate_ids : set[int]
            IDs still unconfirmed as referenced.  Passed in from the
            previous table call (or the full batch on the first call).
        suffix : str
            Column suffix to match, e.g. ``'point3d_id'``.

        Returns
        -------
        set[int]
            The subset of *candidate_ids* not found in this table for the
            current project.  If this table has no columns matching *suffix*,
            the full input set is returned unchanged so the chain continues.
        """
        if not candidate_ids:
            return []

        point_cols = [col for col in self.field_names if col.endswith(suffix)]

        if not point_cols:
            # This table has no relevant columns — pass the set through unchanged
            return candidate_ids

        params = [p for p in candidate_ids]
        placeholders = ','.join('?' * len(params))

        # CTE rows: one parameterized placeholder per candidate id (ids are
        # now UUID bytes, not bare integers -- can't be inlined as literals)
        cte_rows = ','.join('(?)' for _ in params)

        # Each SELECT in the UNION filters to the currently open project by
        # scanning the id range its rows fall in (see _project_id_bounds)
        union_parts = [
            f'SELECT {col} AS point_id '
            f'FROM {self.__table_name__} '
            f'WHERE id >= ? AND id <= ? AND {col} IN ({placeholders})'
            for col in point_cols
        ]
        union_sql = ' UNION '.join(union_parts)

        query = (f'WITH candidates(id) AS (VALUES {cte_rows}) '
                 f'SELECT candidates.id '
                 f'FROM candidates '
                 f'LEFT JOIN ({union_sql}) AS referenced '
                 f'ON candidates.id = referenced.point_id '
                 f'WHERE referenced.point_id IS NULL;')

        # CTE VALUES params first (matches their position in the query text),
        # then one project_id (low, high) bound pair + one copy of the
        # candidate params per column in the UNION.
        low, high = _project_id_bounds(self.project_id)
        all_params = params[:]
        for _ in point_cols:
            all_params.append(low)
            all_params.append(high)
            all_params.extend(params)

        self._con.execute(query, all_params)

        ret = {row[0] for row in self._con.fetchall() if row[0] is not None}
        return list(ret)

    @_check_types.do
    def execute(self, cmd: str, params: tuple | None = None) -> _Generator | None:
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
    def fetchall(self) -> list[tuple]:
        """Execute the fetchall operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._con.fetchall()

    @_check_types.do
    def fetchone(self) -> list[tuple] | None:
        """Execute the fetchone operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._con.fetchone()

    @_check_types.do
    def commit(self) -> None:
        """Execute the commit operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._con.commit()

    @property
    @_check_types.do
    def lastrowid(self) -> int | None:
        """Return the lastrowid.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._con.lastrowid


from .pjt_bundle import PJTBundlesTable  # NOQA
from .pjt_bundle_layout import PJTBundleLayoutsTable  # NOQA
from .pjt_circuit import PJTCircuitsTable  # NOQA
from .pjt_point2d import PJTPoints2DTable  # NOQA
from .pjt_point3d import PJTPoints3DTable  # NOQA
from .pjt_housing import PJTHousingsTable  # NOQA
from .pjt_splice import PJTSplicesTable  # NOQA
from .pjt_transition import PJTTransitionsTable  # NOQA
from .pjt_wire import PJTWiresTable  # NOQA
from .pjt_wire_layout import PJTWireLayoutsTable  # NOQA
from .pjt_wire_path import PJTWirePathsTable  # NOQA
from .pjt_bundle_path import PJTBundlePathsTable  # NOQA
from .pjt_cavity import PJTCavitiesTable  # NOQA
from .pjt_terminal import PJTTerminalsTable  # NOQA
from .pjt_wire_marker import PJTWireMarkersTable  # NOQA
from .pjt_seal import PJTSealsTable  # NOQA
from .pjt_cover import PJTCoversTable  # NOQA
from .pjt_boot import PJTBootsTable  # NOQA
from .pjt_cpa_lock import PJTCPALocksTable  # NOQA
from .pjt_tpa_lock import PJTTPALocksTable  # NOQA
from .pjt_wire_service_loop import PJTWireServiceLoopsTable  # NOQA
from .pjt_note import PJTNotesTable  # NOQA
from .pjt_concentric import PJTConcentricsTable  # NOQA
from .pjt_concentric_layer import PJTConcentricLayersTable  # NOQA
from .pjt_concentric_wire import PJTConcentricWiresTable  # NOQA
from .pjt_transition_branch import PJTTransitionBranchesTable  # NOQA
from .pjt_point_pegboard import PJTPointsPegboardTable  # NOQA
from .pjt_pegboard_table import PJTPegboardTablesTable  # NOQA

from .project import ProjectsTable  # NOQA


class _GestureContext:
    """``with tables.gesture():`` -- opens a gesture on entry, closes it on
    exit (committing/flushing on the outermost exit) even if the block
    raises. See ``PJTTables.gesture``/``begin_gesture``/``end_gesture`` and
    WRITE_DESIGN.md section 4.12.
    """

    @_check_types.do
    def __init__(self, tables: "PJTTables") -> None:
        """Hold the :class:`PJTTables` this gesture belongs to.

        :param tables: The tables instance to open/close the gesture on.
        :type tables: PJTTables
        """
        self._tables = tables

    @_check_types.do
    def __enter__(self) -> "_GestureContext":
        """Open the gesture.

        :returns: This context manager.
        :rtype: _GestureContext
        """
        self._tables.begin_gesture()
        return self

    @_check_types.do
    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Close the gesture regardless of whether the block raised.

        :param exc_type: Exception type, if the block raised. Unused.
        :param exc_val: Exception value, if the block raised. Unused.
        :param exc_tb: Traceback, if the block raised. Unused.
        """
        self._tables.end_gesture()


class PJTTables:
    """Represent a PJT tables in :mod:`harness_designer.database.project_db.pjt_bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, splash: "_splash.Splash", mainframe: "_ui.MainFrame") -> None:
        """Initialise the :class:`PJTTables` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """
        self.mainframe = mainframe
        self.global_db = mainframe.global_db
        self.connector = mainframe.db_connector

        tables = self.connector.get_tables()
        self._projects_table = ProjectsTable(self, None, tables, splash)

        self._pjt_bundles_table = None
        self._pjt_bundle_layouts_table = None
        self._pjt_circuits_table = None
        self._pjt_points2d_table = None
        self._pjt_points3d_table = None
        self._pjt_housings_table = None
        self._pjt_splices_table = None
        self._pjt_transitions_table = None
        self._pjt_wires_table = None
        self._pjt_wire_layouts_table = None
        self._pjt_wire_paths_table = None
        self._pjt_bundle_paths_table = None
        self._pjt_cavities_table = None
        self._pjt_terminals_table = None
        self._pjt_seals_table = None
        self._pjt_covers_table = None
        self._pjt_boots_table = None
        self._pjt_cpa_locks_table = None
        self._pjt_tpa_locks_table = None
        self._pjt_wire_markers_table = None
        self._pjt_wire_service_loops_table = None
        self._pjt_notes_table = None
        self._pjt_concentrics_table = None
        self._pjt_concentric_layers_table = None
        self._pjt_concentric_wires_table = None
        self._pjt_transition_branches_table = None
        self._pjt_points_pegboard_table = None
        self._pjt_pegboard_tables_table = None

        self._points2d = []
        self._points3d = []

        self._current_count = 0

        # Gesture depth for move/rotate (WRITE_DESIGN.md section 4.12).
        # 0 = no gesture open, every write is immediate (today's behavior).
        # > 0 = a drag/rotate is in progress; PJTTableBase.update/batch_update
        # defer into each table's TableData cache instead of touching the
        # database, and the outermost end_gesture() flushes everything that
        # accumulated in one transaction.
        self._gesture_depth = 0

        # This instance's own fixed table SET never changes after this
        # __init__ returns, so the real insert-safe ordering of them
        # (see _insert_safe_project_tables) is computed once, lazily, on
        # the first gesture flush, and reused for this PJTTables' whole
        # lifetime -- never rebuilt per flush.
        self._insert_order_cache: list["PJTTableBase"] | None = None

    @property
    @_check_types.do
    def tables(self) -> list[PJTTableBase]:
        """Return the tables.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[PJTTableBase]
        """
        return [getattr(self, name) for name in sorted(list(dir(self)), reverse=True)
                if name.endswith('_table') and not name.startswith('_')]

    @_check_types.do
    def load(self, project_id: bytes) -> None:
        """Execute the load operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param project_id: Identifier for the project.
        :type project_id: UNKNOWN
        """
        self.mainframe.unload()
        tables = self.connector.get_tables()

        _logger.database('TABLES:', tables)

        class Splash:
            """Represent a splash in :mod:`harness_designer.database.project_db.pjt_bases`.

            UNKNOWN details are inferred from the class name and surrounding code.
            """

            @staticmethod
            @_check_types.do
            def SetText(msg: str) -> None:
                """Execute the set text operation.

                UNKNOWN details are inferred from the callable name and signature.

                :param msg: Value for ``msg``.
                :type msg: UNKNOWN
                """
                self.mainframe.logger.info(msg)

        self._current_count = 0

        self._pjt_bundles_table = PJTBundlesTable(self, project_id, tables, Splash)
        self._pjt_bundle_layouts_table = PJTBundleLayoutsTable(self, project_id, tables, Splash)
        self._pjt_circuits_table = PJTCircuitsTable(self, project_id, tables, Splash)
        self._pjt_points2d_table = PJTPoints2DTable(self, project_id, tables, Splash)
        self._pjt_points3d_table = PJTPoints3DTable(self, project_id, tables, Splash)
        self._pjt_housings_table = PJTHousingsTable(self, project_id, tables, Splash)
        self._pjt_splices_table = PJTSplicesTable(self, project_id, tables, Splash)
        self._pjt_transitions_table = PJTTransitionsTable(self, project_id, tables, Splash)
        self._pjt_wires_table = PJTWiresTable(self, project_id, tables, Splash)
        self._pjt_wire_layouts_table = PJTWireLayoutsTable(self, project_id, tables, Splash)
        self._pjt_wire_paths_table = PJTWirePathsTable(self, project_id, tables, Splash)
        self._pjt_bundle_paths_table = PJTBundlePathsTable(self, project_id, tables, Splash)
        self._pjt_cavities_table = PJTCavitiesTable(self, project_id, tables, Splash)
        self._pjt_terminals_table = PJTTerminalsTable(self, project_id, tables, Splash)
        self._pjt_seals_table = PJTSealsTable(self, project_id, tables, Splash)
        self._pjt_covers_table = PJTCoversTable(self, project_id, tables, Splash)
        self._pjt_boots_table = PJTBootsTable(self, project_id, tables, Splash)
        self._pjt_cpa_locks_table = PJTCPALocksTable(self, project_id, tables, Splash)
        self._pjt_tpa_locks_table = PJTTPALocksTable(self, project_id, tables, Splash)
        self._pjt_wire_markers_table = PJTWireMarkersTable(self, project_id, tables, Splash)
        self._pjt_wire_service_loops_table = PJTWireServiceLoopsTable(self, project_id, tables, Splash)
        self._pjt_notes_table = PJTNotesTable(self, project_id, tables, Splash)
        self._pjt_concentrics_table = PJTConcentricsTable(self, project_id, tables, Splash)
        self._pjt_concentric_layers_table = PJTConcentricLayersTable(self, project_id, tables, Splash)
        self._pjt_concentric_wires_table = PJTConcentricWiresTable(self, project_id, tables, Splash)
        self._pjt_transition_branches_table = PJTTransitionBranchesTable(self, project_id, tables, Splash)
        self._pjt_points_pegboard_table = PJTPointsPegboardTable(self, project_id, tables, Splash)
        self._pjt_pegboard_tables_table = PJTPegboardTablesTable(self, project_id, tables, Splash)

        for table in self._ordered_project_tables():
            table.load_cache()

    @_check_types.do
    def _ordered_project_tables(self) -> list[PJTTableBase]:
        """Every project (UUID-id) table, parents before the children that
        reference them.

        This is the one order every project table was already loaded in
        (``load()`` above); the gesture flush (section 4.12) reuses it for
        the same reason ``load()`` needed it -- a child's foreign key (e.g.
        a housing's ``position3d_id``) must point at a row that already
        exists, so on insert a parent table's statement must run before the
        children that reference it, and on delete the reverse.

        :returns: Every project table, in parent-before-child order.
        :rtype: list[PJTTableBase]
        """
        return [
            self._pjt_bundles_table, self._pjt_bundle_layouts_table, self._pjt_circuits_table,
            self._pjt_points2d_table, self._pjt_points3d_table, self._pjt_housings_table,
            self._pjt_splices_table, self._pjt_transitions_table, self._pjt_wires_table,
            self._pjt_wire_layouts_table, self._pjt_wire_paths_table, self._pjt_bundle_paths_table,
            self._pjt_cavities_table, self._pjt_terminals_table, self._pjt_seals_table,
            self._pjt_covers_table, self._pjt_boots_table, self._pjt_cpa_locks_table,
            self._pjt_tpa_locks_table, self._pjt_wire_markers_table, self._pjt_wire_service_loops_table,
            self._pjt_notes_table, self._pjt_concentrics_table, self._pjt_concentric_layers_table,
            self._pjt_concentric_wires_table, self._pjt_transition_branches_table,
            self._pjt_points_pegboard_table, self._pjt_pegboard_tables_table,
        ]

    @_check_types.do
    def _insert_safe_project_tables(self) -> list[PJTTableBase]:
        """Every project table this :class:`PJTTables` holds, ordered so
        a table's own row can always be inserted before anything that
        references it -- the real dependency order from
        :func:`_schema_dependency_order`, not
        :meth:`_ordered_project_tables`'s own hand-picked list.

        Computed once and cached on ``self`` -- this instance's own
        table set is fixed for its whole lifetime (built once in
        ``__init__``), so there is nothing here that could ever change
        between flushes; a fresh project load gets its own new
        ``PJTTables`` (and so its own fresh cache) regardless.

        :returns: Every project table, in true parent-before-child order.
        :rtype: list[PJTTableBase]
        """
        if self._insert_order_cache is not None:
            return self._insert_order_cache

        by_name = {
            table.__table_name__: table for table in self._ordered_project_tables()
            if table is not None}
        order = _schema_dependency_order()

        ordered = [by_name[name] for name in order if name in by_name]

        # Anything this PJTTables holds that the schema scan somehow
        # missed still gets flushed, just appended rather than dropped.
        ordered_set = set(ordered)
        ordered.extend(table for table in by_name.values() if table not in ordered_set)

        self._insert_order_cache = ordered
        return ordered

    @property
    @_check_types.do
    def gesture_depth(self) -> int:
        """How many gestures are currently nested (0 = none open).

        :returns: The current gesture depth.
        :rtype: int
        """
        return self._gesture_depth

    @_check_types.do
    def begin_gesture(self) -> None:
        """Open one gesture (a drag or rotate in progress).

        Writes made while any gesture is open are deferred into each
        table's cache instead of reaching the database -- see
        ``PJTTableBase.update``/``batch_update`` and WRITE_DESIGN.md section
        4.12. Nested calls just increment the depth; only the outermost
        :meth:`end_gesture` flushes.
        """
        self._gesture_depth += 1

    @_check_types.do
    def end_gesture(self) -> None:
        """Close one gesture. The outermost call flushes every table that
        accumulated a pending write, in one transaction.

        :raises RuntimeError: Called with no gesture open.
        """
        if self._gesture_depth == 0:
            raise RuntimeError('end_gesture() called with no gesture open')

        self._gesture_depth -= 1

        if self._gesture_depth == 0:
            self._flush_gesture()

    @_check_types.do
    def gesture(self) -> "_GestureContext":
        """A ``with`` block that opens a gesture on entry and closes it on
        exit, flushing on the outermost exit even if the block raises.

        :returns: The context manager.
        :rtype: _GestureContext
        """
        return _GestureContext(self)

    @_check_types.do
    def _flush_gesture(self) -> None:
        """Write every pending change, across every project table, in one
        transaction (WRITE_DESIGN.md section 4.8). Called only by
        :meth:`end_gesture` on the outermost close.

        Deletes run before inserts (children before the parents they
        reference go away), inserts run before updates (a row's own
        insert must exist before anything can update it -- now a real
        case, not just a defensive one, since ``insert()`` defers too --
        see its own comment). Both the delete and insert phases visit
        tables in :meth:`_insert_safe_project_tables`'s own real
        dependency order (reversed for delete) -- NOT
        :meth:`_ordered_project_tables`'s hand-picked one, which is not
        a valid insert order in general. The update phase's own order
        never mattered either way (a plain ``UPDATE`` never depends on
        another table's row existing).
        """
        tables = [table for table in self._ordered_project_tables() if table is not None]
        dirty = [table for table in tables if table._cache is not None and table._cache.is_dirty]

        if not dirty:
            return

        dirty_set = set(dirty)
        insert_order = [table for table in self._insert_safe_project_tables() if table in dirty_set]

        for table in reversed(insert_order):
            statement = table._cache.delete_statement()
            if statement is not None:
                sql, rows = statement
                self.connector.executemany(sql, rows)

        for table in insert_order:
            statement = table._cache.insert_statement()
            if statement is not None:
                sql, rows = statement
                self.connector.executemany(sql, rows)

        for table in dirty:
            for sql, rows in table._cache.update_statements():
                self.connector.executemany(sql, rows)

        self.connector.commit()

        for table in dirty:
            table._cache.commit_flushed()

    @property
    @_check_types.do
    def pjt_bundles_table(self) -> PJTBundlesTable:
        """Return the PJT bundles table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundlesTable`
        """
        return self._pjt_bundles_table

    @property
    @_check_types.do
    def pjt_bundle_layouts_table(self) -> PJTBundleLayoutsTable:
        """Return the PJT bundle layouts table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayoutsTable`
        """
        return self._pjt_bundle_layouts_table

    @property
    @_check_types.do
    def pjt_circuits_table(self) -> PJTCircuitsTable:
        """Return the PJT circuits table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTCircuitsTable`
        """
        return self._pjt_circuits_table

    @property
    @_check_types.do
    def pjt_points2d_table(self) -> PJTPoints2DTable:
        """Return the PJT points 2D table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTPoints2DTable`
        """
        return self._pjt_points2d_table

    @property
    @_check_types.do
    def pjt_points3d_table(self) -> PJTPoints3DTable:
        """Return the PJT points 3D table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTPoints3DTable`
        """
        return self._pjt_points3d_table

    @property
    @_check_types.do
    def pjt_housings_table(self) -> PJTHousingsTable:
        """Return the PJT housings table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTHousingsTable`
        """
        return self._pjt_housings_table

    @property
    @_check_types.do
    def pjt_splices_table(self) -> PJTSplicesTable:
        """Return the PJT splices table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTSplicesTable`
        """
        return self._pjt_splices_table

    @property
    @_check_types.do
    def pjt_transitions_table(self) -> PJTTransitionsTable:
        """Return the PJT transitions table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTransitionsTable`
        """
        return self._pjt_transitions_table

    @property
    @_check_types.do
    def pjt_wires_table(self) -> PJTWiresTable:
        """Return the PJT wires table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWiresTable`
        """
        return self._pjt_wires_table

    @property
    @_check_types.do
    def pjt_wire_layouts_table(self) -> PJTWireLayoutsTable:
        """Return the PJT wire layouts table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireLayoutsTable`
        """
        return self._pjt_wire_layouts_table

    @property
    @_check_types.do
    def pjt_wire_paths_table(self) -> PJTWirePathsTable:
        """Return the PJT wire paths table (every wire's route, one row per
        point per wire per view).

        :returns: The wire paths table.
        :rtype: :class:`PJTWirePathsTable`
        """
        return self._pjt_wire_paths_table

    @property
    @_check_types.do
    def pjt_bundle_paths_table(self) -> PJTBundlePathsTable:
        """Return the PJT bundle paths table (every bundle's interior
        waypoint list, one row per point per bundle per view).

        :returns: The bundle paths table.
        :rtype: :class:`PJTBundlePathsTable`
        """
        return self._pjt_bundle_paths_table

    @property
    @_check_types.do
    def projects_table(self) -> ProjectsTable:
        """Return the projects table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`ProjectsTable`
        """
        return self._projects_table

    @property
    @_check_types.do
    def pjt_cavities_table(self) -> PJTCavitiesTable:
        """Return the PJT cavities table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTCavitiesTable`
        """
        return self._pjt_cavities_table

    @property
    @_check_types.do
    def pjt_terminals_table(self) -> PJTTerminalsTable:
        """Return the PJT terminals table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTerminalsTable`
        """
        return self._pjt_terminals_table

    @property
    @_check_types.do
    def pjt_seals_table(self) -> PJTSealsTable:
        """Return the PJT seals table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTSealsTable`
        """
        return self._pjt_seals_table

    @property
    @_check_types.do
    def pjt_covers_table(self) -> PJTCoversTable:
        """Return the PJT covers table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTCoversTable`
        """
        return self._pjt_covers_table

    @property
    @_check_types.do
    def pjt_boots_table(self) -> PJTBootsTable:
        """Return the PJT boots table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBootsTable`
        """
        return self._pjt_boots_table

    @property
    @_check_types.do
    def pjt_cpa_locks_table(self) -> PJTCPALocksTable:
        """Return the PJT CPA locks table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTCPALocksTable`
        """
        return self._pjt_cpa_locks_table

    @property
    @_check_types.do
    def pjt_tpa_locks_table(self) -> PJTTPALocksTable:
        """Return the PJT TPA locks table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTPALocksTable`
        """
        return self._pjt_tpa_locks_table

    @property
    @_check_types.do
    def pjt_wire_markers_table(self) -> PJTWireMarkersTable:
        """Return the PJT wire markers table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireMarkersTable`
        """
        return self._pjt_wire_markers_table

    @property
    @_check_types.do
    def pjt_wire_service_loops_table(self) -> PJTWireServiceLoopsTable:
        """Return the PJT wire service loops table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireServiceLoopsTable`
        """
        return self._pjt_wire_service_loops_table

    @property
    @_check_types.do
    def pjt_notes_table(self) -> PJTNotesTable:
        """Return the PJT notes table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTNotesTable`
        """
        return self._pjt_notes_table

    @property
    @_check_types.do
    def pjt_concentrics_table(self) -> PJTConcentricsTable:
        """Return the PJT concentrics table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTConcentricsTable`
        """
        return self._pjt_concentrics_table

    @property
    @_check_types.do
    def pjt_concentric_layers_table(self) -> PJTConcentricLayersTable:
        """Return the PJT concentric layers table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTConcentricLayersTable`
        """
        return self._pjt_concentric_layers_table

    @property
    @_check_types.do
    def pjt_concentric_wires_table(self) -> PJTConcentricWiresTable:
        """Return the PJT concentric wires table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTConcentricWiresTable`
        """
        return self._pjt_concentric_wires_table

    @property
    @_check_types.do
    def pjt_transition_branches_table(self) -> PJTTransitionBranchesTable:
        """Return the PJT transition branches table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTransitionBranchesTable`
        """
        return self._pjt_transition_branches_table

    @property
    @_check_types.do
    def pjt_points_pegboard_table(self) -> PJTPointsPegboardTable:
        """Return the peg-board points table.

        :returns: The peg-board points table for the loaded project.
        :rtype: :class:`PJTPointsPegboardTable`
        """
        return self._pjt_points_pegboard_table

    @property
    @_check_types.do
    def pjt_pegboard_tables_table(self) -> PJTPegboardTablesTable:
        """Return the peg-board data-table overlay table.

        :returns: The peg-board tables overlay table for the loaded project.
        :rtype: :class:`PJTPegboardTablesTable`
        """
        return self._pjt_pegboard_tables_table
