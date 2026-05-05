from typing import Iterable as _Iterable, TYPE_CHECKING

import weakref

from ... import logger as _logger
from ..common_db import callback as _callback

if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import splash as _splash


class _PJTEntrySingleton(type):
    _instances = {}

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        setattr(cls, '_instances', {})
        cls._instances = {}

    @classmethod
    def __remove_instance_ref(cls, ref):
        for key, value in cls._instances.items():
            if value == ref:
                break
        else:
            return

        del cls._instances[key]

    def __call__(cls, table, db_id: int, project_id: int | None):
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

    def __init__(self, table: "PJTTableBase", db_id: int, project_id: int | None):
        self._table = table
        self._db_id = db_id
        self.project_id = project_id

        self._obj = None
        self._objects = []
        self._treeitem = None
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

    def get_object(self):
        raise NotImplementedError

    def set_object(self, obj):
        raise NotImplementedError

    _selected: bool = False

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, flag: bool):
        self._selected = flag

    @staticmethod
    def merge_packet_data(src: dict, dst: dict):
        for key, values in src.items():
            if key in dst:
                values = [value for value in values if value not in dst[key]]
                dst[key].extend(values)
            else:
                dst[key] = values[:]

    @property
    def db_id(self) -> int:
        return self._db_id

    @property
    def table(self):
        return self._table

    def delete(self) -> None:
        self._table.delete(self.db_id)

        del self.__class__._instances[self.db_id]  # NOQA


class PJTTableBase:
    __table_name__: str = None

    def __init__(self, db: "PJTTables", project_id: int | None, table_names: list['str'], splash: "_splash.Splash"):
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
        if self.__field_names__ is None:
            field_names = list(self._con.get_table_column_names(self.__table_name__))
            if 'id' in field_names:
                field_names.remove('id')

            field_names = sorted(field_names)
            field_names.insert(0, 'id')

            self.__field_names__ = field_names

        return self.__field_names__

    def get_records(self, project_id):
        self.execute(f'SELECT {", ".join(self.field_names)} FROM {self.__table_name__} WHERE project_id={project_id};')
        rows = self.fetchall()
        if rows:
            rows = list(rows)
        else:
            rows = []

        rows.insert(0, tuple(self.field_names))

        return rows

    def set_project(self, project_id: int | None = None):
        self.project_id = project_id

    def _table_needs_update(self) -> bool:
        raise NotImplementedError

    def _add_table_to_db(self):
        raise NotImplementedError

    def _update_table_in_db(self):
        raise NotImplementedError

    def __getitem__(self, item):
        self._con.execute(f'SELECT * FROM {self.__table_name__} WHERE id = {item};')

        for line in self._con.fetchall():
            return line

    def __iter__(self) -> _Iterable[int]:
        if self.project_id is None:
            self._con.execute(f'SELECT id FROM {self.__table_name__};')
        else:
            self._con.execute(f'SELECT id FROM {self.__table_name__} WHERE project_id = {self.project_id};')

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

    @property
    def has_points3d(self):
        return any([name for name in self.field_names if name.endswith('_point3d_id')])

    @property
    def has_points2d(self):
        return any([name for name in self.field_names if name.endswith('_point2d_id')])

    def find_unreferenced_point3d_ids(self, candidate_ids: list[int]) -> list[int]:
        return self._find_unreferenced_point_ids(candidate_ids, '_point3d_id')

    def find_unreferenced_point2d_ids(self, candidate_ids: list[int]) -> list[int]:
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
        if params is None:
            return self._con.execute(cmd)
        else:
            return self._con.execute(cmd, params)

    def fetchall(self):
        return self._con.fetchall()

    def fetchone(self):
        return self._con.fetchone()

    def commit(self):
        self._con.commit()

    @property
    def lastrowid(self):
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

from .project import ProjectsTable  # NOQA


class PJTTables:

    def __init__(self, splash, mainframe: "_ui.MainFrame"):
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

        self._points2d = []
        self._points3d = []

        self._current_count = 0

    @property
    def tables(self) -> list[PJTTableBase]:
        return [getattr(self, name) for name in sorted(list(dir(self)), reverse=True)
                if name.endswith('_table') and not name.startswith('_')]

    def load(self, project_id):
        self.mainframe.unload()
        tables = self.connector.get_tables()

        _logger.logger.database('TABLES:', tables)

        class Splash:

            @staticmethod
            def SetText(msg):
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

    @property
    def pjt_bundles_table(self) -> PJTBundlesTable:
        return self._pjt_bundles_table

    @property
    def pjt_bundle_layouts_table(self) -> PJTBundleLayoutsTable:
        return self._pjt_bundle_layouts_table

    @property
    def pjt_circuits_table(self) -> PJTCircuitsTable:
        return self._pjt_circuits_table

    @property
    def pjt_points2d_table(self) -> PJTPoints2DTable:
        return self._pjt_points2d_table

    @property
    def pjt_points3d_table(self) -> PJTPoints3DTable:
        return self._pjt_points3d_table

    @property
    def pjt_housings_table(self) -> PJTHousingsTable:
        return self._pjt_housings_table

    @property
    def pjt_splices_table(self) -> PJTSplicesTable:
        return self._pjt_splices_table

    @property
    def pjt_transitions_table(self) -> PJTTransitionsTable:
        return self._pjt_transitions_table

    @property
    def pjt_wires_table(self) -> PJTWiresTable:
        return self._pjt_wires_table

    @property
    def pjt_wire_layouts_table(self) -> PJTWireLayoutsTable:
        return self._pjt_wire_layouts_table

    @property
    def projects_table(self) -> ProjectsTable:
        return self._projects_table

    @property
    def pjt_cavities_table(self) -> PJTCavitiesTable:
        return self._pjt_cavities_table

    @property
    def pjt_terminals_table(self) -> PJTTerminalsTable:
        return self._pjt_terminals_table

    @property
    def pjt_seals_table(self) -> PJTSealsTable:
        return self._pjt_seals_table

    @property
    def pjt_covers_table(self) -> PJTCoversTable:
        return self._pjt_covers_table

    @property
    def pjt_boots_table(self) -> PJTBootsTable:
        return self._pjt_boots_table

    @property
    def pjt_cpa_locks_table(self) -> PJTCPALocksTable:
        return self._pjt_cpa_locks_table

    @property
    def pjt_tpa_locks_table(self) -> PJTTPALocksTable:
        return self._pjt_tpa_locks_table

    @property
    def pjt_wire_markers_table(self) -> PJTWireMarkersTable:
        return self._pjt_wire_markers_table

    @property
    def pjt_wire_service_loops_table(self) -> PJTWireServiceLoopsTable:
        return self._pjt_wire_service_loops_table

    @property
    def pjt_notes_table(self) -> PJTNotesTable:
        return self._pjt_notes_table

    @property
    def pjt_concentrics_table(self) -> PJTConcentricsTable:
        return self._pjt_concentrics_table

    @property
    def pjt_concentric_layers_table(self) -> PJTConcentricLayersTable:
        return self._pjt_concentric_layers_table

    @property
    def pjt_concentric_wires_table(self) -> PJTConcentricWiresTable:
        return self._pjt_concentric_wires_table

    @property
    def pjt_transition_branches_table(self) -> PJTTransitionBranchesTable:
        return self._pjt_transition_branches_table
