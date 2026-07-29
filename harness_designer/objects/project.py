# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets
import time
import weakref as _weakref

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
from .objects3d.wire import _HELIX_OVERSHOOT_MM  # NOQA
from . import wire_layout as _wire_layout
from . import wire_marker as _wire_marker
from . import wire_service_loop as _wire_service_loop
from .. import config as _config
from .. import logger as _logger
from ..shapes import helix as _helix


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import project as _project
    from ..database.global_db import model3d as _model3d


Config = _config.Config.project


def _reconcile_wire_sibling_graph(project: "Project") -> None:
    """Rebuild the in-memory sibling graph (Wire <-> Terminal/Splice/
    WireServiceLoop) from persisted point-id matches.

    set_sibling/add_wire/set_siblings only ever build weakref bookkeeping
    in memory -- nothing about the graph itself is a DB column (a wire's
    own start/stop point ids already encode it; see
    objects.wire.Wire.set_sibling) -- so a freshly reloaded project has
    none of it until this runs once, after every Terminal/Wire/
    WireServiceLoop/Splice for the project already exists (see
    Project.load_project's own load order, which loads Splice last of
    the four for exactly this reason).

    Reaches directly into each object's own sibling-tracking attributes
    (_wire_refs, _start_sibling_ref, etc.) rather than through add_wire()/
    set_siblings() themselves -- those also perform the DB-mutation side
    of a *fresh* attach (routing waypoints, cross-section checks) that a
    reload must never redo; only the in-memory bookkeeping needs
    rebuilding here, from geometry already persisted.
    """
    for wire in project.wires:
        start_id = wire.db_obj.start_position3d_id
        stop_id = wire.db_obj.stop_position3d_id

        for terminal in project.terminals:
            attach_id = terminal.db_obj.attach_point3d_id_raw
            if attach_id is None:
                continue
            if attach_id == start_id:
                wire.set_sibling(terminal, 'start')
                terminal._wire_refs.append(_weakref.ref(wire))  # NOQA
            if attach_id == stop_id:
                wire.set_sibling(terminal, 'stop')
                terminal._wire_refs.append(_weakref.ref(wire))  # NOQA

        for splice in project.splices:
            sdb = splice.db_obj
            if sdb.start_position3d_id == start_id:
                wire.set_sibling(splice, 'start')
                splice._start_sibling_ref = _weakref.ref(wire)  # NOQA
            if sdb.start_position3d_id == stop_id:
                wire.set_sibling(splice, 'stop')
                splice._start_sibling_ref = _weakref.ref(wire)  # NOQA
            if sdb.stop_position3d_id == start_id:
                wire.set_sibling(splice, 'start')
                splice._stop_sibling_ref = _weakref.ref(wire)  # NOQA
            if sdb.stop_position3d_id == stop_id:
                wire.set_sibling(splice, 'stop')
                splice._stop_sibling_ref = _weakref.ref(wire)  # NOQA
            if sdb.branch_position3d_id == start_id:
                wire.set_sibling(splice, 'start')
                splice._branch_wire_refs.append(_weakref.ref(wire))  # NOQA
            if sdb.branch_position3d_id == stop_id:
                wire.set_sibling(splice, 'stop')
                splice._branch_wire_refs.append(_weakref.ref(wire))  # NOQA

        for loop in project.wire_service_loops:
            ldb = loop.db_obj
            if ldb.start_position3d_id == start_id:
                wire.set_sibling(loop, 'start')
                loop._start_sibling_ref = _weakref.ref(wire)  # NOQA
            if ldb.start_position3d_id == stop_id:
                wire.set_sibling(loop, 'stop')
                loop._start_sibling_ref = _weakref.ref(wire)  # NOQA
            if ldb.stop_position3d_id == start_id:
                wire.set_sibling(loop, 'start')
                loop._stop_sibling_ref = _weakref.ref(wire)  # NOQA
            if ldb.stop_position3d_id == stop_id:
                wire.set_sibling(loop, 'stop')
                loop._stop_sibling_ref = _weakref.ref(wire)  # NOQA


