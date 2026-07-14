# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable, TYPE_CHECKING

import weakref

from ... import logger as _logger
from ..common_db import callback as _callback


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import splash as _splash


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

    @classmethod
    def __remove_instance_ref(cls, ref):
        """Remove the instance ref.

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

    def __call__(cls, table, db_id: int, project_id: int | None):
        """Call the instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param table: Value for ``table``.
        :type table: UNKNOWN
        :param db_id: Identifier for the database.
        :type db_id: int
        :param project_id: Identifier for the project.
        :type project_id: int | None
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        key = (project_id, db_id)

        if key in cls._instances:
            ref = cls._instances[key]
            instance = ref()
        else:
            instance = None

        if instance is None:
            instance = super().__call__(table, db_id, project_id)
            cls._instances[key] = weakref.ref(instance, cls.__remove_instance_ref)

        return instance


class PJTEntryBase(_callback.CallbackMixin, metaclass=_PJTEntrySingleton):
    """Represent a PJT entry base in :mod:`harness_designer.database.project_db.pjt_bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, table: "PJTTableBase", db_id: int, project_id: int | None):
        """Initialise the :class:`PJTEntryBase` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param table: Value for ``table``.
        :type table: :class:`PJTTableBase`
        :param db_id: Identifier for the database.
        :type db_id: int
        :param project_id: Identifier for the project.
        :type project_id: int | None
        """
        self._table = table
        self._db_id = db_id
        self.project_id = project_id

        self._obj = None
        self._objects = []
        self._treeitem = None
        _callback.CallbackMixin.__init__(self)

    def update_objects(self):
        """Update the objects.

        UNKNOWN details are inferred from the callable name and signature.
        """
        for ref in self._objects:
            obj = ref()
            if obj is None:
                continue

            obj.reload_from_db()

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

    def add_object(self, obj):
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._objects.append(weakref.ref(obj, self.__remove_ref))

    def get_object(self):
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

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
    def selected(self) -> bool:
        """Return the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._selected

    @selected.setter
    def selected(self, flag: bool):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self._selected = flag

    @staticmethod
    def merge_packet_data(src: dict, dst: dict):
        """Execute the merge packet data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param src: Value for ``src``.
        :type src: dict
        :param dst: Value for ``dst``.
        :type dst: dict
        """
        for key, values in src.items():
            if key in dst:
                values = [value for value in values if value not in dst[key]]
                dst[key].extend(values)
            else:
                dst[key] = values[:]

    @property
    def db_id(self) -> int:
        """Return the database ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._db_id

    @property
    def table(self):
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._table

    def delete(self) -> None:
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._table.delete(self.db_id)

        key = (self.project_id, self.db_id)

        if key in self.__class__._instances:  # NOQA
            del self.__class__._instances[key]  # NOQA


class PJTTableBase:
    """Represent a PJT table base in :mod:`harness_designer.database.project_db.pjt_bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__: str = None

    def __init__(self, db: "PJTTables", project_id: int | None, table_names: list['str'], splash: "_splash.Splash"):
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

    def get_records(self, project_id):
        """Return the records.

        UNKNOWN details are inferred from the callable name and signature.

        :param project_id: Identifier for the project.
        :type project_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        self.execute(f'SELECT {", ".join(self.field_names)} FROM {self.__table_name__} WHERE project_id={project_id};')
        rows = self.fetchall()
        if rows:
            rows = list(rows)
        else:
            rows = []

        rows.insert(0, tuple(self.field_names))

        return rows

    def set_project(self, project_id: int | None = None):
        """Set the project.

        UNKNOWN details are inferred from the callable name and signature.

        :param project_id: Identifier for the project.
        :type project_id: int | None
        """
        self.project_id = project_id

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    def __getitem__(self, item):
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        self._con.execute(f'SELECT * FROM {self.__table_name__} WHERE id = {item};')

        for line in self._con.fetchall():
            return line

    def __iter__(self) -> _Iterable[int]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable[int]
        """
        if self.project_id is None:
            self._con.execute(f'SELECT id FROM {self.__table_name__};')
        else:
            self._con.execute(f'SELECT id FROM {self.__table_name__} WHERE project_id = {self.project_id};')

        for line in self._con.fetchall():
            yield line[0]

    @property
    def table_name(self) -> str:
        """Return the table name.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self.__table_name__

    def __contains__(self, db_id: int) -> bool:
        """Return whether the requested item is present.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: int
        :returns: ``True`` when the condition is satisfied.
        :rtype: bool
        """
        self._con.execute(f'SELECT id FROM {self.__table_name__} WHERE id = {db_id};')

        if self._con.fetchall():
            return True

        return False

    def insert(self, **kwargs) -> int:
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        fields = []
        values = []
        args = []

        if self.project_id is not None:
            fields.append('project_id')
            values.append('?')
            args.append(self.project_id)

        for key, value in kwargs.items():
            fields.append(key)
            args.append(value)
            values.append('?')

        fields = ', '.join(fields)
        values = ', '.join(values)
        self._con.execute(f'INSERT INTO {self.__table_name__} ({fields}) VALUES ({values});', args)
        self._con.commit()
        return self._con.lastrowid

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

        values = []

        if self.project_id is not None:
            values.append(f'project_id = {self.project_id}')

        for key, value in kwargs.items():
            if isinstance(value, (str, float)):
                value = f'"{value}"'
            elif value is None:
                value = 'NULL'

            values.append(f'{key} = {value}')

        if OR:

            values = ' OR '.join(values)
        else:
            values = ' AND '.join(values)

        where = f' WHERE {values}'

        self._con.execute(f'SELECT {args} FROM {self.__table_name__}{where};')
        res = self._con.fetchall()
        return res

    def delete(self, db_id: int) -> None:
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: int
        """
        self._con.execute(f'DELETE FROM {self.__table_name__} WHERE id = {db_id};')
        self._con.commit()

    def update(self, db_id: int, **kwargs):
        """Execute the update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: int
        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        """
        fields = []
        values = []

        for key, value in kwargs.items():
            fields.append(f'{key} = ?')
            values.append(value)

        fields = ', '.join(fields)
        self._con.execute(f'UPDATE {self.__table_name__} SET {fields} WHERE id = {db_id};', values)
        self._con.commit()

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
    def has_points3d(self):
        """Return the has points 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return any([name for name in self.field_names if name.endswith('_point3d_id')])

    @property
    def has_points2d(self):
        """Return the has points 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return any([name for name in self.field_names if name.endswith('_point2d_id')])

    def find_unreferenced_point3d_ids(self, candidate_ids: list[int]) -> list[int]:
        """Find the unreferenced point 3D IDs.

        UNKNOWN details are inferred from the callable name and signature.

        :param candidate_ids: Identifier for the candidate.
        :type candidate_ids: list[int]
        :returns: Return value. UNKNOWN details.
        :rtype: list[int]
        """
        return self._find_unreferenced_point_ids(candidate_ids, '_point3d_id')

    def find_unreferenced_point2d_ids(self, candidate_ids: list[int]) -> list[int]:
        """Find the unreferenced point 2D IDs.

        UNKNOWN details are inferred from the callable name and signature.

        :param candidate_ids: Identifier for the candidate.
        :type candidate_ids: list[int]
        :returns: Return value. UNKNOWN details.
        :rtype: list[int]
        """
        return self._find_unreferenced_point_ids(candidate_ids, '_point2d_id')

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
                    WHERE project_id = ? AND col1 IN (?, ?, ...)
                UNION
                SELECT col2 FROM table
                    WHERE project_id = ? AND col2 IN (?, ?, ...)
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
            return set()

        point_cols = [col for col in self.field_names if col.endswith(suffix)]

        if not point_cols:
            # This table has no relevant columns — pass the set through unchanged
            return candidate_ids

        params = candidate_ids[:]
        placeholders = ','.join('?' * len(params))

        # CTE rows: candidate IDs inlined as literals
        cte_rows = ','.join(f'({p})' for p in params)

        # Each SELECT in the UNION filters by project_id so we only
        # consider rows belonging to the currently open project
        union_parts = [
            f'SELECT {col} AS point_id '
            f'FROM {self.__table_name__} '
            f'WHERE project_id = ? AND {col} IN ({placeholders})'
            for col in point_cols
        ]
        union_sql = ' UNION '.join(union_parts)

        query = (f'WITH candidates(id) AS (VALUES {cte_rows}) '
                 f'SELECT candidates.id '
                 f'FROM candidates '
                 f'LEFT JOIN ({union_sql}) AS referenced '
                 f'ON candidates.id = referenced.point_id '
                 f'WHERE referenced.point_id IS NULL;')

        # One project_id + one copy of params per column in the UNION
        all_params = []
        for _ in point_cols:
            all_params.append(self.project_id)
            all_params.extend(params)

        self._con.execute(query, all_params)

        ret = {row[0] for row in self._con.fetchall() if row[0] is not None}
        return list(ret)

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

    def fetchall(self):
        """Execute the fetchall operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._con.fetchall()

    def fetchone(self):
        """Execute the fetchone operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._con.fetchone()

    def commit(self):
        """Execute the commit operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._con.commit()

    @property
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
from .pjt_pegboard_point import PJTPegboardPointsTable  # NOQA
from .pjt_pegboard_waypoint import PJTPegboardWaypointsTable  # NOQA
from .pjt_pegboard_table import PJTPegboardTablesTable  # NOQA

from .project import ProjectsTable  # NOQA


class PJTTables:
    """Represent a PJT tables in :mod:`harness_designer.database.project_db.pjt_bases`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

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
        self._pjt_pegboard_points_table = None
        self._pjt_pegboard_waypoints_table = None
        self._pjt_pegboard_tables_table = None

        self._points2d = []
        self._points3d = []

        self._current_count = 0

    @property
    def tables(self) -> list[PJTTableBase]:
        """Return the tables.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[PJTTableBase]
        """
        return [getattr(self, name) for name in sorted(list(dir(self)), reverse=True)
                if name.endswith('_table') and not name.startswith('_')]

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
        self._pjt_pegboard_points_table = PJTPegboardPointsTable(self, project_id, tables, Splash)
        self._pjt_pegboard_waypoints_table = PJTPegboardWaypointsTable(self, project_id, tables, Splash)
        self._pjt_pegboard_tables_table = PJTPegboardTablesTable(self, project_id, tables, Splash)

    @property
    def pjt_bundles_table(self) -> PJTBundlesTable:
        """Return the PJT bundles table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundlesTable`
        """
        return self._pjt_bundles_table

    @property
    def pjt_bundle_layouts_table(self) -> PJTBundleLayoutsTable:
        """Return the PJT bundle layouts table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayoutsTable`
        """
        return self._pjt_bundle_layouts_table

    @property
    def pjt_circuits_table(self) -> PJTCircuitsTable:
        """Return the PJT circuits table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTCircuitsTable`
        """
        return self._pjt_circuits_table

    @property
    def pjt_points2d_table(self) -> PJTPoints2DTable:
        """Return the PJT points 2D table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTPoints2DTable`
        """
        return self._pjt_points2d_table

    @property
    def pjt_points3d_table(self) -> PJTPoints3DTable:
        """Return the PJT points 3D table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTPoints3DTable`
        """
        return self._pjt_points3d_table

    @property
    def pjt_housings_table(self) -> PJTHousingsTable:
        """Return the PJT housings table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTHousingsTable`
        """
        return self._pjt_housings_table

    @property
    def pjt_splices_table(self) -> PJTSplicesTable:
        """Return the PJT splices table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTSplicesTable`
        """
        return self._pjt_splices_table

    @property
    def pjt_transitions_table(self) -> PJTTransitionsTable:
        """Return the PJT transitions table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTransitionsTable`
        """
        return self._pjt_transitions_table

    @property
    def pjt_wires_table(self) -> PJTWiresTable:
        """Return the PJT wires table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWiresTable`
        """
        return self._pjt_wires_table

    @property
    def pjt_wire_layouts_table(self) -> PJTWireLayoutsTable:
        """Return the PJT wire layouts table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireLayoutsTable`
        """
        return self._pjt_wire_layouts_table

    @property
    def projects_table(self) -> ProjectsTable:
        """Return the projects table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`ProjectsTable`
        """
        return self._projects_table

    @property
    def pjt_cavities_table(self) -> PJTCavitiesTable:
        """Return the PJT cavities table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTCavitiesTable`
        """
        return self._pjt_cavities_table

    @property
    def pjt_terminals_table(self) -> PJTTerminalsTable:
        """Return the PJT terminals table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTerminalsTable`
        """
        return self._pjt_terminals_table

    @property
    def pjt_seals_table(self) -> PJTSealsTable:
        """Return the PJT seals table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTSealsTable`
        """
        return self._pjt_seals_table

    @property
    def pjt_covers_table(self) -> PJTCoversTable:
        """Return the PJT covers table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTCoversTable`
        """
        return self._pjt_covers_table

    @property
    def pjt_boots_table(self) -> PJTBootsTable:
        """Return the PJT boots table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBootsTable`
        """
        return self._pjt_boots_table

    @property
    def pjt_cpa_locks_table(self) -> PJTCPALocksTable:
        """Return the PJT CPA locks table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTCPALocksTable`
        """
        return self._pjt_cpa_locks_table

    @property
    def pjt_tpa_locks_table(self) -> PJTTPALocksTable:
        """Return the PJT TPA locks table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTPALocksTable`
        """
        return self._pjt_tpa_locks_table

    @property
    def pjt_wire_markers_table(self) -> PJTWireMarkersTable:
        """Return the PJT wire markers table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireMarkersTable`
        """
        return self._pjt_wire_markers_table

    @property
    def pjt_wire_service_loops_table(self) -> PJTWireServiceLoopsTable:
        """Return the PJT wire service loops table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireServiceLoopsTable`
        """
        return self._pjt_wire_service_loops_table

    @property
    def pjt_notes_table(self) -> PJTNotesTable:
        """Return the PJT notes table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTNotesTable`
        """
        return self._pjt_notes_table

    @property
    def pjt_concentrics_table(self) -> PJTConcentricsTable:
        """Return the PJT concentrics table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTConcentricsTable`
        """
        return self._pjt_concentrics_table

    @property
    def pjt_concentric_layers_table(self) -> PJTConcentricLayersTable:
        """Return the PJT concentric layers table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTConcentricLayersTable`
        """
        return self._pjt_concentric_layers_table

    @property
    def pjt_concentric_wires_table(self) -> PJTConcentricWiresTable:
        """Return the PJT concentric wires table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTConcentricWiresTable`
        """
        return self._pjt_concentric_wires_table

    @property
    def pjt_transition_branches_table(self) -> PJTTransitionBranchesTable:
        """Return the PJT transition branches table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTransitionBranchesTable`
        """
        return self._pjt_transition_branches_table

    @property
    def pjt_pegboard_points_table(self) -> PJTPegboardPointsTable:
        """Return the peg-board points overlay table.

        :returns: The peg-board points table for the loaded project.
        :rtype: :class:`PJTPegboardPointsTable`
        """
        return self._pjt_pegboard_points_table

    @property
    def pjt_pegboard_waypoints_table(self) -> PJTPegboardWaypointsTable:
        """Return the peg-board waypoints table.

        :returns: The peg-board waypoints table for the loaded project.
        :rtype: :class:`PJTPegboardWaypointsTable`
        """
        return self._pjt_pegboard_waypoints_table

    @property
    def pjt_pegboard_tables_table(self) -> PJTPegboardTablesTable:
        """Return the peg-board data-table overlay table.

        :returns: The peg-board tables overlay table for the loaded project.
        :rtype: :class:`PJTPegboardTablesTable`
        """
        return self._pjt_pegboard_tables_table
