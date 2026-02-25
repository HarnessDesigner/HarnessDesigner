from typing import Iterable as _Iterable, TYPE_CHECKING

import weakref

if TYPE_CHECKING:
    from ... import ui as _ui


class _PJTEntrySingleton(type):
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

    def __call__(cls, table, db_id: int, project_id: int):
        key = (project_id, db_id)

        if key in cls._instances:
            ref = cls._instances[key]
            instance = ref()
        else:
            instance = None

        if instance is None:
            instance = super().__call__(table, db_id, project_id)
            cls._instances[key] = weakref.ref(instance, cls.__remove_ref)

        return instance


class PJTEntryBase(metaclass=_PJTEntrySingleton):

    def __init__(self, table: "PJTTableBase", db_id: int, project_id: int):
        self._table = table
        self._db_id = db_id
        self.project_id = project_id
        self.__callbacks = []
        self.__stop_callbacks = 0

    def __enter__(self):
        self.__stop_callbacks += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__stop_callbacks -= 1
        self._process_callbacks()

    def __remove_ref(self, ref):
        try:
            self.__callbacks.remove(ref)
        except ValueError:
            pass

    _selected: bool = False

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, flag: bool):
        self._selected = flag
        self._process_callbacks()

    def Bind(self, callback):
        for ref in self.__callbacks[:]:
            cb = ref()
            if cb is None:
                try:
                    self.__callbacks.remove(ref)
                except ValueError:
                    pass

            elif cb == callback:
                return
        else:
            self.__callbacks.append(weakref.ref(callback, self.__remove_ref))

    def Unbind(self, callback):
        for ref in self.__callbacks[:]:
            cb = ref()
            if cb is None:
                try:
                    self.__callbacks.remove(ref)
                except ValueError:
                    pass
            elif cb == callback:
                self.__callbacks.remove(ref)
                return

    def _process_callbacks(self):
        if self.__stop_callbacks > 0:
            return

        for ref in self.__callbacks[:]:
            cb = ref()
            if cb is None:
                try:
                    self.__callbacks.remove(ref)
                except ValueError:
                    pass

                continue

            cb(self)

    @property
    def db_id(self) -> int:
        return self._db_id

    @property
    def table(self):
        return self._table

    def delete(self) -> None:
        self._table.delete(self.db_id)

        del self.__class__._instances[self.db_id]  # NOQA

        self._process_callbacks()


class PJTTableBase:
    __table_name__: str = None

    def __init__(self, db: "PJTTables", project_id: int | None = None):
        self.db = db
        self._con = db.connector

        self.project_id = project_id

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

    def execute(self, cmd, params=None):
        if params is None:
            self._con.execute(cmd)
        else:
            self._con.execute(cmd, params)

    def fetchall(self):
        return self._con.fetchall()


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

        from ..setup_db import create_tables

        tables = self.connector.get_tables()

        for table_name, func in create_tables.project_table_mapping():
            if table_name not in tables:
                splash.SetText(f'Creating database table {table_name}...')
                func(self.connector, self.connector)

        self._projects_table = ProjectsTable(self)

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

    def load(self, project_id):
        self.mainframe.unload()

        self._current_count = 0

        self._pjt_bundles_table = PJTBundlesTable(self, project_id)
        self._pjt_bundle_layouts_table = PJTBundleLayoutsTable(self, project_id)
        self._pjt_circuits_table = PJTCircuitsTable(self, project_id)
        self._pjt_points2d_table = PJTPoints2DTable(self, project_id)
        self._pjt_points3d_table = PJTPoints3DTable(self, project_id)
        self._pjt_housings_table = PJTHousingsTable(self, project_id)
        self._pjt_splices_table = PJTSplicesTable(self, project_id)
        self._pjt_transitions_table = PJTTransitionsTable(self, project_id)
        self._pjt_wires_table = PJTWiresTable(self, project_id)
        self._pjt_wire_layouts_table = PJTWireLayoutsTable(self, project_id)
        self._pjt_cavities_table = PJTCavitiesTable(self, project_id)
        self._pjt_terminals_table = PJTTerminalsTable(self, project_id)
        self._pjt_seals_table = PJTSealsTable(self, project_id)
        self._pjt_covers_table = PJTCoversTable(self, project_id)
        self._pjt_boots_table = PJTBootsTable(self, project_id)
        self._pjt_cpa_locks_table = PJTCPALocksTable(self, project_id)
        self._pjt_tpa_locks_table = PJTTPALocksTable(self, project_id)
        self._pjt_wire_markers_table = PJTWireMarkersTable(self, project_id)
        self._pjt_wire_service_loops_table = PJTWireServiceLoopsTable(self, project_id)
        self._pjt_notes_table = PJTNotesTable(self, project_id)
        self._pjt_concentrics_table = PJTConcentricsTable(self, project_id)
        self._pjt_concentric_layers_table = PJTConcentricLayersTable(self, project_id)
        self._pjt_concentric_wires_table = PJTConcentricWiresTable(self, project_id)
        self._pjt_transition_branches_table = PJTTransitionBranchesTable(self, project_id)

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
    def pjt_wire3d_layouts_table(self) -> PJTWireLayoutsTable:
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
