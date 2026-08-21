# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable, TYPE_CHECKING

import weakref
import threading
import functools

from ... import logger as _logger
from ..common_db import callback as _callback
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import splash as _splash


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
    def __init__(cls, name, bases, dct):
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
        setattr(cls, '_instances', {})
        cls._instances = {}
        # See _EntrySingleton (global_db/bases.py) for why this needs a
        # lock: _instances is read/written from __call__ (any thread that
        # looks up or constructs an entry) and mutated from
        # __remove_instance_ref, which runs as a weakref callback on
        # whatever thread happens to drop the last reference -- unrelated
        # to whichever thread is concurrently in __call__. Unsynchronized
        # concurrent mutation was corrupting this dict's internal
        # structure (see the crash investigation).
        setattr(cls, '_instances_lock', threading.RLock())
        cls._instances_lock = threading.RLock()

    @staticmethod
    @_check_types.do
    def __remove_instance_ref(cls, ref):
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

    def __contains__(cls, db_id: int | bytes):
        return db_id in cls._instances and cls._instances[db_id]() is not None

    @_check_types.do
    def __call__(cls, table, db_id: int | bytes):
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


class PJTEntryBase(_callback.CallbackMixin, metaclass=_PJTEntrySingleton):
    """Represent a PJT entry base in :mod:`harness_designer.database.project_db.pjt_bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, table: "PJTTableBase", db_id: int | bytes):
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

    @_check_types.do
    def get_object(self):
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    @_check_types.do
    def set_object(self, obj):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    _selected: bool = False

    @property
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
    def selected(self, flag: bool):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self._selected = flag

    @property
    @_check_types.do
    def db_id(self) -> int | bytes:
        """Return the database ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int | bytes
        """
        return self._db_id

    @property
    @_check_types.do
    def table(self):
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


class PJTTableBase:
    """Represent a PJT table base in :mod:`harness_designer.database.project_db.pjt_bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__: str = None

    # True for every migrated pjt_* table (client-generated UUID row ids).
    # False only for ProjectsTable, which keeps a plain AUTO_INCREMENT id --
    # see the migration plan for why.
    __uses_uuid_id__: bool = True

    @_check_types.do
    def __init__(self, db: "PJTTables", project_id: int | None, table_names: list[str], splash: "_splash.Splash"):
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

        if self.__table_name__ not in table_names:
            splash.SetText(f'Creating {self.__table_name__.replace("_", " ")} database table...')

            self._add_table_to_db()

        if self._table_needs_update():
            splash.SetText(f'Adding {self.__table_name__.replace("_", " ")} table fields...')

            self._update_table_in_db()

        splash.SetText(f'Loading {self.__table_name__.replace("_", " ")} database table...')

        self.project_id = project_id

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
    def get_records(self, project_id):
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
    def set_project(self, project_id: int | None = None):
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
    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    @_check_types.do
    def _update_table_in_db(self):
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
        fields = []
        values = []
        args = []
        new_id = None

        if self.__uses_uuid_id__:
            new_id = _id_generator.generate_project_row_id(self._con, self.project_id)
            fields.append('id')
            values.append('?')
            args.append(new_id.bytes)

        # There is no real project_id column -- see _project_id_bounds()
        # for why -- so project_id is never inserted directly; it's only
        # ever read back out of the leading bytes of id.

        for key, value in kwargs.items():
            fields.append(key)
            args.append(value)
            values.append('?')

        fields = ', '.join(fields)
        values = ', '.join(values)
        self._con.execute(f'INSERT INTO {self.__table_name__} ({fields}) VALUES ({values});', args)
        self._con.commit()

        if self.__uses_uuid_id__:
            return new_id.bytes

        return self._con.lastrowid

    @_check_types.do
    def select(self, *args, OR: bool = False, **kwargs):
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
        self._con.execute(f'DELETE FROM {self.__table_name__} WHERE id = ?;',
                          (db_id,))

        self._con.commit()

    @_check_types.do
    def update(self, db_id: int | bytes, **kwargs):
        """Execute the update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: int | bytes
        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        """
        fields = []
        values = []

        for key, value in kwargs.items():
            fields.append(f'{key} = ?')
            values.append(value)

        fields = ', '.join(fields)
        values.append(db_id)
        self._con.execute(f'UPDATE {self.__table_name__} SET {fields} WHERE id = ?;', values)
        self._con.commit()

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
        set_clause = ', '.join(f'{f} = ?' for f in field_names)
        sql = f'UPDATE {self.__table_name__} SET {set_clause} WHERE id = ?'
        self._con.executemany(sql, rows)
        self._con.commit()

    @property
    @_check_types.do
    def has_points3d(self):
        """Return the has points 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return any([name for name in self.field_names if name.endswith('_point3d_id')])

    @property
    @_check_types.do
    def has_points2d(self):
        """Return the has points 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return any([name for name in self.field_names if name.endswith('_point2d_id')])

    @_check_types.do
    def find_unreferenced_point3d_ids(self, candidate_ids: list[int]) -> list[int]:
        """Find the unreferenced point 3D IDs.

        UNKNOWN details are inferred from the callable name and signature.

        :param candidate_ids: Identifier for the candidate.
        :type candidate_ids: list[int]
        :returns: Return value. UNKNOWN details.
        :rtype: list[int]
        """
        return self._find_unreferenced_point_ids(candidate_ids, '_point3d_id')

    @_check_types.do
    def find_unreferenced_point2d_ids(self, candidate_ids: list[int]) -> list[int]:
        """Find the unreferenced point 2D IDs.

        UNKNOWN details are inferred from the callable name and signature.

        :param candidate_ids: Identifier for the candidate.
        :type candidate_ids: list[int]
        :returns: Return value. UNKNOWN details.
        :rtype: list[int]
        """
        return self._find_unreferenced_point_ids(candidate_ids, '_point2d_id')

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
            Column suffix to match, e.g. ``'_point3d_id'``.

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


class PJTTables:
    """Represent a PJT tables in :mod:`harness_designer.database.project_db.pjt_bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, splash, mainframe: "_ui.MainFrame"):
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
    def load(self, project_id):
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
            def SetText(msg):
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
