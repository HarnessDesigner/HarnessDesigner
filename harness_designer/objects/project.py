# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication, QDialog


from ..config import Config as _Config
from . import boot as _boot
from . import bundle as _bundle
from . import bundle_layout as _bundle_layout
from . import circuit as _circuit
from . import cover as _cover
from . import cavity as _cavity
from . import cpa_lock as _cpa_lock
from . import housing as _housing
from . import note as _note
from . import seal as _seal
from . import splice as _splice
from . import terminal as _terminal
from . import tpa_lock as _tpa_lock
from . import transition as _transition
from . import wire as _wire
from . import wire_layout as _wire_layout
from . import wire_marker as _wire_marker
from . import wire_service_loop as _wire_service_loop
from .. import config as _config
from .. import logger as _logger


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import project as _project
    from ..database.global_db import model3d as _model3d


Config = _config.Config.project


class Project:
    """Represent a project in :mod:`harness_designer.objects.project`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def _set_model(self, model3d: "_model3d.Model3D"):
        from ..gl import vbo as _vbo_handler
        import numpy as np
        from . import project_model as _project_model

        uuid = model3d.uuid
        project_obj = self.mainframe.project_db.projects_table[self.project_id]

        self.mainframe.editor3d.context.acquire()
        if uuid in _vbo_handler.PooledVBOHandler:
            vbo = _vbo_handler.PooledVBOHandler(uuid)
        else:
            v_count = model3d.vertex_count
            obb = model3d.obb
            aabb = model3d.aabb
            data_path = model3d.data_path
            packed = np.load(data_path)

            angle = model3d.angle3d
            packed @= angle
            aabb @= angle
            obb @= angle

            vbo = _vbo_handler.PooledVBOHandler(uuid, packed, v_count, aabb, obb)

        self.mainframe.editor3d.context.release()
        self._model = _project_model.ProjectModel(self.mainframe, project_obj, vbo)

    def __init__(self, mainframe: "_ui.MainFrame", db_obj: "_project.Project", project_name: str, project_id: int):
        """Initialise the :class:`Project` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_project.Project`
        :param project_name: Value for ``project_name``.
        :type project_name: str
        :param project_id: Identifier for the project.
        :type project_id: int
        """

        _logger.info(f'project loading - db_id: {project_id}, name: {project_name}')
        self.db_obj = db_obj

        self.mainframe = mainframe
        self.gtables = mainframe.global_db
        self.connector = mainframe.db_connector
        self.project_id = project_id
        self.project_name = project_name
        self.ptables = ptables = mainframe.project_db
        self.mainframe.process_manager.reset()
        ptables.load(project_id)
        mainframe.object_browser.reset()

        project_obj = mainframe.project_db.projects_table[project_id]
        model = project_obj.model
        self._model = None

        if model is not None:
            model.load('project', project_id, self._set_model)

        from ..database.project_db.cleanup import ProjectCleanup

        self.cleanup = ProjectCleanup(self)

        project_tables = [getattr(self.ptables, item) for item in dir(self.ptables) if not item.startswith('_') and item.endswith('_table')]
        global_tables = [getattr(self.gtables, item) for item in dir(self.gtables) if not item.startswith('_') and item.endswith('_table')]

        for table in project_tables + global_tables:
            kwargs = {'type': f'field_names_{table.table_name}', 'data': table.field_names}
            self.mainframe.process_manager.send(**kwargs)

        self._boots = {}
        self._bundles = {}
        self._bundle_layouts = {}
        self._covers = {}
        self._cpa_locks = {}
        self._housings = {}
        self._notes = {}
        self._seals = {}
        self._splices = {}
        self._terminals = {}
        self._tpa_locks = {}
        self._transitions = {}
        self._wires = {}
        self._wire_markers = {}
        self._wire_service_loops = {}
        self._wire_layouts = {}
        self._circuits = {}
        self._cavities = {}

        self._obj_count = mainframe.project_db.projects_table.get_object_count(project_id)

        mainframe.start_progress('Loading Project...', self._obj_count)

        db_ids = {}
        count = 0

        def _load_objects(table_, label, obj_cls, ids_, container,
                          add_func, cur_count, max_count):
            # helper function for loading a project

            for db_obj_ in table_:
                cur_count += 1
                if cur_count < max_count:
                    mainframe.set_progress(cur_count, f'Loading {label}...')
                else:
                    mainframe.set_progress(max_count - 1, f'Loading {label}...')

                gui_obj = obj_cls(mainframe, db_obj_, project_load=True)
                db_obj_.merge_packet_data(db_obj_.build_monitor_packet(), ids_)
                container[db_obj_.db_id] = gui_obj

                if add_func is not None:
                    add_func(gui_obj)

                _logger.info(f'{label} Loaded - db_id: {db_obj_.db_id}')

            return cur_count

        count = _load_objects(
            ptables.pjt_notes_table, 'Note',
            _note.Note, db_ids, self._notes,
            mainframe.object_browser.add_note, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_circuits_table, 'Circuit',
            _circuit.Circuit, db_ids, self._circuits,
            mainframe.object_browser.add_circuit, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_housings_table, 'Housing',
            _housing.Housing, db_ids, self._housings,
            mainframe.object_browser.add_housing, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_covers_table, 'Cover',
            _cover.Cover, db_ids, self._covers,
            mainframe.object_browser.add_cover, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_cpa_locks_table, 'CPA Lock',
            _cpa_lock.CPALock, db_ids, self._cpa_locks,
            mainframe.object_browser.add_cpa_lock, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_tpa_locks_table, 'TPA Lock',
            _tpa_lock.TPALock, db_ids, self._tpa_locks,
            mainframe.object_browser.add_tpa_lock, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_boots_table, 'Boot',
            _boot.Boot, db_ids, self._boots,
            mainframe.object_browser.add_boot, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_cavities_table, 'Cavity',
            _cavity.Cavity, db_ids, self._cavities,
            mainframe.object_browser.add_cavity, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_terminals_table, 'Terminal',
            _terminal.Terminal, db_ids, self._terminals,
            mainframe.object_browser.add_terminal, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_seals_table, 'Seal',
            _seal.Seal, db_ids, self._seals,
            mainframe.object_browser.add_seal,
            count, self._obj_count)

        for housing in self._housings.values():
            housing.obj3d.match_cavity_surfaces()

        count = _load_objects(
            ptables.pjt_wires_table, 'Wire',
            _wire.Wire, db_ids, self._wires,
            mainframe.object_browser.add_wire, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_wire_service_loops_table, 'Wire Service Loop',
            _wire_service_loop.WireServiceLoop, db_ids, self._wire_service_loops,
            mainframe.object_browser.add_wire_service_loop, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_wire_markers_table, 'Wire Marker',
            _wire_marker.WireMarker, db_ids, self._wire_markers,
            mainframe.object_browser.add_wire_marker, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_wire_layouts_table, 'Wire Layout',
            _wire_layout.WireLayout, db_ids, self._wire_layouts,
            None, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_splices_table, 'Splice',
            _splice.Splice, db_ids, self._splices,
            mainframe.object_browser.add_splice, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_bundles_table, 'Bundle',
            _bundle.Bundle, db_ids, self._bundles,
            mainframe.object_browser.add_bundle, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_bundle_layouts_table, 'Bundle Layout',
            _bundle_layout.BundleLayout, db_ids, self._bundle_layouts,
            None, count, self._obj_count)

        count = _load_objects(
            ptables.pjt_transitions_table, 'Transition',
            _transition.Transition, db_ids, self._transitions,
            mainframe.object_browser.add_transition, count, self._obj_count)



        mainframe.set_progress(self._obj_count, 'DONE!')

        if self._obj_count != count:
            _logger.warning(
                f'project object count inconsistant, correcting mismatch. '
                f'stored count: {self._obj_count}  actual count: {count}')

        self._obj_count = count
        self.obj_count = count

        _logger.info(f'project loaded: object count: {count}')

        for table_name, ids in db_ids.items():
            while None in ids:
                ids.remove(None)

            kwargs = {'type': f'add_{table_name}', 'data': ids}
            self.mainframe.process_manager.send(**kwargs)

    def update_objects(self, table_name, db_id):
        """Update the objects.

        UNKNOWN details are inferred from the callable name and signature.

        :param table_name: Value for ``table_name``.
        :type table_name: UNKNOWN
        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        # TODO: Add updating objects from subprocess
        pass

    @property
    def obj_count(self) -> int:
        """Return the obj count.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._obj_count

    @obj_count.setter
    def obj_count(self, value: int):
        """Set the obj count.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._obj_count = value
        self.ptables.projects_table.set_object_count(self.project_id, value)

    @classmethod
    def select_project(cls, mainframe: "_ui.MainFrame") -> "Project":
        """Execute the select project operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Project`
        """
        from ..ui.dialogs.project_dialog import OpenProjectDialog

        connector = mainframe.db_connector

        project_names = []

        connector.execute(f'SELECT name FROM projects;')
        for name in connector.fetchall():
            project_names.append(name[0])

        dlg = OpenProjectDialog(mainframe, Config.last_project, project_names)
        try:
            res = dlg.exec()
            if res != QDialog.DialogCode.Rejected:
                project_name = dlg.GetValue()
            else:
                return
        finally:
            dlg.deleteLater()
        connector.execute(f'SELECT id FROM projects WHERE name = "{project_name}";')
        res = connector.fetchall()

        if res:
            project_id = res[0][0]
        else:
            from ..ui.dialogs import add_project as _add_project

            dlg = _add_project.AddProjectDialog(mainframe, project_name, mainframe.project_db.projects_table)
            if dlg.exec() == QDialog.DialogCode.Accepted:

                project_name, creator, description, model_path, color_id = dlg.GetValue()

                if model_path:
                    connector.execute(
                        f'INSERT INTO models3d (path) VALUES (?);', (model_path,))
                    connector.commit()
                    model_id = connector.lastrowid
                else:
                    model_id = None

                connector.execute(f'INSERT INTO projects (name, creator, description, model_id, color_id) VALUES (?, ?, ?, ?, ?);',
                                  (project_name, creator, description, model_id, color_id))
                connector.commit()
                project_id = connector.lastrowid
            else:
                return cls.select_project(mainframe)

        db_obj = mainframe.project_db.projects_table[project_id]

        Config.last_project = project_name

        return cls(mainframe, db_obj, project_name, project_id)

    def delete_note(self, db_id):
        """Delete the note.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        note = self._notes.pop(db_id)
        note.delete()
        self.obj_count -= 1

    def add_note(self, obj: _note.Note) -> None:
        """Add a note.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_note.Note`
        """
        self._notes[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_note(self, db_id) -> _note.Note:
        """Return the note.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_note.Note`
        """
        db_obj = self.ptables.pjt_notes_table[db_id]
        return db_obj.get_object()

    @property
    def notes(self) -> list[_note.Note]:
        """Return the notes.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_note.Note]
        """
        return list(self._notes.values())

    def delete_seal(self, db_id):
        """Delete the seal.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._seals.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_seal(self, obj: _seal.Seal) -> None:
        """Add a seal.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_seal.Seal`
        """
        self._seals[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_seal(self, db_id) -> _seal.Seal:
        """Return the seal.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_seal.Seal`
        """
        db_obj = self.ptables.pjt_seals_table[db_id]
        return db_obj.get_object()

    @property
    def seals(self) -> list[_seal.Seal]:
        """Return the seals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_seal.Seal]
        """
        return list(self._seals.values())

    def delete_terminal(self, db_id):
        """Delete the terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        terminal = self._terminals.pop(db_id)
        terminal.delete()
        self.obj_count -= 1

    def add_terminal(self, obj: _terminal.Terminal) -> None:
        """Add a terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_terminal.Terminal`
        """
        self._terminals[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_terminal(self, db_id) -> _terminal.Terminal:
        """Return the terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_terminal.Terminal`
        """
        db_obj = self.ptables.pjt_terminals_table[db_id]
        return db_obj.get_object()

    @property
    def terminals(self) -> list[_terminal.Terminal]:
        """Return the terminals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_terminal.Terminal]
        """
        return list(self._terminals.values())

    def delete_cavity(self, db_id):
        """Delete the cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._cavities.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_cavity(self, obj: _cavity.Cavity) -> None:
        """Add a cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cavity.Cavity`
        """
        self._cavities[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_cavity(self, db_id) -> _cavity.Cavity:
        """Return the cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_cavity.Cavity`
        """
        db_obj = self.ptables.pjt_cavities_table[db_id]
        return db_obj.get_object()

    @property
    def cavities(self) -> list[_cavity.Cavity]:
        """Return the cavities.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_cavity.Cavity]
        """
        return list(self._cavities.values())

    def delete_tpa_lock(self, db_id):
        """Delete the TPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._tpa_locks.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_tpa_lock(self, obj: _tpa_lock.TPALock) -> None:
        """Add a TPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_tpa_lock.TPALock`
        """
        self._tpa_locks[obj.db_obj.db_id] = obj
        self.obj_count += 1
        return obj

    def get_tpa_lock(self, db_id) -> _tpa_lock.TPALock:
        """Return the TPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_tpa_lock.TPALock`
        """
        db_obj = self.ptables.pjt_tpa_locks_table[db_id]
        return db_obj.get_object()

    @property
    def tpa_locks(self) -> list[_tpa_lock.TPALock]:
        """Return the TPA locks.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_tpa_lock.TPALock]
        """
        return list(self._tpa_locks.values())

    def delete_wire_marker(self, db_id):
        """Delete the wire marker.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._wire_markers.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire_marker(self, obj: _wire_marker.WireMarker) -> None:
        """Add a wire marker.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_marker.WireMarker`
        """
        self._wire_markers[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_wire_marker(self, db_id) -> _wire_marker.WireMarker:
        """Return the wire marker.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_wire_marker.WireMarker`
        """
        db_obj = self.ptables.pjt_wire_markers_table[db_id]
        return db_obj.get_object()

    @property
    def wire_markers(self) -> list[_wire_marker.WireMarker]:
        """Return the wire markers.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_wire_marker.WireMarker]
        """
        return list(self._wire_markers.values())

    def delete_wire_service_loop(self, db_id):
        """Delete the wire service loop.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._wire_service_loops.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire_service_loop(self, obj: _wire_service_loop.WireServiceLoop) -> None:
        """Add a wire service loop.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_service_loop.WireServiceLoop`
        """
        self._wire_service_loops[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_wire_service_loop(self, db_id) -> _wire_service_loop.WireServiceLoop:
        """Return the wire service loop.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_wire_service_loop.WireServiceLoop`
        """
        db_obj = self.ptables.pjt_wire_service_loops_table[db_id]
        return db_obj.get_object()

    @property
    def wire_service_loops(self) -> list[_wire_service_loop.WireServiceLoop]:
        """Return the wire service loops.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_wire_service_loop.WireServiceLoop]
        """
        return list(self._wire_service_loops.values())

    @property
    def circuits(self) -> list[_circuit.Circuit]:
        """Return the circuits.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_circuit.Circuit]
        """
        return list(self._circuits.values())

    def delete_cpa_lock(self, db_id):
        """Delete the CPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._cpa_locks.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_cpa_lock(self, obj: _cpa_lock.CPALock) -> None:
        """Add a CPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cpa_lock.CPALock`
        """
        self._cpa_locks[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_cpa_lock(self, db_id) -> _cpa_lock.CPALock:
        """Return the CPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_cpa_lock.CPALock`
        """
        db_obj = self.ptables.pjt_cpa_locks_table[db_id]
        return db_obj.get_object()

    @property
    def cpa_locks(self) -> list[_cpa_lock.CPALock]:
        """Return the CPA locks.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_cpa_lock.CPALock]
        """
        return list(self._cpa_locks.values())

    def delete_cover(self, db_id):
        """Delete the cover.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._covers.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_cover(self, obj: _cover.Cover) -> None:
        """Add a cover.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cover.Cover`
        """
        self._covers[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_cover(self, db_id) -> _cover.Cover:
        """Return the cover.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_cover.Cover`
        """
        db_obj = self.ptables.pjt_covers_table[db_id]
        return db_obj.get_object()

    @property
    def covers(self) -> list[_cover.Cover]:
        """Return the covers.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_cover.Cover]
        """
        return list(self._covers.values())

    def delete_boot(self, db_id):
        """Delete the boot.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._boots.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_boot(self, obj: _boot.Boot) -> None:
        """Add a boot.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_boot.Boot`
        """
        self._boots[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_boot(self, db_id) -> _boot.Boot:
        """Return the boot.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_boot.Boot`
        """
        db_obj = self.ptables.pjt_boots_table[db_id]
        return db_obj.get_object()

    @property
    def boots(self) -> list[_boot.Boot]:
        """Return the boots.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_boot.Boot]
        """
        return list(self._boots.values())

    def delete_transition(self, db_id):
        """Delete the transition.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._transitions.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_transition(self, obj: _transition.Transition) -> None:
        """Add a transition.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_transition.Transition`
        """
        self._transitions[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_transition(self, db_id) -> _transition.Transition:
        """Return the transition.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_transition.Transition`
        """
        db_obj = self.ptables.pjt_transitions_table[db_id]
        return db_obj.get_object()

    @property
    def transitions(self) -> list[_transition.Transition]:
        """Return the transitions.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_transition.Transition]
        """
        return list(self._transitions.values())

    def delete_housing(self, db_id):
        """Delete the housing.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        housing = self._housings.pop(db_id)
        housing.delete()
        self.obj_count -= 1

    def add_housing(self, obj: _housing.Housing) -> None:
        """Add a housing.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_housing.Housing`
        """
        self._housings[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_housing(self, db_id) -> _housing.Housing:
        """Return the housing.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_housing.Housing`
        """
        db_obj = self.ptables.pjt_housings_table[db_id]
        return db_obj.get_object()

    @property
    def housings(self) -> list[_housing.Housing]:
        """Return the housings.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_housing.Housing]
        """
        return list(self._housings.values())

    def delete_splice(self, db_id):
        """Delete the splice.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._splices.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_splice(self, obj: _splice.Splice) -> None:
        """Add a splice.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_splice.Splice`
        """
        self._splices[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_splice(self, db_id) -> _splice.Splice:
        """Return the splice.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_splice.Splice`
        """
        db_obj = self.ptables.pjt_splices_table[db_id]
        return db_obj.get_object()

    @property
    def splices(self) -> list[_splice.Splice]:
        """Return the splices.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_splice.Splice]
        """
        return list(self._splices.values())

    def delete_wire(self, db_id):
        """Delete the wire.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._wires.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire(self, obj: _wire.Wire) -> None:
        """Add a wire.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire.Wire`
        """
        self._wires[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_wire(self, db_id) -> _wire.Wire:
        """Return the wire.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_wire.Wire`
        """
        db_obj = self.ptables.pjt_wires_table[db_id]
        return db_obj.get_object()

    @property
    def wires(self) -> list[_wire.Wire]:
        """Return the wires.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_wire.Wire]
        """
        return list(self._wires.values())

    def delete_wire_layout(self, db_id):
        """Delete the wire layout.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._wire_layouts.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire_layout(self, obj: _wire_layout.WireLayout) -> None:
        """Add a wire layout.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_layout.WireLayout`
        """
        self._wire_layouts[obj.db_obj.db_id] = obj
        self.obj_count += 1

    @property
    def wire_layouts(self) -> list[_wire_layout.WireLayout]:
        """Return the wire layouts.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_wire_layout.WireLayout]
        """
        return list(self._wire_layouts.values())

    def delete_bundle(self, db_id):
        """Delete the bundle.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._bundles.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_bundle(self, obj: _bundle.Bundle) -> None:
        """Add a bundle.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_bundle.Bundle`
        """
        self._bundles[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_bundle(self, db_id) -> _bundle.Bundle:
        """Return the bundle.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_bundle.Bundle`
        """
        db_obj = self.ptables.pjt_bundles_table[db_id]
        return db_obj.get_object()

    @property
    def bundles(self) -> list[_bundle.Bundle]:
        """Return the bundles.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_bundle.Bundle]
        """
        return list(self._bundles.values())

    def delete_bundle_layout(self, db_id):
        """Delete the bundle layout.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        seal = self._bundle_layouts.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_bundle_layout(self, obj: _bundle_layout.BundleLayout) -> None:
        """Add a bundle layout.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_bundle_layout.BundleLayout`
        """
        self._bundle_layouts[obj.db_obj.db_id] = obj
        self.obj_count += 1

    def get_bundle_layout(self, db_id) -> _bundle_layout.BundleLayout:
        """Return the bundle layout.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_bundle_layout.BundleLayout`
        """
        db_obj = self.ptables.pjt_bundle_layouts_table[db_id]
        return db_obj.get_object()

    @property
    def bundle_layouts(self) -> list[_bundle_layout.BundleLayout]:
        """Return the bundle layouts.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[_bundle_layout.BundleLayout]
        """
        return list(self._bundle_layouts.values())
