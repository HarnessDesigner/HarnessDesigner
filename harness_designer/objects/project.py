from typing import TYPE_CHECKING
import wx

from ..config import Config as _Config

from . import boot as _boot
from . import bundle as _bundle
from . import bundle_layout as _bundle_layout
from . import circuit as _circuit
from . import cover as _cover
from . import cpa_lock as _cpa_lock
from . import housing as _housing
from . import note as _note
from . import seal as _seal
from . import splice as _splice
from . import terminal as _terminal
from . import tpa_lock as _tpa_lock
from . import transition as _transition
from . import wire as _wire
from . import wire_marker as _wire_marker
from . import wire_service_loop as _wire_service_loop
from . import wire2d_layout as _wire2d_layout
from . import wire3d_layout as _wire3d_layout

from ..geometry import point as _point
from ..geometry import angle as _angle
from ..geometry import line as _line
from .. import Config

from ..wrappers.decimal import Decimal as _decimal

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.global_db import wire_marker as _wire_marker_part
    from ..database.global_db import transition as _transition_part
    from ..database.global_db import tpa_lock as _tpa_lock_part
    from ..database.global_db import cpa_lock as _cpa_lock_part
    from ..database.global_db import boot as _boot_part
    from ..database.global_db import bundle_cover as _bundle_cover_part
    from ..database.global_db import splice as _splice_part
    from ..database.global_db import wire as _wire_part
    from ..database.global_db import seal as _seal_part
    from ..database.global_db import cover as _cover_part
    from ..database.global_db import housing as _housing_part
    from ..database.global_db import terminal as _terminal_part


Config = Config.project