def _reconcile_bundle_sibling_graph(project: "Project") -> None:
    """Rebuild the in-memory sibling graph (Bundle <-> Transition) from
    persisted point-id matches, mirroring _reconcile_wire_sibling_graph
    above -- see objects.bundle.Bundle.set_sibling and
    objects.transition.Transition.add_bundle for why none of this is a
    DB column needing no reconciliation in the first place.

    Reaches directly into Transition._bundle_refs rather than through
    add_bundle() itself -- that call also performs the DB-mutation side
    of a *fresh* attach (nothing here, today, but see add_bundle's own
    docstring), which a reload must never redo; only the in-memory
    bookkeeping needs rebuilding here, from geometry already persisted.
    """
    for bundle in project.bundles:
        bdb = bundle.db_obj
        start_id = bdb.start_position3d_id
        stop_id = bdb.stop_position3d_id

        for transition in project.transitions:
            for branch_id in range(1, 7):
                branch = getattr(transition.db_obj, f'branch{branch_id}')
                if branch is None:
                    continue

                branch_point_id = branch.position3d_id
                if branch_point_id == start_id:
                    bundle.set_sibling(transition, 'start')
                    transition._bundle_refs[branch_id] = _weakref.ref(bundle)  # NOQA
                if branch_point_id == stop_id:
                    bundle.set_sibling(transition, 'stop')
                    transition._bundle_refs[branch_id] = _weakref.ref(bundle)  # NOQA


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

        # Every state an object might reflexively read via mainframe.project
        # during its own construction below (db_obj, ptables, the container
        # dicts) is already set at this point -- assign it now, before any
        # object loads, instead of waiting for this constructor to return.
        # Objects loaded further down (e.g. Wire, whose stripe-VBO seeding
        # reads mainframe.project.db_obj.wire_stripe_max_length) run inside
        # this same call stack, and mainframe.project's getter re-enters
        # _open_project() -- re-showing the open-project dialog -- for as
        # long as it's still None.
        mainframe.project = self

        db_ids = {}
        count = 0

        # Build the shared wire-stripe helix mesh at the project's last
        # known max wire-segment length *before* any Wire loads, so it
        # never needs to grow (and re-upload its VBO) more than once per
        # session even if this project has hundreds of wires -- see
        # shapes.helix.create_vbo and objects3d.wire.WireStripe. Padded by
        # the same _HELIX_OVERSHOOT_MM headroom WireStripe._ensure_stripe_capacity
        # builds in when it grows the mesh mid-session -- otherwise the
        # very first live drag/preview after loading would immediately
        # trigger a regrow. VBO creation requires an acquired GL context,
        # same as every other VBO-creating call site (e.g. Wire.__init__).
        mainframe.editor3d.context.acquire()
        # we have to store the VBO in a variable this way it doesn't get GC'd
        # If we store it as a variable name that goes unusedCython may throw a
        # a warning for it.
        _ = _helix.create_vbo(db_obj.wire_stripe_max_length + _HELIX_OVERSHOOT_MM)
        mainframe.editor3d.context.release()

        def _load_objects(table_, label, obj_cls, ids_, container,
                          cur_count, max_count):
            # helper function for loading a project
            # note: the object browser tree is populated by
            # mainframe.add_object -- every wrapper's __init__ calls it
            # unconditionally (project_load or not), so there is no
            # separate add-to-browser step here.

            for db_obj_ in table_:
                cur_count += 1
                if cur_count < max_count:
                    mainframe.set_progress(cur_count, f'Loading {label}...')
                else:
                    mainframe.set_progress(max_count - 1, f'Loading {label}...')

                gui_obj = obj_cls(mainframe, db_obj_, project_load=True)
                db_obj_.merge_packet_data(db_obj_.build_monitor_packet(), ids_)
                container[db_obj_.db_id] = gui_obj

                _logger.info(f'{label} Loaded - db_id: {db_obj_.db_id}')

            return cur_count

        start_time = time.time()
        count = _load_objects(
            ptables.pjt_notes_table, 'Note',
            _note.Note, db_ids, self._notes,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_circuits_table, 'Circuit',
            _circuit.Circuit, db_ids, self._circuits,
            count, self._obj_count)

        # Loaded before housings: a housing whose model is already cached
        # from a prior session runs its Model3D.load() callback (_set_model,
        # ending in match_cavity_surfaces()) synchronously, during its own
        # construction below -- match_cavity_surfaces() needs this housing's
        # cavities to already exist (Cavity.get_object() resolving to real
        # wrapper objects) or it leaves every cavity's surf_idx/
        # wire_surf_idx unset, permanently unclickable for the rest of the
        # session (it's a one-shot callback, never reruns on its own).
        # Cavity construction has no dependency on the housing wrapper
        # existing yet -- it only reads its own pjt_cavities row, whose
        # position3d/angle3d/obb/aabb were already fully computed and
        # persisted at insert time.
        count = _load_objects(
            ptables.pjt_cavities_table, 'Cavity',
            _cavity.Cavity, db_ids, self._cavities,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_housings_table, 'Housing',
            _housing.Housing, db_ids, self._housings,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_covers_table, 'Cover',
            _cover.Cover, db_ids, self._covers,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_cpa_locks_table, 'CPA Lock',
            _cpa_lock.CPALock, db_ids, self._cpa_locks,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_tpa_locks_table, 'TPA Lock',
            _tpa_lock.TPALock, db_ids, self._tpa_locks,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_boots_table, 'Boot',
            _boot.Boot, db_ids, self._boots,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_terminals_table, 'Terminal',
            _terminal.Terminal, db_ids, self._terminals,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_seals_table, 'Seal',
            _seal.Seal, db_ids, self._seals,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_wires_table, 'Wire',
            _wire.Wire, db_ids, self._wires,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_wire_service_loops_table, 'Wire Service Loop',
            _wire_service_loop.WireServiceLoop, db_ids, self._wire_service_loops,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_wire_markers_table, 'Wire Marker',
            _wire_marker.WireMarker, db_ids, self._wire_markers,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_wire_layouts_table, 'Wire Layout',
            _wire_layout.WireLayout, db_ids, self._wire_layouts,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_splices_table, 'Splice',
            _splice.Splice, db_ids, self._splices,
            count, self._obj_count)

        # Terminal/Wire/WireServiceLoop/Splice all exist by now -- rebuild
        # the in-memory sibling graph between them from persisted point-id
        # matches (set_sibling/add_wire's own bookkeeping is weakrefs only,
        # nothing DB-persisted -- see objects.wire.Wire.set_sibling).
        _reconcile_wire_sibling_graph(self)

        count = _load_objects(
            ptables.pjt_bundles_table, 'Bundle',
            _bundle.Bundle, db_ids, self._bundles,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_bundle_layouts_table, 'Bundle Layout',
            _bundle_layout.BundleLayout, db_ids, self._bundle_layouts,
            count, self._obj_count)

        count = _load_objects(
            ptables.pjt_transitions_table, 'Transition',
            _transition.Transition, db_ids, self._transitions,
            count, self._obj_count)

        # Bundle/Transition both exist by now -- rebuild the in-memory
        # sibling graph between them from persisted point-id matches
        # (see _reconcile_wire_sibling_graph above for why this is a
        # from-scratch rebuild rather than something reload can skip).
        _reconcile_bundle_sibling_graph(self)

        stop_time = time.time()

        duration = (stop_time - start_time)
        _logger.info('Project Load Time:', round(duration, 2), 'secs')
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

    def close(self):
        """Drop every reference this project holds to its own registered
        objects, without touching the database or calling any object's
        own ``delete()``.

        Used when switching to a different project while the app is
        running -- see :meth:`harness_designer.ui.mainframe.MainFrame.
        unload`, the only caller, which clears every *other* place that
        holds a reference to these same objects (the three canvases, the
        object browser, the object editor dock, the current selection)
        before calling this. Once nothing referencing them is left, normal
        GC/weakref teardown releases their pooled VBOs back to the pool
        (see ``gl.vbo.VBOSingleton._remove_ref``) -- nothing here needs to
        touch a VBO directly.
        """
        self._boots.clear()
        self._bundles.clear()
        self._bundle_layouts.clear()
        self._covers.clear()
        self._cpa_locks.clear()
        self._housings.clear()
        self._notes.clear()
        self._seals.clear()
        self._splices.clear()
        self._terminals.clear()
        self._tpa_locks.clear()
        self._transitions.clear()
        self._wires.clear()
        self._wire_markers.clear()
        self._wire_service_loops.clear()
        self._wire_layouts.clear()
        self._circuits.clear()
        self._cavities.clear()
        self._model = None

    def delete(self):
        """Delete every object in the project, then the project's own row.

        Project has no obj2d/obj3d/objpeg of its own, so unlike a normal
        ObjectBase there is no single view-teardown hook to lean on --
        this walks every part-type registry directly instead, calling
        each object's own ``delete()`` (the object is the entry point for
        a delete, not project.delete_<type> -- those only pop the
        registry now). Housings first: Housing.delete() cascades to its
        cavities, each cavity's seated terminal and seal, its own seal,
        its CPA lock, both TPA locks, its cover, and its boot -- each via
        that child's own delete(), which pops itself out of the matching
        registry -- so by the time the terminals sweep below runs, only
        bare terminals (never seated in a cavity) are left in
        ``self._terminals``.
        """
        for obj in list(self._housings.values()):
            obj.delete()

        for obj in list(self._terminals.values()):
            obj.delete()

        for obj in list(self._transitions.values()):
            obj.delete()

        for obj in list(self._splices.values()):
            obj.delete()

        for obj in list(self._bundles.values()):
            obj.delete()

        for obj in list(self._bundle_layouts.values()):
            obj.delete()

        for obj in list(self._wire_layouts.values()):
            obj.delete()

        for obj in list(self._wire_service_loops.values()):
            obj.delete()

        for obj in list(self._wire_markers.values()):
            obj.delete()

        for obj in list(self._wires.values()):
            obj.delete()

        for obj in list(self._notes.values()):
            obj.delete()

        self.db_obj.delete()

    @property
    def wire_stripe_max_length(self) -> float:
        return self.db_obj.wire_stripe_max_length

    @wire_stripe_max_length.setter
    def wire_stripe_max_length(self, value: float):
        self.db_obj.wire_stripe_max_length = value

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
    def resolve_project_id(cls, mainframe: "_ui.MainFrame") -> tuple[str, int] | None:
        """Show the open-project dialog and resolve the chosen name to a
        project id, creating a new project row via ``AddProjectDialog`` if
        the typed name doesn't exist yet.

        Split out of :meth:`select_project` so a caller that needs to
        inspect the resolved id *before* deciding whether to construct a
        new :class:`Project` (e.g. :meth:`harness_designer.ui.mainframe.
        MainFrame.load_project`, which no-ops if the user picked the
        project that's already open) can reuse the exact same picking/
        creation flow without duplicating it.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :returns: ``(project_name, project_id)``, or ``None`` if the user
            canceled.
        :rtype: tuple[str, int] | None
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
            if res != QtWidgets.QDialog.DialogCode.Rejected:
                project_name = dlg.GetValue()
            else:
                return None
        finally:
            dlg.deleteLater()
        connector.execute(f'SELECT id FROM projects WHERE name = "{project_name}";')
        res = connector.fetchall()

        if res:
            project_id = res[0][0]
        else:
            from ..ui.dialogs import add_project as _add_project

            dlg = _add_project.AddProjectDialog(mainframe, project_name, mainframe.project_db.projects_table)
            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:

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
                return cls.resolve_project_id(mainframe)

        return project_name, project_id

    @classmethod
    def select_project(cls, mainframe: "_ui.MainFrame") -> "Project":
        """Execute the select project operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Project`
        """
        resolved = cls.resolve_project_id(mainframe)
        if resolved is None:
            return

        project_name, project_id = resolved

        db_obj = mainframe.project_db.projects_table[project_id]

        Config.last_project = project_name

        return cls(mainframe, db_obj, project_name, project_id)

    def delete_note(self, db_id):
        """Delete the note.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_id: Identifier for the database.
        :type db_id: UNKNOWN
        """
        if self._notes.pop(db_id, None) is not None:
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
        if self._seals.pop(db_id, None) is not None:
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
        if self._terminals.pop(db_id, None) is not None:
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
        if self._cavities.pop(db_id, None) is not None:
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
        if self._tpa_locks.pop(db_id, None) is not None:
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
        if self._wire_markers.pop(db_id, None) is not None:
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
        if self._wire_service_loops.pop(db_id, None) is not None:
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
        if self._cpa_locks.pop(db_id, None) is not None:
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
        if self._covers.pop(db_id, None) is not None:
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
        if self._boots.pop(db_id, None) is not None:
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
        if self._transitions.pop(db_id, None) is not None:
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
        if self._housings.pop(db_id, None) is not None:
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
        if self._splices.pop(db_id, None) is not None:
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
        if self._wires.pop(db_id, None) is not None:
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
        if self._wire_layouts.pop(db_id, None) is not None:
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
        if self._bundles.pop(db_id, None) is not None:
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
        if self._bundle_layouts.pop(db_id, None) is not None:
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
