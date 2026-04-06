from typing import TYPE_CHECKING
import wx

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
# from . import wire2d_layout as _wire2d_layout
# from . import wire3d_layout as _wire3d_layout

from ..geometry import point as _point
from ..geometry import angle as _angle
from ..geometry import line as _line
from ..geometry.decimal import Decimal as _d
from .. import config as _config


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.global_db import wire_marker as _wire_marker_part
    from ..database.global_db import transition as _transition_part
    from ..database.global_db import bundle_cover as _bundle_cover_part
    from ..database.global_db import splice as _splice_part
    from ..database.global_db import wire as _wire_part
    from ..database.global_db import seal as _seal_part
    from ..database.global_db import terminal as _terminal_part

    from ..database.project_db import project as _project


Config = _config.Config.project


class Project:

    def __init__(self, mainframe: "_ui.MainFrame", db_obj: "_project.Project", project_name: str, project_id: int):
        self.db_obj = db_obj
        db_obj.set_object(self)

        self.mainframe = mainframe
        self.gtables = mainframe.global_db
        self.connector = mainframe.db_connector
        self.project_id = project_id
        self.project_name = project_name
        self.ptables = ptables = mainframe.project_db
        self.connector.monitor.reset()
        ptables.load(project_id)
        mainframe.object_browser.reset()

        for table in (
            self.ptables.pjt_boots_table,
            self.ptables.pjt_bundle_layouts_table,
            self.ptables.pjt_bundles_table,
            self.ptables.pjt_cavities_table,
            self.ptables.pjt_circuits_table,
            self.ptables.pjt_concentric_layers_table,
            self.ptables.pjt_concentric_wires_table,
            self.ptables.pjt_concentrics_table,
            self.ptables.pjt_covers_table,
            self.ptables.pjt_cpa_locks_table,
            self.ptables.pjt_housings_table,
            self.ptables.pjt_notes_table,
            self.ptables.pjt_points2d_table,
            self.ptables.pjt_points3d_table,
            self.ptables.pjt_seals_table,
            self.ptables.pjt_splices_table,
            self.ptables.pjt_terminals_table,
            self.ptables.pjt_tpa_locks_table,
            self.ptables.pjt_transition_branches_table,
            self.ptables.pjt_transitions_table,
            self.ptables.pjt_wire3d_layouts_table,
            self.ptables.pjt_wire_markers_table,
            self.ptables.pjt_wire_service_loops_table,
            self.ptables.pjt_wires_table
        ):
            kwargs = {f'field_names_{table.table_name}': table.field_names}
            self.connector.monitor.send(**kwargs)

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
        self._wire2d_layouts = {}
        self._wire3d_layouts = {}
        self._circuits = {}

        self._obj_count = mainframe.project_db.projects_table.get_object_count(project_id)

        db_ids = {}

        for wire_service_loop in ptables.pjt_wire_service_loops_table:
            with self.mainframe.editor3d.context:
                obj = _wire_service_loop.WireServiceLoop(mainframe, wire_service_loop)

            wire_service_loop.merge_packet_data(wire_service_loop.build_monitor_packet(), db_ids)

            self._wire_service_loops[wire_service_loop.db_id] = obj
            mainframe.object_browser.add_wire_service_loop(obj)

        for wire_marker in ptables.pjt_wire_markers_table:
            with self.mainframe.editor3d.context:
                obj = _wire_marker.WireMarker(mainframe, wire_marker)

            wire_marker.merge_packet_data(wire_marker.build_monitor_packet(), db_ids)

            self._wire_markers[wire_marker.db_id] = obj
            mainframe.object_browser.add_wire_marker(obj)

        for note in ptables.pjt_notes_table:
            with self.mainframe.editor3d.context:
                obj = _note.Note(mainframe, note)

            note.merge_packet_data(note.build_monitor_packet(), db_ids)

            self._notes[note.db_id] = obj
            mainframe.object_browser.add_note(obj)

        for circuit in ptables.pjt_circuits_table:
            with self.mainframe.editor3d.context:
                obj = _circuit.Circuit(mainframe, circuit)

            circuit.merge_packet_data(circuit.build_monitor_packet(), db_ids)
            self._circuits[circuit.db_id] = obj
            mainframe.object_browser.add_circuit(obj)

        for boot in ptables.pjt_boots_table:
            with self.mainframe.editor3d.context:
                obj = _boot.Boot(mainframe, boot)

            boot.merge_packet_data(boot.build_monitor_packet(), db_ids)
            self._boots[boot.db_id] = obj
            mainframe.object_browser.add_boot(obj)

        for cover in ptables.pjt_covers_table:
            with self.mainframe.editor3d.context:
                obj = _cover.Cover(mainframe, cover)

            cover.merge_packet_data(cover.build_monitor_packet(), db_ids)
            self._covers[cover.db_id] = obj
            mainframe.object_browser.add_cover(obj)

        for cpa_lock in ptables.pjt_cpa_locks_table:
            with self.mainframe.editor3d.context:
                obj = _cpa_lock.CPALock(mainframe, cpa_lock)

            cpa_lock.merge_packet_data(cpa_lock.build_monitor_packet(), db_ids)
            self._cpa_locks[cpa_lock.db_id] = obj
            mainframe.object_browser.add_cpa_lock(obj)

        for tpa_lock in ptables.pjt_tpa_locks_table:
            with self.mainframe.editor3d.context:
                obj = _tpa_lock.TPALock(mainframe, tpa_lock)

            tpa_lock.merge_packet_data(tpa_lock.build_monitor_packet(), db_ids)
            self._tpa_locks[tpa_lock.db_id] = obj
            mainframe.object_browser.add_tpa_lock(obj)

        for seal in ptables.pjt_seals_table:
            with self.mainframe.editor3d.context:
                obj = _seal.Seal(mainframe, seal)

            seal.merge_packet_data(seal.build_monitor_packet(), db_ids)
            self._seals[seal.db_id] = obj
            mainframe.object_browser.add_seal(obj)

        for terminal in ptables.pjt_terminals_table:
            with self.mainframe.editor3d.context:
                obj = _terminal.Terminal(mainframe, terminal)

            terminal.merge_packet_data(terminal.build_monitor_packet(), db_ids)
            self._terminals[terminal.db_id] = obj
            mainframe.object_browser.add_terminal(obj)

        for transition in ptables.pjt_transitions_table:
            with self.mainframe.editor3d.context:
                obj = _transition.Transition(mainframe, transition)

            transition.merge_packet_data(transition.build_monitor_packet(), db_ids)
            self._transitions[transition.db_id] = obj
            mainframe.object_browser.add_transition(obj)

        for housing in ptables.pjt_housings_table:
            with self.mainframe.editor3d.context:
                obj = _housing.Housing(mainframe, housing)

            housing.merge_packet_data(housing.build_monitor_packet(), db_ids)
            self._housings[housing.db_id] = obj
            mainframe.object_browser.add_housing(obj)

        for splice in ptables.pjt_splices_table:
            with self.mainframe.editor3d.context:
                obj = _splice.Splice(mainframe, splice)

            splice.merge_packet_data(splice.build_monitor_packet(), db_ids)
            self._splices[splice.db_id] = obj
            mainframe.object_browser.add_splice(obj)

        for wire in ptables.pjt_wires_table:
            with self.mainframe.editor3d.context:
                obj = _wire.Wire(mainframe, wire)

            wire.merge_packet_data(wire.build_monitor_packet(), db_ids)
            self._wires[wire.db_id] = obj
            mainframe.object_browser.add_wire(obj)

        #
        # for layout in ptables.pjt_wire2d_layouts_table:
        #     mainframe.IncrementProgress()
        #     self._wire2d_layouts[layout.db_id] = (
        #         _wire2d_layout.Wire2DLayout(mainframe, layout))
        #
        #     layout.merge_packet_data(layout.build_monitor_packet(), db_ids)
        #
        # for layout in ptables.pjt_wire3d_layouts_table:
        #     mainframe.IncrementProgress()
        #     self._wire3d_layouts[layout.db_id] = (
        #         _wire3d_layout.Wire3DLayout(mainframe, layout))
        #
        #     layout.merge_packet_data(layout.build_monitor_packet(), db_ids)

        for bundle in ptables.pjt_bundles_table:
            with self.mainframe.editor3d.context:
                obj = _bundle.Bundle(mainframe, bundle)

            bundle.merge_packet_data(bundle.build_monitor_packet(), db_ids)
            self._bundles[bundle.db_id] = obj
            mainframe.object_browser.add_bundle(obj)

        for layout in ptables.pjt_bundle_layouts_table:
            with self.mainframe.editor3d.context:
                obj = _bundle_layout.BundleLayout(mainframe, layout)

            layout.merge_packet_data(layout.build_monitor_packet(), db_ids)
            self._bundle_layouts[layout.db_id] = obj

        for table_name, ids in db_ids.items():
            kwargs = {f'add_{table_name}': ids}
            self.connector.monitor.send(**kwargs)

    @property
    def obj_count(self) -> int:
        return self._obj_count

    @obj_count.setter
    def obj_count(self, value: int):
        self._obj_count = value
        self.ptables.projects_table.set_object_count(self.project_id, value)

    @classmethod
    def select_project(cls, mainframe: "_ui.MainFrame") -> "Project":
        from ..ui.dialogs.project_dialog import OpenProjectDialog

        connector = mainframe.db_connector

        project_names = []

        connector.execute(f'SELECT name FROM projects;')
        for name in connector.fetchall():
            project_names.append(name[0])

        dlg = OpenProjectDialog(mainframe, Config.recent_projects, project_names)

        try:
            if dlg.ShowModal() != wx.ID_CANCEL:
                project_name = dlg.GetValue()
            else:
                return
        finally:
            dlg.Destroy()

        connector.execute(f'SELECT id FROM projects WHERE name = "{project_name}";')
        res = connector.fetchall()

        if res:
            project_id = res[0][0]
        else:
            from ..ui.dialogs import add_project as _add_project

            dlg = _add_project.AddProjectDialog(mainframe, project_name, mainframe.project_db.projects_table)
            if dlg.ShowModal() == wx.ID_OK:

                project_name, creator, description, model_path = dlg.GetValue()

                connector.execute(f'INSERT INTO projects (name, creator, description, user_model) VALUES (?, ?, ?, ?);',
                                  (project_name, creator, description, model_path))
                connector.commit()
                project_id = connector.lastrowid
            else:
                return cls.select_project(mainframe)

        db_obj = mainframe.project_db.projects_table[project_id]

        return cls(mainframe, db_obj, project_name, project_id)

    def delete_note(self, db_id):
        note = self._notes.pop(db_id)
        note.delete()
        self.obj_count -= 1

    def add_note(self, note: str,  position2d: _point.Point = None,
                 position3d: _point.Point = None) -> _note.Note:

        if not note:
            note = 'NEW NOTE'

        if position2d is None:
            position2d_id = None
        else:
            position2d_id = self.ptables.pjt_points2d_table.insert(
                position2d.x, position2d.y).db_id

        if position3d is None:
            position3d_id = None
        else:
            position3d_id = self.ptables.pjt_points3d_table.insert(
                position3d.x, position3d.y, position3d.z).db_id

        db_obj = self.ptables.pjt_notes_table.insert(
            position2d_id, position3d_id, note, 1)

        new_obj = _note.Note(self.mainframe, db_obj)
        self._notes[db_obj.db_id] = new_obj

        self.obj_count += 1
        return new_obj

    def get_note(self, db_id) -> _note.Note:
        db_obj = self.ptables.pjt_notes_table[db_id]
        return db_obj.get_object()

    @property
    def notes(self) -> list["_note.Note"]:
        return list(self._notes.values())

    def delete_seal(self, db_id):
        seal = self._seals.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_seal(self, part_id: int,  position3d: _point.Point) -> _seal.Seal:
        position3d_id = int(position3d.db_id[:-2])

        c_table = self.ptables.pjt_cavities_table
        t_table = self.ptables.pjt_terminals_table
        h_table = self.ptables.pjt_housings_table

        cavity = c_table.get_from_position3d_id(position3d_id)
        if cavity is None:
            cavity_id = None

            terminal = t_table.get_from_position3d_id(position3d_id)
            if terminal is None:
                terminal_id = None

                housing = h_table.get_from_position3d_id(position3d_id)

                housing_id = housing.db_id
            else:
                terminal_id = terminal.db_id
                housing_id = None
        else:
            cavity_id = cavity.db_id
            terminal_id = None
            housing_id = None

        db_obj = self.ptables.pjt_seals_table.insert(
            part_id, position3d_id, housing_id=housing_id,
            terminal_id=terminal_id, cavity_id=cavity_id)

        new_obj = _seal.Seal(self.mainframe, db_obj)
        self._seals[db_obj.db_id] = new_obj

        self.obj_count += 1
        return new_obj

    def get_seal(self, db_id) -> _seal.Seal:
        db_obj = self.ptables.pjt_seals_table[db_id]
        return db_obj.get_object()

    @property
    def seals(self) -> list["_seal.Seal"]:
        return list(self._seals.values())

    def delete_terminal(self, db_id):
        seal = self._terminals.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_terminal(self, part_id: int, position2d: _point.Point = None,
                     position3d: _point.Point = None) -> _terminal.Terminal:

        c_table = self.ptables.pjt_cavities_table

        if position2d is None:

            position3d_id = int(position3d.db_id[:-2])
            cavity = c_table.get_from_position3d_id(position3d_id)

            position2d_id = cavity.position2d_id
            position3d_id = cavity.terminal_position3d_id

        else:
            position2d_id = int(position2d.db_id[:-2])
            cavity = c_table.get_from_position2d_id(position2d_id)

            position3d_id = cavity.terminal_position3d_id

        db_obj = self.ptables.pjt_terminals_table.insert(part_id, position2d_id, position3d_id, cavity.db_id)

        with self.mainframe.editor3d.context:
            obj = _terminal.Terminal(self.mainframe, db_obj)

        self._terminals[db_obj.db_id] = obj

        self.obj_count += 1
        return obj

    def get_terminal(self, db_id) -> _terminal.Terminal:
        db_obj = self.ptables.pjt_terminals_table[db_id]
        return db_obj.get_object()

    @property
    def terminals(self) -> list["_terminal.Terminal"]:
        return list(self._terminals.values())

    def delete_tpa_lock(self, db_id):
        seal = self._tpa_locks.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_tpa_lock(self, part_id: int, position3d: _point.Point) -> _tpa_lock.TPALock:
        position_id = housing.obj3d.db_obj.tpa_lock_1_position3d_id

        db_obj = self.ptables.pjt_tpa_locks_table.insert(
            part_id, position_id, housing.db_obj.db_id)

        with self.mainframe.editor3d.context:
            obj = _tpa_lock.TPALock(self.mainframe, db_obj)

        self._tpa_locks[db_obj.db_id] = obj

        self.obj_count += 1
        return obj

    def get_tpa_lock(self, db_id) -> _tpa_lock.TPALock:
        db_obj = self.ptables.pjt_tpa_locks_table[db_id]
        return db_obj.get_object()

    @property
    def tpa_locks(self) -> list["_tpa_lock.TPALock"]:
        return list(self._tpa_locks.values())

    def delete_wire_marker(self, db_id):
        seal = self._wire_markers.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire_marker(self, part_id: int, position2d: _point.Point = None,
                        position3d: _point.Point = None) -> _wire_marker.WireMarker:

        if point.is2d:
            p_db_obj = self.ptables.pjt_points2d_table.insert(point.x, point.y)
            wm_db_obj = self.ptables.pjt_wire_markers_table.insert(p_db_obj.db_id, None, wire.db_obj.db_id, part.db_id, '')
        else:
            p_db_obj = self.ptables.pjt_points3d_table.insert(point.x, point.y, point.z)
            wm_db_obj = self.ptables.pjt_wire_markers_table.insert(None, p_db_obj.db_id, wire.db_obj.db_id, part.db_id, '')

        new_obj = _wire_marker.WireMarker(self.mainframe, wm_db_obj)
        self._wire_markers[wm_db_obj.db_id] = new_obj
        self.obj_count += 1
        return new_obj

    def get_wire_marker(self, db_id) -> _wire_marker.WireMarker:
        db_obj = self.ptables.pjt_wire_markers_table[db_id]
        return db_obj.get_object()

    @property
    def wire_markers(self) -> list["_wire_marker.WireMarker"]:
        return list(self._wire_markers.values())

    def delete_wire_service_loop(self, db_id):
        seal = self._wire_service_loops.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire_service_loop(self, part_id: int,  position3d: _point.Point) -> _wire_service_loop.WireServiceLoop:
        from .objects3d import wire

        start_point = obj.db_obj.start_position3d
        stop_point = obj.db_obj.stop_position3d
        if start_point == point:
            angle = _angle.Angle.from_points(stop_point, start_point)
            point = start_point
            p_db_obj = obj.db_obj.start_position3d
        else:
            angle = _angle.Angle.from_points(start_point, stop_point)
            point = stop_point
            p_db_obj = obj.db_obj.stop_position3d

        part = obj.db_obj.part
        diameter = part.od_mm

        # stop point is an approximation not an exact.
        # this will get corrected when the wire loop gets rendered
        lsp = _point.Point(0.0, 0.0, -diameter)
        lsp += _point.Point(diameter + diameter * 0.133, 0.0, 0.0)
        lsp += _point.Point(0.0, -(diameter * 0.0195), 0.0)
        lsp += _point.Point(0.0, 0.0, -(diameter * 0.15))
        lsp += _point.Point(0.0, 0.0, -diameter)

        lsp @= angle
        lsp += point

        lsp_db_obj = self.ptables.pjt_points3d_table.insert(lsp.x, lsp.y, lsp.z)

        loop_db_obj = self.ptables.pjt_wire_service_loops_table.insert(
            p_db_obj.db_id, lsp_db_obj.db_id,  part.db_id, obj.db_obj.circuit_id, True, angle.as_quat)

        new_obj = _wire_service_loop.WireServiceLoop(self.mainframe, loop_db_obj)

        self._wire_service_loops[loop_db_obj.db_id] = new_obj
        self.obj_count += 1
        return new_obj

    def get_wire_service_loop(self, db_id) -> _wire_service_loop.WireServiceLoop:
        db_obj = self.ptables.pjt_wire_service_loops_table[db_id]
        return db_obj.get_object()

    @property
    def wire_service_loops(self) -> list["_wire_service_loop.WireServiceLoop"]:
        return list(self._wire_service_loops.values())

    @property
    def circuits(self) -> list["_circuit.Circuit"]:
        return list(self._circuits.values())

    def delete_cpa_lock(self, db_id):
        seal = self._cpa_locks.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_cpa_lock(self, part_id: int,  position3d: _point.Point) -> _cpa_lock.CPALock:
        position_id = housing.obj3d.db_obj.cpa_lock_position3d_id

        db_obj = self.ptables.pjt_cpa_locks_table.insert(
            part_id, position_id, housing.db_obj.db_id)

        with self.mainframe.editor3d.context:
            obj = _cpa_lock.CPALock(self.mainframe, db_obj)

        self._cpa_locks[db_obj.db_id] = obj

        self.obj_count += 1
        return obj

    def get_cpa_lock(self, db_id) -> _cpa_lock.CPALock:
        db_obj = self.ptables.pjt_cpa_locks_table[db_id]
        return db_obj.get_object()

    @property
    def cpa_locks(self) -> list["_cpa_lock.CPALock"]:
        return list(self._cpa_locks.values())

    def delete_cover(self, db_id):
        seal = self._covers.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_cover(self, part_id: int,  position3d: _point.Point) -> _cover.Cover:
        position_id = housing.obj3d.db_obj.cover_position3d_id

        db_obj = self.ptables.pjt_covers_table.insert(
            part_id, position_id, housing.db_obj.db_id)

        with self.mainframe.editor3d.context:
            obj = _cover.Cover(self.mainframe, db_obj)

        self._covers[db_obj.db_id] = obj

        self.obj_count += 1
        return obj

    def get_cover(self, db_id) -> _cover.Cover:
        db_obj = self.ptables.pjt_covers_table[db_id]
        return db_obj.get_object()

    @property
    def covers(self) -> list["_cover.Cover"]:
        return list(self._covers.values())

    def delete_boot(self, db_id):
        seal = self._boots.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_boot(self, part_id: int,  position3d: _point.Point) -> _boot.Boot:

        position_id = housing.obj3d.db_obj.boot_position3d_id

        db_obj = self.ptables.pjt_boots_table.insert(
            part_id, position_id, housing.db_obj.db_id)

        with self.mainframe.editor3d.context:
            obj = _boot.Boot(self.mainframe, db_obj)

        self._boots[db_obj.db_id] = obj

        self.obj_count += 1
        return obj

    def get_boot(self, db_id) -> _boot.Boot:
        db_obj = self.ptables.pjt_boots_table[db_id]
        return db_obj.get_object()

    @property
    def boots(self) -> list["_boot.Boot"]:
        return list(self._boots.values())

    def delete_transition(self, db_id):
        seal = self._transitions.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_transition(self, part_id: int,  position3d: _point.Point) -> _transition.Transition:

        '''
        part_id: int, center_id: int, angle: _angle.Angle, name: str,
               branch1_id: int | None, branch2_id: int | None,
               branch3_id: int | None, branch4_id: int | None,
               branch5_id: int | None, branch6_id: int | None,
               branch1dia: _decimal | None, branch2dia: _decimal | None,
               branch3dia: _decimal | None, branch4dia: _decimal | None,
               branch5dia: _decimal | None, branch6dia: _decimal | None
        '''
        
        cpa_db_obj = self.ptables.pjt_transitions_table.insert(
            point.point_id, housing.db_obj.db_id, part.db_id)
        
        new_obj = _transition.Transition(self.mainframe, cpa_db_obj)
        self._transitions[cpa_db_obj.db_id] = new_obj

        self.obj_count += 1
        return new_obj

    def get_transition(self, db_id) -> _transition.Transition:
        db_obj = self.ptables.pjt_transitions_table[db_id]
        return db_obj.get_object()

    @property
    def transitions(self) -> list["_transition.Transition"]:
        return list(self._transitions.values())

    def delete_housing(self, db_id):
        housing = self._housings.pop(db_id)
        housing.delete()
        self.obj_count -= 1

    def add_housing(self, part_id: int, position2d: _point.Point = None,
                   position3d: _point.Point = None) -> _housing.Housing:
        housing = self.ptables.pjt_housings_table.insert(part_id, position2d=position2d, position3d=position3d)

        with self.mainframe.editor3d.context:
            obj = _housing.Housing(self.mainframe, housing)

        self._housings[housing.db_id] = obj
        self.obj_count += 1

        return obj

    def get_housing(self, db_id) -> _housing.Housing:
        db_obj = self.ptables.pjt_housings_table[db_id]
        return db_obj.get_object()

    @property
    def housings(self) -> list["_housing.Housing"]:
        return list(self._housings.values())

    def delete_splice(self, db_id):
        seal = self._splices.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_splice(self, part_id: int, position2d: _point.Point = None,
                   position3d: _point.Point = None) -> _splice.Splice:
        pass

    def get_splice(self, db_id) -> _splice.Splice:
        db_obj = self.ptables.pjt_splices_table[db_id]
        return db_obj.get_object()

    @property
    def splices(self) -> list["_splice.Splice"]:
        return list(self._splices.values())

    def delete_wire(self, db_id):
        seal = self._wires.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire(self, part_id: int, position2d: _point.Point = None,
                 position3d: _point.Point = None) -> _wire.Wire:
        pass

    def get_wire(self, db_id) -> _wire.Wire:
        db_obj = self.ptables.pjt_wires_table[db_id]
        return db_obj.get_object()

    @property
    def wires(self) -> list["_wire.Wire"]:
        return list(self._wires.values())

    def delete_wire2d_layout(self, db_id):
        seal = self._wire2d_layouts.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire2d_layout(self, point) -> "_wire2d_layout.Wire2DLayout":
        pass

    @property
    def wire2d_layouts(self) -> list["_wire2d_layout.Wire2DLayout"]:
        return list(self._wire2d_layouts.values())

    def delete_wire3d_layout(self, db_id):
        seal = self._wire3d_layouts.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire3d_layout(self, point) -> "_wire3d_layout.Wire3DLayout":
        pass

    @property
    def wire3d_layouts(self) -> list["_wire3d_layout.Wire3DLayout"]:
        return list(self._wire3d_layouts.values())

    def delete_bundle(self, db_id):
        seal = self._bundles.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_bundle(self, part_id: int, position3d: _point.Point) -> _bundle.Bundle:
        pass

    def get_bundle(self, db_id) -> _bundle.Bundle:
        db_obj = self.ptables.pjt_bundles_table[db_id]
        return db_obj.get_object()

    @property
    def bundles(self) -> list["_bundle.Bundle"]:
        return list(self._bundles.values())

    def delete_bundle_layout(self, db_id):
        seal = self._bundle_layouts.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_bundle_layout(self, point) -> _bundle_layout.BundleLayout:
        pass

    @property
    def bundle_layouts(self) -> list["_bundle_layout.BundleLayout"]:
        return list(self._bundle_layouts.values())

    @property
    def recent_projects(self) -> list:
        return Config.recent_projects[:]