class Project:

    def __init__(self, mainframe: "_ui.MainFrame", project_name: str, project_id: int):
        self.mainframe = mainframe
        self.gtables = mainframe.global_db
        self.connector = mainframe.db_connector
        self.project_id = project_id
        self.project_name = project_name
        self.ptables = ptables = mainframe.project_db

        ptables.load(project_id)

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

        mainframe.ShowProgress(self._obj_count)

        for wire_service_loop in ptables.pjt_wire_service_loops_table:
            mainframe.IncrementProgress()
            self._wire_service_loops[wire_service_loop.db_id] = (
                _wire_service_loop.WireServiceLoop(mainframe, wire_service_loop))

        for wire_marker in ptables.pjt_wire_markers_table:
            mainframe.IncrementProgress()
            self._wire_markers[wire_marker.db_id] = (
                _wire_marker.WireMarker(mainframe, wire_marker))

        for note in ptables.pjt_notes_table:
            mainframe.IncrementProgress()
            self._notes[note.db_id] = _note.Note(mainframe, note)

        for circuit in ptables.pjt_circuits_table:
            mainframe.IncrementProgress()
            self._circuits[circuit.db_id] = (
                _circuit.Circuit(mainframe, circuit))

        for boot in ptables.pjt_boots_table:
            mainframe.IncrementProgress()
            self._boots[boot.db_id] = _boot.Boot(mainframe, boot)

        for cover in ptables.pjt_covers_table:
            mainframe.IncrementProgress()
            self._covers[cover.db_id] = _cover.Cover(mainframe, cover)

        for cpa_lock in ptables.pjt_cpa_locks_table:
            mainframe.IncrementProgress()
            self._cpa_locks[cpa_lock.db_id] = (
                _cpa_lock.CPALock(mainframe, cpa_lock))

        for tpa_lock in ptables.pjt_tpa_locks_table:
            mainframe.IncrementProgress()
            self._tpa_locks[tpa_lock.db_id] = (
                _tpa_lock.TPALock(mainframe, tpa_lock))

        for seal in ptables.pjt_seals_table:
            mainframe.IncrementProgress()
            self._seals[seal.db_id] = _seal.Seal(mainframe, seal)

        for terminal in ptables.pjt_terminals_table:
            mainframe.IncrementProgress()
            self._terminals[terminal.db_id] = (
                _terminal.Terminal(mainframe, terminal))

        for transition in ptables.pjt_transitions_table:
            mainframe.IncrementProgress()
            self._transitions[transition.db_id] = (
                _transition.Transition(mainframe, transition))

        for housing in ptables.pjt_housings_table:
            mainframe.IncrementProgress()
            self._housings[housing.db_id] = (
                _housing.Housing(mainframe, housing))

        for splice in ptables.pjt_splices_table:
            mainframe.IncrementProgress()
            self._splices[splice.db_id] = _splice.Splice(mainframe, splice)

        for wire in ptables.pjt_wires_table:
            mainframe.IncrementProgress()
            self._wires[wire.db_id] = _wire.Wire(mainframe, wire)

        for layout in ptables.pjt_wire2d_layouts_table:
            mainframe.IncrementProgress()
            self._wire2d_layouts[layout.db_id] = (
                _wire2d_layout.Wire2DLayout(mainframe, layout))

        for layout in ptables.pjt_wire3d_layouts_table:
            mainframe.IncrementProgress()
            self._wire3d_layouts[layout.db_id] = (
                _wire3d_layout.Wire3DLayout(mainframe, layout))

        for bundle in ptables.pjt_bundles_table:
            mainframe.IncrementProgress()
            self._bundles[bundle.db_id] = _bundle.Bundle(mainframe, bundle)

        for layout in ptables.pjt_bundle_layouts_table:
            mainframe.IncrementProgress()
            self._bundle_layouts[layout.db_id] = (
                _bundle_layout.BundleLayout(mainframe, layout))

        mainframe.IncrementProgress()

    @property
    def obj_count(self) -> int:
        return self._obj_count

    @obj_count.setter
    def obj_count(self, value: int):
        self._obj_count = value
        self.ptables.projects_table.set_object_count(self.project_id, value)

    @classmethod
    def select_project(cls, mainframe: "_ui.MainFrame") -> "Project":
        from ..dialogs.project_dialog import OpenProjectDialog

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
            connector.execute(f'INSERT INTO projects (name) VALUES (?);', (project_name,))
            connector.commit()
            project_id = connector.lastrowid

        return cls(mainframe, project_name, project_id)

    def delete_note(self, db_id):
        note = self._notes.pop(db_id)
        note.delete()
        self.obj_count -= 1

    def add_note(self, point: _point.Point) -> _note.Note:
        if point.is2d:
            p_db_obj = self.ptables.pjt_points2d_table.insert(point.x, point.y)
            note_db_obj = self.ptables.pjt_notes_table.insert(p_db_obj.db_id, None, 'NEW NOTE', 1)

        else:
            p_db_obj = self.ptables.pjt_points2d_table.insert(point.x, point.y, point.z)
            note_db_obj = self.ptables.pjt_notes_table.insert(None, p_db_obj.db_id, 'NEW NOTE', 1)

        new_obj = _note.Note(self.mainframe, note_db_obj)
        self._notes[note_db_obj.db_id] = new_obj

        self.obj_count += 1
        return new_obj

    @property
    def notes(self) -> list["_note.Note"]:
        return list(self._notes.values())

    def delete_seal(self, db_id):
        seal = self._seals.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_seal(self, point: _point.Point, housing: _housing.Housing, terminal: _terminal.Terminal | None, part: "_seal_part.Seal") -> _seal.Seal:
        if terminal is None:
            terminal_id = None
        else:
            terminal_id = terminal.db_obj.db_id

        seal_db_obj = self.ptables.pjt_seals_table.insert(
            point.point_id, housing.db_obj.db_id, terminal_id, part.db_id)
        new_obj = _seal.Seal(self.mainframe, seal_db_obj)
        self._seals[seal_db_obj.db_id] = new_obj

        self.obj_count += 1
        return new_obj

    @property
    def seals(self) -> list["_seal.Seal"]:
        return list(self._seals.values())

    def delete_terminal(self, db_id):
        seal = self._terminals.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_terminal(self, point: _point.Point, cavity, 
                     part: "_terminal_part.Terminal") -> _terminal.Terminal:
        
        if point.is2d:
            point2d_id = point.point_id
            point3d_id = cavity.point3d.db_id
        else:
            point2d_id = cavity.point2d.db_id
            point3d_id = point.point_id
 
        t_db_obj = self.ptables.pjt_terminals_table.insert(
            part.db_id, cavity.db_id, 0, point3d_id, point2d_id, cavity.angle2d, 
            cavity.angle3d.as_quat, False, _decimal(0.0), _decimal(0.0), _decimal(0.0))
        
        new_obj = _terminal.Terminal(self.mainframe, t_db_obj)
        self._terminals[t_db_obj.db_id] = new_obj
        self.obj_count += 1
        return new_obj

    @property
    def terminals(self) -> list["_terminal.Terminal"]:
        return list(self._terminals.values())

    def delete_tpa_lock(self, db_id):
        seal = self._tpa_locks.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_tpa_lock(self, point: _point.Point, housing: _housing.Housing, 
                     part: "_tpa_lock_part.TPALock") -> _tpa_lock.TPALock:
        
        tpa_db_obj = self.ptables.pjt_tpa_locks_table.insert(
            point.point_id, housing.db_obj.db_id, part.db_id)
        
        new_obj = _tpa_lock.TPALock(self.mainframe, tpa_db_obj)
        self._tpa_locks[tpa_db_obj.db_id] = new_obj

        self.obj_count += 1
        return new_obj

    @property
    def tpa_locks(self) -> list["_tpa_lock.TPALock"]:
        return list(self._tpa_locks.values())

    def delete_wire_marker(self, db_id):
        seal = self._wire_markers.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire_marker(self, point, wire: _wire.Wire, part: "_wire_marker_part.WireMarker") -> _wire_marker.WireMarker:
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

    @property
    def wire_markers(self) -> list["_wire_marker.WireMarker"]:
        return list(self._wire_markers.values())

    def delete_wire_service_loop(self, db_id):
        seal = self._wire_service_loops.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire_service_loop(self, point: _point.Point) -> _wire_service_loop.WireServiceLoop:
        from .objects3d import wire

        for obj in point.objects:
            if isinstance(obj, wire.Wire):
                break
        else:
            raise RuntimeError('sanity check')

        start_point = obj.db_obj.start_point3d.point
        stop_point = obj.db_obj.stop_point3d.point
        if start_point == point:
            angle = _angle.Angle.from_points(stop_point, start_point)
            point = start_point
            p_db_obj = obj.db_obj.start_point3d
        else:
            angle = _angle.Angle.from_points(start_point, stop_point)
            point = stop_point
            p_db_obj = obj.db_obj.stop_point3d

        part = obj.db_obj.part
        diameter = part.od_mm

        # stop point is an approximation not an exact.
        # this will get corrected when the wire loop gets rendered
        lsp = _point.Point(_decimal(0.0), _decimal(0.0), -diameter)
        lsp += _point.Point(diameter + diameter * _decimal(0.133), _decimal(0.0), _decimal(0.0))
        lsp += _point.Point(_decimal(0.0), -(diameter * _decimal(0.0195)), _decimal(0.0))
        lsp += _point.Point(_decimal(0.0), _decimal(0.0), -(diameter * _decimal(0.15)))
        lsp += _point.Point(_decimal(0.0), _decimal(0.0), -diameter)

        lsp @= angle
        lsp += point

        lsp_db_obj = self.ptables.pjt_points3d_table.insert(lsp.x, lsp.y, lsp.z)

        loop_db_obj = self.ptables.pjt_wire_service_loops_table.insert(
            p_db_obj.db_id, lsp_db_obj.db_id,  part.db_id, obj.db_obj.circuit_id, True, angle.as_quat)

        new_obj = _wire_service_loop.WireServiceLoop(self.mainframe, loop_db_obj)

        self._wire_service_loops[loop_db_obj.db_id] = new_obj
        self.obj_count += 1
        return new_obj

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

    def add_cpa_lock(self, point: _point.Point, housing: _housing.Housing, 
                     part: "_cpa_lock_part.CPALock") -> _cpa_lock.CPALock:
        
        cpa_db_obj = self.ptables.pjt_cpa_locks_table.insert(
            point.point_id, housing.db_obj.db_id, part.db_id)
        
        new_obj = _cpa_lock.CPALock(self.mainframe, cpa_db_obj)
        self._cpa_locks[cpa_db_obj.db_id] = new_obj

        self.obj_count += 1
        return new_obj

    @property
    def cpa_locks(self) -> list["_cpa_lock.CPALock"]:
        return list(self._cpa_locks.values())

    def delete_cover(self, db_id):
        seal = self._covers.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_cover(self, point: _point.Point, housing: _housing.Housing, 
                  part: "_cover_part.Cover") -> _cover.Cover:
        
        cpa_db_obj = self.ptables.pjt_covers_table.insert(
            point.point_id, housing.db_obj.db_id, part.db_id)
        
        new_obj = _cover.Cover(self.mainframe, cpa_db_obj)
        self._covers[cpa_db_obj.db_id] = new_obj

        self.obj_count += 1
        return new_obj

    @property
    def covers(self) -> list["_cover.Cover"]:
        return list(self._covers.values())

    def delete_boot(self, db_id):
        seal = self._boots.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_boot(self, point: _point.Point, housing: _housing.Housing, 
                 part: "_boot_part.Boot") -> _boot.Boot:
        
        cpa_db_obj = self.ptables.pjt_boots_table.insert(
            point.point_id, housing.db_obj.db_id, part.db_id)
        
        new_obj = _boot.Boot(self.mainframe, cpa_db_obj)
        self._boots[cpa_db_obj.db_id] = new_obj

        self.obj_count += 1
        return new_obj

    @property
    def boots(self) -> list["_boot.Boot"]:
        return list(self._boots.values())

    def delete_transition(self, db_id):
        seal = self._transitions.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_transition(self, point: _point.Point, housing: _housing.Housing, 
                       part: "_transition_part.Transition") -> _transition.Transition:

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

    @property
    def transitions(self) -> list["_transition.Transition"]:
        return list(self._transitions.values())

    def delete_housing(self, db_id):
        seal = self._housings.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_housing(self, point: _point.Point, part: "_housing_part.Housing") -> _housing.Housing:
        pass

    @property
    def housings(self) -> list["_housing.Housing"]:
        return list(self._housings.values())

    def delete_splice(self, db_id):
        seal = self._splices.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_splice(self, point: _point.Point, part: "_splice_part.Splice") -> _splice.Splice:
        pass

    @property
    def splices(self) -> list["_splice.Splice"]:
        return list(self._splices.values())

    def delete_wire(self, db_id):
        seal = self._wires.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire(self, point: _point.Point, part: "_wire_part.Wire") -> _wire.Wire:
        pass

    @property
    def wires(self) -> list["_wire.Wire"]:
        return list(self._wires.values())

    def delete_wire2d_layout(self, db_id):
        seal = self._wire2d_layouts.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire2d_layout(self, point) -> _wire2d_layout.Wire2DLayout:
        pass

    @property
    def wire2d_layouts(self) -> list["_wire2d_layout.Wire2DLayout"]:
        return list(self._wire2d_layouts.values())

    def delete_wire3d_layout(self, db_id):
        seal = self._wire3d_layouts.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_wire3d_layout(self, point) -> _wire3d_layout.Wire3DLayout:
        pass

    @property
    def wire3d_layouts(self) -> list["_wire3d_layout.Wire3DLayout"]:
        return list(self._wire3d_layouts.values())

    def delete_bundle(self, db_id):
        seal = self._bundles.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_bundle(self, point: _point.Point, part: "_bundle_cover_part.BundleCover") -> _bundle.Bundle:
        pass

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
